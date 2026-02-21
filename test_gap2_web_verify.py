"""
GAP 2 smoke test — Web Search Grounding (Tavily)
Run: .\venv\Scripts\python.exe test_gap2_web_verify.py

Two modes:
  - Without TAVILY_API_KEY: tests graceful fallback (warning, no crash)
  - With    TAVILY_API_KEY: live search tests against real web results
"""
import sys
import asyncio
import os

sys.path.insert(0, ".")

from backend.core.web_verifier import WebVerifier, WebVerificationResult
from backend.core.rule_engine import RuleEngine
from backend.core.validation_engine import ValidationEngine
from backend.config.settings import settings

TAVILY_KEY = settings.TAVILY_API_KEY or os.environ.get("TAVILY_API_KEY", "")

print("=" * 65)
print("GAP 2 — Web Search Grounding Smoke Test")
print("=" * 65)
if TAVILY_KEY:
    print(f"  TAVILY_API_KEY: found ({TAVILY_KEY[:12]}...)")
else:
    print("  TAVILY_API_KEY: NOT SET — running fallback / graceful-error path")
    print("  To run live tests, add TAVILY_API_KEY=tvly-... to truthchain/.env")
print()


# ---------------------------------------------------------------------------
# Test 1: Module imports and class instantiation
# ---------------------------------------------------------------------------
print("TEST 1 — Module imports and class structure")
from backend.core.web_verifier import WebVerifier, WebSource, WebVerificationResult

wv = WebVerifier(api_key="tvly-fake-key-for-import-test")
assert hasattr(wv, "verify"), "WebVerifier must have verify() method"
assert hasattr(wv, "_score_results"), "WebVerifier must have _score_results()"
print("  [PASS] WebVerifier imported and instantiated correctly")
print()


# ---------------------------------------------------------------------------
# Test 2: RuleEngine web_verify without API key → graceful warning
# ---------------------------------------------------------------------------
print("TEST 2 — RuleEngine: web_verify without API key → graceful warning")


async def test_no_key_fallback():
    # Temporarily clear the verifier to test no-key path
    import backend.core.rule_engine as re_mod
    original = re_mod._web_verifier
    re_mod._web_verifier = None

    # Patch settings to have empty key
    original_key = settings.TAVILY_API_KEY
    settings.TAVILY_API_KEY = ""

    try:
        engine = RuleEngine()
        output = {"claim": "The Earth orbits the Sun"}
        rules = [
            {
                "type": "web_verify",
                "field": "claim",
                "confidence_threshold": 0.7,
            }
        ]
        violations = await engine.validate(output, rules, None)
        assert len(violations) == 1, f"Expected 1 violation, got {len(violations)}"
        v = violations[0]
        assert v.severity == "warning", f"Expected warning severity, got {v.severity}"
        assert "TAVILY_API_KEY" in v.message, "Message should mention TAVILY_API_KEY"
        print(f"  [PASS] Got expected warning: {v.message[:90]}")
    finally:
        re_mod._web_verifier = original
        settings.TAVILY_API_KEY = original_key


asyncio.run(test_no_key_fallback())
print()


# ---------------------------------------------------------------------------
# Test 3: RuleEngine: missing field → warning
# ---------------------------------------------------------------------------
print("TEST 3 — RuleEngine: web_verify on missing field → warning")


async def test_missing_field():
    import backend.core.rule_engine as re_mod
    original = re_mod._web_verifier
    re_mod._web_verifier = None
    original_key = settings.TAVILY_API_KEY
    settings.TAVILY_API_KEY = ""

    try:
        engine = RuleEngine()
        output = {"other_field": "something"}
        rules = [{"type": "web_verify", "field": "claim", "confidence_threshold": 0.7}]
        violations = await engine.validate(output, rules, None)
        # Should warn about missing field OR missing API key
        assert len(violations) >= 1
        print(f"  [PASS] Got {len(violations)} violation(s): {violations[0].message[:80]}")
    finally:
        re_mod._web_verifier = original
        settings.TAVILY_API_KEY = original_key


asyncio.run(test_missing_field())
print()


# ---------------------------------------------------------------------------
# Test 4 (LIVE): Real Tavily search — only if API key set
# ---------------------------------------------------------------------------
if not TAVILY_KEY:
    print("TEST 4 — SKIPPED (no TAVILY_API_KEY)")
    print("  Add  TAVILY_API_KEY=tvly-...  to truthchain/.env to enable live tests")
else:
    print("TEST 4 — LIVE: WebVerifier.verify() with real Tavily search")

    async def test_live_verify():
        verifier = WebVerifier(api_key=TAVILY_KEY)

        # Case A: True claim — should be SUPPORTED
        print("\n  Case A: well-known true fact")
        result_a = await verifier.verify(
            claim="The Earth orbits the Sun and completes one orbit per year",
            max_results=5,
        )
        print(f"    web_confidence: {result_a.web_confidence}  verdict: {result_a.verdict}")
        for s in result_a.sources[:2]:
            print(f"    source: {s.title[:60]}  sem={s.semantic_score:.3f}")
        assert result_a.error is None or result_a.sources, "Should have results or non-fatal error"

        # Case B: False / disputed claim — should be CONTRADICTED or UNCERTAIN
        print("\n  Case B: likely false claim (Apple Q4 revenue off by ~10B)")
        result_b = await verifier.verify(
            claim="Apple Q4 2025 revenue was exactly 200 billion dollars",
            max_results=5,
        )
        print(f"    web_confidence: {result_b.web_confidence}  verdict: {result_b.verdict}")
        for s in result_b.sources[:2]:
            print(f"    source: {s.title[:60]}  sem={s.semantic_score:.3f}")

    asyncio.run(test_live_verify())
    print()

    # ---------------------------------------------------------------------------
    # Test 5 (LIVE): Full ValidationEngine pipeline with web_verify rule
    # ---------------------------------------------------------------------------
    print()
    print("TEST 5 — LIVE: Full ValidationEngine with web_verify rule")

    async def test_full_pipeline():
        engine = ValidationEngine()

        # Claim that should fail web grounding
        result = await engine.validate(
            output={"ai_response": "Apple Q4 2025 revenue was exactly 200 billion dollars"},
            rules=[
                {
                    "type": "web_verify",
                    "name": "revenue_fact_check",
                    "field": "ai_response",
                    "confidence_threshold": 0.7,
                    "severity": "error",
                }
            ],
        )
        print(f"  is_valid: {result.is_valid}")
        print(f"  violations: {len(result.violations)}")
        if result.violations:
            v = result.violations[0]
            print(f"  [{v.severity.upper()}] {v.message[:160]}")

    asyncio.run(test_full_pipeline())

print()
print("=" * 65)
print("GAP 2 smoke tests complete.")
print("=" * 65)
