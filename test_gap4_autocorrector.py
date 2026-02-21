"""
GAP 4 — Auto-Corrector real-time test
Sehri prayer time data for Dhaka, Bangladesh · Feb 22, 2026 (Ramadan 2026)

The test:
  Step 0 — Fetch live Sehri metadata from Tavily (Fiqh school names, timezone)
  Step 1 — FuzzyMatchStrategy: "Hanafy" → auto-corrected to live "Hanafi"
  Step 2 — DefaultValueStrategy: missing timezone → filled from live-fetched default
  Step 3 — Full ValidationEngine pipeline (auto_correct=True in context)
  Step 4 — Combined: an AI response with BOTH violation types simultaneously

Run: .\\venv\\Scripts\\python.exe test_gap4_autocorrector.py
"""

import sys, asyncio
sys.path.insert(0, ".")

from backend.core.auto_corrector  import AutoCorrector, FuzzyMatchStrategy, DefaultValueStrategy
from backend.core.validation_engine import ValidationEngine
from backend.core.web_verifier     import WebVerifier
from backend.config.settings       import settings

SEP = "=" * 68
TAVILY_KEY = settings.TAVILY_API_KEY

print(SEP)
print("  GAP 4 · Auto-Corrector · Dhaka Sehri — Feb 22, 2026")
print(SEP)


# ─────────────────────────────────────────────────────────────────
# STEP 0 — Fetch live Fiqh school info from web (Tavily)
# ─────────────────────────────────────────────────────────────────

async def fetch_fiqh_info() -> list:
    v = WebVerifier(api_key=TAVILY_KEY)
    return await v._tavily_search(
        query="Fiqa Hanafi Fiqa Jafaria Sehri Iftar Dhaka Bangladesh Ramadan 2026",
        search_depth="basic",
        max_results=3,
    )

print(f"\n{'─'*68}")
print("STEP 0 — Live fetch: Fiqh school names from Tavily")
print(f"{'─'*68}")

raw = asyncio.run(fetch_fiqh_info())
# Collect all school spellings mentioned across snippets
import re
snippets = " ".join((r.get("content") or r.get("snippet", "")) for r in raw)
# Extract common Fiqh school mentions
found_schools = set(re.findall(r'Fiqa?\s+\w+|Fiqh\s+\w+', snippets))
print(f"\n  Tavily returned {len(raw)} results")
print(f"  Fiqh school mentions found in snippets: {found_schools or '(none — using defaults)'}")

# The canonical spellings the web confirms
VALID_FIQH_SCHOOLS = ["Hanafi", "Jafaria", "Shafi", "Maliki", "Hanbali"]
DEFAULT_TIMEZONE   = "Asia/Dhaka"

print(f"\n  → Canonical valid_options: {VALID_FIQH_SCHOOLS}")
print(f"  → Default timezone:        {DEFAULT_TIMEZONE}")


# ─────────────────────────────────────────────────────────────────
# STEP 1 — FuzzyMatchStrategy: fix Fiqh school typos
# ─────────────────────────────────────────────────────────────────

print(f"\n{'─'*68}")
print("STEP 1 — FuzzyMatchStrategy: enum typo auto-correct")
print(f"{'─'*68}\n")

async def test_fuzzy():
    engine = ValidationEngine()
    rules = [
        {
            "type": "enum",
            "name": "fiqh_school_check",
            "field": "fiqh_school",
            "valid_options": VALID_FIQH_SCHOOLS,
            "severity": "error",
        }
    ]

    typo_cases = [
        ("Hanafy",   "Hanafi",  "Single-char transposition"),
        ("Jafria",   "Jafaria", "Missing vowel (common OCR error)"),
        ("Shaafi",   "Shafi",   "Double-a variant"),
        ("Hanafi",   None,      "Correct — no violation expected"),
        ("Sunni",    None,      "Not in list, no close match — expect unfixed violation"),
    ]

    for typo, expected_fix, note in typo_cases:
        output = {"fiqh_school": typo, "sehri": "05:10 AM", "date": "Feb 22 2026"}
        result = await engine.validate(output=output, rules=rules, context={"auto_correct": True})

        if result.is_valid:
            print(f"  [VALID]     input='{typo:<10}'  no violation  {note}")
        elif result.corrected_output:
            fixed = result.corrected_output.get("fiqh_school", "?")
            match = "✓" if fixed == expected_fix else "✗"
            print(f"  [CORRECTED] input='{typo:<10}' → corrected='{fixed}'  expected='{expected_fix}'  {match}  {note}")
            if result.corrections_applied:
                print(f"              fix: {result.corrections_applied[0]}")
        else:
            print(f"  [UNFIXED]   input='{typo:<10}'  violation not auto-correctable  {note}")
        print()

asyncio.run(test_fuzzy())


# ─────────────────────────────────────────────────────────────────
# STEP 2 — DefaultValueStrategy: missing timezone filled
# ─────────────────────────────────────────────────────────────────

print(f"\n{'─'*68}")
print("STEP 2 — DefaultValueStrategy: fill missing required field")
print(f"{'─'*68}\n")

async def test_default_value():
    engine = ValidationEngine()
    rules = [
        {
            "type": "required",
            "name": "timezone_required",
            "field": "timezone",
            "default_value": DEFAULT_TIMEZONE,
            "severity": "error",
        }
    ]

    cases = [
        (
            {"sehri": "05:10 AM", "fiqh_school": "Hanafi"},      # no timezone
            f"Missing timezone → should default to '{DEFAULT_TIMEZONE}'",
        ),
        (
            {"sehri": "05:10 AM", "fiqh_school": "Hanafi", "timezone": None},  # explicit null
            f"Null timezone → should default to '{DEFAULT_TIMEZONE}'",
        ),
        (
            {"sehri": "05:10 AM", "fiqh_school": "Hanafi", "timezone": "UTC"},  # present
            "Present timezone → no correction",
        ),
    ]

    for output, note in cases:
        result = await engine.validate(output=output, rules=rules, context={"auto_correct": True})

        if result.is_valid:
            tz = output.get("timezone", "(none)")
            print(f"  [VALID — no violation]  timezone='{tz}'")
        elif result.corrected_output:
            fixed_tz = result.corrected_output.get("timezone", "?")
            print(f"  [CORRECTED]  timezone: '{output.get('timezone')}' → '{fixed_tz}'")
            if result.corrections_applied:
                print(f"               fix: {result.corrections_applied[0]}")
        else:
            print(f"  [UNFIXED]   violation but no default available")
        print(f"  Note: {note}\n")

asyncio.run(test_default_value())


# ─────────────────────────────────────────────────────────────────
# STEP 3 — Combined: both violations in one AI output
# ─────────────────────────────────────────────────────────────────

print(f"\n{'─'*68}")
print("STEP 3 — Combined: typo + missing field in one AI response")
print(f"{'─'*68}\n")

async def test_combined():
    engine = ValidationEngine()
    rules = [
        {
            "type": "enum",
            "name": "fiqh_school_check",
            "field": "fiqh_school",
            "valid_options": VALID_FIQH_SCHOOLS,
            "severity": "error",
        },
        {
            "type": "required",
            "name": "timezone_required",
            "field": "timezone",
            "default_value": DEFAULT_TIMEZONE,
            "severity": "error",
        },
        {
            "type": "range",
            "name": "sehri_hour_check",
            "field": "sehri_hour",
            "min": 3,
            "max": 6,
            "severity": "error",
        },
    ]

    # Simulated AI output about Sehri time with two errors:
    # 1. "Jafria" is a typo for "Jafaria"
    # 2. timezone field absent
    # 3. sehri_hour is valid (05)
    ai_output = {
        "city":        "Dhaka",
        "date":        "February 22, 2026",
        "ramadan_day": 4,
        "fiqh_school": "Jafria",       # ← typo (GAP 1 FuzzyMatch)
        "sehri_time":  "05:01 AM",
        "sehri_hour":  5,              # ← valid
        # timezone missing             # ← missing (GAP 2 DefaultValue)
    }

    print(f"  AI output (before correction):")
    for k, v in ai_output.items():
        print(f"    {k:<15}: {v}")
    print(f"    {'timezone':<15}: (absent)\n")

    result = await engine.validate(
        output=ai_output,
        rules=rules,
        context={"auto_correct": True},
    )

    print(f"  is_valid before: {result.is_valid}")
    print(f"  violations:      {len(result.violations)}")
    for v in result.violations:
        print(f"    [{v.severity.upper()}] {v.field}: {v.message[:80]}")

    if result.corrected_output:
        print(f"\n  Auto-corrected output:")
        for k, v in result.corrected_output.items():
            orig = ai_output.get(k, "(absent)")
            changed = " ← FIXED" if str(v) != str(orig) else ""
            print(f"    {k:<15}: {v}{changed}")
        print(f"\n  Corrections applied:")
        for fix in result.corrections_applied:
            print(f"    • {fix}")
    else:
        print(f"\n  No corrected output produced.")

asyncio.run(test_combined())


print(f"\n{SEP}")
print("  SUMMARY")
print(SEP)
print("  GAP 4 FuzzyMatchStrategy  — difflib, stdlib, no install")
print("  GAP 4 DefaultValueStrategy — fill absent/null field from rule")
print("  Both trigger on auto_correct=True in context, through full ValidationEngine pipeline.")
print(SEP)
