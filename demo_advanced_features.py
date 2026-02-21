"""
TruthChain Week 9-10 Demo Script
Demonstrates auto-correction and reference validation features
"""
import requests
import json

# Configuration
API_BASE = "http://localhost:8888"

def print_header(title):
    """Print formatted section header"""
    print("\n" + "="*70)
    print(f"🎯 {title}")
    print("="*70)


def print_json(data, indent=2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent))


def demo_auto_correction():
    """Demo: Auto-correction fixes invalid data automatically"""
    print_header("Demo 1: Auto-Correction")
    
    # Create test organization
    print("\n1️⃣ Creating test organization...")
    signup_data = {
        "name": "Demo Corporation",
        "email": "demo@truthchain.com",
        "password": "Demo123!",
        "tier": "business"
    }
    
    response = requests.post(f"{API_BASE}/v1/auth/signup", json=signup_data)
    
    if response.status_code != 201:
        print("⚠️ Organization may already exist. Use existing API key.")
        return None
    
    result = response.json()
    api_key = result["api_key"]
    print(f"✅ Organization created!")
    print(f"   API Key: {api_key[:30]}...")
    
    # Test auto-correction
    print("\n2️⃣ Sending invalid data (hours=30, max=24)...")
    
    validation_request = {
        "output": {
            "employee_id": "999",      # Wrong type (string instead of int)
            "hours_worked": 30,        # Over limit (max: 24)
            "overtime_rate": 150.5
        },
        "rules": [
            {
                "type": "range",
                "name": "hours_limit",
                "field": "hours_worked",
                "min": 0,
                "max": 24,
                "severity": "error"
            },
            {
                "type": "schema",
                "name": "data_types",
                "schema": {
                    "type": "object",
                    "properties": {
                        "employee_id": {"type": "integer"},
                        "hours_worked": {"type": "number"},
                        "overtime_rate": {"type": "number"}
                    }
                }
            }
        ],
        "context": {
            "auto_correct": True  # Enable auto-correction
        }
    }
    
    print("\n📤 Request:")
    print_json(validation_request["output"])
    
    response = requests.post(
        f"{API_BASE}/v1/validate",
        headers={"X-API-Key": api_key},
        json=validation_request
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print("\n📥 Response:")
        print(f"   Status: {result['status']}")
        print(f"   Valid: {result['valid']}")
        print(f"   Auto-corrected: {result['auto_corrected']}")
        
        if result.get('corrected_output'):
            print("\n✨ Corrected Output:")
            print_json(result['corrected_output'])
        
        if result.get('corrections_applied'):
            print("\n🔧 Corrections Applied:")
            for correction in result['corrections_applied']:
                print(f"   • {correction}")
        
        print("\n⚠️ Violations Found:")
        for v in result['violations']:
            print(f"   • {v['field']}: {v['message']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
    
    return api_key


def demo_reference_validation(api_key=None):
    """Demo: Reference validation checks database"""
    print_header("Demo 2: Reference Validation")
    
    if not api_key:
        print("⚠️ Need API key from Demo 1")
        return
    
    print("\n1️⃣ Testing VALID organization reference...")
    
    # Get current organization ID
    response = requests.get(
        f"{API_BASE}/v1/analytics/overview",
        headers={"X-API-Key": api_key}
    )
    
    if response.status_code != 200:
        print("❌ Could not fetch organization info")
        return
    
    # For this demo, we'll use a fake org_id to show invalid reference
    print("\n2️⃣ Testing INVALID organization reference...")
    
    validation_request = {
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
    
    print("\n📤 Request:")
    print_json(validation_request["output"])
    
    response = requests.post(
        f"{API_BASE}/v1/validate",
        headers={"X-API-Key": api_key},
        json=validation_request
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print("\n📥 Response:")
        print(f"   Status: {result['status']}")
        print(f"   Valid: {result['valid']}")
        
        if result['violations']:
            print("\n❌ Reference Violation:")
            for v in result['violations']:
                print(f"   Field: {v['field']}")
                print(f"   Message: {v['message']}")
                print(f"   Type: {v['violation_type']}")
                if v.get('suggestion'):
                    print(f"   💡 Suggestion: {v['suggestion']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)


def demo_combined_features(api_key=None):
    """Demo: Multiple validations with auto-correction"""
    print_header("Demo 3: Combined Validation")
    
    if not api_key:
        print("⚠️ Need API key from Demo 1")
        return
    
    print("\n1️⃣ Validating complex data with multiple issues...")
    
    validation_request = {
        "output": {
            "user_id": "12345",        # Wrong type
            "hours": 40,               # Over limit (max: 24)
            "rate": "85.50",           # Wrong type
            "percentage": 150,         # Over limit (max: 100)
            "status": "  active  "     # Needs trimming
        },
        "rules": [
            {
                "type": "schema",
                "name": "type_check",
                "schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer"},
                        "hours": {"type": "number"},
                        "rate": {"type": "number"},
                        "percentage": {"type": "number"},
                        "status": {"type": "string"}
                    }
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
    
    print("\n📤 Original Data (with 5+ issues):")
    print_json(validation_request["output"])
    
    response = requests.post(
        f"{API_BASE}/v1/validate",
        headers={"X-API-Key": api_key},
        json=validation_request
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print("\n📥 Validation Result:")
        print(f"   Status: {result['status']}")
        print(f"   Valid: {result['valid']}")
        print(f"   Auto-corrected: {result['auto_corrected']}")
        print(f"   Violations: {len(result['violations'])}")
        print(f"   Latency: {result['latency_ms']}ms")
        
        if result.get('corrected_output'):
            print("\n✨ Corrected Output:")
            print_json(result['corrected_output'])
        
        if result.get('corrections_applied'):
            print(f"\n🔧 Corrections Applied ({len(result['corrections_applied'])}):")
            for i, correction in enumerate(result['corrections_applied'], 1):
                print(f"   {i}. {correction}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)


def main():
    """Run all demos"""
    print("\n" + "🚀"*35)
    print("TruthChain - Week 9-10 Feature Demonstration")
    print("Advanced Validation: Auto-Correction + Reference Validation")
    print("🚀"*35)
    
    # Demo 1: Auto-correction
    api_key = demo_auto_correction()
    
    if api_key:
        # Demo 2: Reference validation
        demo_reference_validation(api_key)
        
        # Demo 3: Combined features
        demo_combined_features(api_key)
    
    print("\n" + "="*70)
    print("✅ Demo completed! Check results above.")
    print("="*70 + "\n")
    
    print("📚 Learn More:")
    print("   • See WEEK_9-10_SUMMARY.md for detailed documentation")
    print("   • Run test_advanced_features.py for comprehensive tests")
    print("   • Check SESSION_SUMMARY.md for API reference\n")


if __name__ == "__main__":
    main()
