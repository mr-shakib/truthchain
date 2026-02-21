"""
Audit Logger Utility for TruthChain

Provides easy-to-use functions for logging audit events throughout the application.
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from ..models.audit_log import (
    AuditLog,
    AuditLogCreate,
    AuditEventType,
    AuditEventCategory
)


class AuditLogger:
    """
    Utility class for logging audit events
    
    Usage:
        audit = AuditLogger(db)
        await audit.log_signup(email="user@example.com", org_id=org.id, request=request)
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize audit logger
        
        Args:
            db: Optional database session. If None, must be passed to log methods.
        """
        self.db = db
    
    async def log(
        self,
        db: Optional[AsyncSession],
        event_type: str,
        event_category: str,
        action: str,
        organization_id: Optional[uuid.UUID] = None,
        api_key_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Log an audit event
        
        Args:
            db: Database session
            event_type: Type of event (use AuditEventType constants)
            event_category: Category (use AuditEventCategory constants)
            action: Action performed (create, update, delete, access)
            organization_id: Organization UUID
            api_key_id: API key UUID
            actor_email: Email of actor (for signup events)
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            metadata: Additional event data
            status: Status (success, failure, error)
            error_message: Error message if status is failure/error
            request: FastAPI Request object for extracting IP, user agent
            
        Returns:
            Created AuditLog instance
        """
        db_session = db or self.db
        if db_session is None:
            raise ValueError("Database session required")
        
        # Extract request metadata if available
        ip_address = None
        user_agent = None
        request_id = None
        
        if request:
            # Extract IP address
            ip_address = request.client.host if request.client else None
            
            # Check for forwarded IP (behind proxy/load balancer)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                ip_address = forwarded_for.split(",")[0].strip()
            
            # Extract user agent
            user_agent = request.headers.get("User-Agent")
            
            # Generate or extract request ID
            request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        
        # Create audit log entry
        audit_log = AuditLog(
            id=uuid.uuid4(),
            event_type=event_type,
            event_category=event_category,
            organization_id=organization_id,
            api_key_id=api_key_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            event_metadata=metadata,
            status=status,
            error_message=error_message,
            created_at=datetime.utcnow()
        )
        
        db_session.add(audit_log)
        await db_session.commit()
        await db_session.refresh(audit_log)
        
        return audit_log
    
    # Convenience methods for common events
    
    async def log_signup(
        self,
        db: AsyncSession,
        email: str,
        organization_id: uuid.UUID,
        tier: str,
        request: Optional[Request] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Log organization signup event"""
        return await self.log(
            db=db,
            event_type=AuditEventType.SIGNUP,
            event_category=AuditEventCategory.AUTH,
            action="create",
            organization_id=organization_id,
            actor_email=email,
            resource_type="organization",
            resource_id=str(organization_id),
            metadata={"tier": tier},
            status=status,
            error_message=error_message,
            request=request
        )
    
    async def log_api_key_create(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        api_key_id: uuid.UUID,
        key_name: str,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log API key creation"""
        return await self.log(
            db=db,
            event_type=AuditEventType.API_KEY_CREATE,
            event_category=AuditEventCategory.API_KEY,
            action="create",
            organization_id=organization_id,
            api_key_id=api_key_id,
            resource_type="api_key",
            resource_id=str(api_key_id),
            metadata={"key_name": key_name},
            request=request
        )
    
    async def log_api_key_revoke(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        api_key_id: uuid.UUID,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log API key revocation"""
        return await self.log(
            db=db,
            event_type=AuditEventType.API_KEY_REVOKE,
            event_category=AuditEventCategory.API_KEY,
            action="delete",
            organization_id=organization_id,
            api_key_id=api_key_id,
            resource_type="api_key",
            resource_id=str(api_key_id),
            request=request
        )
    
    async def log_api_key_rotate(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        old_key_id: uuid.UUID,
        new_key_id: uuid.UUID,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log API key rotation"""
        return await self.log(
            db=db,
            event_type=AuditEventType.API_KEY_ROTATE,
            event_category=AuditEventCategory.API_KEY,
            action="update",
            organization_id=organization_id,
            api_key_id=new_key_id,
            resource_type="api_key",
            resource_id=str(new_key_id),
            metadata={"old_key_id": str(old_key_id)},
            request=request
        )
    
    async def log_rate_limit_exceeded(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        api_key_id: Optional[uuid.UUID],
        limit_window: str,
        limit_value: int,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log rate limit exceeded event"""
        return await self.log(
            db=db,
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            event_category=AuditEventCategory.RATE_LIMIT,
            action="access",
            organization_id=organization_id,
            api_key_id=api_key_id,
            resource_type="rate_limit",
            metadata={
                "window": limit_window,
                "limit": limit_value
            },
            status="failure",
            request=request
        )
    
    async def log_validation_quota_exceeded(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        api_key_id: uuid.UUID,
        current_usage: int,
        quota: int,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log validation quota exceeded event"""
        return await self.log(
            db=db,
            event_type=AuditEventType.VALIDATION_QUOTA_EXCEEDED,
            event_category=AuditEventCategory.VALIDATION,
            action="access",
            organization_id=organization_id,
            api_key_id=api_key_id,
            resource_type="validation",
            metadata={
                "current_usage": current_usage,
                "quota": quota
            },
            status="failure",
            request=request
        )
    
    async def log_tier_change(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        old_tier: str,
        new_tier: str,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log organization tier change"""
        return await self.log(
            db=db,
            event_type=AuditEventType.ORG_TIER_CHANGE,
            event_category=AuditEventCategory.ORGANIZATION,
            action="update",
            organization_id=organization_id,
            resource_type="organization",
            resource_id=str(organization_id),
            metadata={
                "old_tier": old_tier,
                "new_tier": new_tier
            },
            request=request
        )


# Global instance for convenience
audit_logger = AuditLogger()
