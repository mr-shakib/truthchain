"""
Audit Log Model for TruthChain

Tracks all sensitive operations for security and compliance:
- User authentication (signup, login attempts)
- API key operations (create, revoke, rotate)
- Organization changes (tier updates, settings)
- Critical validation events
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, Field
from ..db.base import Base


class AuditLog(Base):
    """
    Audit log table for tracking sensitive operations
    
    Stores comprehensive audit trail for:
    - Security events (authentication, authorization)
    - Data changes (create, update, delete)
    - Administrative actions
    - Compliance requirements
    """
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event identification
    event_type = Column(String(100), nullable=False, index=True)  # e.g., "signup", "api_key_create"
    event_category = Column(String(50), nullable=False, index=True)  # e.g., "auth", "api_key", "validation"
    
    # Actor (who performed the action)
    organization_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # May be null for signup
    api_key_id = Column(UUID(as_uuid=True), nullable=True)
    actor_email = Column(String(255), nullable=True)  # For signup events
    
    # Action details
    action = Column(String(50), nullable=False)  # create, update, delete, access
    resource_type = Column(String(50), nullable=True)  # api_key, organization, validation
    resource_id = Column(String(255), nullable=True)  # UUID of affected resource
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(100), nullable=True)
    
    # Event data
    event_metadata = Column(JSON, nullable=True)  # Additional event-specific data
    status = Column(String(20), nullable=False)  # success, failure, error
    error_message = Column(String(500), nullable=True)  # For failed operations
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_audit_org_created', 'organization_id', 'created_at'),
        Index('idx_audit_event_created', 'event_type', 'created_at'),
        Index('idx_audit_category_created', 'event_category', 'created_at'),
    )


# Pydantic models for API responses

class AuditLogCreate(BaseModel):
    """Schema for creating audit log entries"""
    event_type: str = Field(..., max_length=100)
    event_category: str = Field(..., max_length=50)
    organization_id: Optional[uuid.UUID] = None
    api_key_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    action: str = Field(..., max_length=50)
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None
    status: str = "success"
    error_message: Optional[str] = None


class AuditLogResponse(BaseModel):
    """Schema for audit log API responses"""
    id: str
    event_type: str
    event_category: str
    organization_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda v: v.isoformat()
        }


# Event type constants for consistency

class AuditEventType:
    """Standard audit event types"""
    # Authentication
    SIGNUP = "auth.signup"
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    
    # API Keys
    API_KEY_CREATE = "api_key.create"
    API_KEY_REVOKE = "api_key.revoke"
    API_KEY_ROTATE = "api_key.rotate"
    API_KEY_ACCESS = "api_key.access"
    
    # Organization
    ORG_UPDATE = "organization.update"
    ORG_TIER_CHANGE = "organization.tier_change"
    ORG_DELETE = "organization.delete"
    
    # Validation
    VALIDATION_CRITICAL = "validation.critical"  # For validations that fail critically
    VALIDATION_QUOTA_EXCEEDED = "validation.quota_exceeded"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"
    
    # System
    SYSTEM_ERROR = "system.error"
    CONFIG_CHANGE = "system.config_change"


class AuditEventCategory:
    """Event categories for grouping"""
    AUTH = "auth"
    API_KEY = "api_key"
    ORGANIZATION = "organization"
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    SYSTEM = "system"
