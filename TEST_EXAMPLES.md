# Week 3-4 Core Validation Engine - Test Examples

## ✅ Implementation Complete

All core validation engine components have been successfully implemented and tested.

---

## Test Cases

### Test 1: Valid Data (All Rules Pass)
**Request:**
```bash
curl -X POST "http://localhost:8000/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "output": {
      "user_id": 12345,
      "hours": 8,
      "project_name": "Project-X"
    },
    "rules": [
      {
        "type": "schema",
        "name": "output_structure",
        "schema": {
          "type": "object",
          "properties": {
            "user_id": {"type": "integer"},
            "hours": {"type": "number"},
            "project_name": {"type": "string"}
          },
          "required": ["user_id", "hours", "project_name"]
        }
      },
      {
        "type": "range",
        "name": "hours_check",
        "field": "hours",
        "min": 0,
        "max": 24,
        "severity": "error"
      }
    ]
  }'
```

**Expected Response:**
```json
{
  "status": "passed",
  "valid": true,
  "violations": [],
  "auto_corrected": false,
  "corrected_output": null,
  "validation_id": "val_xxxxx",
  "latency_ms": 0,
  "timestamp": "2026-02-20T23:25:41.001247"
}
```

---

### Test 2: Range Violation
**Request:**
```bash
curl -X POST "http://localhost:8000/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "output": {
      "user_id": 12345,
      "hours": 30,
      "project_name": "Project-X"
    },
    "rules": [
      {
        "type": "range",
        "name": "hours_check",
        "field": "hours",
        "min": 0,
        "max": 24,
        "severity": "error"
      }
    ]
  }'
```

**Expected Response:**
```json
{
  "status": "failed",
  "valid": false,
  "violations": [
    {
      "rule_name": "hours_check",
      "violation_type": "constraint",
      "field": "hours",
      "message": "hours must be <= 24",
      "severity": "error",
      "found_value": 30,
      "expected_value": "<= 24",
      "suggestion": null
    }
  ],
  "auto_corrected": false,
  "corrected_output": null,
  "validation_id": "val_xxxxx",
  "latency_ms": 0,
  "timestamp": "2026-02-20T23:34:41.089704"
}
```

---

### Test 3: Schema and Pattern Violations
**Request:**
```bash
curl -X POST "http://localhost:8000/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "output": {
      "user_id": "not-a-number",
      "email": "invalid-email",
      "hours": 8
    },
    "rules": [
      {
        "type": "schema",
        "name": "type_check",
        "schema": {
          "type": "object",
          "properties": {
            "user_id": {"type": "integer"},
            "email": {"type": "string"},
            "hours": {"type": "number"}
          },
          "required": ["user_id", "email"]
        }
      },
      {
        "type": "pattern",
        "name": "email_format",
        "field": "email",
        "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}$",
        "message": "Invalid email format"
      }
    ]
  }'
```

**Expected Response:**
```json
{
  "status": "failed",
  "valid": false,
  "violations": [
    {
      "rule_name": "type_check",
      "violation_type": "schema",
      "field": "user_id",
      "message": "'not-a-number' is not of type 'integer'",
      "severity": "error",
      "found_value": "not-a-number",
      "expected_value": "{'type': 'integer'}",
      "suggestion": null
    },
    {
      "rule_name": "email_format",
      "violation_type": "constraint",
      "field": "email",
      "message": "Invalid email format",
      "severity": "error",
      "found_value": "invalid-email",
      "expected_value": "Pattern: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
      "suggestion": null
    }
  ],
  "auto_corrected": false,
  "corrected_output": null,
  "validation_id": "val_xxxxx",
  "latency_ms": 0,
  "timestamp": "2026-02-20T23:35:01.897487"
}
```

---

### Test 4: Constraint Validation (Custom Expressions)
**Request:**
```bash
curl -X POST "http://localhost:8000/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "output": {
      "amount": -50,
      "quantity": 5
    },
    "rules": [
      {
        "type": "constraint",
        "name": "positive_amount",
        "field": "amount",
        "expression": "value > 0",
        "message": "Amount must be positive",
        "severity": "error"
      },
      {
        "type": "constraint",
        "name": "quantity_check",
        "field": "quantity",
        "expression": "value >= 1 and value <= 100",
        "message": "Quantity must be between 1 and 100"
      }
    ]
  }'
```

**Expected Response:**
```json
{
  "status": "failed",
  "valid": false,
  "violations": [
    {
      "rule_name": "positive_amount",
      "violation_type": "constraint",
      "field": "amount",
      "message": "Amount must be positive",
      "severity": "error",
      "found_value": -50,
      "expected_value": "value > 0",
      "suggestion": null
    }
  ],
  "auto_corrected": false,
  "corrected_output": null,
  "validation_id": "val_xxxxx",
  "latency_ms": 0,
  "timestamp": "2026-02-20T23:36:36.304450"
}
```

---

## PowerShell Test Commands

```powershell
# Test 1: Valid data
$body = @'
{
  "output": {"user_id": 12345, "hours": 8, "project_name": "Project-X"},
  "rules": [
    {"type": "range", "name": "hours_check", "field": "hours", "min": 0, "max": 24}
  ]
}
'@
Invoke-RestMethod -Uri "http://localhost:8000/v1/validate" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10

# Test 2: Invalid range (hours > 24)
$body = @'
{
  "output": {"user_id": 12345, "hours": 30, "project_name": "Project-X"},
  "rules": [
    {"type": "range", "name": "hours_check", "field": "hours", "min": 0, "max": 24}
  ]
}
'@
Invoke-RestMethod -Uri "http://localhost:8000/v1/validate" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10

# Test 3: Schema violation
$body = @'
{
  "output": {"user_id": "not-a-number", "email": "bad-email"},
  "rules": [
    {
      "type": "schema",
      "name": "type_check",
      "schema": {
        "type": "object",
        "properties": {
          "user_id": {"type": "integer"},
          "email": {"type": "string"}
        },
        "required": ["user_id", "email"]
      }
    },
    {
      "type": "pattern",
      "name": "email_format",
      "field": "email",
      "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    }
  ]
}
'@
Invoke-RestMethod -Uri "http://localhost:8000/v1/validate" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10

# Test 4: Constraint violation
$body = @'
{
  "output": {"amount": -50, "quantity": 5},
  "rules": [
    {
      "type": "constraint",
      "name": "positive_amount",
      "field": "amount",
      "expression": "value > 0",
      "message": "Amount must be positive"
    }
  ]
}
'@
Invoke-RestMethod -Uri "http://localhost:8000/v1/validate" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10
```

---

## API Endpoints

- **Base URL:** http://localhost:8000
- **Documentation:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health
- **Validation Endpoint:** POST http://localhost:8000/v1/validate

---

## Implemented Features

### ✅ Schema Validator (`backend/core/schema_validator.py`)
- JSON Schema validation
- Type checking (integer, string, number, boolean, array, object)
- Required field validation
- Nested object support
- Error handling and detailed violation messages

### ✅ Rule Engine (`backend/core/rule_engine.py`)
- Range validation (min/max values)
- Constraint validation (custom expressions with safe eval)
- Pattern validation (regex)
- Nested field access using dot notation
- Comprehensive error handling

### ✅ Validation API Endpoint (`backend/api/routes/validation.py`)
- POST /v1/validate endpoint
- Request/response Pydantic models
- Auto-generated API documentation
- Health check endpoint
- Error handling

### ✅ Validation Engine Integration (`backend/core/validation_engine.py`)
- Orchestrates schema and rule validation
- Generates unique validation IDs
- Tracks latency
- Determines validation status (passed/failed/warning)
- Returns detailed violation information

---

## Next Steps (Week 5-6)

1. **Context Manager** - Database reference validation
2. **Auto-Corrector** - Automatic fixing of violations
3. **Authentication** - API key management
4. **Database Models** - PostgreSQL schema and ORM
5. **Validation Logging** - Track validation history
6. **Usage Tracking** - Monitor API usage and quotas

---

**Last Updated:** February 21, 2026  
**Status:** Week 3-4 Core Validation Engine ✅ **COMPLETE**
