"""
TruthChain SDK — end-to-end live demo
Run from: truthchain/  with the backend server running on port 8000

    .\venv\Scripts\python.exe sdk/python/demo.py
"""
from truthchain import signup, login, TruthChain
from truthchain.exceptions import TruthChainError, ConflictError

BASE = "http://localhost:8000"

# ── 1. Create an account ──────────────────────────────────────────
print("=" * 55)
print(" STEP 1 — Sign up")
print("=" * 55)
try:
    account = signup(
        name="Demo Org",
        email="demo@example.com",
        password="password123",
        tier="free",
        base_url=BASE,
    )
    api_key = account.api_key
    print(f"  ✓ org created : {account.name} ({account.organization_id[:8]}...)")
    print(f"  ✓ tier        : {account.tier}")
    print(f"  ✓ quota       : {account.monthly_quota:,} validations / month")
    print(f"  ✓ api_key     : {api_key[:24]}...")
except ConflictError:
    print("  Account already exists — logging in instead...")
    auth = login("demo@example.com", "password123", base_url=BASE)
    api_key = auth.api_key
    print(f"  ✓ logged in as : {auth.email}")
    print(f"  ✓ api_key      : {api_key[:24]}...")

client = TruthChain(api_key=api_key, base_url=BASE)

# ── 2. Validate a correct payload ────────────────────────────────
print()
print("=" * 55)
print(" STEP 2 — Validate a PASSING payload")
print("=" * 55)

r = client.validate(
    output={"user_id": 42, "hours": 8, "project_name": "Project-X"},
    rules=[
        {
            "type": "schema",
            "name": "structure_check",
            "schema": {
                "type": "object",
                "properties": {
                    "user_id":      {"type": "integer"},
                    "hours":        {"type": "number"},
                    "project_name": {"type": "string"},
                },
                "required": ["user_id", "hours", "project_name"],
            },
        },
        {
            "type": "range",
            "name": "hours_check",
            "field": "hours",
            "min": 0,
            "max": 24,
        },
    ],
)
print(f"  status      : {r.status}")
print(f"  is_valid    : {r.is_valid}")
print(f"  violations  : {len(r.violations)}")
print(f"  latency     : {r.latency_ms} ms")

# ── 3. Validate a BAD payload (hours=99, missing field) ──────────
print()
print("=" * 55)
print(" STEP 3 — Validate a FAILING payload (hours=99)")
print("=" * 55)

r2 = client.validate(
    output={"user_id": 7, "hours": 99, "project_name": "Overwork"},
    rules=[
        {
            "type": "range",
            "name": "hours_check",
            "field": "hours",
            "min": 0,
            "max": 24,
            "severity": "error",
        },
    ],
    context={"auto_correct": True},
)
print(f"  status          : {r2.status}")
print(f"  is_valid        : {r2.is_valid}")
print(f"  violations      : {len(r2.violations)}")
for v in r2.violations:
    print(f"    ↳ [{v.severity}] {v.rule_name}: {v.message}")
print(f"  auto_corrected  : {r2.auto_corrected}")
if r2.corrected_output:
    print(f"  corrected hours : {r2.corrected_output.get('hours')}")

# ── 4. Analytics ─────────────────────────────────────────────────
print()
print("=" * 55)
print(" STEP 4 — Analytics")
print("=" * 55)
stats = client.get_validation_stats()
print(f"  total_validations : {stats.total_validations}")
print(f"  passed            : {stats.passed}")
print(f"  failed            : {stats.failed}")
print(f"  success_rate      : {stats.success_rate:.1f}%")
print(f"  avg_latency       : {stats.avg_latency_ms:.1f} ms")

# ── 5. Billing ────────────────────────────────────────────────────
print()
print("=" * 55)
print(" STEP 5 — Subscription")
print("=" * 55)
sub = client.get_subscription()
print(f"  tier         : {sub.tier}")
print(f"  price        : {sub.price_display}")
print(f"  quota        : {sub.monthly_quota:,}")
print(f"  used         : {sub.quota_used}")
print(f"  remaining    : {sub.monthly_quota - sub.quota_used:,}  ({100 - sub.quota_percentage:.1f}%)")

print()
print("=" * 55)
print(" All steps complete — SDK is working!")
print("=" * 55)
