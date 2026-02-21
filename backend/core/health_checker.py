"""
Health Checker for TruthChain

Monitors health of all system dependencies:
- PostgreSQL database
- Redis cache
- Application status
- System metrics
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from ..config.settings import get_settings


class ComponentHealth(BaseModel):
    """Health status of a single component"""
    name: str
    status: str  # healthy, degraded, unhealthy
    response_time_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    last_check: datetime = datetime.utcnow()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemHealth(BaseModel):
    """Overall system health status"""
    status: str  # healthy, degraded, unhealthy
    version: str = "1.0.0"
    uptime_seconds: Optional[float] = None
    components: Dict[str, ComponentHealth]
    timestamp: datetime = datetime.utcnow()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthChecker:
    """
    System health checker
    
    Monitors all critical dependencies and provides detailed health status.
    Supports:
    - Live dependency checks
    - Response time monitoring
    - Graceful degradation
    - Detailed error reporting
    """
    
    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        """
        Initialize health checker
        
        Args:
            db: Optional database session
            redis_client: Optional Redis client
        """
        self.db = db
        self.redis_client = redis_client
        self._start_time = time.time()
        self.settings = get_settings()
    
    async def check_all(
        self,
        db: Optional[AsyncSession] = None,
        include_details: bool = True
    ) -> SystemHealth:
        """
        Check health of all components
        
        Args:
            db: Database session (required if not provided in constructor)
            include_details: Include detailed component information
            
        Returns:
            SystemHealth object with status of all components
        """
        db_session = db or self.db
        
        # Run all health checks in parallel
        checks = await asyncio.gather(
            self.check_database(db_session, include_details),
            self.check_redis(include_details),
            self.check_application(include_details),
            return_exceptions=True
        )
        
        components = {}
        for check in checks:
            if isinstance(check, ComponentHealth):
                components[check.name] = check
            elif isinstance(check, Exception):
                # Handle unexpected errors gracefully
                components["unknown"] = ComponentHealth(
                    name="unknown",
                    status="unhealthy",
                    message=f"Health check error: {str(check)}"
                )
        
        # Determine overall system status
        overall_status = self._calculate_overall_status(components)
        
        return SystemHealth(
            status=overall_status,
            version="1.0.0",
            uptime_seconds=time.time() - self._start_time,
            components=components,
            timestamp=datetime.utcnow()
        )
    
    async def check_database(
        self,
        db: Optional[AsyncSession] = None,
        include_details: bool = True
    ) -> ComponentHealth:
        """
        Check PostgreSQL database health
        
        Args:
            db: Database session
            include_details: Include connection pool statistics
            
        Returns:
            ComponentHealth for database
        """
        db_session = db or self.db
        
        if db_session is None:
            return ComponentHealth(
                name="database",
                status="unhealthy",
                message="No database session available"
            )
        
        start_time = time.time()
        
        try:
            # Simple connectivity check
            result = await db_session.execute(text("SELECT 1"))
            result.scalar()
            
            response_time = (time.time() - start_time) * 1000
            
            details = None
            if include_details:
                # Check table count
                table_result = await db_session.execute(
                    text("""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """)
                )
                table_count = table_result.scalar()
                
                # Check organizations count
                org_result = await db_session.execute(
                    text("SELECT COUNT(*) FROM organizations")
                )
                org_count = org_result.scalar()
                
                details = {
                    "tables": table_count,
                    "organizations": org_count,
                    "connection_url": self.settings.DATABASE_URL.split("@")[-1]  # Hide credentials
                }
            
            # Determine status based on response time
            if response_time < 100:
                status = "healthy"
                message = "Database responding normally"
            elif response_time < 500:
                status = "degraded"
                message = f"Database response slow ({response_time:.0f}ms)"
            else:
                status = "degraded"
                message = f"Database response very slow ({response_time:.0f}ms)"
            
            return ComponentHealth(
                name="database",
                status=status,
                response_time_ms=response_time,
                message=message,
                details=details,
                last_check=datetime.utcnow()
            )
            
        except Exception as e:
            return ComponentHealth(
                name="database",
                status="unhealthy",
                message=f"Database connection failed: {str(e)}",
                details={"error_type": type(e).__name__},
                last_check=datetime.utcnow()
            )
    
    async def check_redis(
        self,
        include_details: bool = True
    ) -> ComponentHealth:
        """
        Check Redis health
        
        Args:
            include_details: Include Redis statistics
            
        Returns:
            ComponentHealth for Redis
        """
        start_time = time.time()
        
        try:
            # Get or create Redis connection
            redis_conn = self.redis_client
            if redis_conn is None:
                redis_conn = await redis.from_url(
                    self.settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            
            # Ping Redis
            await redis_conn.ping()
            
            response_time = (time.time() - start_time) * 1000
            
            details = None
            if include_details:
                # Get Redis info
                info = await redis_conn.info()
                details = {
                    "version": info.get("redis_version"),
                    "uptime_seconds": info.get("uptime_in_seconds"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "total_keys": await redis_conn.dbsize()
                }
            
            # Close connection if we created it
            if self.redis_client is None:
                await redis_conn.close()
            
            # Determine status
            if response_time < 50:
                status = "healthy"
                message = "Redis responding normally"
            elif response_time < 200:
                status = "degraded"
                message = f"Redis response slow ({response_time:.0f}ms)"
            else:
                status = "degraded"
                message = f"Redis response very slow ({response_time:.0f}ms)"
            
            return ComponentHealth(
                name="redis",
                status=status,
                response_time_ms=response_time,
                message=message,
                details=details,
                last_check=datetime.utcnow()
            )
            
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status="unhealthy",
                message=f"Redis connection failed: {str(e)}",
                details={"error_type": type(e).__name__},
                last_check=datetime.utcnow()
            )
    
    async def check_application(
        self,
        include_details: bool = True
    ) -> ComponentHealth:
        """
        Check application health
        
        Args:
            include_details: Include application metrics
            
        Returns:
            ComponentHealth for application
        """
        try:
            uptime = time.time() - self._start_time
            
            details = None
            if include_details:
                import sys
                import platform
                
                details = {
                    "python_version": sys.version.split()[0],
                    "platform": platform.system(),
                    "uptime_seconds": round(uptime, 2),
                    "uptime_human": self._format_uptime(uptime)
                }
            
            return ComponentHealth(
                name="application",
                status="healthy",
                message="Application running normally",
                details=details,
                last_check=datetime.utcnow()
            )
            
        except Exception as e:
            return ComponentHealth(
                name="application",
                status="unhealthy",
                message=f"Application check failed: {str(e)}",
                last_check=datetime.utcnow()
            )
    
    def _calculate_overall_status(
        self,
        components: Dict[str, ComponentHealth]
    ) -> str:
        """
        Calculate overall system status from component statuses
        
        Rules:
        - If any component is unhealthy: system is unhealthy
        - If any component is degraded: system is degraded
        - Otherwise: system is healthy
        """
        if not components:
            return "unhealthy"
        
        statuses = [c.status for c in components.values()]
        
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "degraded" in statuses:
            return "degraded"
        else:
            return "healthy"
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        minutes = int(seconds // 60)
        hours = int(minutes // 60)
        days = int(hours // 24)
        
        if days > 0:
            return f"{days}d {hours % 24}h"
        elif hours > 0:
            return f"{hours}h {minutes % 60}m"
        elif minutes > 0:
            return f"{minutes}m {int(seconds % 60)}s"
        else:
            return f"{int(seconds)}s"
    
    async def check_liveness(self) -> bool:
        """
        Simple liveness check (Kubernetes-style)
        
        Returns True if application is alive (even if degraded).
        Only returns False if application is completely dead.
        """
        return True  # Application is alive if this code runs
    
    async def check_readiness(
        self,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Readiness check (Kubernetes-style)
        
        Returns True if application is ready to serve traffic.
        Checks that critical dependencies (database) are accessible.
        """
        db_session = db or self.db
        
        try:
            if db_session:
                # Check database connectivity
                await db_session.execute(text("SELECT 1"))
                return True
            return False
        except Exception:
            return False
