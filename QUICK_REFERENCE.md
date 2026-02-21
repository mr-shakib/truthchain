# TruthChain - Quick Reference

**Current Version:** Week 7-8 Complete  
**Last Updated:** February 21, 2026

---

## 🚀 Quick Start

### Start the System

```powershell
# 1. Navigate to project
cd D:\Personal\Project\AI-Engineering\ai-labs\truthchain

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Start API server
.\venv\Scripts\python.exe -m uvicorn backend.api.main:app --host localhost --port 8888 --reload
```

### Create Organization & Test

```powershell
# Create organization
$signup = @{
    name = "My Company"
    email = "company@example.com"
    password = "SecurePass123!"
    tier = "free"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8888/v1/auth/signup" `
    -Method POST -Body $signup -ContentType "application/json"

$apiKey = $response.api_key

# Run validation
$validation = @{
    output = @{ user_id = 123; hours = 8 }
    rules = @(
        @{
            type = "schema"
            name = "check"
            schema = @{
                type = "object"
                properties = @{
                    user_id = @{ type = "integer" }
                    hours = @{ type = "number" }
                }
            }
        }
    )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:8888/v1/validate" `
    -Method POST -Headers @{"X-API-Key"=$apiKey} `
    -Body $validation -ContentType "application/json"

# Check analytics
Invoke-RestMethod -Uri "http://localhost:8888/v1/analytics/overview" `
    -Headers @{"X-API-Key"=$apiKey}
```

---

## 📋 Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/auth/signup` | POST | Create organization |
| `/v1/auth/api-keys` | POST | Create API key |
| `/v1/auth/api-keys` | GET | List API keys |
| `/v1/auth/api-keys/{id}` | DELETE | Revoke API key |
| `/v1/validate` | POST | Validate AI output |
| `/v1/analytics/overview` | GET | Full analytics dashboard |
| `/v1/analytics/validation-stats` | GET | Validation metrics |
| `/v1/analytics/usage-stats` | GET | Quota usage |
| `/v1/analytics/daily-stats` | GET | Daily breakdown |
| `/v1/analytics/recent-validations` | GET | Recent logs |
| `/v1/analytics/top-violations` | GET | Common errors |
| `/docs` | GET | Interactive API docs |

---

## 🗄️ Database Access

```powershell
# Connect to PostgreSQL
psql -U postgres -d truthchain

# Common queries
SELECT * FROM organizations ORDER BY created_at DESC LIMIT 5;
SELECT * FROM validation_logs ORDER BY created_at DESC LIMIT 5;
SELECT name, usage_current_month, monthly_quota FROM organizations;
```

---

## 🔧 Database Migrations

```powershell
cd backend

# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Check current version
alembic current

# View history
alembic history
```

---

## 📊 Useful Scripts

### Check Logs
```powershell
.\venv\Scripts\python.exe check_logs.py
```

### Test Week 7-8 Features
```powershell
.\venv\Scripts\python.exe test_week7_8.py
```

---

## 🧪 Testing Commands

```powershell
# Test signup
$body = '{"name":"Test","email":"test@test.com","password":"Test123!","tier":"free"}'
Invoke-RestMethod "http://localhost:8888/v1/auth/signup" -Method POST -Body $body -ContentType "application/json"

# Test validation (replace with your API key)
$key = "tc_live_your-key-here"
$val = '{"output":{"x":1},"rules":[{"type":"schema","name":"t","schema":{"type":"object"}}]}'
Invoke-RestMethod "http://localhost:8888/v1/validate" -Method POST -Headers @{"X-API-Key"=$key} -Body $val -ContentType "application/json"

# Test analytics
Invoke-RestMethod "http://localhost:8888/v1/analytics/usage-stats" -Headers @{"X-API-Key"=$key}
```

---

## 📁 Important Files

| File | Description |
|------|-------------|
| `SESSION_SUMMARY.md` | Complete project history |
| `WEEK_7-8_SUMMARY.md` | Latest features documentation |
| `backend/api/main.py` | FastAPI app entry point |
| `backend/api/routes/` | API endpoint implementations |
| `backend/core/` | Business logic (validation, auth, analytics) |
| `backend/models/` | Database models |
| `backend/alembic/` | Database migrations |
| `.env` | Local configuration |

---

## 🔑 Environment Variables

Required in `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:nacht0905@localhost:5432/truthchain
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
```

---

## 🐛 Troubleshooting

### Server won't start
```powershell
# Kill process on port 8888
Get-NetTCPConnection -LocalPort 8888 -ErrorAction SilentlyContinue | 
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### Database connection fails
```powershell
# Test connection
psql -U postgres -d truthchain -c "SELECT 1;"
```

### Check server logs
Server logs appear in terminal where uvicorn is running

---

## 📈 Current Stats

- **Total Endpoints:** 14 (auth: 4, validation: 2, analytics: 6, health: 2)
- **Database Tables:** 3 (organizations, api_keys, validation_logs)
- **Organization Tiers:** 4 (free, startup, business, enterprise)
- **Features Completed:** Weeks 3-8 ✅
- **Next Phase:** Week 9-10 (Advanced features or frontend)

---

## 🎯 What's Working

- [x] Organization signup with tier selection
- [x] API key generation and management
- [x] Schema validation (JSON Schema)
- [x] Rule-based validation (range, pattern, etc.)
- [x] Quota enforcement (429 when exhausted)
- [x] Validation logging (full audit trail)
- [x] Usage tracking (real-time)
- [x] Analytics queries (stats, trends, violations)
- [x] Database migrations (Alembic)
- [x] Async operations (FastAPI + SQLAlchemy)

---

## 📚 Documentation

- **API Docs:** http://localhost:8888/docs
- **ReDoc:** http://localhost:8888/redoc
- **Session Summary:** [SESSION_SUMMARY.md](SESSION_SUMMARY.md)
- **Week 7-8 Details:** [WEEK_7-8_SUMMARY.md](WEEK_7-8_SUMMARY.md)

---

**Ready to build!** 🚀
