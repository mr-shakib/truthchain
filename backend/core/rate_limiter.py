"""
Rate Limiter for TruthChain API

Implements distributed rate limiting using Redis with sliding window algorithm.
Supports per-organization rate limiting with configurable windows and limits.
"""

import time
from typing import Optional, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel
import redis.asyncio as redis
from ..config.settings import get_settings


class RateLimitConfig(BaseModel):
    """Rate limit configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    
    def __init__(self, tier: str = "free", **kwargs):
        """Initialize rate limits based on organization tier"""
        # Default limits by tier
        tier_limits = {
            "free": {
                "requests_per_minute": 10,
                "requests_per_hour": 100,
                "requests_per_day": 1000
            },
            "startup": {
                "requests_per_minute": 30,
                "requests_per_hour": 500,
                "requests_per_day": 10000
            },
            "business": {
                "requests_per_minute": 100,
                "requests_per_hour": 2000,
                "requests_per_day": 100000
            },
            "enterprise": {
                "requests_per_minute": 500,
                "requests_per_hour": 10000,
                "requests_per_day": 1000000
            }
        }
        
        # Apply tier-based limits
        limits = tier_limits.get(tier, tier_limits["free"])
        limits.update(kwargs)
        super().__init__(**limits)


class RateLimitResult(BaseModel):
    """Result of a rate limit check"""
    allowed: bool
    limit: int
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None  # Seconds until rate limit resets
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, result: RateLimitResult):
        self.result = result
        self.retry_after = result.retry_after
        super().__init__(f"Rate limit exceeded. Retry after {result.retry_after} seconds.")


class RateLimiter:
    """
    Distributed rate limiter using Redis
    
    Uses sliding window algorithm for accurate rate limiting across
    multiple API servers. Tracks requests per minute, hour, and day.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize rate limiter
        
        Args:
            redis_client: Optional Redis client. If None, creates new connection.
        """
        self.redis_client = redis_client
        self._redis_url = get_settings().REDIS_URL if redis_client is None else None
    
    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client
    
    def _get_key(self, organization_id: str, window: str) -> str:
        """Generate Redis key for rate limit tracking"""
        return f"ratelimit:{organization_id}:{window}"
    
    async def check_rate_limit(
        self,
        organization_id: str,
        config: RateLimitConfig
    ) -> RateLimitResult:
        """
        Check if request is within rate limits
        
        Args:
            organization_id: Organization UUID
            config: Rate limit configuration
            
        Returns:
            RateLimitResult with allowed status and metadata
            
        Raises:
            RateLimitExceeded: If any rate limit is exceeded
        """
        redis_conn = await self._get_redis()
        current_time = int(time.time())
        
        # Check all windows (minute, hour, day)
        windows = [
            ("minute", 60, config.requests_per_minute),
            ("hour", 3600, config.requests_per_hour),
            ("day", 86400, config.requests_per_day)
        ]
        
        for window_name, window_seconds, limit in windows:
            result = await self._check_window(
                redis_conn,
                organization_id,
                window_name,
                window_seconds,
                limit,
                current_time
            )
            
            if not result.allowed:
                raise RateLimitExceeded(result)
        
        # All checks passed - increment counters
        for window_name, window_seconds, limit in windows:
            await self._increment_counter(
                redis_conn,
                organization_id,
                window_name,
                window_seconds,
                current_time
            )
        
        # Return success result (using minute window for response)
        return RateLimitResult(
            allowed=True,
            limit=config.requests_per_minute,
            remaining=await self._get_remaining(
                redis_conn,
                organization_id,
                "minute",
                60,
                config.requests_per_minute,
                current_time
            ),
            reset_at=datetime.fromtimestamp(current_time + 60)
        )
    
    async def _check_window(
        self,
        redis_conn: redis.Redis,
        organization_id: str,
        window_name: str,
        window_seconds: int,
        limit: int,
        current_time: int
    ) -> RateLimitResult:
        """
        Check rate limit for a specific time window
        
        Uses sliding window algorithm:
        1. Remove expired entries (older than window)
        2. Count entries in current window
        3. Check if count < limit
        """
        key = self._get_key(organization_id, window_name)
        
        # Remove expired entries
        cutoff_time = current_time - window_seconds
        await redis_conn.zremrangebyscore(key, 0, cutoff_time)
        
        # Count current requests in window
        count = await redis_conn.zcard(key)
        
        # Calculate remaining and reset time
        remaining = max(0, limit - count)
        reset_at = datetime.fromtimestamp(current_time + window_seconds)
        
        if count >= limit:
            # Rate limit exceeded
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=reset_at,
                retry_after=window_seconds
            )
        
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=remaining - 1,  # Account for current request
            reset_at=reset_at
        )
    
    async def _increment_counter(
        self,
        redis_conn: redis.Redis,
        organization_id: str,
        window_name: str,
        window_seconds: int,
        current_time: int
    ):
        """Increment request counter for a window"""
        key = self._get_key(organization_id, window_name)
        
        # Add current request with timestamp as score and unique ID as value
        request_id = f"{current_time}:{id(self)}"
        await redis_conn.zadd(key, {request_id: current_time})
        
        # Set expiration to window duration + buffer
        await redis_conn.expire(key, window_seconds + 60)
    
    async def _get_remaining(
        self,
        redis_conn: redis.Redis,
        organization_id: str,
        window_name: str,
        window_seconds: int,
        limit: int,
        current_time: int
    ) -> int:
        """Get remaining requests for a window"""
        key = self._get_key(organization_id, window_name)
        
        # Remove expired entries
        cutoff_time = current_time - window_seconds
        await redis_conn.zremrangebyscore(key, 0, cutoff_time)
        
        # Count current requests
        count = await redis_conn.zcard(key)
        
        return max(0, limit - count)
    
    async def get_usage_stats(
        self,
        organization_id: str,
        config: RateLimitConfig
    ) -> dict:
        """
        Get current rate limit usage statistics
        
        Args:
            organization_id: Organization UUID
            config: Rate limit configuration
            
        Returns:
            Dictionary with usage stats for all windows
        """
        redis_conn = await self._get_redis()
        current_time = int(time.time())
        
        windows = [
            ("minute", 60, config.requests_per_minute),
            ("hour", 3600, config.requests_per_hour),
            ("day", 86400, config.requests_per_day)
        ]
        
        stats = {}
        for window_name, window_seconds, limit in windows:
            remaining = await self._get_remaining(
                redis_conn,
                organization_id,
                window_name,
                window_seconds,
                limit,
                current_time
            )
            
            used = limit - remaining
            stats[window_name] = {
                "limit": limit,
                "used": used,
                "remaining": remaining,
                "percentage": round((used / limit) * 100, 2) if limit > 0 else 0
            }
        
        return stats
    
    async def reset_limits(self, organization_id: str):
        """
        Reset all rate limits for an organization
        
        Useful for testing or administrative purposes.
        """
        redis_conn = await self._get_redis()
        
        for window_name in ["minute", "hour", "day"]:
            key = self._get_key(organization_id, window_name)
            await redis_conn.delete(key)
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
