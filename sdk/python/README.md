# TruthChain Python SDK

[![PyPI version](https://img.shields.io/pypi/v/truthchain.svg)](https://pypi.org/project/truthchain/)
[![Python versions](https://img.shields.io/pypi/pyversions/truthchain.svg)](https://pypi.org/project/truthchain/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Validate AI / LLM outputs against any business rules in **<100ms**.  
Catch hallucinations, schema violations, out-of-range values, and more — before they reach your users.

---

## Installation

```bash
pip install truthchain
```

Requires Python 3.9+. The only dependency (`httpx`) is installed automatically.

---

## Quick Start

```python
from truthchain import signup, TruthChain

# One-time: create an account
result = signup(
    name="Acme Corp",
    email="dev@acme.com",
    password="s3cretPW!",
    base_url="https://your-server.com",
)
API_KEY = result.api_key   # tc_live_...  — save this securely!

# Validate an AI output
client = TruthChain(api_key=API_KEY, base_url="https://your-server.com")

result = client.validate(
    output={"user_id": 12345, "hours": 8, "project_name": "Project-X"},
    rules=[
        {
            "type": "schema",
            "name": "structure",
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
    context={"auto_correct": True},
)

print(result.status)            # "passed" | "failed" | "warning"
print(result.is_valid)          # True / False
print(result.violations)        # list of Violation objects
print(result.corrected_output)  # auto-corrected dict (if auto_correct=True)
print(result.latency_ms)        # e.g. 12
```

---

## Authentication

### Sign up

```python
from truthchain import signup

result = signup(
    name="Acme Corp",
    email="dev@acme.com",
    password="s3cretPW!",
    tier="free",   # "free" | "startup" | "business" | "enterprise"
    base_url="https://your-server.com",
)
print(result.api_key)   # tc_live_...  � shown only once, save immediately
```

### Login

```python
from truthchain import login

auth = login("dev@acme.com", "s3cretPW!", base_url="https://your-server.com")
client = TruthChain(api_key=auth.api_key, base_url="https://your-server.com")
```

---

## Validation

```python
result = client.validate(
    output={"score": 95, "label": "positive"},
    rules=[
        {"type": "range",    "name": "score_range",  "field": "score", "min": 0, "max": 100},
        {"type": "required", "name": "has_label",    "fields": ["label"]},
    ],
)
```

**Rule types**

| Type | Required fields | Description |
|------|----------------|-------------|
| `schema` | `schema` (JSON Schema) | Structure & type validation |
| `range` | `field`, `min`, `max` | Numeric range check |
| `pattern` | `field`, `pattern` (regex) | Regex match |
| `required` | `fields` (list) | Presence check |
| `reference` | `field`, `reference_type` | External reference check |

All rules accept an optional `"severity": "error"` (default) or `"warning"`.

---

## Async Usage

```python
import asyncio
from truthchain import AsyncTruthChain

async def main():
    async with AsyncTruthChain(api_key="tc_live_...", base_url="https://your-server.com") as client:
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
from truthchain.exceptions import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    ValidationError,
    ServerError,
)

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
except ServerError:
    print("Server error � try again later")
```

Error hierarchy:

```
TruthChainError
├── AuthenticationError   (401)
├── NotFoundError         (404)
├── ValidationError       (422)
├── RateLimitError        (429)
├── QuotaExceededError    (429 + quota)
├── ConflictError         (400 / 409)
└── ServerError           (5xx)
```

---

## API Reference

### `TruthChain(api_key, base_url, timeout)`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_key` | — | Your `tc_live_...` API key |
| `base_url` | `http://localhost:8000` | TruthChain server URL |
| `timeout` | `30.0` | Request timeout in seconds |

Supports context manager: `with TruthChain(...) as client:`.  
`AsyncTruthChain` mirrors the same interface with `async/await`.

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `validate(output, rules, context)` | `ValidationResult` | Validate AI output |
| `get_analytics()` | `AnalyticsOverview` | Analytics overview |
| `get_validation_stats()` | `ValidationStats` | Aggregated stats |
| `get_subscription()` | `Subscription` | Current plan & usage |
| `get_plans()` | `List[BillingPlan]` | Available plans |
| `upgrade(tier)` | `Subscription` | Change plan |
| `list_api_keys()` | `List[APIKey]` | List all keys |
| `create_api_key(name)` | `APIKey` | Create new key |
| `rotate_api_key(key_id)` | `APIKey` | Rotate key |
| `revoke_api_key(key_id)` | `None` | Revoke key |

### Top-level helpers

| Function | Description |
|----------|-------------|
| `signup(name, email, password, tier, base_url)` | Register new org |
| `login(email, password, base_url)` | Login, get fresh key |

---

## License

[MIT](LICENSE) © 2026 TruthChain
