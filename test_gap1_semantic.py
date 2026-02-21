"""
GAP 1 smoke test — Semantic Contradiction Detector
Run: .\venv\Scripts\python.exe test_gap1_semantic.py
"""
import sys, asyncio
sys.path.insert(0, ".")

from backend.core.semantic_validator import SemanticValidator
from backend.core.rule_engine import RuleEngine
from backend.core.validation_engine import ValidationEngine


# ---------------------------------------------------------------------------
# Test 1: SemanticValidator raw scores
# ---------------------------------------------------------------------------
print("=" * 65)
print("TEST 1 — SemanticValidator.check_alignment()")
print("=" * 65)

sv = SemanticValidator()
cases = [
    (
        "Prescribe amoxicillin 500mg twice daily",
        "Patient is allergic to penicillin and all beta-lactam antibiotics",
        0.5,
        "SHOULD be CONTRADICTION",
    ),
    (
        "We recommend the patient rest and take acetaminophen for fever",
        "Patient is allergic to penicillin and all beta-lactam antibiotics",
        0.5,
        "SHOULD PASS (safe recommendation)",
    ),
    (
        "The loan is approved for the requested amount",
        "Applicant credit score is 420, below minimum threshold of 580",
        0.5,
        "SHOULD be CONTRADICTION",
    ),
    (
        "Apple Q4 2025 revenue was 94.9 billion dollars",
        "What was Apple revenue in Q4 2025?",
        0.5,
        "SHOULD PASS (aligned Q&A)",
    ),
]

for output_text, context_text, threshold, note in cases:
    r = sv.check_alignment(output_text, context_text, threshold)
    flag = "CONTRADICTION" if r.is_contradiction else "OK"
    print(f"\n  [{flag}] score={r.score:.4f}  threshold={threshold}")
    print(f"  note: {note}")
    print(f"  output:  {output_text[:70]}")
    print(f"  context: {context_text[:70]}")
    print(f"  detail:  {r.explanation}")


# ---------------------------------------------------------------------------
# Test 2: RuleEngine with type:semantic
# ---------------------------------------------------------------------------
print()
print("=" * 65)
print("TEST 2 — RuleEngine with semantic rule (allergy safety check)")
print("=" * 65)


async def test_rule_engine():
    engine = RuleEngine()
    output = {"recommendation": "Prescribe amoxicillin 500mg twice daily"}
    rules = [
        {
            "type": "semantic",
            "name": "allergy_safety_check",
            "output_field": "recommendation",
            "context_field": "patient_history",
            "min_alignment": 0.5,
            "severity": "error",
        }
    ]
    context = {
        "patient_history": (
            "Patient is allergic to penicillin and all beta-lactam antibiotics"
        )
    }
    violations = await engine.validate(output, rules, context)
    if violations:
        v = violations[0]
        print(f"  VIOLATION detected: [{v.severity.upper()}] {v.violation_type}")
        print(f"  Message: {v.message[:140]}")
    else:
        print("  No violations — threshold may need adjustment for this example")


asyncio.run(test_rule_engine())


# ---------------------------------------------------------------------------
# Test 3: Full ValidationEngine pipeline
# ---------------------------------------------------------------------------
print()
print("=" * 65)
print("TEST 3 — Full ValidationEngine: semantic + range rule together")
print("=" * 65)


async def test_full_engine():
    engine = ValidationEngine()

    # Case A — passes both rules
    result_a = await engine.validate(
        output={
            "recommendation": "Rest and stay hydrated. Take acetaminophen for fever.",
            "dosage_mg": 500,
        },
        rules=[
            {
                "type": "semantic",
                "name": "treatment_context_check",
                "output_field": "recommendation",
                "context_field": "patient_notes",
                "min_alignment": 0.5,
            },
            {
                "type": "range",
                "name": "dosage_range",
                "field": "dosage_mg",
                "min": 100,
                "max": 1000,
            },
        ],
        context={"patient_notes": "Patient presents with mild fever and fatigue"},
    )
    print(f"\n  Case A (should PASS):")
    print(f"    is_valid={result_a.is_valid}  violations={len(result_a.violations)}")

    # Case B — semantic violation
    result_b = await engine.validate(
        output={
            "recommendation": "Approve the loan for the full requested amount.",
            "dosage_mg": 500,
        },
        rules=[
            {
                "type": "semantic",
                "name": "credit_coherence_check",
                "output_field": "recommendation",
                "context_field": "credit_info",
                "min_alignment": 0.5,
            },
        ],
        context={
            "credit_info": "Applicant credit score is 380. Minimum required is 620. High default risk."
        },
    )
    print(f"\n  Case B (should FAIL — loan approved despite bad credit):")
    print(f"    is_valid={result_b.is_valid}  violations={len(result_b.violations)}")
    if result_b.violations:
        v = result_b.violations[0]
        print(f"    violation type: {v.violation_type}")
        print(f"    message: {v.message[:150]}")


asyncio.run(test_full_engine())

print()
print("=" * 65)
print("GAP 1 smoke tests complete.")
print("=" * 65)
