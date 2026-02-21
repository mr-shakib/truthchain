"""
Authentication and security utilities for TruthChain
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.organization import Organization
from ..models.api_key import APIKey

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (max 72 bytes)"""
    # Bcrypt has a 72-byte limit, so we truncate if necessary
    # For better security with long passwords, we pre-hash with SHA256
    import hashlib
    if len(password.encode('utf-8')) > 72:
        # Pre-hash long passwords
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def generate_api_key() -> str:
    """
    Generate a secure random API key
    Format: tc_live_<32 random hex chars>
    """
    random_part = secrets.token_hex(32)
    return f"tc_live_{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256
    Stores only the hash, not the plain key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


async def create_api_key(
    db: AsyncSession,
    organization_id: int,
    name: str = "Default API Key"
) -> tuple[APIKey, str]:
    """
    Create a new API key for an organization
    
    Returns:
        tuple: (APIKey model instance, plain API key string)
        The plain API key is returned only once and should be shown to the user
    """
    # Generate the key
    plain_key = generate_api_key()
    key_hash = hash_api_key(plain_key)
    
    # Create database record
    api_key = APIKey(
        organization_id=organization_id,
        key_hash=key_hash,
        name=name,
        is_active=True
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    return api_key, plain_key


async def verify_api_key(
    db: AsyncSession,
    api_key: str
) -> Optional[tuple[Organization, APIKey]]:
    """
    Verify an API key and return the associated organization
    
    Args:
        db: Database session
        api_key: Plain API key from request header
    
    Returns:
        tuple of (Organization, APIKey) if valid, None if invalid
    """
    # Hash the provided key
    key_hash = hash_api_key(api_key)
    
    # Query for the API key
    result = await db.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        )
    )
    api_key_obj = result.scalar_one_or_none()
    
    if not api_key_obj:
        return None
    
    # Get the organization
    result = await db.execute(
        select(Organization).where(Organization.id == api_key_obj.organization_id)
    )
    organization = result.scalar_one_or_none()
    
    if not organization:
        return None
    
    # Update last_used timestamp
    await api_key_obj.update_last_used(db)
    
    return organization, api_key_obj


async def check_quota(organization: Organization) -> bool:
    """
    Check if organization has quota remaining
    
    Returns:
        True if quota available, False if exhausted
    """
    return organization.has_quota()


async def increment_usage(db: AsyncSession, organization: Organization) -> None:
    """
    Increment usage counter for an organization
    """
    organization.usage_current_month += 1
    await db.commit()
