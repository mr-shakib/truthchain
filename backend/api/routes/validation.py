"""
Validation API Routes
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from core.validation_engine import ValidationEngine, ValidationResult


router = APIRouter()


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
    authorization: Optional[str] = Header(None)
):
    """
    Validate AI output against business rules
    
    This endpoint validates any JSON output against a set of rules including:
    - Schema validation (JSON Schema)
    - Range validation (min/max values)
    - Pattern validation (regex)
    - Constraint validation (custom expressions)
    
    Returns validation result with any violations found and optionally
    auto-corrected output.
    
    Args:
        request: Validation request with output, rules, and context
        authorization: Optional API key for authentication (future use)
    
    Returns:
        ValidationResult with status, violations, and corrected output
    """
    try:
        # TODO: Implement API key verification when auth is ready
        # if authorization:
        #     api_key = authorization.replace("Bearer ", "")
        #     organization = await verify_api_key(api_key)
        #     if not await organization.has_quota():
        #         raise HTTPException(status_code=403, detail="Validation quota exceeded")
        
        # Run validation
        engine = ValidationEngine()
        result = await engine.validate(
            output=request.output,
            rules=request.rules,
            context=request.context
        )
        
        # TODO: Log validation when database is ready
        # await ValidationLog.create(
        #     organization_id=organization.id if authorization else None,
        #     validation_id=result.validation_id,
        #     input_data=request.output,
        #     output_data=result.corrected_output,
        #     rules_applied=request.rules,
        #     result=result.status.value,
        #     violations=[v.dict() for v in result.violations],
        #     latency_ms=result.latency_ms
        # )
        
        return result
    
    except Exception as e:
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
