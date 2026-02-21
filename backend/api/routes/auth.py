"""
Authentication routes for TruthChain
"""
from fastapi import APIRouter, HTTPException, Depends, Header, Request
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
from ...core.audit_logger import audit_logger

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
    signup_req: SignupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new organization and get an API key
    
    Creates an organization account and generates the first API key.
    **Save the API key securely - it will only be shown once!**
    """
    try:
        # Check if email already exists
        from sqlalchemy import select
        result = await db.execute(
            select(Organization).where(Organization.email == signup_req.email)
        )
        existing_org = result.scalar_one_or_none()
        
        if existing_org:
            # Log failed signup attempt
            await audit_logger.log_signup(
                db=db,
                email=signup_req.email,
                organization_id=existing_org.id,
                tier=signup_req.tier.value,
                request=request,
                status="failure",
                error_message="Email already exists"
            )
            
            raise HTTPException(
                status_code=400,
                detail="Organization with this email already exists"
            )
        
        # Create organization
        organization = Organization(
            name=signup_req.name,
            email=signup_req.email,
            password_hash=hash_password(signup_req.password),
            tier=signup_req.tier
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
        
        # Log successful signup
        await audit_logger.log_signup(
            db=db,
            email=signup_req.email,
            organization_id=organization.id,
            tier=organization.tier if isinstance(organization.tier, str) else organization.tier.value,
            request=request,
            status="success"
        )
        
        return SignupResponse(
            organization_id=organization.id,
            name=organization.name,
            email=organization.email,
            tier=organization.tier if isinstance(organization.tier, str) else organization.tier.value,
            api_key=plain_key,
            monthly_quota=organization.monthly_quota
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Log unexpected error
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Signup failed: {str(e)}"
        )


@router.post("/api-keys", response_model=APIKeyResponse, status_code=201)
async def create_new_api_key(
    name: str = "API Key",
    x_api_key: str = Header(..., description="Existing API key for authentication"),
    request: Request = None,
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
    
    # Log API key creation
    await audit_logger.log_api_key_create(
        db=db,
        organization_id=organization.id,
        api_key_id=api_key_obj.id,
        key_name=name,
        request=request
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


@router.post("/api-keys/{key_id}/rotate", response_model=APIKeyResponse, status_code= 200)
async def rotate_api_key(
    key_id: str,
    x_api_key: str = Header(..., description="API key for authentication"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Rotate an API key (generate new key, revoke old key)
    
    This creates a new API key and immediately revokes the old one.
    **Save the new API key securely - it will only be shown once!**
    
    Best practice: Have at least 2 active keys before rotation, so you can
    update your applications with the new key before the old one is revoked.
    """
    # Verify the requesting API key
    result = await verify_api_key(db, x_api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    organization, requesting_key = result
    
    # Get the key to rotate
    from sqlalchemy import select
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.organization_id == organization.id
        )
    )
    old_api_key = result.scalar_one_or_none()
    
    if not old_api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    if not old_api_key.is_active:
        raise HTTPException(status_code=400, detail="Cannot rotate an inactive API key")
    
    # Create new API key with same name (+ " (Rotated)")
    new_name = f"{old_api_key.name} (Rotated)"
    new_api_key, plain_key = await create_api_key(
        db,
        organization.id,
        name=new_name
    )
    
    # Revoke the old key
    old_api_key.is_active = False
    await db.commit()
    await db.refresh(new_api_key)
    
    # Log API key rotation
    await audit_logger.log_api_key_rotate(
        db=db,
        organization_id=organization.id,
        old_key_id=old_api_key.id,
        new_key_id=new_api_key.id,
        request=request
    )
    
    return APIKeyResponse(
        id=new_api_key.id,
        name=new_api_key.name,
        key=plain_key,  # Only shown on creation
        is_active=new_api_key.is_active,
        created_at=new_api_key.created_at.isoformat(),
        last_used_at=None
    )


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    x_api_key: str = Header(..., description="API key for authentication"),
    request: Request = None,
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
    
    # Log API key revocation
    await audit_logger.log_api_key_revoke(
        db=db,
        organization_id=organization.id,
        api_key_id=api_key.id,
        request=request
    )
    
    return None
