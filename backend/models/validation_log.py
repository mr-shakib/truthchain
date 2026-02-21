"""
Validation Log Model - Track all validations
"""
from sqlalchemy import String, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin
from datetime import datetime
import uuid
from typing import Optional, Dict, Any, List


class ValidationLog(Base, TimestampMixin):
    """
    Validation Log table - tracks all validation requests
    """
    __tablename__ = "validation_logs"
    
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
    
    validation_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    
    input_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    rules_applied: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    
    result: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )  # passed, failed, warning
    
    violations: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    
    auto_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="validation_logs"
    )
    
    def __repr__(self):
        return f"<ValidationLog(id={self.validation_id}, result={self.result})>"
