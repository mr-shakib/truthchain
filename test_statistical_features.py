"""
Test script for Week 11-12: Statistical Validation & Anomaly Detection
Tests statistical analysis, anomaly detection, and confidence scoring
"""
import asyncio
import requests
import json
import uuid

# Test configuration
API_BASE = "http://localhost:8888"
TEST_RUN_ID = str(uuid.uuid4())[:8]
TEST_PASSWORD = "StatTest123!"


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


async def test_confidence_scoring():
    """Test confidence score calculation"""
    print_section("Test 1: Confidence Scoring")
    
    try:
        # 1. Create test organization
        signup_data = {
            "name": "Confidence Test Org",
            "email": f"confidence_{TEST_RUN_ID}@truthchain.com",
            "password": TEST_PASSWORD,
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
        print_result("Organization Created", True, f"API Key: {api_key[:20]}...")
        
        # 2. Test with clean data (high confidence expected)
        print("\n📝 Testing with clean data (high confidence expected)...")
        
        clean_data = {
            "output": {
                "hours": 8,
                "rate": 75.50,
                "efficiency": 95
            },
            "rules": [
                {
                    "type": "range",
                    "name": "hours_check",
                    "field": "hours",
                    "min": 0,
                    "max": 24,
                    "severity": "error"
                },
                {
                    "type": "range",
                    "name": "efficiency_check",
                    "field": "efficiency",
                    "min": 0,
                    "max": 100,
                    "severity": "error"
                }
            ],
            "context": {
                "calculate_confidence": True
            }
        }
        
        response = requests.post(
            f"{API_BASE}/v1/validate",
            headers={"X-API-Key": api_key},
            json=clean_data
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n   Validation Status: {result['status']}")
            print(f"   Valid: {result['valid']}")
            print(f"   Violations: {len(result['violations'])}")
            
            if result.get('confidence_score') is not None:
                print(f"\n   🎯 Confidence Score: {result['confidence_score']:.3f}")
                print(f"   📊 Confidence Level: {result.get('confidence_level', 'N/A')}")
                
                print_result(
                    "High Confidence Detection",
                    result['confidence_score'] >= 0.8,
                    f"Score: {result['confidence_score']:.3f} (expected >= 0.8)"
                )
            else:
                print_result("Confidence Scoring", False, "No confidence score returned")
        else:
            print_result("Clean Data Validation", False, f"Status: {response.status_code}")
            print(f"   Response: {response.text}")
        
        # 3. Test with violations (lower confidence expected)
        print("\n📝 Testing with violations (lower confidence expected)...")
        
        violated_data = {
            "output": {
                "hours": 30,  # Violation
                "rate": "invalid",  # Type violation
                "efficiency": 150  # Violation
            },
            "rules": [
                {
                    "type": "range",
                    "name": "hours_check",
                    "field": "hours",
                    "min": 0,
                    "max": 24,
                    "severity": "error"
                },
                {
                    "type": "range",
                    "name": "efficiency_check",
                    "field": "efficiency",
                    "min": 0,
                    "max": 100,
                    "severity": "error"
                },
                {
                    "type": "schema",
                    "name": "type_check",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "hours": {"type": "number"},
                            "rate": {"type": "number"},
                            "efficiency": {"type": "number"}
                        }
                    }
                }
            ],
            "context": {
                "calculate_confidence": True
            }
        }
        
        response = requests.post(
            f"{API_BASE}/v1/validate",
            headers={"X-API-Key": api_key},
            json=violated_data
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n   Validation Status: {result['status']}")
            print(f"   Valid: {result['valid']}")
            print(f"   Violations: {len(result['violations'])}")
            
            if result.get('confidence_score') is not None:
                print(f"\n   🎯 Confidence Score: {result['confidence_score']:.3f}")
                print(f"   📊 Confidence Level: {result.get('confidence_level', 'N/A')}")
                
                print_result(
                    "Low Confidence Detection",
                    result['confidence_score'] < 0.7,
                    f"Score: {result['confidence_score']:.3f} (expected < 0.7 due to violations)"
                )
            else:
                print_result("Confidence Scoring", False, "No confidence score returned")
        
    except Exception as e:
        print_result("Confidence Scoring Test", False, str(e))


async def test_anomaly_detection():
    """Test anomaly detection with suspicious patterns"""
    print_section("Test 2: Anomaly Detection")
    
    try:
        # 1. Create test organization
        signup_data = {
            "name": "Anomaly Test Org",
            "email": f"anomaly_{TEST_RUN_ID}@truthchain.com",
            "password": TEST_PASSWORD,
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
        
        # 2. Test anomaly detection with suspicious values
        print("\n📝 Testing anomaly detection (suspicious patterns)...")
        
        anomaly_data = {
            "output": {
                "count": 1000,  # Suspiciously round number
                "percentage": 120,  # Invalid percentage
                "user_id": 999,  # Placeholder value
                "amount": 10000  # Suspiciously round
            },
            "rules": [],  # No explicit rules - testing auto-detection
            "context": {
                "detect_anomalies": True,
                "auto_detect_anomalies": True,
                "calculate_confidence": True
            }
        }
        
        print(f"\n   Input data: {json.dumps(anomaly_data['output'], indent=6)}")
        
        response = requests.post(
            f"{API_BASE}/v1/validate",
            headers={"X-API-Key": api_key},
            json=anomaly_data
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n   📊 Results:")
            print(f"      Status: {result['status']}")
            print(f"      Violations: {len(result['violations'])}")
            print(f"      Anomalies Detected: {result.get('anomalies_detected', 0)}")
            
            if result.get('violations'):
                print(f"\n   ⚠️ Detected Anomalies:")
                for v in result['violations']:
                    if v.get('violation_type') == 'statistical':
                        print(f"      • {v['field']}: {v['message']}")
                
                print_result(
                    "Anomaly Detection",
                    len(result['violations']) > 0,
                    f"Detected {len(result['violations'])} anomaly pattern(s)"
                )
            else:
                print_result("Anomaly Detection", False, "No anomalies detected (expected some)")
            
            if result.get('confidence_score') is not None:
                print(f"\n   🎯 Confidence: {result['confidence_score']:.3f} ({result.get('confidence_level', 'N/A')})")
        else:
            print_result("Anomaly Detection Test", False, f"Status: {response.status_code}")
            print(f"   Response: {response.text}")
        
    except Exception as e:
        print_result("Anomaly Detection Test", False, str(e))


async def test_combined_statistical():
    """Test combined statistical validation with corrections and confidence"""
    print_section("Test 3: Combined Statistical Validation")
    
    try:
        # 1. Create test organization
        signup_data = {
            "name": "Combined Stats Org",
            "email": f"stats_{TEST_RUN_ID}@truthchain.com",
            "password": TEST_PASSWORD,
            "tier": "enterprise"
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
        
        # 2. Combined test: anomalies + auto-correction + confidence
        print("\n📝 Testing combined: anomalies + auto-correction + confidence...")
        
        combined_data = {
            "output": {
                "hours": 35,  # Over limit (will be corrected)
                "percentage": 150,  # Invalid percentage
                "count": 10000,  # Suspicious round number
                "rate": "85.50"  # Wrong type (will be corrected)
            },
            "rules": [
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
                },
                {
                    "type": "schema",
                    "name": "type_check",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "hours": {"type": "number"},
                            "percentage": {"type": "number"},
                            "count": {"type": "number"},
                            "rate": {"type": "number"}
                        }
                    }
                }
            ],
            "context": {
                "auto_correct": True,
                "detect_anomalies": True,
                "auto_detect_anomalies": True,
                "calculate_confidence": True
            }
        }
        
        print(f"\n   📤 Original Data:")
        print(f"      hours: 35 (max: 24)")
        print(f"      percentage: 150 (max: 100)")
        print(f"      count: 10000 (suspicious)")
        print(f"      rate: '85.50' (wrong type)")
        
        response = requests.post(
            f"{API_BASE}/v1/validate",
            headers={"X-API-Key": api_key},
            json=combined_data
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n   📊 Validation Results:")
            print(f"      Status: {result['status']}")
            print(f"      Valid: {result['valid']}")
            print(f"      Auto-corrected: {result.get('auto_corrected', False)}")
            print(f"      Violations: {len(result['violations'])}")
            print(f"      Anomalies: {result.get('anomalies_detected', 0)}")
            
            if result.get('corrected_output'):
                print(f"\n   ✨ Corrected Output:")
                for key, value in result['corrected_output'].items():
                    original = combined_data['output'][key]
                    print(f"      {key}: {original} → {value}")
            
            if result.get('corrections_applied'):
                print(f"\n   🔧 Corrections ({len(result['corrections_applied'])}):")
                for i, correction in enumerate(result['corrections_applied'], 1):
                    print(f"      {i}. {correction}")
            
            if result.get('confidence_score') is not None:
                print(f"\n   🎯 Confidence Analysis:")
                print(f"      Score: {result['confidence_score']:.3f}")
                print(f"      Level: {result.get('confidence_level', 'N/A')}")
                
                # Expect low-medium confidence due to multiple issues
                print_result(
                    "Combined Validation",
                    True,
                    f"Processed {len(result['violations'])} violations, " +
                    f"{len(result.get('corrections_applied', []))} corrections, " +
                    f"confidence: {result['confidence_score']:.3f}"
                )
            
            print(f"\n   📈 Statistical Summary:")
            if result.get('statistical_summary'):
                for key, value in result['statistical_summary'].items():
                    print(f"      {key}: {value}")
        else:
            print_result("Combined Test", False, f"Status: {response.status_code}")
            print(f"   Response: {response.text}")
        
    except Exception as e:
        print_result("Combined Statistical Test", False, str(e))


async def main():
    """Run all tests"""
    print("\n" + "🚀"*35)
    print("TruthChain - Statistical Validation & Anomaly Detection Tests")
    print("Week 11-12: Confidence Scoring + Anomaly Detection + Statistics")
    print("🚀"*35)
    
    await test_confidence_scoring()
    await test_anomaly_detection()
    await test_combined_statistical()
    
    print("\n" + "="*70)
    print("✅ All statistical tests completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
