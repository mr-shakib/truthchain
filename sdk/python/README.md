# TruthChain Python SDK

[![PyPI version](https://img.shields.io/pypi/v/truthchain.svg)](https://pypi.org/project/truthchain/)
[![Python versions](https://img.shields.io/pypi/pyversions/truthchain.svg)](https://pypi.org/project/truthchain/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Validate AI / LLM outputs against any business rules in **<100ms**.  
Catch hallucinations, schema violations, out-of-range values, and more — before they reach your users.

> **TypeScript SDK:** `sdk/typescript/` — mirrors this SDK, adds native TypeScript types.

---

## Requirements

- **Python 3.9+**
- A running TruthChain backend

---

## Installation

```bash
pip install truthchain
```

The only dependency (`httpx`) is installed automatically.

---

## Quick Start

```python
from truthchain import signup, TruthChain

# 1. Create an account (one-time)
result = signup(
    name="Acme Corp",
    email="dev@acme.com",
    password="s3cretPW!",
    base_url="https://your-server.com",
)
API_KEY = result.api_key   # tc_live_...  ← save this securely!

# 2. Validate an AI output
client = TruthChain(api_key=API_KEY, base_url="https://your-server.com")

result = client.validate(
    output={"user_id": 12345, "hours": 8, "project_name": "Project-X"},
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
    context={"auto_correct": True},
)

print(result.status)           # "passed" | "failed" | "warning"
print(result.is_valid)         # True / False
print(result.violations)       # list of Violation objects
print(result.corrected_output) # auto-corrected dict (if auto_correct=True)
print(result.latency_ms)       # e.g. 12
```

---

## Authentication

### Sign up (one-time)

```python
from truthchain import signup

result = signup(
    name="Acme Corp",
    email="dev@acme.com",
    password="s3cretPW!",
    tier="free",                         # "free" | "startup" | "business" | "enterprise"
    base_url="https://your-server.com",
)
print(result.api_key)   # tc_live_...  ← shown only once, save immediately!
```

### Login (get a fresh API key)

```python
from truthchain import login

auth = login("dev@acme.com", "s3cretPW!", base_url="https://your-server.com")
print(auth.api_key)
```

---

## Validation

```python
from truthchain import TruthChain

client = TruthChain(api_key="tc_live_...", base_url="https://your-server.com")

result = client.validate(
    output={"score": 95, "label": "positive"},
    rules=[
        {"type": "range",    "name": "score_range",    "field": "score", "min": 0, "max": 100},
        {"type": "required", "name": "label_present",  "fields": ["label"]},
    ],
)

print(result.status)     # "passed"
print(result.is_valid)   # True
```

### `ValidationResult` fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | `"passed"` / `"failed"` / `"warning"` |
| `is_valid` | `bool` | `True` if no errors |
| `violations` | `List[Violation]` | List of rule failures |
| `corrected_output` | `dict \| None` | Auto-corrected output (if requested) |
| `latency_ms` | `float` | Server-side processing time |

**Supported rule types:** `schema`, `range`, `pattern`, `required`, `reference`

All rules accept an optional `severity` field: `"error"` (default) or `"warning"`.

---

## Analytics

```python
overview = client.get_analytics()
print(overview.total_validations, overview.pass_rate)

stats = client.get_validation_stats()
print(stats.avg_latency_ms)
```

---

## Billing

```python
sub = client.get_subscription()
print(sub.tier, sub.requests_used, sub.requests_limit)

plans = client.get_plans()
for plan in plans:
    print(plan.name, plan.price_monthly)

updated = client.upgrade("startup")
print(updated.tier)   # "startup"
```

---

## API Key Management

```python
keys    = client.list_api_keys()
new_key = client.create_api_key(name="production-key")
print(new_key.key)   # Save this — shown only once!

rotated = client.rotate_api_key(key_id=new_key.id)
client.revoke_api_key(key_id=rotated.id)
```

---

## Async Usage

Every method is available on `AsyncTruthChain` as a coroutine:

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

All errors extend `TruthChainError`:

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
    print("Server error — try again later")
```

```
TruthChainError
├── AuthenticationError   (HTTP 401)
├── NotFoundError         (HTTP 404)
├── ValidationError       (HTTP 422)
├── RateLimitError        (HTTP 429)
├── QuotaExceededError    (HTTP 429 + quota message)
├── ConflictError         (HTTP 400 / 409)
└── ServerError           (HTTP 5xx)
```

---

## API Reference

### `TruthChain(api_key, base_url, timeout)`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_key` | — | Your `tc_live_...` API key |
| `base_url` | `http://localhost:8000` | TruthChain server URL |
| `timeout` | `30.0` | Request timeout in seconds |

Supports context manager: `with TruthChain(...) as client:`

### Validation
| Method | Returns | Description |
|--------|---------|-------------|
| `validate(output, rules, context)` | `ValidationResult` | Validate an AI output |

### Analytics
| Method | Returns | Description |
|--------|---------|-------------|
| `get_analytics()` | `AnalyticsOverview` | Full analytics overview |
| `get_validation_stats()` | `ValidationStats` | Aggregated stats |

### Billing
| Method | Returns | Description |
|--------|---------|-------------|
| `get_subscription()` | `Subscription` | Current plan & usage |
| `get_plans()` | `List[BillingPlan]` | All available plans |
| `upgrade(tier)` | `Subscription` | Change subscription tier |

### API Key Management
| Method | Returns | Description |
|--------|---------|-------------|
| `list_api_keys()` | `List[APIKey]` | List all keys |
| `create_api_key(name)` | `APIKey` | Create new key |
| `rotate_api_key(key_id)` | `APIKey` | Rotate key (revokes old) |
| `revoke_api_key(key_id)` | `None` | Revoke a key |

### Top-level helpers (no API key needed)

| Function | Returns | Description |
|----------|---------|-------------|
| `signup(name, email, password, tier, base_url)` | `SignupResult` | Register new org |
| `login(email, password, base_url)` | `LoginResult` | Login, get fresh key |

### `AsyncTruthChain`

Identical interface to `TruthChain` — every method is `async`.  
Supports `async with AsyncTruthChain(...) as client:`.

---

## Releasing a New Version

1. Bump `version` in [`pyproject.toml`](pyproject.toml)

2. Build:
   ```bash
   python -m build
   ```

3. Verify:
   ```bash
   python -m twine check dist/*
   ```

4. Upload:
   ```bash
   python -m twine upload dist/* --username __token__ --password <pypi-token>
   ```
   Or drag the files from `dist/` into [pypi.org/manage/project/truthchain/releases/](https://pypi.org/manage/project/truthchain/releases/).

5. Tag:
   ```bash
   git tag v1.x.x && git push origin v1.x.x
   ```

---

## License

MIT


---

## Quick Start

```python
from truthchain import signup, TruthChain

# 1. Create an account (one-time)
result = signup(
    name="Acme Corp",
    email="dev@acme.com",
    password="s3cretPW!",
    base_url="https://your-server.com",
)
API_KEY = result.api_key   # tc_live_...  ← save this securely!

# 2. Validate an AI output
client = TruthChain(api_key=API_KEY, base_url="https://your-server.com")

result = client.validate(
    output={"user_id": 12345, "hours": 8, "project_name": "Project-X"},
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
    context={"auto_correct": True},
)

print(result.status)           # "passed" | "failed" | "warning"
print(result.is_valid)         # True / False
print(result.violations)       # list of Violation objects
print(result.corrected_output) # auto-corrected dict (if auto_correct=True)
print(result.latency_ms)       # e.g. 12
```

---

## Authentication

### Sign up (one-time)

```python
from truthchain import signup

result = signup(
    name="Acme Corp",
    email="dev@acme.com",
    password="s3cretPW!",
    tier="free",                              # "free" | "startup" | "business" | "enterprise"
    base_url="https://your-server.com",
)
print(result.api_key)   # tc_live_...  ← shown only once, save immediately!
```

### Login (get a fresh API key)

```python
from truthchain import login

auth = login("dev@acme.com", "s3cretPW!", base_url="https://your-server.com")
print(auth.api_key)
```

---

## Validation

```python
from truthchain import TruthChain

client = TruthChain(api_key="tc_live_...", base_url="https://your-server.com")

result = client.validate(
    output={"score": 95, "label": "positive"},
    rules=[
        {"type": "range", "name": "score_range", "field": "score", "min": 0, "max": 100},
        {"type": "required", "name": "label_present", "fields": ["label"]},
    ],
)

print(result.status)     # "passed"
print(result.is_valid)   # True
```

### `ValidationResult` fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | `"passed"` / `"failed"` / `"warning"` |
| `is_valid` | `bool` | `True` if no errors |
| `violations` | `List[Violation]` | List of rule failures |
| `corrected_output` | `dict \| None` | Auto-corrected output (if requested) |
| `latency_ms` | `float` | Server-side processing time |

---

## Rule Types

| Type | Required fields | Description |
|------|----------------|-------------|
| `schema` | `schema` (JSON Schema object) | Validate structure & data types |
| `range` | `field`, `min`, `max` | Numeric range check |
| `pattern` | `field`, `pattern` (regex) | Regex pattern match |
| `required` | `fields` (list of strings) | Presence / non-null check |
| `reference` | `field`, `reference_type` | DB / external reference existence |

All rules accept an optional `severity` field: `"error"` (default) or `"warning"`.

---

## Analytics

```python
overview = client.get_analytics()
print(overview.total_validations)
print(overview.pass_rate)

stats = client.get_validation_stats()
print(stats.avg_latency_ms)
```

---

## Billing

```python
# Current plan and usage
sub = client.get_subscription()
print(sub.tier, sub.requests_used, sub.requests_limit)

# Available plans
plans = client.get_plans()
for plan in plans:
    print(plan.name, plan.price_monthly)

# Upgrade tier
updated = client.upgrade("startup")
print(updated.tier)   # "startup"
```

---

## API Key Management

```python
# List all keys
keys = client.list_api_keys()

# Create a named key (save the returned value — shown only once)
new_key = client.create_api_key(name="production-key")
print(new_key.key)

# Rotate a key (old key revoked, new one issued)
rotated = client.rotate_api_key(key_id=new_key.id)
print(rotated.key)

# Revoke a key
client.revoke_api_key(key_id=rotated.id)
```

---

## Async Usage

Every method is available on `AsyncTruthChain` as a coroutine:

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
from truthchain import TruthChain
from truthchain.exceptions import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    ValidationError,
    ServerError,
)

client = TruthChain(api_key="tc_live_...", base_url="https://your-server.com")

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
    print("TruthChain server error — try again later")
```

### Exception hierarchy

```
TruthChainError
├── AuthenticationError   (HTTP 401)
├── NotFoundError         (HTTP 404)
├── ValidationError       (HTTP 422)
├── RateLimitError        (HTTP 429)
├── QuotaExceededError    (HTTP 429 + quota message)
├── ConflictError         (HTTP 400 / 409)
└── ServerError           (HTTP 5xx)
```

---

## Full API Reference

### `TruthChain(api_key, base_url, timeout)`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_key` | — | Your `tc_live_...` API key |
| `base_url` | `http://localhost:8000` | TruthChain server URL |
| `timeout` | `30.0` | Request timeout in seconds |

Supports use as a context manager (`with TruthChain(...) as client:`).

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
| `signup(name, email, password, tier, base_url)` | `SignupResult` | Register new org |
| `login(email, password, base_url)` | `LoginResult` | Login, get fresh key |

### `AsyncTruthChain`

Identical interface to `TruthChain` — every method is `async`. Supports `async with AsyncTruthChain(...) as client:`.

---

## Releasing a New Version

1. **Bump the version** in [`pyproject.toml`](pyproject.toml):
   ```toml
   version = "1.0.2"
   ```

2. **Build** the distribution files:
   ```bash
   pip install build twine
   python -m build
   ```
   This creates `dist/truthchain-<version>-py3-none-any.whl` and `dist/truthchain-<version>.tar.gz`.

3. **Verify** the package:
   ```bash
   python -m twine check dist/*
   ```

4. **Upload to PyPI** (requires a [PyPI API token](https://pypi.org/manage/account/#api-tokens)):
   ```bash
   python -m twine upload dist/* --username __token__ --password <your-pypi-token>
   ```
   Or upload manually at [pypi.org/manage/project/truthchain/releases/](https://pypi.org/manage/project/truthchain/releases/) by dragging the two files from `dist/`.

5. **Tag the release** in Git:
   ```bash
   git tag v1.0.2
   git push origin v1.0.2
   ```

---

## License

[MIT](LICENSE) © 2026 TruthChain

