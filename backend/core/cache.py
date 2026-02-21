"""
Caching Layer for TruthChain
Uses Redis for high-performance caching of validation data
"""
import json
import hashlib
from typing import Any, Optional, Dict
from datetime import timedelta
import redis.asyncio as redis
from pydantic import BaseModel


class CacheConfig(BaseModel):
    """Configuration for cache settings"""
    enabled: bool = True
    ttl_seconds: int = 3600  # 1 hour default
    reference_ttl_seconds: int = 300  # 5 minutes for reference checks
    schema_ttl_seconds: int = 7200  # 2 hours for schemas
    max_memory_mb: int = 100


class CacheLayer:
    """
    Caching layer for TruthChain validation system
    
    Caches:
    - Reference validation results (user_id exists, etc.)
    - Frequently used schemas
    - Validation rules
    - API responses (optional)
    
    Uses Redis for distributed caching across multiple API instances
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", config: Optional[CacheConfig] = None):
        self.redis_url = redis_url
        self.config = config or CacheConfig()
        self._redis: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Initialize Redis connection"""
        if not self.config.enabled:
            return
        
        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._redis.ping()
            print(f"✅ Cache layer connected to Redis")
        except Exception as e:
            print(f"⚠️  Cache layer failed to connect to Redis: {e}")
            print("   Continuing without caching...")
            self._redis = None
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found
        """
        if not self._redis or not self.config.enabled:
            return None
        
        try:
            value = await self._redis.get(key)
            if value:
                # Try to parse as JSON, fallback to string
                try:
                    return json.loads(value)
                except:
                    return value
            return None
        except Exception as e:
            print(f"Cache get error for key '{key}': {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl_seconds: Time to live in seconds (uses default if None)
        
        Returns:
            True if successful, False otherwise
        """
        if not self._redis or not self.config.enabled:
            return False
        
        try:
            # Serialize value to JSON
            serialized = json.dumps(value) if not isinstance(value, str) else value
            
            # Use provided TTL or default
            ttl = ttl_seconds or self.config.ttl_seconds
            
            await self._redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Cache set error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache
        
        Args:
            key: Cache key to delete
        
        Returns:
            True if deleted, False otherwise
        """
        if not self._redis or not self.config.enabled:
            return False
        
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._redis or not self.config.enabled:
            return False
        
        try:
            return await self._redis.exists(key) > 0
        except:
            return False
    
    # Specialized cache methods for TruthChain
    
    async def cache_reference_check(
        self,
        table: str,
        column: str,
        value: Any,
        exists: bool
    ) -> bool:
        """
        Cache a reference validation result
        
        Args:
            table: Database table
            column: Column name
            value: Value checked
            exists: Whether the reference exists
        
        Returns:
            True if cached successfully
        """
        key = self._get_reference_key(table, column, value)
        return await self.set(key, exists, self.config.reference_ttl_seconds)
    
    async def get_reference_check(
        self,
        table: str,
        column: str,
        value: Any
    ) -> Optional[bool]:
        """
        Get cached reference validation result
        
        Args:
            table: Database table
            column: Column name
            value: Value to check
        
        Returns:
            True/False if cached, None if not in cache
        """
        key = self._get_reference_key(table, column, value)
        result = await self.get(key)
        return result if result is not None else None
    
    async def cache_schema(self, schema_hash: str, schema: Dict[str, Any]) -> bool:
        """
        Cache a JSON schema
        
        Args:
            schema_hash: Hash of the schema (for key)
            schema: Schema definition
        
        Returns:
            True if cached successfully
        """
        key = f"schema:{schema_hash}"
        return await self.set(key, schema, self.config.schema_ttl_seconds)
    
    async def get_schema(self, schema_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached schema"""
        key = f"schema:{schema_hash}"
        return await self.get(key)
    
    async def cache_validation_result(
        self,
        validation_id: str,
        result: Dict[str, Any],
        ttl_seconds: int = 300
    ) -> bool:
        """
        Cache a validation result (for idempotent requests)
        
        Args:
            validation_id: Unique validation identifier
            result: Validation result to cache
            ttl_seconds: TTL (default 5 minutes)
        
        Returns:
            True if cached successfully
        """
        key = f"validation:{validation_id}"
        return await self.set(key, result, ttl_seconds)
    
    async def get_validation_result(self, validation_id: str) -> Optional[Dict[str, Any]]:
        """Get cached validation result"""
        key = f"validation:{validation_id}"
        return await self.get(key)
    
    async def invalidate_references(self, table: str) -> int:
        """
        Invalidate all cached references for a table
        Useful when data in the table changes
        
        Args:
            table: Table name
        
        Returns:
            Number of keys deleted
        """
        if not self._redis or not self.config.enabled:
            return 0
        
        try:
            pattern = f"ref:{table}:*"
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self._redis.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            print(f"Cache invalidation error: {e}")
            return 0
    
    async def clear_all(self) -> bool:
        """Clear all TruthChain cache entries"""
        if not self._redis or not self.config.enabled:
            return False
        
        try:
            # Only clear TruthChain keys (ref:, schema:, validation:)
            patterns = ["ref:*", "schema:*", "validation:*"]
            total_deleted = 0
            
            for pattern in patterns:
                keys = []
                async for key in self._redis.scan_iter(match=pattern):
                    keys.append(key)
                
                if keys:
                    await self._redis.delete(*keys)
                    total_deleted += len(keys)
            
            print(f"Cleared {total_deleted} cache entries")
            return True
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._redis or not self.config.enabled:
            return {"enabled": False}
        
        try:
            info = await self._redis.info("stats")
            return {
                "enabled": True,
                "total_keys": await self._redis.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}
    
    def _get_reference_key(self, table: str, column: str, value: Any) -> str:
        """Generate cache key for reference check"""
        # Hash the value for consistent key length
        value_hash = hashlib.md5(str(value).encode()).hexdigest()[:16]
        return f"ref:{table}:{column}:{value_hash}"
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)
    
    @staticmethod
    def hash_schema(schema: Dict[str, Any]) -> str:
        """Generate hash for a schema"""
        schema_str = json.dumps(schema, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()[:16]


# Global cache instance
_cache_instance: Optional[CacheLayer] = None


async def get_cache() -> CacheLayer:
    """Get global cache instance"""
    global _cache_instance
    
    if _cache_instance is None:
        from ..db.connection import get_redis_url
        redis_url = get_redis_url()
        _cache_instance = CacheLayer(redis_url)
        await _cache_instance.connect()
    
    return _cache_instance


async def close_cache() -> None:
    """Close global cache instance"""
    global _cache_instance
    
    if _cache_instance:
        await _cache_instance.disconnect()
        _cache_instance = None
