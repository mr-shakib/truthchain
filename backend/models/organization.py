"""
Organization Model - Multi-tenant support
"""
from enum import Enum
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin
import uuid
from typing import List


class OrganizationTier(str, Enum):
    """Organization subscription tiers"""
    FREE = "free"
    STARTUP = "startup"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class Organization(Base, TimestampMixin):
    """
    Organization table for multi-tenant support
    """
    __tablename__ = "organizations"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    tier: Mapped[str] = mapped_column(
        String(50),
        default="free",
        nullable=False,
        index=True
    )  # free, startup, business, enterprise
    
    monthly_quota: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)
    
    usage_current_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    validation_logs: Mapped[List["ValidationLog"]] = relationship(
        "ValidationLog",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name}, email={self.email})>"
    
    async def has_quota(self) -> bool:
        """Check if organization has remaining validation quota"""
        return self.usage_current_month < self.monthly_quota
    
    async def increment_usage(self):
        """Increment monthly usage counter"""
        self.usage_current_month += 1
