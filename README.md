# TruthChain - AI Validation SaaS Platform

> Real-time hallucination detection and factual accuracy verification for LLM outputs

## 🚀 Project Status

**Current Phase:** Week 1-2 - Environment Setup ✅ **COMPLETED**

## 📋 What's Been Set Up

### ✅ Completed Tasks

1. **Project Structure** - Git repository initialized
   - Backend, frontend, SDK, docs, tests, infra directories created
   - `.gitignore` configured

2. **Backend (FastAPI)** ✅
   - Python 3.11.9 virtual environment created
   - All dependencies installed (FastAPI, PostgreSQL, Redis, ML libraries)
   - Project structure: `api/`, `core/`, `models/`, `db/`, `config/`
   - `api/main.py` - Main FastAPI application with CORS and timing middleware
   - `core/validation_engine.py` - Core validation engine skeleton
   - `config/settings.py` - Environment configuration with Pydantic Settings
   - **Server running:** http://localhost:8000

3. **Frontend (Next.js 14)** ✅
   - TypeScript + Tailwind CSS configured
   - Additional dependencies: Recharts, Zustand, Radix UI
   - Ready for dashboard development

4. **Docker Infrastructure** ✅
   - `docker-compose.yml` created for PostgreSQL & Redis
   - Dockerfiles created for backend and frontend
   - *Note: Docker not installed yet - will use local PostgreSQL/Redis for now*

5. **Configuration** ✅
   - `.env.example` template created
   - Settings management with Pydantic

## 🏗️ Project Structure

```
truthchain/
├── backend/                 # FastAPI backend
│   ├── api/                # API routes and endpoints
│   │   ├── __init__.py
│   │   └── main.py        # Main FastAPI app ✅
│   ├── core/               # Core business logic
│   │   ├── __init__.py
│   │   └── validation_engine.py  # Validation engine ✅
│   ├── models/             # Database models (SQLAlchemy)
│   ├── db/                 # Database connection & migrations
│   ├── config/             # Configuration
│   │   ├── __init__.py
│   │   └── settings.py    # Environment settings ✅
│   ├── requirements.txt   # Python dependencies ✅
│   ├── Dockerfile         # Docker configuration ✅
│   └── venv/              # Virtual environment ✅
├── frontend/               # Next.js 14 frontend
│   ├── app/               # App router pages
│   ├── components/        # React components
│   ├── lib/               # Utilities
│   ├── package.json       # Node dependencies ✅
│   └── Dockerfile         # Docker configuration ✅
├── sdk/                    # Client SDKs
│   └── python/            # Python SDK (to be built)
│       └── truthchain/
├── tests/                  # Test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                   # Documentation
├── infra/                  # Infrastructure as code
│   ├── docker/
│   └── k8s/
├── docker-compose.yml     # Docker Compose config ✅
└── .gitignore             # Git ignore rules ✅
```

## 🔧 Quick Start

### Backend API

```bash
# Activate virtual environment
cd backend
.\venv\Scripts\Activate.ps1  # Windows

# Run the API server
uvicorn api.main:app --reload

# API will be at: http://localhost:8000
# Docs at: http://localhost:8000/docs
```

**Test the API:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
# Response: {"status": "healthy"}
```

### Frontend (Next.js)

```bash
cd frontend
npm run dev

# Dashboard will be at: http://localhost:3000
```

## 📊 API Endpoints (Current)

- `GET /` - Service info
- `GET /health` - Health check ✅
- `GET /docs` - Interactive API documentation (Swagger UI)

## 🎯 Next Steps (Week 3-4: Core Validation Engine)

According to the [Implementation Guide](TRUTHCHAIN_IMPLEMENTATION_GUIDE.md), the next phase is:

### Week 3-4 Goals:

1. **Schema Validator** (`backend/core/schema_validator.py`)
   - JSON Schema validation
   - Type checking (int, string, float, bool, array, object)
   - Required field validation
   - Nested object support

2. **Rule Engine** (`backend/core/rule_engine.py`)
   - Range validation (min/max)
   - Constraint validation (custom expressions)
   - Pattern validation (regex)
   - Nested field access

3. **Context Manager** (`backend/core/context_manager.py`)
   - Database reference validation
   - Connection pooling
   - Query caching

4. **Auto-Corrector** (`backend/core/auto_corrector.py`)
   - Constraint fixing (clamping values)
   - Fuzzy matching for references

5. **Database Setup**
   - Install PostgreSQL locally or use Docker
   - Create database schema
   - Set up Alembic migrations

6. **Validation API Endpoint**
   - `POST /v1/validate`
   - Request/response models
   - Error handling

## 🛠️ Technology Stack

| Component | Technology | Status |
|-----------|-----------|--------|
| **Backend** | FastAPI 0.104+ | ✅ Installed |
| **Database** | PostgreSQL 15+ | ⏳ Pending setup |
| **Cache** | Redis 7+ | ⏳ Pending setup |
| **Frontend** | Next.js 14 | ✅ Installed |
| **ML/AI** | Scikit-learn, Sentence Transformers | ✅ Installed |
| **Testing** | Pytest | ✅ Installed |
| **Container** | Docker | ❌ Not installed |

## 📝 Development Notes

### Environment Variables

Copy `.env.example` to `.env` in the `backend/` directory:

```bash
cd backend
cp .env.example .env
```

Default development values:
- Database: `postgresql://truthchain:truthchain_dev_password@localhost:5432/truthchain`
- Redis: `redis://localhost:6379`
- Secret Key: `dev-secret-key-change-in-production` (⚠️ Change in production!)

### Dependencies Installed

**Backend Python packages:**
- FastAPI 0.104.1 - Web framework
- Uvicorn 0.24.0 - ASGI server
- Pydantic 2.5.0 - Data validation
- SQLAlchemy 2.0.23 - ORM
- Alembic 1.12.1 - Database migrations
- psycopg2-binary 2.9.9 - PostgreSQL driver
- Redis 5.0.1 - Redis client
- python-jose 3.3.0 - JWT tokens
- passlib 1.7.4 - Password hashing
- scikit-learn 1.3.2 - ML algorithms
- sentence-transformers 2.2.2 - Semantic embeddings
- pytest 7.4.3 - Testing framework

**Frontend npm packages:**
- Next.js 14 - React framework
- TypeScript - Type safety
- Tailwind CSS - Styling
- Recharts - Data visualization
- Zustand - State management
- Radix UI - Accessible components

## 🧪 Testing

```bash
# Backend tests (when written)
cd backend
pytest

# Frontend tests (when written)
cd frontend
npm test
```

## 📚 Documentation

- [Implementation Guide](TRUTHCHAIN_IMPLEMENTATION_GUIDE.md) - Week-by-week build plan
- [API Documentation](TRUTHCHAIN_API_DOCUMENTATION.md) - Complete API reference
- [Product Spec](TRUTHCHAIN_PRODUCT_SPEC.md) - Product vision & features
- [Deployment Guide](TRUTHCHAIN_DEPLOYMENT_GUIDE.md) - AWS deployment instructions
- [Security & Compliance](TRUTHCHAIN_SECURITY_COMPLIANCE.md) - GDPR, SOC 2, HIPAA

## 🚦 Current Server Status

- ✅ **Backend API:** Running at http://localhost:8000
- ⏳ **Frontend:** Not started yet
- ⏳ **PostgreSQL:** Not running (need to install or use Docker)
- ⏳ **Redis:** Not running (need to install or use Docker)

## 📞 Need Help?

Follow the [Implementation Guide](TRUTHCHAIN_IMPLEMENTATION_GUIDE.md) step-by-step for detailed instructions on each feature.

---

**Last Updated:** February 21, 2026  
**Week:** 1-2 (Environment Setup) ✅ COMPLETED  
**Next Week:** 3-4 (Core Validation Engine)
