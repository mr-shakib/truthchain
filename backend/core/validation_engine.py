from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import time
from datetime import datetime
import uuid


class ValidationStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class ViolationType(Enum):
    SCHEMA = "schema"
    CONSTRAINT = "constraint"
    REFERENCE = "reference"
    STATISTICAL = "statistical"
    SEMANTIC = "semantic"


class Violation(BaseModel):
    rule_name: str
    violation_type: ViolationType
    field: str
    message: str
    severity: str  # error, warning
    found_value: Any
    expected_value: Optional[Any] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    status: ValidationStatus
    is_valid: bool
    violations: List[Violation]
    auto_corrected: bool
    corrected_output: Optional[Dict[str, Any]] = None
    corrections_applied: Optional[List[str]] = None
    validation_id: str
    latency_ms: int
    timestamp: str
    # New fields for Week 11-12
    confidence_score: Optional[float] = None  # 0.0-1.0
    confidence_level: Optional[str] = None  # very_high, high, medium, low, very_low
    statistical_summary: Optional[Dict[str, Any]] = None  # Statistical metrics
    anomalies_detected: Optional[int] = None  # Count of anomalies


def generate_validation_id() -> str:
    """Generate unique validation ID"""
    return f"val_{uuid.uuid4().hex[:16]}"


class ValidationEngine:
    def __init__(self, db_session=None, cache=None):
        """
        Initialize ValidationEngine with optional database and cache
        
        Args:
            db_session: SQLAlchemy async session for reference validation
            cache: CacheLayer instance for performance optimization
        """
        # Import here to avoid circular imports
        from .schema_validator import SchemaValidator
        from .rule_engine import RuleEngine
        from .context_manager import ContextManager
        from .auto_corrector import AutoCorrector
        from .statistical_analyzer import StatisticalAnalyzer
        from .anomaly_detector import AnomalyDetector
        from .confidence_scorer import ConfidenceScorer
        
        self.schema_validator = SchemaValidator()
        self.rule_engine = RuleEngine()
        
        # Advanced features (Week 9-10)
        self.context_manager = ContextManager(db_session) if db_session else None
        self.auto_corrector = AutoCorrector()
        self.cache = cache
        
        # Statistical features (Week 11-12)
        self.statistical_analyzer = StatisticalAnalyzer(db_session) if db_session else None
        self.anomaly_detector = AnomalyDetector(self.statistical_analyzer) if self.statistical_analyzer else None
        self.confidence_scorer = ConfidenceScorer()
    
    async def validate(
        self,
        output: Dict[str, Any],
        rules: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Main validation orchestration with advanced features
        
        Validation pipeline:
        1. Schema validation (structure, types)
        2. Business rules validation (ranges, patterns, constraints)
        3. Reference validation (database lookups) - if enabled
        4. Statistical validation & anomaly detection - if enabled
        5. Auto-correction attempt - if enabled
        6. Confidence scoring
        
        Args:
            output: AI-generated output to validate
            rules: List of validation rules to apply
            context: Optional context (auto_correct, organization_id, etc.)
        
        Returns:
            ValidationResult with status, violations, confidence score, and optional corrections
        """
        start_time = time.time()
        violations = []
        statistical_summary = None
        anomalies_detected = 0
        
        # Step 1: Schema validation
        schema_violations = await self.schema_validator.validate(output, rules)
        violations.extend(schema_violations)
        
        # Step 2: Business rules validation
        rule_violations = await self.rule_engine.validate(output, rules, context)
        violations.extend(rule_violations)
        
        # Step 3: Reference validation (if context manager available)
        reference_violation_count = 0
        if self.context_manager:
            try:
                ref_violations = await self.context_manager.validate_references(
                    output, rules, context
                )
                violations.extend(ref_violations)
                reference_violation_count = len(ref_violations)
            except Exception as e:
                print(f"Reference validation error: {e}")
                # Continue without reference validation
        
        # Step 4: Statistical validation & anomaly detection (NEW - Week 11-12)
        if self.anomaly_detector and context and context.get('detect_anomalies', False):
            try:
                anomaly_violations = await self.anomaly_detector.detect_anomalies(
                    output, rules, context
                )
                violations.extend(anomaly_violations)
                anomalies_detected = len(anomaly_violations)
                
                # Build statistical summary
                statistical_summary = {
                    "anomalies_detected": anomalies_detected,
                    "detection_methods": ["zscore", "iqr", "pattern_matching"]
                }
            except Exception as e:
                print(f"Anomaly detection error: {e}")
                # Continue without anomaly detection
        
        # Step 5: Auto-correction attempt (if enabled and violations exist)
        corrected_output = None
        corrections_applied = []
        auto_corrected = False
        
        if violations and context and context.get('auto_correct', False):
            try:
                corrected_output, corrections_applied = await self.auto_corrector.fix(
                    output, violations, context
                )
                auto_corrected = corrected_output is not None
            except Exception as e:
                print(f"Auto-correction error: {e}")
                # Continue without auto-correction
        
        # Calculate result
        latency_ms = int((time.time() - start_time) * 1000)
        validation_id = generate_validation_id()
        
        # Determine status
        error_count = len([v for v in violations if v.severity == 'error'])
        warning_count = len([v for v in violations if v.severity == 'warning'])
        
        if error_count == 0 and warning_count == 0:
            status = ValidationStatus.PASSED
        elif error_count == 0 and warning_count > 0:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAILED
        
        # Step 6: Calculate confidence score (NEW - Week 11-12)
        confidence_score = None
        confidence_level = None
        
        if self.confidence_scorer and context and context.get('calculate_confidence', True):
            # Build temporary result for scoring
            temp_result = ValidationResult(
                status=status,
                is_valid=error_count == 0,
                violations=violations,
                auto_corrected=auto_corrected,
                corrected_output=corrected_output,
                corrections_applied=corrections_applied,
                validation_id=validation_id,
                latency_ms=latency_ms,
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Calculate confidence factors
            confidence_factors = self.confidence_scorer.calculate_confidence(
                result=temp_result,
                statistical_score=None,  # TODO: Calculate from statistical analysis
                has_reference_violations=(reference_violation_count > 0)
            )
            
            confidence_score = confidence_factors.overall_confidence
            confidence_level = self.confidence_scorer.get_confidence_level(confidence_score)
        
        return ValidationResult(
            status=status,
            is_valid=error_count == 0,
            violations=violations,
            auto_corrected=auto_corrected,
            corrected_output=corrected_output,
            corrections_applied=corrections_applied if corrections_applied else None,
            validation_id=validation_id,
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat(),
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            statistical_summary=statistical_summary,
            anomalies_detected=anomalies_detected if anomalies_detected > 0 else None
        )
