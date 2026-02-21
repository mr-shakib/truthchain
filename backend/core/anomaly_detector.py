"""
Anomaly Detector for TruthChain
Detects anomalies and unusual patterns in AI outputs using statistical methods
"""
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime
import math

from ..core.validation_engine import Violation, ViolationType
from ..core.statistical_analyzer import (
    StatisticalAnalyzer,
    StatisticalMetrics,
    OutlierDetectionResult
)


class AnomalyRule(BaseModel):
    """Configuration for anomaly detection rule"""
    type: str = "anomaly"
    name: str
    field: str
    method: str = "zscore"  # zscore, iqr, or both
    threshold: Optional[float] = None  # Custom threshold
    severity: str = "warning"  # warning or error
    use_historical: bool = True  # Use historical baseline
    history_days: int = 30


class AnomalyPattern(BaseModel):
    """Detected anomaly pattern"""
    pattern_type: str  # outlier, drift, unusual_value, etc.
    field: str
    description: str
    confidence: float  # 0.0 to 1.0
    severity: str
    metadata: Dict[str, Any]


class AnomalyDetector:
    """
    Detects anomalies in AI-generated outputs
    
    Detection methods:
    1. Statistical outliers (z-score, IQR)
    2. Historical drift detection
    3. Pattern-based anomalies
    4. Type-based anomalies (unexpected types)
    
    Use cases:
    - Detect when AI hallucinates unusual numbers
    - Flag outputs that deviate from historical norms
    - Identify sudden distribution changes
    - Catch data quality issues early
    """
    
    def __init__(self, statistical_analyzer: StatisticalAnalyzer):
        """
        Initialize anomaly detector
        
        Args:
            statistical_analyzer: StatisticalAnalyzer instance
        """
        self.analyzer = statistical_analyzer
        
        # Common AI hallucination patterns
        self.suspicious_patterns = {
            # Suspiciously round numbers
            "round_numbers": [100, 1000, 10000, 100000],
            # Common placeholder values
            "placeholder_values": [0, 1, -1, 999, 9999],
            # Suspicious percentages (> 100%)
            "invalid_percentages": lambda x: x > 100 or x < 0
        }
    
    async def detect_anomalies(
        self,
        output: Dict[str, Any],
        rules: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Violation]:
        """
        Detect anomalies based on rules
        
        Args:
            output: AI output to analyze
            rules: List of anomaly detection rules
            context: Optional context (organization_id, etc.)
        
        Returns:
            List of violations for detected anomalies
        """
        violations = []
        
        # Filter for anomaly rules
        anomaly_rules = [r for r in rules if r.get("type") == "anomaly"]
        
        for rule_dict in anomaly_rules:
            try:
                rule = AnomalyRule(**rule_dict)
                violation = await self._check_anomaly_rule(output, rule, context)
                if violation:
                    violations.append(violation)
            except Exception as e:
                print(f"Error processing anomaly rule: {e}")
                continue
        
        # Auto-detect common anomaly patterns
        if context and context.get("auto_detect_anomalies", False):
            pattern_violations = await self._detect_common_patterns(output, context)
            violations.extend(pattern_violations)
        
        return violations
    
    async def _check_anomaly_rule(
        self,
        output: Dict[str, Any],
        rule: AnomalyRule,
        context: Optional[Dict[str, Any]]
    ) -> Optional[Violation]:
        """
        Check a single anomaly detection rule
        
        Args:
            output: AI output data
            rule: Anomaly rule to check
            context: Optional context
        
        Returns:
            Violation if anomaly detected, None otherwise
        """
        # Extract field value
        value = self._get_field_value(output, rule.field)
        
        if value is None:
            return None
        
        # Convert to float for numeric analysis
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            return None
        
        # Method 1: Use historical baseline
        if rule.use_historical and context and context.get("organization_id"):
            hist_metrics = await self.analyzer.get_historical_statistics(
                organization_id=context["organization_id"],
                field=rule.field,
                days=rule.history_days
            )
            
            if hist_metrics:
                # Check against historical baseline
                if rule.method in ["zscore", "both"]:
                    result = self.analyzer.detect_outlier_zscore(
                        field=rule.field,
                        value=numeric_value,
                        mean=hist_metrics.mean,
                        std_dev=hist_metrics.std_dev,
                        threshold=rule.threshold
                    )
                    
                    if result.is_outlier:
                        return self._create_anomaly_violation(rule, result, value, hist_metrics)
                
                if rule.method in ["iqr", "both"]:
                    result = self.analyzer.detect_outlier_iqr(
                        field=rule.field,
                        value=numeric_value,
                        q1=hist_metrics.q1,
                        q3=hist_metrics.q3,
                        iqr=hist_metrics.iqr,
                        multiplier=rule.threshold
                    )
                    
                    if result.is_outlier:
                        return self._create_anomaly_violation(rule, result, value, hist_metrics)
        
        # Method 2: Without historical baseline (use provided thresholds from rule metadata)
        # This could be expanded to check against rule-defined bounds
        
        return None
    
    async def _detect_common_patterns(
        self,
        output: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Violation]:
        """
        Detect common AI hallucination patterns
        
        Args:
            output: AI output to analyze
            context: Validation context
        
        Returns:
            List of violations for detected patterns
        """
        violations = []
        
        # Flatten output to get all numeric fields
        numeric_fields = self._extract_numeric_fields(output)
        
        for field, value in numeric_fields.items():
            # Pattern 1: Suspiciously round numbers
            if self._is_suspicious_round_number(value):
                violations.append(Violation(
                    rule_name="auto_pattern_round_number",
                    violation_type=ViolationType.STATISTICAL,
                    field=field,
                    message=f"{field} has a suspiciously round value ({value}) - possible AI hallucination",
                    severity="warning",
                    found_value=value,
                    suggestion="Verify this value is accurate and not a placeholder"
                ))
            
            # Pattern 2: Placeholder values
            if value in self.suspicious_patterns["placeholder_values"]:
                violations.append(Violation(
                    rule_name="auto_pattern_placeholder",
                    violation_type=ViolationType.STATISTICAL,
                    field=field,
                    message=f"{field} contains a common placeholder value ({value})",
                    severity="warning",
                    found_value=value,
                    suggestion="Verify this is a real value and not a placeholder"
                ))
            
            # Pattern 3: Invalid percentages
            if "percent" in field.lower() or "rate" in field.lower():
                if value > 100 or value < 0:
                    violations.append(Violation(
                        rule_name="auto_pattern_invalid_percentage",
                        violation_type=ViolationType.STATISTICAL,
                        field=field,
                        message=f"{field} has an invalid percentage value ({value}%)",
                        severity="error",
                        found_value=value,
                        expected_value={"min": 0, "max": 100},
                        suggestion="Percentages should be between 0 and 100"
                    ))
        
        return violations
    
    def detect_distribution_shift(
        self,
        current_values: List[float],
        historical_values: List[float],
        threshold: float = 0.3
    ) -> Optional[AnomalyPattern]:
        """
        Detect if the distribution of values has shifted significantly
        
        Uses Kolmogorov-Smirnov-like comparison of distributions
        
        Args:
            current_values: Recent values
            historical_values: Historical baseline values
            threshold: Shift threshold (0.0 to 1.0)
        
        Returns:
            AnomalyPattern if shift detected, None otherwise
        """
        if len(current_values) < 5 or len(historical_values) < 10:
            return None
        
        # Calculate means
        current_mean = sum(current_values) / len(current_values)
        historical_mean = sum(historical_values) / len(historical_values)
        
        # Calculate relative shift
        if historical_mean == 0:
            shift = abs(current_mean)
        else:
            shift = abs(current_mean - historical_mean) / abs(historical_mean)
        
        if shift > threshold:
            confidence = min(shift / threshold, 1.0)
            
            return AnomalyPattern(
                pattern_type="distribution_shift",
                field="multiple",
                description=f"Distribution shifted by {shift*100:.1f}% from historical baseline",
                confidence=confidence,
                severity="error" if shift > threshold * 2 else "warning",
                metadata={
                    "current_mean": current_mean,
                    "historical_mean": historical_mean,
                    "shift_percentage": shift * 100,
                    "threshold_percentage": threshold * 100
                }
            )
        
        return None
    
    def _create_anomaly_violation(
        self,
        rule: AnomalyRule,
        result: OutlierDetectionResult,
        value: Any,
        metrics: StatisticalMetrics
    ) -> Violation:
        """
        Create a violation from an outlier detection result
        
        Args:
            rule: Anomaly detection rule
            result: Outlier detection result
            value: Original value
            metrics: Statistical metrics
        
        Returns:
            Violation object
        """
        # Build descriptive message
        if result.method == "zscore":
            message = (
                f"{rule.field} value ({value}) is {result.score:.2f} standard deviations "
                f"from the mean ({metrics.mean:.2f})"
            )
        else:  # iqr
            message = (
                f"{rule.field} value ({value}) is an outlier "
                f"(outside IQR range: {metrics.q1:.2f} - {metrics.q3:.2f})"
            )
        
        return Violation(
            rule_name=rule.name,
            violation_type=ViolationType.STATISTICAL,
            field=rule.field,
            message=message,
            severity=result.severity,
            found_value=value,
            expected_value={
                "mean": metrics.mean,
                "median": metrics.median,
                "std_dev": metrics.std_dev,
                "q1": metrics.q1,
                "q3": metrics.q3
            },
            suggestion=f"Expected range: {metrics.q1:.2f} to {metrics.q3:.2f} (IQR method)"
        )
    
    def _is_suspicious_round_number(self, value: float) -> bool:
        """Check if a number is suspiciously round (possible hallucination)"""
        # Check if it's exactly one of the suspicious round numbers
        if value in self.suspicious_patterns["round_numbers"]:
            return True
        
        # Check if it's a power of 10
        if value > 0 and value == 10 ** int(math.log10(value)):
            return True
        
        return False
    
    def _extract_numeric_fields(
        self,
        data: Dict[str, Any],
        prefix: str = ""
    ) -> Dict[str, float]:
        """
        Extract all numeric fields from nested dictionary
        
        Args:
            data: Dictionary to extract from
            prefix: Prefix for nested keys
        
        Returns:
            Dict mapping field paths to numeric values
        """
        numeric_fields = {}
        
        for key, value in data.items():
            field_path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_fields[field_path] = float(value)
            elif isinstance(value, dict):
                # Recurse into nested dicts
                nested = self._extract_numeric_fields(value, field_path)
                numeric_fields.update(nested)
        
        return numeric_fields
    
    def _get_field_value(self, data: Dict[str, Any], field: str) -> Any:
        """Extract field value from nested dictionary"""
        keys = field.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return None
            else:
                return None
        
        return value
