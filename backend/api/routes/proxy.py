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


class ViolationItem(BaseModel):
    rule_name:  str
    severity:   str
    message:    str
    suggestion: Optional[str] = None
    metadata:   Optional[Dict[str, Any]] = None


class ValidationSummary(BaseModel):
    is_valid:          bool
    total_rules:       int
    violations:        int
    auto_corrected:    int
    violations_detail: List[ViolationItem] = []


class CompleteResponse(BaseModel):
    """Response from POST /v1/complete."""

    content:               str
    raw_content:           str
    output:                Dict[str, Any]
    provider:              str
    model:                 str
    usage:                 Dict[str, Any]
    latency_ms:            int
    error:                 str
    validation:            Optional[ValidationSummary] = None
    web_grounded_answer:   Optional[str] = None   # synthesized from web sources when LLM answer is contradicted
    grounding_reason:      Optional[str] = None   # 'contradicted' | 'llm_uncertain'


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
    web_grounded_answer: Optional[str] = None
    grounding_reason: Optional[str] = None

    if result.validation is not None:
        v = result.validation
        corrected_count = len(getattr(v, "corrections", []) if hasattr(v, "corrections") else [])
        raw_violations = v.violations if hasattr(v, "violations") else []
        val_summary = ValidationSummary(
            is_valid=v.is_valid,
            total_rules=getattr(v, "total_rules", len(request.validation_rules)),
            # "info" severity is informational — exclude from actionable violation count
            violations=len([vl for vl in raw_violations if getattr(vl, "severity", "") in ("error", "warning")]),
            auto_corrected=corrected_count,
            violations_detail=[
                ViolationItem(
                    rule_name=viol.rule_name,
                    severity=viol.severity,
                    message=viol.message,
                    suggestion=getattr(viol, "suggestion", None),
                    metadata=getattr(viol, "metadata", None),
                )
                for viol in raw_violations
            ],
        )

        # Phrases that indicate the LLM couldn't answer the question from its own knowledge
        _LLM_CANT_ANSWER = (
            "i don't know", "i do not know", "i'm unable", "i am unable",
            "i cannot provide", "i can't provide", "i don't have access",
            "i do not have access", "my training data", "as of my training",
            "as of my knowledge cutoff", "i don't have real-time",
            "i don't have current", "i cannot access", "i can't access",
            "i'm not able to provide", "would need to know the date",
        )
        llm_admits_ignorance = any(
            phrase in (result.content or "").lower()
            for phrase in _LLM_CANT_ANSWER
        )

        # Trigger grounding when:
        # 1. Web found CONTRADICTED/UNCERTAIN verdict (LLM gave wrong answer), OR
        # 2. LLM admitted it doesn't know AND web sources are available
        _is_contradicted = lambda viol: (
            getattr(viol, "severity", "") in ("error", "warning")
            and (getattr(viol, "metadata", None) or {}).get("verdict") in ("CONTRADICTED", "UNCERTAIN")
        )
        web_violation = next(
            (viol for viol in raw_violations
             if (getattr(viol, "metadata", None) or {}).get("sources")
             and (
                 # Case 1: LLM gave a factually wrong/uncertain answer
                 _is_contradicted(viol)
                 or
                 # Case 2: LLM admitted it doesn't know but web has the answer
                 llm_admits_ignorance
             )),
            None,
        )
        if web_violation:
            # Record why grounding triggered
            if _is_contradicted(web_violation):
                grounding_reason = "contradicted"
            elif llm_admits_ignorance:
                grounding_reason = "llm_uncertain"
            try:
                sources = web_violation.metadata["sources"]  # type: ignore[index]
                # Build grounding context from snippets
                context_blocks = []
                for idx, src in enumerate(sources[:3], 1):
                    snippet = src.get("snippet", "").strip()
                    if snippet:
                        context_blocks.append(
                            f"[{idx}] {src.get('title', '')}\n{snippet}\nURL: {src.get('url', '')}"
                        )

                if context_blocks:
                    user_query = next(
                        (m.content for m in reversed(request.messages) if m.role == "user"),
                        "",
                    )
                    grounding_prompt = (
                        "You are a fact-checking assistant. "
                        "Answer the user's question using ONLY the web sources below. "
                        "Be concise (2-4 sentences). Mention which source(s) support your answer."
                    )
                    sources_text = "\n\n".join(context_blocks)
                    grounding_messages = [
                        {"role": "system", "content": grounding_prompt},
                        {
                            "role": "user",
                            "content": (
                                f"Question: {user_query}\n\n"
                                f"Web Sources:\n{sources_text}\n\n"
                                "Answer based on these sources only:"
                            ),
                        },
                    ]
                    grounding_result = await proxy.complete(
                        provider=request.provider,
                        messages=grounding_messages,
                        model=request.model,
                        validation_rules=[],
                        auto_correct=False,
                        provider_api_key=request.provider_api_key,
                        db_session=db,
                    )
                    if grounding_result.content and not grounding_result.error:
                        web_grounded_answer = grounding_result.content
            except Exception:
                pass  # grounding is best-effort; never fail the main response

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
        web_grounded_answer=web_grounded_answer,
        grounding_reason=grounding_reason,
    )
