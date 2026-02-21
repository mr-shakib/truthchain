"""
Validation API Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import time

from ...core.validation_engine import ValidationEngine, ValidationResult
from ...models.organization import Organization
from ...models.api_key import APIKey
from ...models.validation_log import ValidationLog
from ...db.connection import get_db
from ..dependencies import require_quota
from ...core.auth import increment_usage


router = APIRouter(prefix="/v1", tags=["Validation"])


class ValidationRequest(BaseModel):
    """Request model for validation endpoint"""
    output: Dict[str, Any] = Field(..., description="AI output data to validate")
    rules: List[Dict[str, Any]] = Field(..., description="Validation rules to apply")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context for validation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "output": {
                    "user_id": 12345,
                    "hours": 8,
                    "project_name": "Project-X"
                },
                "rules": [
                    {
                        "type": "schema",
                        "name": "output_structure",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "integer"},
                                "hours": {"type": "number"},
                                "project_name": {"type": "string"}
                            },
                            "required": ["user_id", "hours", "project_name"]
                        }
                    },
                    {
                        "type": "range",
                        "name": "hours_check",
                        "field": "hours",
                        "min": 0,
                        "max": 24,
                        "severity": "error"
                    }
                ],
                "context": {
                    "auto_correct": True
                }
            }
        }


@router.post("/validate", response_model=ValidationResult)
async def validate(
    request: ValidationRequest,
    org_data: Tuple[Organization, APIKey] = Depends(require_quota),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate AI output against business rules
    
    This endpoint validates any JSON output against a set of rules including:
    - Schema validation (JSON Schema)
    - Range validation (min/max values)
    - Pattern validation (regex)
    - Constraint validation (custom expressions)
    
    **Requires authentication via X-API-Key header**
    
    Returns validation result with any violations found and optionally
    auto-corrected output.
    
    Args:
        request: Validation request with output, rules, and context
        org_data: Current organization and API key (injected by auth)
        db: Database session
    
    Returns:
        ValidationResult with status, violations, and corrected output
    """
    organization, api_key = org_data
    start_time = time.time()
    
    try:
        # Run validation
        engine = ValidationEngine()
        result = await engine.validate(
            output=request.output,
            rules=request.rules,
            context=request.context
        )
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Update result with latency
        result.latency_ms = latency_ms
        
        # Log validation to database
        validation_log = ValidationLog(
            organization_id=organization.id,
            validation_id=result.validation_id,  # Use the ID from ValidationEngine
            input_data=request.output,
            output_data=result.corrected_output if result.corrected_output else request.output,
            rules_applied=request.rules,
            result=result.status.value,
            violations=[v.dict() for v in result.violations] if result.violations else [],
            auto_corrected=result.auto_corrected,
            latency_ms=latency_ms
        )
        
        db.add(validation_log)
        
        # Increment usage counter
        await increment_usage(db, organization)
        
        # Commit all changes to database
        await db.commit()
        
        return result
    
    except Exception as e:
        # Rollback on error
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Validation error: {str(e)}"
        )


@router.get("/validate/health")
async def validation_health():
    """Health check for validation service"""
    return {
        "status": "healthy",
        "service": "validation",
        "version": "1.0.0"
    }
