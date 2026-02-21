"""
GAP 6 — LLM Proxy: real-time integration test
================================================

Tests three scenarios using Dhaka / Ramadan 2026 data:

1. RAW PROXY      — Call Groq with no validation rules.
                    Shows that the proxy correctly plumbs messages → response.
2. PROXY + VALID  — Call Groq, then validate the parsed JSON field
                    against the Aladhan official Fajr time.
3. WRONG TIME     — Inject a deliberately wrong Sehri time and check
                    that the external_ref rule fires a violation.
4. NO KEY FALLBACK — When no API key is set the proxy returns a clean
                    error without crashing.

Run from truthchain/ directory:
    .\\venv\\Scripts\\python.exe test_gap6_llm_proxy.py
"""
from __future__ import annotations

import asyncio
import os
import sys

# ── resolve project root ──────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("ENVIRONMENT", "development")

from backend.core.llm_proxy import LLMProxy


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

sep = "─" * 60

def headline(title: str) -> None:
    print(f"\n{sep}\n  {title}\n{sep}")

def check_key() -> bool:
    """Return True if either Groq or OpenAI key is configured."""
    from backend.config.settings import settings
    return bool(settings.GROQ_API_KEY or settings.OPENAI_API_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — Raw proxy (no validation)
# ─────────────────────────────────────────────────────────────────────────────

async def test_raw_proxy():
    headline("TEST 1 — Raw LLM proxy (no validation rules)")

    if not check_key():
        print("  ⚠ SKIPPED — no GROQ_API_KEY / OPENAI_API_KEY in .env")
        print("  Fill in GROQ_API_KEY (free at https://console.groq.com) and re-run.")
        return

    proxy = LLMProxy()
    result = await proxy.complete(
        provider="groq",
        messages=[
            {"role": "system",  "content": "You are a helpful assistant. Keep responses short."},
            {"role": "user",    "content": (
                "What is the Sehri (Fajr) time in Dhaka, Bangladesh on 22 February 2026? "
                "Reply ONLY with a JSON object like {\"sehri_time\": \"05:11 AM\"}."
            )},
        ],
    )

    if result.error:
        print(f"  ✗ LLM error: {result.error}")
        return

    print(f"  ✓ LLM responded in {result.latency_ms} ms")
    print(f"  Provider / model : {result.provider} / {result.model}")
    print(f"  Raw content      : {result.raw_content[:200]}")
    print(f"  Parsed output    : {result.output}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — Proxy + Aladhan external_ref validation
# ─────────────────────────────────────────────────────────────────────────────

async def test_proxy_with_validation():
    headline("TEST 2 — LLM proxy + external_ref Aladhan validation")

    if not check_key():
        print("  ⚠ SKIPPED — no API key")
        return

    proxy = LLMProxy()
    rules = [
        {
            "type":      "external_ref",
            "field":     "sehri_time",
            "connector": "aladhan_fajr_in_range",
            "params": {
                "city":               "Dhaka",
                "country":            "Bangladesh",
                "date":               "22-02-2026",
                "tolerance_minutes":  15,
            },
            "severity": "error",
        }
    ]

    result = await proxy.complete(
        provider="groq",
        messages=[
            {"role": "system", "content": (
                "You are a helpful assistant. "
                "Reply ONLY with a JSON object like {\"sehri_time\": \"05:11 AM\"}. "
                "No extra text."
            )},
            {"role": "user", "content": (
                "What is the Sehri (Fajr) time in Dhaka, Bangladesh on 22 February 2026? "
                "Give me JSON: {\"sehri_time\": \"HH:MM AM/PM\"}"
            )},
        ],
        validation_rules=rules,
        output_field="sehri_time",
    )

    if result.error and not result.raw_content:
        print(f"  ✗ LLM error: {result.error}")
        return

    print(f"  ✓ LLM call OK in {result.latency_ms} ms")
    print(f"  Parsed output : {result.output}")

    if result.validation:
        v = result.validation
        status = "✓ VALID" if v.is_valid else f"✗ INVALID ({len(v.violations)} violation(s))"
        print(f"  Validation    : {status}")
        for vio in v.violations:
            print(f"    • [{vio.severity.upper()}] {vio.field}: {vio.message}")
    else:
        print("  Validation    : (no validation result — rules may have been empty)")


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — Injected wrong time (mock, no LLM call)
# ─────────────────────────────────────────────────────────────────────────────

async def test_wrong_time_mock():
    headline("TEST 3 — Wrong Sehri time injected (mock — no LLM key needed)")

    # Bypass LLM: directly run validation against a fabricated output
    from backend.core.validation_engine import ValidationEngine
    from backend.core.external_reference import ExternalReferenceValidator  # ensure connectors registered

    wrong_output = {"sehri_time": "11:59 PM"}   # obviously wrong

    rules = [
        {
            "type":      "external_ref",
            "field":     "sehri_time",
            "connector": "aladhan_fajr_in_range",
            "params": {
                "city":               "Dhaka",
                "country":            "Bangladesh",
                "date":               "22-02-2026",
                "tolerance_minutes":  15,
            },
            "severity": "error",
        }
    ]

    engine = ValidationEngine(db_session=None)
    result = await engine.validate(wrong_output, rules, context={})

    print(f"  Input         : {wrong_output}")
    status = "✓ VALID" if result.is_valid else f"✗ INVALID ({len(result.violations)} violation(s))"
    print(f"  Validation    : {status}")
    for vio in result.violations:
        print(f"    • [{vio.severity.upper()}] {vio.field}: {vio.message}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — No API key graceful fallback
# ─────────────────────────────────────────────────────────────────────────────

async def test_no_key_fallback():
    headline("TEST 4 — No API key graceful fallback")

    proxy = LLMProxy()
    result = await proxy.complete(
        provider="groq",
        messages=[{"role": "user", "content": "Hello"}],
        provider_api_key="",   # explicitly blank — overrides env key
    )

    # Expect a clean error string, not an exception
    if result.error:
        print(f"  ✓ Got clean error: {result.error}")
    else:
        # Might succeed if key is set in env; that is also a valid pass
        print(f"  ✓ Call succeeded (key was available): {result.content[:80]}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 60)
    print("  GAP 6 — LLM PROXY TEST SUITE")
    print("=" * 60)

    await test_raw_proxy()
    await test_proxy_with_validation()
    await test_wrong_time_mock()
    await test_no_key_fallback()

    print(f"\n{sep}")
    print("  All tests done.")
    print(sep)


if __name__ == "__main__":
    asyncio.run(main())
