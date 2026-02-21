# @truthchain/node

TypeScript / JavaScript SDK for the [TruthChain](https://github.com/truthchain/truthchain) AI-validation API.

Validates AI / LLM outputs against configurable rules — range checks, schema validation,
fuzzy-match enum correction, semantic grounding, external reference verification, and more.

> **Python SDK:** `sdk/python/` (feature-complete, pip-installable)  
> **This package:** `@truthchain/node` — mirrors the Python SDK, adds native TypeScript types.

---

## Requirements

- **Node.js ≥ 18** (for native `fetch`)
- A running TruthChain backend (`uvicorn backend.api.main:app --reload`)

---

## Installation

```bash
# From npm (once published)
npm install @truthchain/node

# Local development — from this directory
npm install
npm run build
```

---

## Quick Start

```typescript
import { TruthChain } from "@truthchain/node";

const client = new TruthChain({ apiKey: "tc_live_..." });

// Validate AI output
const result = await client.validate(
  { fiqh_school: "Hanafy", sehri_duration_minutes: 30 },
  [
    {
      type: "enum",
      name: "fiqh_school_check",
      field: "fiqh_school",
      valid_options: ["Hanafi", "Jafaria", "Shafi", "Maliki", "Hanbali"],
    },
  ],
  { auto_correct: true },
);

console.log(result.is_valid);            // false (typo detected)
console.log(result.corrected_output);    // { fiqh_school: "Hanafi", ... }
console.log(result.corrections_applied); // ["Clamped fiqh_school..."]
```

---

## API Reference

### `new TruthChain(config)`

| Option | Type | Default | Description |
|---|---|---|---|
| `apiKey` | `string` | — | Your TruthChain API key (`tc_live_...`) |
| `baseUrl` | `string` | `http://localhost:8000` | API server URL |
| `timeoutMs` | `number` | `30000` | Request timeout in ms |

---

### `client.validate(output, rules, context?)`

Validate AI output against a list of rules.

```typescript
const result = await client.validate(
  { hours: 25 },
  [{ type: "range", field: "hours", name: "hours_check", min: 0, max: 24 }],
);
// result.is_valid === false
// result.violations[0].message === "hours must be between 0 and 24"
```

**Supported rule types:** `schema`, `range`, `pattern`, `semantic`, `web_verify`,
`anomaly_ml`, `enum`, `required`, `external_ref`

---

### `client.complete(request)` — LLM Proxy

Proxy an LLM call through TruthChain validation. The server forwards your
`messages` to the chosen provider (Groq, OpenAI, or custom), validates the
response, optionally auto-corrects it, and returns the full result.

```typescript
const result = await client.complete({
  provider: "groq",
  messages: [
    { role: "system", content: 'Reply only with JSON: {"sehri_time": "HH:MM AM/PM"}' },
    { role: "user",   content: "What is the Sehri time in Dhaka today?" },
  ],
  validation_rules: [
    {
      type: "external_ref",
      field: "sehri_time",
      connector: "aladhan_fajr_in_range",
      params: { city: "Dhaka", country: "Bangladesh", tolerance_minutes: 15 },
    },
  ],
  output_field: "sehri_time",
});

console.log(result.validation?.is_valid);  // true/false
console.log(result.content);               // final (possibly corrected) text
```

Requires `GROQ_API_KEY` (free at [console.groq.com](https://console.groq.com)) or
`OPENAI_API_KEY` set in the server's `.env`.

---

### Analytics

```typescript
const overview = await client.getAnalytics();
const stats    = await client.getValidationStats();
```

### Billing

```typescript
const plans = await client.getPlans();
const sub   = await client.getSubscription();
await client.upgrade("startup");
```

### API Key Management

```typescript
const keys    = await client.listApiKeys();
const newKey  = await client.createApiKey("Production Key");
console.log(newKey.key);   // Save this — shown only once!

await client.rotateApiKey(keys[0].id);
await client.revokeApiKey(keys[1].id);
```

---

### Top-level Helpers (no API key required)

```typescript
import { signup, login } from "@truthchain/node";

// Register a new organization
const { api_key } = await signup("Acme Corp", "dev@acme.com", "s3cretPW!");
console.log(api_key); // tc_live_... ← save this!

// Login to get a fresh key
const result = await login("dev@acme.com", "s3cretPW!");
const client = new TruthChain({ apiKey: result.api_key });
```

---

## Error Handling

All errors extend `TruthChainError` for easy `instanceof` checks:

```typescript
import {
  TruthChain,
  TruthChainError,
  AuthenticationError,
  QuotaExceededError,
  RateLimitError,
} from "@truthchain/node";

try {
  const result = await client.validate(output, rules);
} catch (err) {
  if (err instanceof AuthenticationError) {
    console.error("Bad API key:", err.message);
  } else if (err instanceof RateLimitError) {
    console.error(`Rate limited. Retry after ${err.retryAfter}s`);
  } else if (err instanceof QuotaExceededError) {
    console.error("Monthly quota exhausted — upgrade your plan");
  } else if (err instanceof TruthChainError) {
    console.error(`API error ${err.statusCode}: ${err.message}`);
  }
}
```

---

## TypeScript Types

All request/response shapes are exported as TypeScript interfaces:

```typescript
import type {
  ValidationResult,
  ValidationRule,
  Violation,
  ProxyResult,
  CompleteRequest,
  AnalyticsOverview,
  Subscription,
} from "@truthchain/node";
```

---

## Demo

```bash
npm run build
node dist/demo.js
# or with custom server:
TRUTHCHAIN_BASE_URL=http://myserver:8000 TRUTHCHAIN_API_KEY=tc_live_... node dist/demo.js
```

---

## Publishing to npm

```bash
npm run build
npm publish --access public
```

---

## License

MIT
