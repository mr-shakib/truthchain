"""
GAP 5 — External Reference Connectors real-time test
Dhaka, Bangladesh · Feb 22, 2026 (Ramadan 2026 — Day 4)

Live source used throughout: https://api.aladhan.com  (free, no API key)

Steps:
  Step 0 — Raw Aladhan fetch: get the real Fajr time for today
  Step 1 — http_get_200: check Aladhan endpoint is live
  Step 2 — http_json_field: read Fajr from Aladhan JSON automatically
  Step 3 — aladhan_fajr_in_range: validate claimed Sehri times
  Step 4 — Full ValidationEngine pipeline with external_ref rules
  Step 5 — Unregistered-connector graceful degradation

Run: .\\venv\\Scripts\\python.exe test_gap5_external_ref.py
"""

import sys, asyncio, json
sys.path.insert(0, ".")

from backend.core.external_reference import (
    ExternalReferenceValidator, ConnectorResult,
)
from backend.core.validation_engine import ValidationEngine

SEP = "=" * 68
ALADHAN_URL = (
    "https://api.aladhan.com/v1/timingsByCity"
    "?city=Dhaka&country=Bangladesh&method=1&date=22-02-2026"
)

print(SEP)
print("  GAP 5 · External Reference Connectors · Dhaka Sehri — Feb 22, 2026")
print(SEP)

# ─────────────────────────────────────────────────────────────────
# STEP 0 — Raw fetch to see the full Aladhan response first
# ─────────────────────────────────────────────────────────────────

print(f"\n{'─'*68}")
print("STEP 0 — Raw Aladhan API fetch (source of truth)")
print(f"{'─'*68}\n")

import httpx

async def fetch_raw():
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as c:
        r = await c.get(ALADHAN_URL)
        return r.json()

raw = asyncio.run(fetch_raw())
timings = raw.get("data", {}).get("timings", {})
date_info = raw.get("data", {}).get("date", {}).get("readable", "?")

print(f"  Date  : {date_info}")
print(f"  Timings from Aladhan API:")
for name, t in timings.items():
    marker = " ◄ Sehri ends at Fajr" if name == "Fajr" else ""
    print(f"    {name:<12}: {t}{marker}")

official_fajr = timings.get("Fajr", "?")
print(f"\n  → Official Fajr (Sehri end): {official_fajr}")


# ─────────────────────────────────────────────────────────────────
# STEP 1 — http_get_200: liveness check
# ─────────────────────────────────────────────────────────────────

print(f"\n{'─'*68}")
print("STEP 1 — http_get_200: Aladhan endpoint liveness")
print(f"{'─'*68}\n")

async def test_http_get_200():
    cases = [
        (ALADHAN_URL,                        "Aladhan API — should be 200"),
        ("https://api.aladhan.com/v1/bogus", "Bad path — should be non-200 → FAIL"),
    ]
    for url, note in cases:
        result = await ExternalReferenceValidator.check("http_get_200", url)
        flag = "EXISTS ✓" if result.exists else "FAIL   ✗"
        print(f"  [{flag}]  {result.detail[:80]}")
        print(f"  Note   : {note}")
        print(f"  Latency: {result.latency_ms} ms\n")

asyncio.run(test_http_get_200())


# ─────────────────────────────────────────────────────────────────
# STEP 2 — http_json_field: auto-read Fajr time from JSON
# ─────────────────────────────────────────────────────────────────

print(f"\n{'─'*68}")
print("STEP 2 — http_json_field: read Fajr from Aladhan JSON")
print(f"{'─'*68}\n")

async def test_http_json_field():
    # Just check that the field exists (no expected comparison)
    result = await ExternalReferenceValidator.check(
        "http_json_field",
        value=None,   # value unused — URL defines the source
        params={
            "url": ALADHAN_URL,
            "json_path": "data.timings.Fajr",
        },
    )
    print(f"  [{'EXISTS ✓' if result.exists else 'FAIL   ✗'}]  {result.detail}")
    if result.raw:
        print(f"  Found  : {result.raw.get('found', '?')}")
    print()

    # Cross-check: does Dhga today also have an Isha time?
    result2 = await ExternalReferenceValidator.check(
        "http_json_field",
        value=None,
        params={
            "url": ALADHAN_URL,
            "json_path": "data.timings.Isha",
        },
    )
    print(f"  [{'EXISTS ✓' if result2.exists else 'FAIL   ✗'}]  {result2.detail}")
    if result2.raw:
        print(f"  Found  : {result2.raw.get('found', '?')}")
    print()

asyncio.run(test_http_json_field())


# ─────────────────────────────────────────────────────────────────
# STEP 3 — aladhan_fajr_in_range: validate claimed Sehri times
# ─────────────────────────────────────────────────────────────────

print(f"\n{'─'*68}")
print(f"STEP 3 — aladhan_fajr_in_range: validate Sehri claims")
print(f"  (Official Fajr = {official_fajr})")
print(f"{'─'*68}\n")

ALADHAN_PARAMS = {
    "city":              "Dhaka",
    "country":           "Bangladesh",
    "date":              "22-02-2026",
    "tolerance_minutes": 15,
}

async def test_aladhan_range():
    cases = [
        ("05:10",  "Within 15 min of official Fajr — should PASS"),
        ("05:01",  "Fiqa Jafaria time from web — should PASS (within 15 min)"),
        ("04:50",  "Borderline — 20 min early — should FAIL"),
        ("11:59",  "Impossible — 11:59 PM — should FAIL"),
        ("02:00",  "2 AM — completely wrong — should FAIL"),
    ]

    for claimed, note in cases:
        result = await ExternalReferenceValidator.check(
            "aladhan_fajr_in_range",
            value=claimed,
            params=ALADHAN_PARAMS,
        )
        flag = "EXISTS ✓" if result.exists else "FAIL   ✗"
        print(f"  [{flag}]  claimed={claimed}  {result.detail}")
        print(f"  Note   : {note}")
        print(f"  Latency: {result.latency_ms} ms\n")

asyncio.run(test_aladhan_range())


# ─────────────────────────────────────────────────────────────────
# STEP 4 — Full ValidationEngine pipeline
# ─────────────────────────────────────────────────────────────────

print(f"\n{'─'*68}")
print("STEP 4 — Full ValidationEngine pipeline with external_ref rules")
print(f"{'─'*68}\n")

async def test_pipeline():
    engine = ValidationEngine()
    rules = [
        # Rule A — source URL must be reachable
        {
            "type":      "external_ref",
            "name":      "source_url_live",
            "field":     "source_url",
            "connector": "http_get_200",
            "severity":  "warning",
        },
        # Rule B — claimed Sehri time must match Aladhan official within 15 min
        {
            "type":      "external_ref",
            "name":      "sehri_time_valid",
            "field":     "sehri_time",
            "connector": "aladhan_fajr_in_range",
            "params":    {**ALADHAN_PARAMS},
            "severity":  "error",
        },
    ]

    test_outputs = [
        {
            "label":      "Correct AI response",
            "source_url": ALADHAN_URL,
            "sehri_time": "05:10",
            "city":       "Dhaka",
        },
        {
            "label":      "Wrong Sehri time (11:59 PM)",
            "source_url": ALADHAN_URL,
            "sehri_time": "23:59",
            "city":       "Dhaka",
        },
        {
            "label":      "Dead source URL + wrong time",
            "source_url": "https://api.aladhan.com/v1/404notfound",
            "sehri_time": "02:00",
            "city":       "Dhaka",
        },
    ]

    for output in test_outputs:
        label = output.pop("label")
        result = await engine.validate(output=output, rules=rules)
        verdict = "✓ VALID" if result.is_valid else "✗ INVALID"
        print(f"  [{verdict}]  {label}")
        for v in result.violations:
            print(f"    [{v.severity.upper()}] {v.field}: {v.message[:100]}")
        print()

asyncio.run(test_pipeline())


# ─────────────────────────────────────────────────────────────────
# STEP 5 — Unregistered connector: graceful degradation
# ─────────────────────────────────────────────────────────────────

print(f"\n{'─'*68}")
print("STEP 5 — Graceful degradation: unregistered connector")
print(f"{'─'*68}\n")

async def test_unregistered():
    engine = ValidationEngine()
    rules = [{
        "type":      "external_ref",
        "field":     "customer_id",
        "connector": "stripe_customer",   # not registered
        "severity":  "error",
    }]
    result = await engine.validate(
        output={"customer_id": "cus_abc123"},
        rules=rules,
    )
    print(f"  is_valid: {result.is_valid}")
    for v in result.violations:
        print(f"  [{v.severity.upper()}] {v.message[:110]}")
    print(f"\n  Registered connectors: {ExternalReferenceValidator.registered_names()}")

asyncio.run(test_unregistered())


print(f"\n{SEP}")
print("  SUMMARY")
print(SEP)
print("  GAP 5  http_get_200            — live HTTP liveness check (no key)")
print("  GAP 5  http_json_field         — live JSON field extraction (no key)")
print("  GAP 5  aladhan_fajr_in_range   — real Fajr time from Aladhan API")
print("  GAP 5  external_ref rule type  — wired into ValidationEngine pipeline")
print("  GAP 5  Graceful degradation    — unregistered connector → warning")
print(SEP)
