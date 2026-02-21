"""
LLM Proxy Routes — /v1/complete
================================
Thin HTTP wrapper around LLMProxy.complete().

POST /v1/complete
  - Accepts an OpenAI-compatible messages list + TruthChain validation rules.
  - Returns the LLM response with inline validation results.
  - Optionally auto-corrects the output before returning.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_quota_and_rate_limit
from ...core.llm_proxy import LLMProxy, ProxyResult

router = APIRouter(prefix="/v1", tags=["LLM Proxy"])


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────────────────────────────────────

class MessageItem(BaseModel):
    role:    str
    content: str


class CompleteRequest(BaseModel):
    """Body for POST /v1/complete."""

    provider:          str               = Field("groq",  description="LLM provider: openai | groq | custom")
    model:             Optional[str]     = Field(None,    description="Model name. Defaults to provider default.")
    messages:          List[MessageItem] = Field(...,     description="OpenAI-format messages list")
    validation_rules:  List[Dict[str, Any]] = Field(default_factory=list, description="TruthChain rules to validate the output")
    output_field:      Optional[str]     = Field(None,    description="Top-level JSON key expected in LLM response")
    auto_correct:      bool              = Field(False,   description="Apply AutoCorrector strategies to violations")
    provider_api_key:  Optional[str]     = Field(None,    description="Per-request API key override")
    base_url:          Optional[str]     = Field(None,    description="Custom base URL (for provider='custom')")
    extra_params:      Optional[Dict[str, Any]] = Field(None, description="Extra params forwarded to LLM API body")


class ValidationSummary(BaseModel):
    is_valid:      bool
    total_rules:   int
    violations:    int
    auto_corrected: int


class CompleteResponse(BaseModel):
    """Response from POST /v1/complete."""

    content:     str
    raw_content: str
    output:      Dict[str, Any]
    provider:    str
    model:       str
    usage:       Dict[str, int]
    latency_ms:  int
    error:       str
    validation:  Optional[ValidationSummary] = None


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/complete",
    response_model=CompleteResponse,
    summary="Proxy an LLM request through TruthChain validation",
)
async def complete(
    request: CompleteRequest,
    _quota_check: None = Depends(require_quota_and_rate_limit),
    db: Session = Depends(get_db),
) -> CompleteResponse:
    """
    Send ``messages`` to the chosen LLM provider, validate the response with
    ``validation_rules``, optionally auto-correct violations, and return the
    full result.

    **Minimal example (no validation):**

    ```json
    {
      "provider": "groq",
      "messages": [{"role": "user", "content": "Hello"}]
    }
    ```

    **With validation:**

    ```json
    {
      "provider": "groq",
      "messages": [{"role": "user", "content": "Give me Sehri time in Dhaka as JSON {\"sehri_time\": \"HH:MM AM/PM\"}"}],
      "validation_rules": [
        {
          "type": "external_ref",
          "field": "sehri_time",
          "connector": "aladhan_fajr_in_range",
          "params": {"city": "Dhaka", "country": "Bangladesh", "tolerance_minutes": 15}
        }
      ],
      "output_field": "sehri_time",
      "auto_correct": false
    }
    ```
    """
    proxy = LLMProxy()

    result: ProxyResult = await proxy.complete(
        provider=request.provider,
        messages=[m.model_dump() for m in request.messages],
        model=request.model,
        validation_rules=request.validation_rules,
        output_field=request.output_field,
        auto_correct=request.auto_correct,
        provider_api_key=request.provider_api_key,
        base_url=request.base_url,
        extra_params=request.extra_params,
        db_session=db,
    )

    # Surface LLM-level errors as 502
    if result.error and not result.content:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error,
        )

    # Build optional validation summary
    val_summary: Optional[ValidationSummary] = None
    if result.validation is not None:
        v = result.validation
        corrected_count = len(getattr(v, "corrections", []) if hasattr(v, "corrections") else [])
        val_summary = ValidationSummary(
            is_valid=v.is_valid,
            total_rules=getattr(v, "total_rules", len(request.validation_rules)),
            violations=len(v.violations) if hasattr(v, "violations") else 0,
            auto_corrected=corrected_count,
        )

    return CompleteResponse(
        content=result.content,
        raw_content=result.raw_content,
        output=result.output,
        provider=result.provider,
        model=result.model,
        usage=result.usage,
        latency_ms=result.latency_ms,
        error=result.error or "",
        validation=val_summary,
    )
