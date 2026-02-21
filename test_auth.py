"""
Test script for TruthChain Authentication
Demonstrates signup, API key management, and authenticated validation
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def pretty_print(label, data):
    """Pretty print JSON responses"""
    print(f"\n{'='*60}")
    print(f"{label}")
    print('='*60)
    print(json.dumps(data, indent=2))
    print('='*60)


def test_signup():
    """Test organization signup"""
    print("\n🔐 Testing Organization Signup...")
    
    response = requests.post(
        f"{BASE_URL}/v1/auth/signup",
        json={
            "name": "Test Organization",
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "tier": "startup"
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    
    if response.status_code == 201:
        data = response.json()
        pretty_print("✅ Signup Successful", data)
        return data['api_key']
    else:
        try:
            pretty_print("❌ Signup Failed", response.json())
        except:
            print(f"❌ Signup Failed - Non-JSON response: {response.text}")
        return None


def test_create_api_key(api_key):
    """Test creating additional API key"""
    print("\n🔑 Testing API Key Creation...")
    
    response = requests.post(
        f"{BASE_URL}/v1/auth/api-keys",
        params={"name": "Production API Key"},
        headers={"X-API-Key": api_key}
    )
    
    if response.status_code == 201:
        data = response.json()
        pretty_print("✅ API Key Created", data)
        return data['key']
    else:
        pretty_print("❌ API Key Creation Failed", response.json())
        return None


def test_list_api_keys(api_key):
    """Test listing all API keys"""
    print("\n📋 Testing List API Keys...")
    
    response = requests.get(
        f"{BASE_URL}/v1/auth/api-keys",
        headers={"X-API-Key": api_key}
    )
    
    if response.status_code == 200:
        data = response.json()
        pretty_print("✅ API Keys Retrieved", data)
    else:
        pretty_print("❌ List API Keys Failed", response.json())


def test_validation_with_auth(api_key):
    """Test validation endpoint with authentication"""
    print("\n✅ Testing Authenticated Validation...")
    
    payload = {
        "output": {
            "user_id": 12345,
            "hours": 8,
            "project_name": "TruthChain"
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
        ],
        "context": {
            "auto_correct": True
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/validate",
        json=payload,
        headers={"X-API-Key": api_key}
    )
    
    if response.status_code == 200:
        data = response.json()
        pretty_print("✅ Validation Successful", data)
    else:
        pretty_print("❌ Validation Failed", response.json())


def test_invalid_api_key():
    """Test with invalid API key"""
    print("\n🚫 Testing Invalid API Key...")
    
    response = requests.get(
        f"{BASE_URL}/v1/auth/api-keys",
        headers={"X-API-Key": "tc_live_invalid_key_12345"}
    )
    
    if response.status_code == 401:
        pretty_print("✅ Invalid Key Rejected (Expected)", response.json())
    else:
        pretty_print("❌ Expected 401 Unauthorized", response.json())


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 TruthChain Authentication & Validation Tests")
    print("="*60)
    
    # Test 1: Signup
    api_key = test_signup()
    if not api_key:
        print("\n❌ Signup failed, stopping tests")
        return
    
    # Test 2: Create additional API key
    new_api_key = test_create_api_key(api_key)
    
    # Test 3: List API keys
    test_list_api_keys(api_key)
    
    # Test 4: Authenticated validation
    test_validation_with_auth(api_key)
    
    # Test 5: Invalid API key
    test_invalid_api_key()
    
    print("\n" + "="*60)
    print("✅ All Tests Complete!")
    print("="*60)
    print(f"\n💡 Your API Key: {api_key}")
    print(f"📚 API Documentation: {BASE_URL}/docs")
    print("\n")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to TruthChain API")
        print("   Make sure the server is running at http://localhost:8000")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
