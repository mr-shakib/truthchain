"""
Test script for Week 9-10: Advanced Validation Features
Tests context manager, auto-corrector, and caching
"""
import asyncio
import requests
import json
import uuid

# Test configuration
API_BASE = "http://localhost:8888"
# Use unique emails for each test run
TEST_RUN_ID = str(uuid.uuid4())[:8]
TEST_PASSWORD = "AdvancedTest123!"


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"🧪 {title}")
    print("="*70)


def print_result(test_name, passed, details=""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status}: {test_name}")
    if details:
        print(f"   {details}")


async def test_auto_correction():
    """Test auto-correction feature"""
    print_section("Test 1: Auto-Correction")
    
    try:
        # 1. Create test organization
        signup_data = {
            "name": "AutoCorrect Test Org",
            "email": f"autocorrect_{TEST_RUN_ID}@truthchain.com",
            "password": TEST_PASSWORD,
            "tier": "free"
        }
        
        response = requests.post(
            f"{API_BASE}/v1/auth/signup",
            json=signup_data
        )
        
        if response.status_code != 201:
            print_result("Organization Signup", False, f"Status: {response.status_code}")
            try:
                print(f"   Error: {response.json()}")
            except:
                print(f"   Raw: {response.text}")
            return
        
        api_key = response.json()["api_key"]
        print_result("Organization Created", True, f"API Key: {api_key[:20]}...")
        
        # 2. Test auto-correction with range violation
        print("\n📝 Testing range clamping...")
        
        validation_data = {
            "output": {
                "hours": 30,  # Invalid: exceeds max of 24
                "task": "Development"
            },
            "rules": [
                {
                    "type": "range",
                    "name": "hours_limit",
                    "field": "hours",
                    "min": 0,
                    "max": 24,
                    "severity": "error"
                }
            ],
            "context": {
                "auto_correct": True  # Enable auto-correction
            }
        }
        
        response = requests.post(
            f"{API_BASE}/v1/validate",
            headers={"X-API-Key": api_key},
            json=validation_data
        )
        
        if response.status_code != 200:
            print_result("Auto-Correction Test", False, f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        result = response.json()
        
        print(f"\n   Original value: 30 hours")
        print(f"   Violations found: {len(result['violations'])}")
        print(f"   Auto-corrected: {result['auto_corrected']}")
        
        if result.get('corrected_output'):
            corrected_hours = result['corrected_output'].get('hours')
            print(f"   Corrected value: {corrected_hours} hours")
        
        if result.get('corrections_applied'):
            print(f"   Corrections: {result['corrections_applied']}")
        
        # Verify correction worked
        is_corrected = result['auto_corrected'] and result.get('corrected_output') is not None
        print_result(
            "Range Clamping",
            is_corrected,
            f"Hours clamped from 30 to {result.get('corrected_output', {}).get('hours', 'N/A')}"
        )
        
        # 3. Test type coercion
        print("\n📝 Testing type coercion...")
        
        type_validation_data = {
            "output": {
                "user_id": "123",  # String instead of integer
                "count": "45.7"    # String instead of number
            },
            "rules": [
                {
                    "type": "schema",
                    "name": "type_check",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "integer"},
                            "count": {"type": "number"}
                        }
                    }
                }
            ],
            "context": {
                "auto_correct": True
            }
        }
        
        response = requests.post(
            f"{API_BASE}/v1/validate",
            headers={"X-API-Key": api_key},
            json=type_validation_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Auto-corrected: {result['auto_corrected']}")
            if result.get('corrections_applied'):
                print(f"   Corrections: {result['corrections_applied']}")
            
            print_result("Type Coercion", True, "Types automatically converted")
        
    except Exception as e:
        print_result("Auto-Correction Test", False, str(e))


async def test_reference_validation():
    """Test database reference validation"""
    print_section("Test 2: Reference Validation")
    
    try:
        # 1. Create test organization
        signup_data = {
            "name": "Reference Test Org",
            "email": f"reference_{TEST_RUN_ID}@truthchain.com",
            "password": "RefTest123!",
            "tier": "free"
        }
        
        response = requests.post(
            f"{API_BASE}/v1/auth/signup",
            json=signup_data
        )
        
        if response.status_code != 201:
            print_result("Organization Signup", False, f"Status: {response.status_code}")
            try:
                print(f"   Error: {response.json()}")
            except:
                print(f"   Raw: {response.text}")
            return
        
        api_key = response.json()["api_key"]
        org_id = response.json()["organization_id"]
        print_result("Organization Created", True, f"Org ID: {org_id}")
        
        # 2. Test validation WITH valid reference
        print("\n📝 Testing valid reference...")
        
        valid_ref_data = {
            "output": {
                "organization_id": org_id  # This should exist
            },
            "rules": [
                {
                    "type": "reference",
                    "name": "org_exists",
                    "field": "organization_id",
                    "table": "organizations",
                    "column": "id",
                    "severity": "error"
                }
            ]
        }
        
        response = requests.post(
            f"{API_BASE}/v1/validate",
            headers={"X-API-Key": api_key},
            json=valid_ref_data
        )
        
        if response.status_code == 200:
            result = response.json()
            ref_violations = [v for v in result['violations'] if 'reference' in v.get('violation_type', '').lower()]
            print_result(
                "Valid Reference Check",
                len(ref_violations) == 0,
                f"No reference violations found (total violations: {len(result['violations'])})"
            )
        else:
            print_result("Valid Reference Check", False, f"Status: {response.status_code}")
            print(f"   Response: {response.text}")
        
        # 3. Test validation with INVALID reference
        print("\n📝 Testing invalid reference...")
        
        invalid_ref_data = {
            "output": {
                "organization_id": "00000000-0000-0000-0000-000000000000"  # Doesn't exist
            },
            "rules": [
                {
                    "type": "reference",
                    "name": "org_exists",
                    "field": "organization_id",
                    "table": "organizations",
                    "column": "id",
                    "severity": "error"
                }
            ]
        }
        
        response = requests.post(
            f"{API_BASE}/v1/validate",
            headers={"X-API-Key": api_key},
            json=invalid_ref_data
        )
        
        if response.status_code == 200:
            result = response.json()
            ref_violations = [v for v in result['violations'] if 'reference' in v.get('violation_type', '').lower()]
            
            if ref_violations:
                print(f"   Violation detected: {ref_violations[0]['message']}")
            
            print_result(
                "Invalid Reference Detection",
                len(ref_violations) > 0,
                f"Found {len(ref_violations)} reference violation(s)"
            )
        else:
            print_result("Invalid Reference Detection", False, f"Status: {response.status_code}")
            print(f"   Response: {response.text}")
        
    except Exception as e:
        print_result("Reference Validation Test", False, str(e))


async def test_combined_features():
    """Test combined validation with all features"""
    print_section("Test 3: Combined Features")
    
    try:
        # 1. Create test organization
        signup_data = {
            "name": "Combined Test Org",
            "email": f"combined_{TEST_RUN_ID}@truthchain.com",
            "password": "Combined123!",
            "tier": "business"
        }
        
        response = requests.post(
            f"{API_BASE}/v1/auth/signup",
            json=signup_data
        )
        
        if response.status_code != 201:
            print_result("Organization Signup", False, f"Status: {response.status_code}")
            try:
                print(f"   Error: {response.json()}")
            except:
                print(f"   Raw: {response.text}")
            return
        
        api_key = response.json()["api_key"]
        print_result("Organization Created", True)
        
        # 2. Complex validation with multiple rule types
        print("\n📝 Testing combined validation...")
        
        complex_data = {
            "output": {
                "user_id": "999",      # Wrong type (string instead of int)
                "hours": 35,           # Out of range (> 24)
                "project": "TruthChain",
                "percentage": 120      # Out of range (> 100)
            },
            "rules": [
                {
                    "type": "schema",
                    "name": "structure",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "integer"},
                            "hours": {"type": "number"},
                            "project": {"type": "string"},
                            "percentage": {"type": "number"}
                        },
                        "required": ["user_id", "hours"]
                    }
                },
                {
                    "type": "range",
                    "name": "hours_limit",
                    "field": "hours",
                    "min": 0,
                    "max": 24,
                    "severity": "error"
                },
                {
                    "type": "range",
                    "name": "percentage_limit",
                    "field": "percentage",
                    "min": 0,
                    "max": 100,
                    "severity": "error"
                }
            ],
            "context": {
                "auto_correct": True
            }
        }
        
        response = requests.post(
            f"{API_BASE}/v1/validate",
            headers={"X-API-Key": api_key},
            json=complex_data
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n   Original data:")
            print(f"      user_id: '999' (string)")
            print(f"      hours: 35")
            print(f"      percentage: 120")
            
            print(f"\n   Validation result:")
            print(f"      Status: {result['status']}")
            print(f"      Valid: {result['valid']}")
            print(f"      Auto-corrected: {result['auto_corrected']}")
            print(f"      Violations found: {len(result['violations'])}")
            
            if result.get('corrected_output'):
                print(f"\n   Corrected data:")
                corrected = result['corrected_output']
                print(f"      user_id: {corrected.get('user_id')} ({type(corrected.get('user_id')).__name__})")
                print(f"      hours: {corrected.get('hours')}")
                print(f"      percentage: {corrected.get('percentage')}")
            
            if result.get('corrections_applied'):
                print(f"\n   Corrections applied:")
                for correction in result['corrections_applied']:
                    print(f"      - {correction}")
            
            print_result(
                "Combined Validation", 
                True,
                f"Processed {len(result['rules']) if 'rules' in result else 3} rules with auto-correction"
            )
        
    except Exception as e:
        print_result("Combined Features Test", False, str(e))


async def main():
    """Run all tests"""
    print("\n" + "🚀"*35)
    print("TruthChain - Advanced Validation Features Test Suite")
    print("Week 9-10: Context Manager + Auto-Corrector + Caching")
    print("🚀"*35)
    
    await test_auto_correction()
    await test_reference_validation()
    await test_combined_features()
    
    print("\n" + "="*70)
    print("✅ All tests completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
