"""
API Key Model - Authentication tokens
"""
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin
from datetime import datetime
import uuid
from typing import Optional


class APIKey(Base, TimestampMixin):
    """
    API Key table for authentication
    """
    __tablename__ = "api_keys"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    key_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True
    )
    
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True
    )
    
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="api_keys"
    )
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, org_id={self.organization_id}, active={self.is_active})>"
    
    async def update_last_used(self, db):
        """Update last_used_at timestamp"""
        self.last_used_at = datetime.utcnow()
        await db.commit()
