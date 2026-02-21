"""
GAP 3 smoke test — ML Anomaly Detection (IsolationForest)
Run: .\venv\Scripts\python.exe test_gap3_anomaly_ml.py
"""
import sys, asyncio, random
sys.path.insert(0, ".")

from backend.core.ml_anomaly_detector import MLAnomalyDetector, get_ml_anomaly_detector
from backend.core.rule_engine import RuleEngine
from backend.core.validation_engine import ValidationEngine

random.seed(42)

print("=" * 65)
print("GAP 3 — ML Anomaly Detection (IsolationForest) Smoke Test")
print("=" * 65)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_normal_sample(i: int) -> dict:
    """Typical timesheet entry: 6–9 hrs, cost $50–90/hr, 3–8 line items."""
    return {
        "employee_id": f"emp_{i}",
        "hours": round(random.uniform(6, 9), 1),
        "hourly_rate": round(random.uniform(50, 90), 2),
        "total_cost": round(random.uniform(300, 810), 2),
        "line_items": random.randint(3, 8),
    }

FIELDS = ["hours", "hourly_rate", "total_cost", "line_items"]
ORG_ID = "test_org_001"


# ---------------------------------------------------------------------------
# Test 1: Train on normal data
# ---------------------------------------------------------------------------
print("\nTEST 1 — Train IsolationForest on 200 normal samples")

detector = MLAnomalyDetector(model_dir=None)   # memory-only for test

historical = [make_normal_sample(i) for i in range(200)]
train_result = detector.train(ORG_ID, historical, FIELDS, contamination=0.05)

print(f"  success    : {train_result.success}")
print(f"  n_samples  : {train_result.n_samples}")
print(f"  fields     : {train_result.fields}")
print(f"  message    : {train_result.message}")
assert train_result.success, "Training must succeed"


# ---------------------------------------------------------------------------
# Test 2: Score normal samples — should NOT be anomalies
# ---------------------------------------------------------------------------
print("\nTEST 2 — Score 5 normal samples (should all be OK)")

normal_pass = 0
for i in range(5):
    s = make_normal_sample(i + 300)
    r = detector.score(ORG_ID, s, FIELDS)
    flag = "ANOMALY" if r.is_anomaly else "OK"
    print(f"  [{flag}] score={r.raw_score:+.4f}  hours={s['hours']}  cost={s['total_cost']}")
    if not r.is_anomaly:
        normal_pass += 1

print(f"  Normal samples correctly classified: {normal_pass}/5")


# ---------------------------------------------------------------------------
# Test 3: Score obvious anomalies — should be flagged
# ---------------------------------------------------------------------------
print("\nTEST 3 — Score obvious anomalies (should be flagged)")

anomalies = [
    {"hours": 30.0, "hourly_rate": 75.0, "total_cost": 2250.0, "line_items": 5},      # 30 hrs in one day
    {"hours": 0.1, "hourly_rate": 5000.0, "total_cost": 500.0, "line_items": 1},      # $5000/hr rate
    {"hours": 8.0, "hourly_rate": 70.0, "total_cost": 85000.0, "line_items": 999},    # 999 line items
    {"hours": -5.0, "hourly_rate": 65.0, "total_cost": -325.0, "line_items": 4},      # negative hours
]

anomaly_caught = 0
for sample in anomalies:
    r = detector.score(ORG_ID, sample, FIELDS)
    flag = "ANOMALY" if r.is_anomaly else "OK"
    print(f"  [{flag}] score={r.raw_score:+.4f}  {sample}")
    if r.is_anomaly:
        anomaly_caught += 1

print(f"  Anomalies correctly caught: {anomaly_caught}/{len(anomalies)}")


# ---------------------------------------------------------------------------
# Test 4: Graceful fallback — untrained org
# ---------------------------------------------------------------------------
print("\nTEST 4 — Untrained org → graceful warning (no crash)")

fresh_detector = MLAnomalyDetector(model_dir=None)
r = fresh_detector.score("unknown_org", make_normal_sample(1), FIELDS)
print(f"  is_anomaly : {r.is_anomaly}")
print(f"  reason     : {r.reason}")
assert not r.is_anomaly, "Untrained model must not raise false positives"
assert "not trained" in r.reason.lower()
print("  [PASS] Graceful fallback confirmed")


# ---------------------------------------------------------------------------
# Test 5: RuleEngine with anomaly_ml rule — untrained org → warning violation
# ---------------------------------------------------------------------------
print("\nTEST 5 — RuleEngine: anomaly_ml rule, untrained org → warning")

async def test_rule_engine_untrained():
    engine = RuleEngine()
    output = make_normal_sample(50)
    rules = [{
        "type": "anomaly_ml",
        "name": "timesheet_anomaly",
        "fields": FIELDS,
        "org_id": "org_notrained",
        "severity": "warning",
    }]
    violations = await engine.validate(output, rules, None)
    assert len(violations) == 1
    v = violations[0]
    assert v.severity == "warning"
    print(f"  [PASS] Warning: {v.message[:100]}")

asyncio.run(test_rule_engine_untrained())


# ---------------------------------------------------------------------------
# Test 6: RuleEngine with a pre-trained detector (patch singleton)
# ---------------------------------------------------------------------------
print("\nTEST 6 — RuleEngine: anomaly_ml with trained model, normal vs anomaly")

import backend.core.rule_engine as re_mod
_original_detector = re_mod._web_verifier   # save unrelated state

# Patch the singleton
import backend.core.ml_anomaly_detector as ml_mod
original_singleton = ml_mod._detector
ml_mod._detector = detector  # inject our trained detector


async def test_rule_engine_trained():
    engine = RuleEngine()
    rules = [{
        "type": "anomaly_ml",
        "name": "timesheet_anomaly",
        "fields": FIELDS,
        "org_id": ORG_ID,
        "severity": "warning",
    }]

    # Normal sample
    normal = make_normal_sample(500)
    violations_normal = await engine.validate(normal, rules, None)
    flag = "ANOMALY" if violations_normal else "OK"
    print(f"  Normal:  [{flag}]  hours={normal['hours']}  violations={len(violations_normal)}")

    # Anomalous sample
    bad = {"hours": 30.0, "hourly_rate": 75.0, "total_cost": 2250.0, "line_items": 5}
    violations_bad = await engine.validate(bad, rules, None)
    flag2 = "ANOMALY" if violations_bad else "OK"
    print(f"  Anomaly: [{flag2}]  hours={bad['hours']}  violations={len(violations_bad)}")
    if violations_bad:
        print(f"    msg: {violations_bad[0].message[:130]}")

asyncio.run(test_rule_engine_trained())

# Restore singleton
ml_mod._detector = original_singleton


# ---------------------------------------------------------------------------
# Test 7: Full ValidationEngine pipeline
# ---------------------------------------------------------------------------
print("\nTEST 7 — Full ValidationEngine pipeline")

import backend.core.ml_anomaly_detector as ml_mod
ml_mod._detector = detector  # inject trained detector


async def test_full_pipeline():
    engine = ValidationEngine()

    result_normal = await engine.validate(
        output=make_normal_sample(999),
        rules=[{
            "type": "anomaly_ml",
            "fields": FIELDS,
            "org_id": ORG_ID,
            "severity": "warning",
        }],
        context={"detect_anomalies": False},   # disable legacy anomaly path
    )
    print(f"  Normal sample  → is_valid={result_normal.is_valid}  violations={len(result_normal.violations)}")

    result_bad = await engine.validate(
        output={"hours": 30.0, "hourly_rate": 75.0, "total_cost": 2250.0, "line_items": 5},
        rules=[{
            "type": "anomaly_ml",
            "fields": FIELDS,
            "org_id": ORG_ID,
            "severity": "error",
        }],
        context={"detect_anomalies": False},
    )
    print(f"  Anomaly sample → is_valid={result_bad.is_valid}  violations={len(result_bad.violations)}")
    if result_bad.violations:
        print(f"  [{result_bad.violations[0].severity.upper()}] {result_bad.violations[0].message[:130]}")

asyncio.run(test_full_pipeline())

ml_mod._detector = original_singleton

print()
print("=" * 65)
print("GAP 3 smoke tests complete.")
print("=" * 65)
