"""
Health Check Routes for TruthChain

Provides comprehensive health monitoring endpoints:
- /health - Overall system health
- /health/live - Liveness probe (Kubernetes-style)
- /health/ready - Readiness probe (Kubernetes-style)
- /health/database - Database-specific health
- /health/redis - Redis-specific health
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.connection import get_db
from ...core.health_checker import HealthChecker, SystemHealth, ComponentHealth

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=SystemHealth)
async def get_system_health(
    include_details: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall system health status
    
    Returns comprehensive health information for all system components:
    - Database (PostgreSQL)
    - Cache (Redis)
    - Application
    
    Query Parameters:
        include_details: Include detailed component information (default: true)
    
    Response Fields:
        - status: overall system status (healthy|degraded|unhealthy)
        - version: application version
        - uptime_seconds: how long the application has been running
        - components: health status of individual components
        - timestamp: when the check was performed
    
    HTTP Status Codes:
        - 200: System is healthy or degraded (still operational)
        - 503: System is unhealthy (critical components down)
    """
    checker = HealthChecker(db=db)
    health = await checker.check_all(db=db, include_details=include_details)
    
    # Return 503 if system is unhealthy
    if health.status == "unhealthy":
        raise HTTPException(
            status_code=503,
            detail="Service unavailable - critical dependencies unhealthy"
        )
    
    return health


@router.get("/live")
async def liveness_probe():
    """
    Liveness probe (Kubernetes-style)
    
    Indicates if the application is alive and running.
    This should only fail if the application process is completely dead.
    
    Use this for Kubernetes liveness probes to restart crashed pods.
    
    Returns:
        - 200 OK: Application is alive
        - 503: Application is dead (should never happen - process crashed)
    """
    checker = HealthChecker()
    is_alive = await checker.check_liveness()
    
    if not is_alive:
        raise HTTPException(status_code=503, detail="Application not alive")
    
    return {
        "status": "alive",
        "message": "Application is running"
    }


@router.get("/ready")
async def readiness_probe(
    db: AsyncSession = Depends(get_db)
):
    """
    Readiness probe (Kubernetes-style)
    
    Indicates if the application is ready to serve traffic.
    Checks that critical dependencies (database) are accessible.
    
    Use this for Kubernetes readiness probes to control traffic routing.
    
    Returns:
        - 200 OK: Application is ready to serve requests
        - 503: Application is not ready (e.g., database down)
    """
    checker = HealthChecker(db=db)
    is_ready = await checker.check_readiness(db=db)
    
    if not is_ready:
        raise HTTPException(
            status_code=503,
            detail="Application not ready - database unavailable"
        )
    
    return {
        "status": "ready",
        "message": "Application is ready to serve traffic"
    }


@router.get("/database", response_model=ComponentHealth)
async def database_health(
    include_details: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Get database health status
    
    Checks PostgreSQL database connectivity and performance.
    
    Query Parameters:
        include_details: Include database statistics (default: true)
    
    Returns:
        ComponentHealth with database-specific health information
    """
    checker = HealthChecker(db=db)
    health = await checker.check_database(db=db, include_details=include_details)
    
    if health.status == "unhealthy":
        raise HTTPException(
            status_code=503,
            detail=f"Database unhealthy: {health.message}"
        )
    
    return health


@router.get("/redis", response_model=ComponentHealth)
async def redis_health(
    include_details: bool = True
):
    """
    Get Redis health status
    
    Checks Redis connectivity and performance.
    
    Query Parameters:
        include_details: Include Redis statistics (default: true)
    
    Returns:
        ComponentHealth with Redis-specific health information
    """
    checker = HealthChecker()
    health = await checker.check_redis(include_details=include_details)
    
    if health.status == "unhealthy":
        raise HTTPException(
            status_code=503,
            detail=f"Redis unhealthy: {health.message}"
        )
    
    return health
