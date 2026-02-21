"""
Demo script for TruthChain Week 11-12 Statistical Validation Features

This script demonstrates the API usage for:
1. Confidence scoring for clean vs problematic data
2. Anomaly detection with pattern matching
3. Combined validation with auto-correction and confidence
4. API examples with expected responses

Usage:
    1. Start the API server: uvicorn backend.api.main:app --reload
    2. Run this demo: python demo_statistical_features.py
"""

import requests
import json
from typing import Dict, Any


API_BASE = "http://localhost:8888"


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_json(data: Dict[str, Any], indent: int = 2):
    """Print JSON data with formatting."""
    print(json.dumps(data, indent=indent))


def print_result(label: str, value):
    """Print a formatted result."""
    print(f"  ✓ {label}: {value}")


def demo_1_confidence_scoring():
    """Demo 1: Confidence Scoring for Clean vs Problematic Data"""
    print_header("DEMO 1: Confidence Scoring")
    
    print("📊 Example Request for Clean Data:")
    clean_request = {
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
            }
        ],
        "context": {
            "calculate_confidence": True
        }
    }
    
    print_json(clean_request)
    
    print("\n📝 Expected Response:")
    clean_response = {
        "status": "passed",
        "valid": True,
        "violations": [],
        "confidence_score": 1.000,
        "confidence_level": "very_high",
        "anomalies_detected": 0
    }
    print_json(clean_response)
    
    print("\n" + "-" * 80)
    print("\n📊 Example Request for Data with Violations:")
    violated_request = {
        "output": {
            "hours": 35,
            "rate": "invalid",
            "efficiency": 150
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
        ],
        "context": {
            "calculate_confidence": True
        }
    }
    
    print_json(violated_request)
    
    print("\n📝 Expected Response:")
    violated_response = {
        "status": "failed",
        "valid": False,
        "violations": [
            {
                "rule_name": "hours_check",
                "violation_type": "constraint",
                "field": "hours",
                "message": "hours must be between 0 and 24",
                "severity": "error",
                "found_value": 35,
                "expected_value": {"min": 0, "max": 24}
            }
        ],
        "confidence_score": 0.560,
        "confidence_level": "medium",
        "anomalies_detected": 0
    }
    print_json(violated_response)


def demo_2_anomaly_detection():
    """Demo 2: Anomaly Detection with Pattern Matching"""
    print_header("DEMO 2: Anomaly Detection")
    
    print("🔍 Example Request with Auto-Detection Enabled:")
    request = {
        "output": {
            "count": 1000,        # Suspiciously round number
            "percentage": 120,    # Invalid percentage
            "user_id": 999,       # Placeholder value
            "amount": 10000       # Suspiciously round number
        },
        "rules": [],
        "context": {
            "detect_anomalies": True,
            "auto_detect_anomalies": True,
            "calculate_confidence": True
        }
    }
    
    print_json(request)
    
    print("\n📝 Expected Response:")
    response = {
        "status": "failed",
        "valid": False,
        "violations": [
            {
                "rule_name": "auto_pattern_round_number",
                "violation_type": "statistical",
                "field": "count",
                "message": "count has a suspiciously round value (1000.0) - possible AI hallucination",
                "severity": "warning"
            },
            {
                "rule_name": "auto_pattern_invalid_percentage",
                "violation_type": "statistical",
                "field": "percentage",
                "message": "percentage has an invalid percentage value (120.0%)",
                "severity": "error"
            },
            {
                "rule_name": "auto_pattern_placeholder",
                "violation_type": "statistical",
                "field": "user_id",
                "message": "user_id contains a common placeholder value (999.0)",
                "severity": "warning"
            },
            {
                "rule_name": "auto_pattern_round_number",
                "violation_type": "statistical",
                "field": "amount",
                "message": "amount has a suspiciously round value (10000.0) - possible AI hallucination",
                "severity": "warning"
            }
        ],
        "anomalies_detected": 4,
        "confidence_score": 0.623,
        "confidence_level": "medium"
    }
    print_json(response)
    
    print("\n💡 Patterns Detected:")
    print("  • Suspiciously round numbers: 1000, 10000")
    print("  • Invalid percentage: 120%")
    print("  • Placeholder value: 999")


def demo_3_combined_features():
    """Demo 3: Combined Validation with Auto-Correction and Confidence"""
    print_header("DEMO 3: Combined Features")
    
    print("🔧 Example Request with All Features Enabled:")
    request = {
        "output": {
            "hours": 35,
            "percentage": 150,
            "rate": "85.50",
            "count": 10000
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
            }
        ],
        "context": {
            "auto_correct": True,
            "detect_anomalies": True,
            "auto_detect_anomalies": True,
            "calculate_confidence": True
        }
    }
    
    print_json(request)
    
    print("\n📝 Expected Response:")
    response = {
        "status": "failed",
        "valid": False,
        "violations": [
            {
                "rule_name": "hours_limit",
                "violation_type": "constraint",
                "message": "hours must be between 0 and 24",
                "severity": "error"
            },
            {
                "rule_name": "percentage_limit",
                "violation_type": "constraint",  
                "message": "percentage must be between 0 and 100",
                "severity": "error"
            },
            {
                "rule_name": "auto_pattern_round_number",
                "violation_type": "statistical",
                "message": "count has a suspiciously round value (10000.0)",
                "severity": "warning"
            }
        ],
        "auto_corrected": True,
        "corrected_output": {
            "hours": 24.0,
            "percentage": 100.0,
            "rate": 85.5,
            "count": 10000
        },
        "corrections_applied": [
            "Clamped hours from 35 to 24.0 (range: 0.0-24.0)",
            "Clamped percentage from 150 to 100.0 (range: 0.0-100.0)",
            "Coerced rate from str to float: 85.5"
        ],
        "anomalies_detected": 1,
        "confidence_score": 0.487,
        "confidence_level": "low"
    }
    print_json(response)
    
    print("\n💡 What Happened:")
    print("  ✓ 5 violations detected (2 range errors, 3 anomalies)")
    print("  ✓ 3 auto-corrections applied (hours, percentage, rate type)")
    print("  ✓ 1 anomaly detected (round number: 10000)")
    print("  ✓ Low confidence (0.487) due to multiple issues")


def demo_4_confidence_levels():
    """Demo 4: Understanding Confidence Levels"""
    print_header("DEMO 4: Confidence Levels Explained")
    
    print("📊 Confidence Score Ranges and Meanings:\n")
    
    levels = [
        {
            "score": "≥ 0.90",
            "level": "very_high",
            "icon": "✅",
            "meaning": "Safe to use without review",
            "example": "Clean data, no violations, all validations pass"
        },
        {
            "score": "≥ 0.75",
            "level": "high",
            "icon": "✓",
            "meaning": "Minor review recommended",
            "example": "1-2 warnings, no critical errors"
        },
        {
            "score": "≥ 0.50",
            "level": "medium",
            "icon": "⚠️",
            "meaning": "Review recommended",
            "example": "Multiple warnings or 1 error with auto-correction"
        },
        {
            "score": "≥ 0.25",
            "level": "low",
            "icon": "❌",
            "meaning": "Manual review required",
            "example": "Multiple errors, anomalies detected"
        },
        {
            "score": "< 0.25",
            "level": "very_low",
            "icon": "🚫",
            "meaning": "Do not use - unreliable data",
            "example": "Severe violations, failed validations"
        }
    ]
    
    for level in levels:
        print(f"{level['icon']} {level['level'].upper()} ({level['score']})")
        print(f"  • {level['meaning']}")
        print(f"  • Example: {level['example']}\n")
    
    print("\n🔬 Scoring Factors (weights):")
    print("  • Violation Count:   30%  (fewer violations = higher score)")
    print("  • Severity:          25%  (error=1.0, warning=0.5, info=0.1)")
    print("  • Auto-Correction:   15%  (penalty for corrections needed)")
    print("  • Statistical:       20%  (based on outlier detection)")
    print("  • Reference Check:   10%  (based on database validation)")


def demo_5_api_usage():
    """Demo 5: How to Use the API"""
    print_header("DEMO 5: API Usage Guide")
    
    print("🚀 Quick Start:\n")
    
    print("1️⃣ Using curl:")
    print("""
    curl -X POST http://localhost:8888/v1/validate \\
      -H "X-API-Key: your-api-key" \\
      -H "Content-Type: application/json" \\
      -d '{
        "output": {"field": "value"},
        "rules": [],
        "context": {
          "detect_anomalies": true,
          "auto_detect_anomalies": true,
          "calculate_confidence": true
        }
      }'
    """)
    
    print("\n2️⃣ Using Python requests:")
    print("""
    import requests

    response = requests.post(
        'http://localhost:8888/v1/validate',
        headers={'X-API-Key': 'your-api-key'},
        json={
            'output': {'field': 'value'},
            'rules': [],
            'context': {
                'detect_anomalies': True,
                'auto_detect_anomalies': True,
                'calculate_confidence': True
            }
        }
    )
    
    result = response.json()
    print(f"Confidence: {result['confidence_score']}")
    print(f"Anomalies: {result['anomalies_detected']}")
    """)
    
    print("\n3️⃣ Context Options:")
    context_options = {
        "auto_correct": "Enable automatic violation correction",
        "detect_anomalies": "Enable anomaly detection",
        "auto_detect_anomalies": "Auto-detect common hallucination patterns",
        "calculate_confidence": "Calculate confidence score",
        "use_cache": "Enable Redis caching for lookups"
    }
    
    for option, description in context_options.items():
        print(f"  • {option}: {description}")


def main():
    """Run all demos."""
    print("""
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                                                                            ║
    ║            TruthChain - Statistical Validation Features Demo              ║
    ║                         Week 11-12 Implementation                          ║
    ║                                                                            ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        demo_1_confidence_scoring()
        demo_2_anomaly_detection()
        demo_3_combined_features()
        demo_4_confidence_levels()
        demo_5_api_usage()
        
        print_header("✅ DEMO COMPLETED SUCCESSFULLY")
        
        print("\n💡 Next Steps:")
        print("  1. Review WEEK_11-12_SUMMARY.md for detailed documentation")
        print("  2. Run test_statistical_features.py for comprehensive tests")
        print("  3. Start the API server and try these examples")
        print("  4. Explore advanced features in production use cases")
        print()
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
