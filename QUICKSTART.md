# 🎯 TruthChain Development Quick Start

## ✅ Week 1-2 COMPLETED!

### What You Have Now:

1. **Backend API** ✅ - Running at http://localhost:8000
2. **Frontend Setup** ✅ - Ready to develop
3. **Project Structure** ✅ - All directories created
4. **Dependencies** ✅ - All packages installed

---

## 🚀 Next: Week 3-4 - Core Validation Engine

### Goals for This Week:

Build the heart of TruthChain - the validation engine that checks AI outputs.

### Step-by-Step Plan:

#### 1️⃣ Schema Validator (Day 1-2)
**File:** `backend/core/schema_validator.py`

```bash
# Create the file and implement:
# - JSON Schema validation
# - Type checking
# - Required fields
# - Nested objects
```

**Test it:**
```python
# Example validation
{
  "output": {"user_id": 123, "hours": 8},
  "rules": [{
    "type": "schema",
    "schema": {
      "type": "object",
      "properties": {
        "user_id": {"type": "integer"},
        "hours": {"type": "number"}
      },
      "required": ["user_id", "hours"]
    }
  }]
}
```

#### 2️⃣ Rule Engine (Day 3-4)
**File:** `backend/core/rule_engine.py`

```bash
# Implement:
# - Range validation (min/max)
# - Constraint checking
# - Regex patterns
# - Nested field access
```

**Test it:**
```python
# Example: hours must be 0-24
{
  "type": "range",
  "field": "hours",
  "min": 0,
  "max": 24
}
```

#### 3️⃣ Validation API Endpoint (Day 5-6)
**File:** `backend/api/routes/validation.py`

```bash
# Create:
# - POST /v1/validate endpoint
# - Request/response models
# - Integration with validation engine
```

**Test it:**
```bash
curl -X POST http://localhost:8000/v1/validate \
  -H "Content-Type: application/json" \
  -d '{
    "output": {"hours": 30},
    "rules": [{"type": "range", "field": "hours", "max": 24}]
  }'
```

#### 4️⃣ Database Setup (Day 7)
```bash
# Option 1: Install PostgreSQL locally
# Download from: https://www.postgresql.org/download/windows/

# Option 2: Use Docker (if installed)
docker compose up -d postgres redis

# Create database
# Run migrations with Alembic
```

---

## 📝 Daily Checklist

### Day 1: Schema Validator
- [ ] Create `schema_validator.py`
- [ ] Implement JSON Schema validation
- [ ] Write 10+ unit tests
- [ ] Test with sample data

### Day 2: Rule Engine
- [ ] Create `rule_engine.py`
- [ ] Implement range validation
- [ ] Implement constraint validation
- [ ] Implement pattern validation
- [ ] Write 15+ unit tests

### Day 3: Complete Validation Engine
- [ ] Update `validation_engine.py`
- [ ] Integrate schema_validator
- [ ] Integrate rule_engine
- [ ] Test end-to-end validation

### Day 4: Auto-Corrector
- [ ] Create `auto_corrector.py`
- [ ] Implement constraint fixing
- [ ] Test auto-correction

### Day 5: Validation API
- [ ] Create `api/routes/validation.py`
- [ ] Create request/response models
- [ ] Implement POST /v1/validate
- [ ] Test with curl/Postman

### Day 6: Context Manager (Optional)
- [ ] Create `context_manager.py`
- [ ] Implement database reference checking
- [ ] Set up connection pooling

### Day 7: Testing & Documentation
- [ ] Run all unit tests
- [ ] Write integration tests
- [ ] Update API documentation
- [ ] Prepare for Week 5-6

---

## 🧪 How to Test Your Code

### Run Backend Tests
```bash
cd backend
.\venv\Scripts\Activate.ps1
pytest tests/ -v
```

### Test API Manually
```bash
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Validation endpoint (when built)
Invoke-RestMethod -Uri "http://localhost:8000/v1/validate" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"output": {"hours": 8}, "rules": []}'
```

### View API Docs
Open in browser: http://localhost:8000/docs

---

## 📚 Reference Files

While building, refer to these sections in the Implementation Guide:

- **Section 1.1** - Validation Engine Architecture
- **Section 1.2** - Schema Validator
- **Section 1.3** - Rule Engine
- **Section 1.4** - Context Manager
- **Section 1.5** - Auto-Corrector
- **Section 2.3** - Validation Endpoint

---

## 🎓 Learning Resources

**JSON Schema:**
- https://json-schema.org/understanding-json-schema/

**FastAPI:**
- https://fastapi.tiangolo.com/tutorial/

**Pydantic:**
- https://docs.pydantic.dev/latest/

**Pytest:**
- https://docs.pytest.org/

---

## 💡 Pro Tips

1. **Test as you go** - Don't wait until the end to test
2. **Use type hints** - Python type hints help catch bugs early
3. **Read the API docs** - http://localhost:8000/docs shows your API
4. **Check examples** - The Implementation Guide has code examples for everything
5. **Commit often** - Use Git to save progress

---

## 🐛 Troubleshooting

**API won't start?**
```bash
# Make sure you're in the backend directory with venv activated
cd backend
.\venv\Scripts\Activate.ps1
uvicorn api.main:app --reload
```

**Import errors?**
```bash
# Make sure all packages are installed
pip install -r requirements.txt
```

**Need to stop the server?**
- Press `Ctrl+C` in the terminal

---

## 📞 Getting Unstuck

If you get stuck:
1. Check the [Implementation Guide](TRUTHCHAIN_IMPLEMENTATION_GUIDE.md) for detailed code examples
2. Look at the API documentation at http://localhost:8000/docs
3. Run tests to see what's failing: `pytest tests/ -v`
4. Check environment variables in `.env`

---

**Ready to build? Let's go! 🚀**

Start with: `backend/core/schema_validator.py`
