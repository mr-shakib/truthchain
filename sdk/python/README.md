# TruthChain Python SDK

Validate AI outputs against any business rules in <100ms.

## Installation

```bash
pip install httpx          # only dependency (until published to PyPI)

# or install directly from source
pip install -e truthchain/sdk/python
```

## Quick Start

### 1. Sign up (one-time)

```python
from truthchain import signup

result = signup(
    name="Acme Corp",
    email="dev@acme.com",
    password="s3cretPW!",
    tier="free",                         # "free" | "startup" | "business" | "enterprise"
    base_url="http://localhost:8000",    # your TruthChain server
)
print(result.api_key)   # tc_...  ← save this securely!
```

### 2. Validate AI output

```python
from truthchain import TruthChain

client = TruthChain(
    api_key="tc_...",
    base_url="http://localhost:8000",  # default
)

result = client.validate(
    output={
        "user_id": 12345,
        "hours": 8,
        "project_name": "Project-X",
    },
    rules=[
        {
            "type": "schema",
            "name": "output_structure",
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
            "severity": "error",
        },
    ],
    context={"auto_correct": True},   # optional
)

print(result.status)          # "passed" | "failed" | "warning"
print(result.is_valid)        # True / False
print(result.violations)      # list of Violation objects
print(result.corrected_output) # auto-corrected dict (if auto_correct=True)
print(result.latency_ms)      # e.g. 12
```

### 3. Login (get a fresh API key)

```python
from truthchain import login, TruthChain

auth = login("dev@acme.com", "s3cretPW!")
client = TruthChain(api_key=auth.api_key)
```

---

## API Reference

### `TruthChain(api_key, base_url, timeout)`

#### Validation
| Method | Returns | Description |
|--------|---------|-------------|
| `validate(output, rules, context)` | `ValidationResult` | Validate an AI output |

#### Analytics
| Method | Returns | Description |
|--------|---------|-------------|
| `get_analytics()` | `AnalyticsOverview` | Full analytics overview |
| `get_validation_stats()` | `ValidationStats` | Aggregated stats |

#### Billing
| Method | Returns | Description |
|--------|---------|-------------|
| `get_subscription()` | `Subscription` | Current plan & usage |
| `get_plans()` | `List[BillingPlan]` | All available plans |
| `upgrade(tier)` | `Subscription` | Change subscription tier |

#### API Key Management
| Method | Returns | Description |
|--------|---------|-------------|
| `list_api_keys()` | `List[APIKey]` | List all keys |
| `create_api_key(name)` | `APIKey` | Create new key |
| `rotate_api_key(key_id)` | `APIKey` | Rotate key (revokes old) |
| `revoke_api_key(key_id)` | `None` | Revoke a key |

### Top-level helpers (no API key needed)
| Function | Returns | Description |
|----------|---------|-------------|
| `signup(name, email, password, tier)` | `SignupResult` | Register new org |
| `login(email, password)` | `LoginResult` | Login, get fresh key |

---

## Async Usage

```python
import asyncio
from truthchain import AsyncTruthChain

async def main():
    async with AsyncTruthChain(api_key="tc_...") as client:
        result = await client.validate(
            output={"score": 95},
            rules=[{"type": "range", "name": "score", "field": "score", "min": 0, "max": 100}],
        )
        print(result.status)

asyncio.run(main())
```

---

## Error Handling

```python
from truthchain import TruthChain
from truthchain.exceptions import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    ValidationError,
)

client = TruthChain(api_key="tc_...")

try:
    result = client.validate(output={}, rules=[])
except AuthenticationError:
    print("Invalid or revoked API key")
except QuotaExceededError:
    print("Monthly quota exhausted — upgrade your plan")
except RateLimitError as e:
    print(f"Rate limited — retry after {e.retry_after}s")
except ValidationError as e:
    print(f"Bad request: {e.message}")
```

---

## Rule Types

| Type | Required fields | Description |
|------|----------------|-------------|
| `schema` | `schema` (JSON Schema) | Validate structure & types |
| `range` | `field`, `min`, `max` | Numeric range check |
| `pattern` | `field`, `pattern` (regex) | Regex match |
| `required` | `fields` (list) | Presence check |
| `reference` | `field`, `reference_type` | DB existence check |

---

## License

MIT
