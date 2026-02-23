# TruthChain — AI Validation Platform

> Real-time hallucination detection and factual accuracy verification for LLM outputs.  
> Validate AI outputs against any business rules in **<100ms**.

[![Python SDK](https://img.shields.io/pypi/v/truthchain.svg?label=pip%20install%20truthchain)](https://pypi.org/project/truthchain/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](sdk/python/LICENSE)

---

## What is TruthChain?

TruthChain is a SaaS platform that sits between your LLM and your users.  
It validates AI-generated outputs against configurable rules — catching schema violations, out-of-range values, hallucinated references, and more — before they reach production.

---

## SDKs

| Language | Install | Source |
|----------|---------|--------|
| **Python** | `pip install truthchain` | [`sdk/python/`](sdk/python/) |
| **TypeScript / Node** | `npm install @truthchain/node` *(coming soon)* | [`sdk/typescript/`](sdk/typescript/) |

**Python SDK quick start:**

```python
from truthchain import TruthChain

client = TruthChain(api_key="tc_live_...", base_url="https://your-server.com")

result = client.validate(
    output={"score": 95, "label": "positive"},
    rules=[
        {"type": "range",    "name": "score_range",   "field": "score", "min": 0, "max": 100},
        {"type": "required", "name": "label_present",  "fields": ["label"]},
    ],
)
print(result.status)    # "passed"
print(result.is_valid)  # True
```

---

## Project Structure

```
truthchain/
├── backend/          # FastAPI backend (Python)
│   ├── api/          # REST endpoints
│   ├── core/         # Validation engine, rule engine, auto-corrector
│   ├── models/       # SQLAlchemy models
│   ├── db/           # Database connection & migrations (Alembic)
│   └── config/       # Environment settings
├── frontend/         # Next.js 14 dashboard (TypeScript)
│   ├── app/          # App router pages
│   ├── components/   # React components
│   └── lib/          # API client, auth, billing helpers
├── sdk/
│   ├── python/       # Python SDK — published at pypi.org/project/truthchain
│   └── typescript/   # TypeScript/Node SDK
├── infra/
│   ├── docker/       # Dockerfiles
│   └── k8s/          # Kubernetes manifests
├── docker-compose.yml
└── docker-compose.prod.yml
```

---

## Quick Start (Local Development)

### 1. Start infrastructure

```bash
docker-compose up -d   # PostgreSQL + Redis
```

### 2. Run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn api.main:app --reload
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 3. Run the frontend

```bash
cd frontend
npm install
npm run dev
# Dashboard: http://localhost:3000
```

### 4. Install the SDK

```bash
pip install truthchain
```

See [`sdk/python/README.md`](sdk/python/README.md) for full SDK documentation.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, Python 3.11+ |
| Database | PostgreSQL 15+ (SQLAlchemy + Alembic) |
| Cache | Redis 7+ |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| ML / AI | scikit-learn, sentence-transformers |
| Container | Docker, Docker Compose |
| Python SDK | `httpx`, published on PyPI |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/auth/signup` | Register organization |
| `POST` | `/v1/auth/login` | Login, receive API key |
| `POST` | `/v1/validate` | Validate AI output |
| `GET` | `/v1/analytics/overview` | Analytics overview |
| `GET` | `/v1/billing/subscription` | Current plan |
| `POST` | `/v1/billing/upgrade` | Upgrade plan |
| `GET` | `/v1/auth/api-keys` | List API keys |
| `GET` | `/health` | Health check |

Full reference: [`/docs`](http://localhost:8000/docs) (Swagger UI when running locally).

---

## Documentation

| Document | Description |
|----------|-------------|
| [`sdk/python/README.md`](sdk/python/README.md) | Python SDK reference |
| [`sdk/typescript/README.md`](sdk/typescript/README.md) | TypeScript SDK reference |
| [`TRUTHCHAIN_API_DOCUMENTATION.md`](../TRUTHCHAIN_API_DOCUMENTATION.md) | Full API reference |
| [`TRUTHCHAIN_DEPLOYMENT_GUIDE.md`](../TRUTHCHAIN_DEPLOYMENT_GUIDE.md) | AWS deployment guide |
| [`TRUTHCHAIN_SECURITY_COMPLIANCE.md`](../TRUTHCHAIN_SECURITY_COMPLIANCE.md) | GDPR, SOC 2, HIPAA |

---

## License

[MIT](sdk/python/LICENSE) © 2026 TruthChain

