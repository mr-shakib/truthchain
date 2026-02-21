"""
Real-world demo: Medical Triage AI + TruthChain validation
===========================================================

Scenario:
  A healthcare app uses Groq (LLaMA 3) to extract structured patient
  triage data from free-text nurse notes.

  The LLM output is NEVER trusted directly.  TruthChain validates every
  response before it is written to the medical record system.

Setup (one-time):
  export GROQ_API_KEY="gsk_..."
  export TRUTHCHAIN_API_KEY="tc_live_..."

Run:
  python sdk/python/groq_demo.py
"""

import json
import os
from groq import Groq
from truthchain import TruthChain

# ── Config — just like any other API, keys come from env vars ─────────────────
GROQ_API_KEY       = os.getenv("GROQ_API_KEY",       "REDACTED_GROQ_KEY")
TRUTHCHAIN_API_KEY = os.getenv("TRUTHCHAIN_API_KEY",  "REDACTED_TC_KEY")
TRUTHCHAIN_URL     = os.getenv("TRUTHCHAIN_URL",      "http://localhost:8000")

# ── Clients — one line each, same pattern as Groq / OpenAI ───────────────────
groq = Groq(api_key=GROQ_API_KEY)
tc   = TruthChain(api_key=TRUTHCHAIN_API_KEY, base_url=TRUTHCHAIN_URL)

print("✓ Groq client ready")
print("✓ TruthChain client ready\n")

# ── Validation rules for triage data ─────────────────────────────────────────
TRIAGE_RULES = [
    {
        "type": "schema",
        "name": "triage_schema",
        "schema": {
            "type": "object",
            "properties": {
                "patient_name":    {"type": "string"},
                "age":             {"type": "integer"},
                "chief_complaint": {"type": "string"},
                "pain_score":      {"type": "integer"},
                "systolic_bp":     {"type": "integer"},
                "heart_rate":      {"type": "integer"},
                "temperature_c":   {"type": "number"},
                "triage_level":    {"type": "string",
                                    "enum": ["immediate", "urgent", "less-urgent", "non-urgent"]},
            },
            "required": ["patient_name", "age", "chief_complaint",
                         "pain_score", "triage_level"],
        },
    },
    {"type": "range", "name": "valid_age",        "field": "age",          "min": 0,   "max": 130},
    {"type": "range", "name": "valid_pain",       "field": "pain_score",   "min": 0,   "max": 10},
    {"type": "range", "name": "valid_bp",         "field": "systolic_bp",  "min": 50,  "max": 300},
    {"type": "range", "name": "valid_hr",         "field": "heart_rate",   "min": 20,  "max": 250},
    {"type": "range", "name": "valid_temp",       "field": "temperature_c","min": 30.0,"max": 45.0},
]

# ── LLM extraction function ───────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a medical data extraction assistant.
Extract structured triage data from nurse notes and return ONLY valid JSON.
Never add comments or markdown. Return exactly this shape:
{
  "patient_name": string,
  "age": integer,
  "chief_complaint": string,
  "pain_score": integer (0-10),
  "systolic_bp": integer,
  "heart_rate": integer,
  "temperature_c": float,
  "triage_level": "immediate" | "urgent" | "less-urgent" | "non-urgent"
}"""

def extract_with_llm(nurse_notes: str) -> dict:
    """Call Groq LLaMA 3 to extract structured triage data."""
    response = groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": f"Extract triage data:\n\n{nurse_notes}"},
        ],
        temperature=0,       # deterministic for medical use
        max_tokens=512,
    )
    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if the model added them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def process_patient(label: str, nurse_notes: str) -> None:
    """Full pipeline: LLM extraction → TruthChain validation → decision."""
    print("─" * 60)
    print(f"📋  {label}")
    print(f"    Notes: {nurse_notes[:80]}...")
    print()

    # Step 1 — LLM extracts structured data
    try:
        extracted = extract_with_llm(nurse_notes)
    except (json.JSONDecodeError, Exception) as e:
        print(f"  ✗ LLM returned unparseable output: {e}")
        print("  → BLOCKED: Cannot write to medical records\n")
        return

    print(f"  LLM extracted: {json.dumps(extracted, indent=4)}")
    print()

    # Step 2 — TruthChain validates before any DB write
    result = tc.validate(
        output=extracted,
        rules=TRIAGE_RULES,
        context={"auto_correct": True},
    )

    # Step 3 — Decision gate
    if result.is_valid:
        print(f"  ✓ PASSED validation  |  confidence: {result.confidence_score}  |  {result.latency_ms}ms")
        print(f"  → ACCEPTED: Writing triage record to medical system")
        print(f"     Triage level : {extracted['triage_level'].upper()}")
        print(f"     Patient       : {extracted['patient_name']}, age {extracted['age']}")
    else:
        print(f"  ✗ FAILED validation  ({len(result.violations)} violation(s))")
        for v in result.violations:
            print(f"     [{v.severity.upper()}] {v.rule_name}: {v.message}")
        if result.auto_corrected and result.corrected_output:
            print(f"  ⚡ Auto-corrected output available:")
            print(f"     {json.dumps(result.corrected_output, indent=4)}")
            print(f"  → CORRECTED record queued for nurse review")
        else:
            print(f"  → BLOCKED: Flagging for manual nurse review")

    print()


# ── Test cases ────────────────────────────────────────────────────────────────

# Case 1: Clean, valid input
process_patient(
    "CASE 1 — Valid patient notes",
    """Patient: Sarah Johnson, 34yo female. Chief complaint: severe chest pain
    radiating to left arm. Pain score 8/10. BP 145/92, HR 98, Temp 37.2C.
    Onset 45 minutes ago. History of hypertension."""
)

# Case 2: LLM hallucinates an out-of-range value (pain score 15)
process_patient(
    "CASE 2 — LLM returns invalid pain score (15/10)",
    """Patient: Mike Torres, 8yo male. Chief complaint: fell off bike, cut on forehead.
    Pain score fifteen out of ten (child very upset). BP 110/70, HR 110, Temp 36.8C.
    Minor laceration 2cm, no loss of consciousness."""
)

# Case 3: LLM invents an unknown triage level
process_patient(
    "CASE 3 — LLM invents non-standard triage level",
    """Patient: elderly male, approximately 80 years old, name unknown.
    Found unresponsive by paramedics. BP 80/50, HR 40, Temp 34.1C.
    Possible cardiac event. Triage: critical."""   # "critical" is not in our enum
)

# Case 4: Missing required fields — LLM skipped some
process_patient(
    "CASE 4 — LLM omits required fields",
    """Walk-in patient: John Smith. Just wants a prescription refill for
    blood pressure medication. Looks well."""
)
