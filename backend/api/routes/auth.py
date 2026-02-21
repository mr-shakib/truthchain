"""
Authentication routes for TruthChain
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from ...db.connection import get_db
from ...models.organization import Organization, OrganizationTier
from ...models.api_key import APIKey
from ...core.auth import (
    hash_password,
    verify_password,
    create_api_key,
    verify_api_key
)

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


# Request/Response Models
class SignupRequest(BaseModel):
    """Organization signup request"""
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    email: EmailStr = Field(..., description="Organization email")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    tier: OrganizationTier = Field(default=OrganizationTier.FREE, description="Subscription tier")


class SignupResponse(BaseModel):
    """Organization signup response"""
    organization_id: str  # UUID string
    name: str
    email: str
    tier: str
    api_key: str
    monthly_quota: int
   
    class Config:
        from_attributes = True


class APIKeyResponse(BaseModel):
    """API key information"""
    id: str  # UUID string
    name: str
    key: Optional[str] = None  # Only included on creation
    is_active: bool
    created_at: str
    last_used_at: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new organization and get an API key
    
    Creates an organization account and generates the first API key.
    **Save the API key securely - it will only be shown once!**
    """
    # Check if email already exists
    from sqlalchemy import select
    result = await db.execute(
        select(Organization).where(Organization.email == request.email)
    )
    existing_org = result.scalar_one_or_none()
    
    if existing_org:
        raise HTTPException(
            status_code=400,
            detail="Organization with this email already exists"
        )
    
    # Create organization
    organization = Organization(
        name=request.name,
        email=request.email,
        password_hash=hash_password(request.password),
        tier=request.tier
    )
    
    db.add(organization)
    await db.commit()
    await db.refresh(organization)
    
    # Create API key
    api_key_obj, plain_key = await create_api_key(
        db,
        organization.id,
        name="Default API Key"
    )
    
    return SignupResponse(
        organization_id=organization.id,
        name=organization.name,
        email=organization.email,
        tier=organization.tier if isinstance(organization.tier, str) else organization.tier.value,
        api_key=plain_key,
        monthly_quota=organization.monthly_quota
    )


@router.post("/api-keys", response_model=APIKeyResponse, status_code=201)
async def create_new_api_key(
    name: str = "API Key",
    x_api_key: str = Header(..., description="Existing API key for authentication"),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key for your organization
    
    Requires authentication with an existing API key.
    **Save the new API key securely - it will only be shown once!**
    """
    # Verify the requesting API key
    result = await verify_api_key(db, x_api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    organization, _ = result
    
    # Create new API key
    api_key_obj, plain_key = await create_api_key(
        db,
        organization.id,
        name=name
    )
    
    return APIKeyResponse(
        id=api_key_obj.id,
        name=api_key_obj.name,
        key=plain_key,  # Only shown on creation
        is_active=api_key_obj.is_active,
        created_at=api_key_obj.created_at.isoformat(),
        last_used_at=api_key_obj.last_used_at.isoformat() if api_key_obj.last_used_at else None
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    x_api_key: str = Header(..., description="API key for authentication"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all API keys for your organization
    
    Note: The actual key values are never returned except during creation.
    """
    # Verify the requesting API key
    result = await verify_api_key(db, x_api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    organization, _ = result
    
    # Get all API keys for the organization
    from sqlalchemy import select
    result = await db.execute(
        select(APIKey).where(APIKey.organization_id == organization.id)
    )
    api_keys = result.scalars().all()
    
    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            is_active=key.is_active,
            created_at=key.created_at.isoformat(),
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None
        )
        for key in api_keys
    ]


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: int,
    x_api_key: str = Header(..., description="API key for authentication"),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke (deactivate) an API key
    
    The key will be marked as inactive but not deleted from the database.
    """
    # Verify the requesting API key
    result = await verify_api_key(db, x_api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    organization, requesting_key = result
    
    # Get the key to revoke
    from sqlalchemy import select
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.organization_id == organization.id
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Prevent revoking the last active key
    result = await db.execute(
        select(APIKey).where(
            APIKey.organization_id == organization.id,
            APIKey.is_active == True
        )
    )
    active_keys = result.scalars().all()
    
    if len(active_keys) == 1 and api_key.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot revoke the last active API key"
        )
    
    # Revoke the key
    api_key.is_active = False
    await db.commit()
    
    return None
