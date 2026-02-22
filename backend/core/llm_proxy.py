"""
LLM Proxy for TruthChain
=========================
Sits between the developer and any OpenAI-compatible LLM provider.

Flow:
  complete(provider, model, messages, validation_rules, ...)
      → call LLM API via httpx (OpenAI-compatible format)
      → parse LLM content into output dict
      → ValidationEngine.validate(output, rules, {auto_correct})
      → return ProxyResult

Providers built-in (all use the OpenAI chat-completions format):
  "openai"   → https://api.openai.com/v1        key: OPENAI_API_KEY
  "groq"     → https://api.groq.com/openai/v1   key: GROQ_API_KEY
  "custom"   → caller-supplied base_url          key: caller-supplied provider_api_key

No extra SDK required — only httpx (already in requirements).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from .validation_engine import ValidationEngine, ValidationResult


# ──────────────────────────────────────────────────────────────────────────────
# Provider registry
# ──────────────────────────────────────────────────────────────────────────────

PROVIDER_BASE_URLS: Dict[str, str] = {
    "openai":    "https://api.openai.com/v1",
    "groq":      "https://api.groq.com/openai/v1",
    "anthropic": "https://api.anthropic.com/v1",   # note: different format — handled separately
}

# Convenient default model per provider
PROVIDER_DEFAULT_MODELS: Dict[str, str] = {
    "openai":    "gpt-4o-mini",
    "groq":      "llama-3.1-8b-instant",
    "custom":    "gpt-4o-mini",
}


# ──────────────────────────────────────────────────────────────────────────────
# Result types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ProxyResult:
    """
    Complete result from a proxied LLM call.

    Attributes:
        content             The final content string (auto-corrected if applicable).
        raw_content         The original LLM response before any correction.
        output              Parsed dict form of the content (for structured outputs).
        validation          Full TruthChain ValidationResult.
        provider            Which LLM provider was used.
        model               Which model was used.
        usage               Token usage from the LLM (prompt_tokens, completion_tokens, etc.).
        latency_ms          Total wall-clock time in milliseconds.
        error               Non-empty if the LLM call itself failed.
    """
    content:     str
    raw_content: str
    output:      Dict[str, Any]
    validation:  Optional[ValidationResult]
    provider:    str
    model:       str
    usage:       Dict[str, Any] = field(default_factory=dict)
    latency_ms:  int = 0
    error:       str = ""


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _resolve_key(provider: str, provider_api_key: Optional[str]) -> str:
    """Return the API key to use for a provider."""
    if provider_api_key:
        return provider_api_key

    from ..config.settings import settings
    key_map = {
        "openai": settings.OPENAI_API_KEY,
        "groq":   settings.GROQ_API_KEY,
    }
    return key_map.get(provider, "")


def _parse_content_to_output(content: str, output_field: Optional[str]) -> Dict[str, Any]:
    """
    Try to extract a structured dict from the LLM response string.

    Attempts (in order):
    1. Parse the whole string as JSON.
    2. Find a JSON block inside triple-backticks.
    3. Fall back to wrapping in ``{output_field: content}`` or ``{"content": content}``.
    """
    stripped = content.strip()

    # 1. Direct JSON parse
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. JSON code block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. Fallback: wrap as single field
    key = output_field or "content"
    return {key: stripped}


# ──────────────────────────────────────────────────────────────────────────────
# LLMProxy
# ──────────────────────────────────────────────────────────────────────────────

class LLMProxy:
    """
    Proxy an LLM call through TruthChain validation.

    Example::

        proxy = LLMProxy()
        result = await proxy.complete(
            provider="groq",
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "What is the Sehri time in Dhaka today?"}],
            validation_rules=[
                {"type": "external_ref", "field": "sehri_time",
                 "connector": "aladhan_fajr_in_range",
                 "params": {"city": "Dhaka", "country": "Bangladesh", "tolerance_minutes": 15}}
            ],
            output_field="sehri_time",
            auto_correct=False,
        )
        print(result.content)
        print(result.validation.is_valid)
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def complete(
        self,
        provider:          str,
        messages:          List[Dict[str, str]],
        model:             Optional[str] = None,
        validation_rules:  Optional[List[Dict[str, Any]]] = None,
        output_field:      Optional[str] = None,
        auto_correct:      bool = False,
        provider_api_key:  Optional[str] = None,
        base_url:          Optional[str] = None,
        extra_params:      Optional[Dict[str, Any]] = None,
        db_session:        Any = None,
    ) -> ProxyResult:
        """
        Call an LLM and validate the response.

        Args:
            provider:         One of ``"openai"``, ``"groq"``, or ``"custom"``.
            messages:         OpenAI-format messages list.
            model:            Model name. Defaults to provider default.
            validation_rules: TruthChain rules to apply to the parsed output.
            output_field:     Expected top-level key in the LLM JSON response
                              (used as fallback wrap key if response is plain text).
            auto_correct:     If True, attempt auto-correction via AutoCorrector strategies
                              including LLMRewriteStrategy.
            provider_api_key: Override API key (takes precedence over settings).
            base_url:         Override base URL (required for ``"custom"`` provider).
            extra_params:     Additional JSON body params forwarded to the LLM API.
            db_session:       Optional SQLAlchemy session for reference validation.

        Returns:
            ProxyResult
        """
        t0 = time.monotonic()
        model = model or PROVIDER_DEFAULT_MODELS.get(provider, "gpt-4o-mini")
        validation_rules = validation_rules or []
        extra_params = extra_params or {}

        # ── 1. Resolve endpoint + key ─────────────────────────────────────────
        api_key = _resolve_key(provider, provider_api_key)
        url_base = base_url or PROVIDER_BASE_URLS.get(provider, PROVIDER_BASE_URLS["openai"])
        chat_url = f"{url_base}/chat/completions"

        if not api_key:
            latency = int((time.monotonic() - t0) * 1000)
            return ProxyResult(
                content="",
                raw_content="",
                output={},
                validation=None,
                provider=provider,
                model=model,
                latency_ms=latency,
                error=(
                    f"No API key for provider '{provider}'. "
                    f"Set {provider.upper()}_API_KEY in .env or pass provider_api_key."
                ),
            )

        # ── 2. Call the LLM ───────────────────────────────────────────────────
        body: Dict[str, Any] = {
            "model":    model,
            "messages": messages,
            **extra_params,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    chat_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type":  "application/json",
                    },
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            latency = int((time.monotonic() - t0) * 1000)
            return ProxyResult(
                content="", raw_content="", output={},
                validation=None, provider=provider, model=model,
                latency_ms=latency,
                error=f"LLM API error {exc.response.status_code}: {exc.response.text[:300]}",
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            return ProxyResult(
                content="", raw_content="", output={},
                validation=None, provider=provider, model=model,
                latency_ms=latency,
                error=f"LLM call failed: {exc}",
            )

        # ── 3. Extract content ────────────────────────────────────────────────
        raw_content: str = (
            data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
        )
        usage: Dict[str, Any] = data.get("usage", {})
        output = _parse_content_to_output(raw_content, output_field)

        # ── 4. Validate ───────────────────────────────────────────────────────
        validation: Optional[ValidationResult] = None
        if validation_rules:
            engine = ValidationEngine(db_session=db_session)
            context: Dict[str, Any] = {"auto_correct": auto_correct}
            validation = await engine.validate(
                output=output,
                rules=validation_rules,
                context=context,
            )
            # If auto-corrected, reflect the corrected content back
            if validation.corrected_output:
                output = validation.corrected_output
                # Rebuild content string from corrected output
                corrected_field_val = output.get(output_field or "content", "")
                content = (
                    json.dumps(output) if len(output) > 1
                    else str(corrected_field_val)
                )
            else:
                content = raw_content
        else:
            content = raw_content

        latency = int((time.monotonic() - t0) * 1000)
        return ProxyResult(
            content=content,
            raw_content=raw_content,
            output=output,
            validation=validation,
            provider=provider,
            model=model,
            usage=usage,
            latency_ms=latency,
        )
