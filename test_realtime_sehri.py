"""
Real-time integration test — Sehri (Suhoor) time for Dhaka, Bangladesh
Date: February 22, 2026 (Ramadan 2026)

Pipeline:
  Step 0  — Fetch actual Sehri time via Tavily (GAP 2)
  Step 1  — GAP 1: Semantic check  (correct claim vs wrong claim vs context)
  Step 2  — GAP 2: Web-verify      (correct claim → SUPPORTED, wrong claim → UNCERTAIN/CONTRADICTED)
  Step 3  — GAP 3: ML anomaly      (train on plausible Sehri times, flag impossible time)

Run: .\venv\Scripts\python.exe test_realtime_sehri.py
"""

import sys, asyncio, random
sys.path.insert(0, ".")
random.seed(0)

from backend.core.semantic_validator import SemanticValidator
from backend.core.web_verifier import WebVerifier
from backend.core.ml_anomaly_detector import MLAnomalyDetector
from backend.core.rule_engine import RuleEngine
from backend.core.validation_engine import ValidationEngine
from backend.config.settings import settings

TAVILY_KEY = settings.TAVILY_API_KEY
DATE_STR   = "February 22, 2026"
CITY       = "Dhaka, Bangladesh"

SEP = "=" * 68

print(SEP)
print(f"  Real-time Sehri time test — {CITY} — {DATE_STR}")
print(SEP)


# ═══════════════════════════════════════════════════════════════════
# STEP 0 — Fetch actual Sehri time from the web (Tavily)
# ═══════════════════════════════════════════════════════════════════

async def fetch_sehri_time() -> dict:
    """
    Query Tavily for today's Sehri time in Dhaka.
    Returns a dict with raw snippets so we can inspect what the web says.
    """
    verifier = WebVerifier(api_key=TAVILY_KEY)
    raw = await verifier._tavily_search(
        query=f"Sehri Suhoor time Dhaka Bangladesh {DATE_STR} Ramadan 2026",
        search_depth="advanced",
        max_results=7,
    )
    return raw


print(f"\n{'─'*68}")
print("STEP 0 — Fetching actual Sehri time from live web (Tavily)")
print(f"{'─'*68}")

raw_results = asyncio.run(fetch_sehri_time())

print(f"\nTavily returned {len(raw_results)} results:\n")
for i, r in enumerate(raw_results, 1):
    snippet = (r.get("content") or r.get("snippet", ""))[:300]
    print(f"  [{i}] {r.get('title', '')[:70]}")
    print(f"       {r.get('url', '')[:75]}")
    print(f"       Score: {r.get('score',0):.3f}")
    print(f"       {snippet}")
    print()

# Build a context string from the top-3 snippets for downstream tests
context_text = "\n".join(
    (r.get("content") or r.get("snippet", ""))[:400]
    for r in raw_results[:3]
)


# ═══════════════════════════════════════════════════════════════════
# STEP 1 — GAP 1: Semantic Contradiction Detector
# ═══════════════════════════════════════════════════════════════════

print(f"\n{'─'*68}")
print("STEP 1 — GAP 1: Semantic alignment check")
print(f"{'─'*68}\n")

sv = SemanticValidator()

cases = [
    (
        "The Sehri time in Dhaka today is approximately 5:10 AM.",
        context_text,
        0.4,
        "Reasonable claim — expect ALIGNED",
    ),
    (
        "There is no Ramadan in Bangladesh and Sehri is not practiced.",
        context_text,
        0.4,
        "Clearly wrong claim — expect CONTRADICTION",
    ),
    (
        "Sehri in Dhaka ends at 2:00 PM, after midday prayer.",
        context_text,
        0.4,
        "Impossible time — expect CONTRADICTION",
    ),
]

for output_text, ctx, threshold, note in cases:
    r = sv.check_alignment(output_text, ctx, threshold)
    flag = "CONTRADICTION" if r.is_contradiction else "ALIGNED"
    print(f"  [{flag}]  score={r.score:.4f}  threshold={threshold}")
    print(f"  Note   : {note}")
    print(f"  Claim  : {output_text}")
    print(f"  Detail : {r.explanation}")
    print()


# ═══════════════════════════════════════════════════════════════════
# STEP 2 — GAP 2: Web-verify claims about Sehri time
# ═══════════════════════════════════════════════════════════════════

print(f"\n{'─'*68}")
print("STEP 2 — GAP 2: Web-verify claims (Tavily live search)")
print(f"{'─'*68}\n")

async def run_web_verify():
    verifier = WebVerifier(api_key=TAVILY_KEY)

    claims = [
        (
            f"The Sehri time in Dhaka, Bangladesh on {DATE_STR} is around 5:10 AM.",
            "Reasonable claim — should be SUPPORTED or UNCERTAIN",
        ),
        (
            f"On {DATE_STR} in Dhaka, the Sehri time is 11:59 PM (midnight), after Isha prayer ends.",
            "Impossible claim — should be UNCERTAIN or CONTRADICTED",
        ),
        (
            f"Ramadan 2026 has not started yet as of {DATE_STR} in Bangladesh.",
            "False claim — Ramadan started ~Feb 18 2026",
        ),
    ]

    engine = ValidationEngine()

    for claim, note in claims:
        rules = [{
            "type": "web_verify",
            "field": "claim",
            "confidence_threshold": 0.65,
            "search_depth": "advanced",
            "max_results": 5,
            "severity": "error",
        }]
        result = await engine.validate(
            output={"claim": claim},
            rules=rules,
        )
        verdict_line = (
            f"  VALID   (no web violation fired)"
            if result.is_valid else
            f"  INVALID: {result.violations[0].message[:130]}"
        )
        print(f"  Note    : {note}")
        print(f"  Claim   : {claim[:110]}")
        print(verdict_line)
        print()

asyncio.run(run_web_verify())


# ═══════════════════════════════════════════════════════════════════
# STEP 3 — GAP 3: ML anomaly detection on Sehri time values
# ═══════════════════════════════════════════════════════════════════

print(f"\n{'─'*68}")
print("STEP 3 — GAP 3: IsolationForest anomaly detection on Sehri times")
print(f"{'─'*68}\n")

# Sehri times in Dhaka during Ramadan 2026 (late Feb / early Mar)
# typically fall between 05:00–05:20 AM.
# We encode time as minutes since midnight for numeric processing.
# 5:00 AM = 300 min, 5:20 AM = 320 min

def mins(h, m): return h * 60 + m
def fmt(minutes): return f"{int(minutes)//60:02d}:{int(minutes)%60:02d}"

# Training data: 60 days of plausible Sehri times
# Ramadan shifts day by day; typical range late-Feb is ~05:05–05:18
training_samples = [
    {
        "sehri_minutes":  round(random.gauss(310, 4), 1),   # ~5:10 AM ± 4 min
        "isha_minutes":   round(random.gauss(1290, 5), 1),  # ~21:30 (9:30 PM)
        "duration_mins":  round(random.gauss(475, 10), 1),  # fasting ~8 hrs
    }
    for _ in range(200)
]

FIELDS = ["sehri_minutes", "isha_minutes", "duration_mins"]
ORG_ID = "dhaka_prayer_times"

detector = MLAnomalyDetector(model_dir=None)
train_result = detector.train(ORG_ID, training_samples, FIELDS)
print(f"  Training: {train_result.message}\n")

test_cases = [
    (
        {"sehri_minutes": mins(5, 10), "isha_minutes": mins(21, 32), "duration_mins": 475},
        f"Normal: Sehri 05:10, Isha 21:32 — should be OK",
    ),
    (
        {"sehri_minutes": mins(5, 12), "isha_minutes": mins(21, 30), "duration_mins": 477},
        f"Normal: Sehri 05:12, Isha 21:30 — should be OK",
    ),
    (
        {"sehri_minutes": mins(11, 59), "isha_minutes": mins(21, 30), "duration_mins": 475},
        f"ANOMALY: Sehri 11:59 PM (midnight) — impossible",
    ),
    (
        {"sehri_minutes": mins(2, 0), "isha_minutes": mins(18, 0), "duration_mins": 200},
        f"ANOMALY: Sehri 02:00 AM, Isha 18:00, duration 200 min — all wrong",
    ),
    (
        {"sehri_minutes": mins(5, 8), "isha_minutes": mins(21, 35), "duration_mins": 470},
        f"Borderline: Sehri 05:08 — just within range",
    ),
]

print(f"  {'RESULT':<12} {'IF Score':>10}  Sample")
print(f"  {'──────':<12} {'────────':>10}  ──────")

for sample, note in test_cases:
    score = detector.score(ORG_ID, sample, FIELDS)
    flag  = "ANOMALY ⚠" if score.is_anomaly else "OK ✓     "
    sehri_fmt = fmt(sample["sehri_minutes"])
    print(f"  {flag:<12} {score.raw_score:>+10.4f}  Sehri={sehri_fmt}  {note[:55]}")

print()

# Full pipeline test with ValidationEngine
async def run_full_pipeline():
    import backend.core.ml_anomaly_detector as ml_mod
    original = ml_mod._detector
    ml_mod._detector = detector

    engine = ValidationEngine()
    rules = [{
        "type": "anomaly_ml",
        "name": "sehri_time_check",
        "fields": FIELDS,
        "org_id": ORG_ID,
        "severity": "error",
    }]

    print(f"\n  Full ValidationEngine pipeline:\n")

    for sample, note in test_cases:
        result = await engine.validate(output=sample, rules=rules)
        verdict = "INVALID ✗" if not result.is_valid else "VALID ✓  "
        sehri = fmt(sample["sehri_minutes"])
        print(f"  [{verdict}]  Sehri={sehri}  {note[:50]}")
        if result.violations:
            print(f"             {result.violations[0].message[:110]}")

    ml_mod._detector = original

asyncio.run(run_full_pipeline())


# ═══════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════

print(f"\n{SEP}")
print("  COMBINED RESULT SUMMARY")
print(SEP)
print(f"  GAP 1 Semantic   — live web context used, alignment scored per claim")
print(f"  GAP 2 Web-verify — Tavily searched with real {DATE_STR} date query")
print(f"  GAP 3 ML Anomaly — IsolationForest trained on Ramadan 2026 Dhaka times")
print(f"  All three rule types exercised against real-world Sehri time data.")
print(SEP)
