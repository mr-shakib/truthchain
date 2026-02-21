"""
FastAPI dependencies for authentication and authorization
"""
from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple

from ..db.connection import get_db
from ..models.organization import Organization
from ..models.api_key import APIKey
from ..core.auth import verify_api_key as verify_api_key_util, check_quota


async def get_current_organization(
    x_api_key: str = Header(..., description="API key for authentication"),
    db: AsyncSession = Depends(get_db)
) -> Tuple[Organization, APIKey]:
    """
    Verify API key and return the current organization
    
    Usage:
        @router.get("/protected")
        async def protected_route(
            org_data: Tuple[Organization, APIKey] = Depends(get_current_organization)
        ):
            organization, api_key = org_data
            ...
    """
    result = await verify_api_key_util(db, x_api_key)
    
    if not result:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key"
        )
    
    return result


async def require_quota(
    org_data: Tuple[Organization, APIKey] = Depends(get_current_organization)
) -> Tuple[Organization, APIKey]:
    """
    Verify API key and check that organization has quota remaining
    
    Usage:
        @router.post("/validate")
        async def validate(
            org_data: Tuple[Organization, APIKey] = Depends(require_quota)
        ):
            organization, api_key = org_data
            ...
    """
    organization, api_key = org_data
    
    if not check_quota(organization):
        raise HTTPException(
            status_code=429,
            detail=f"Monthly quota exhausted. Quota: {organization.monthly_quota}, Used: {organization.usage_current_month}"
        )
    
    return organization, api_key
