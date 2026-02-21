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
    valid: bool
    violations: List[Violation]
    auto_corrected: bool
    corrected_output: Optional[Dict[str, Any]] = None
    corrections_applied: Optional[List[str]] = None
    validation_id: str
    latency_ms: int
    timestamp: str


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
        
        self.schema_validator = SchemaValidator()
        self.rule_engine = RuleEngine()
        
        # Advanced features (Week 9-10)
        self.context_manager = ContextManager(db_session) if db_session else None
        self.auto_corrector = AutoCorrector()
        self.cache = cache
    
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
        4. Auto-correction attempt - if enabled
        
        Args:
            output: AI-generated output to validate
            rules: List of validation rules to apply
            context: Optional context (auto_correct, organization_id, etc.)
        
        Returns:
            ValidationResult with status, violations, and optional corrections
        """
        start_time = time.time()
        violations = []
        
        # Step 1: Schema validation
        schema_violations = await self.schema_validator.validate(output, rules)
        violations.extend(schema_violations)
        
        # Step 2: Business rules validation
        rule_violations = await self.rule_engine.validate(output, rules, context)
        violations.extend(rule_violations)
        
        # Step 3: Reference validation (if context manager available)
        if self.context_manager:
            try:
                ref_violations = await self.context_manager.validate_references(
                    output, rules, context
                )
                violations.extend(ref_violations)
            except Exception as e:
                print(f"Reference validation error: {e}")
                # Continue without reference validation
        
        # Step 4: Auto-correction attempt (if enabled and violations exist)
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
        
        return ValidationResult(
            status=status,
            valid=error_count == 0,
            violations=violations,
            auto_corrected=auto_corrected,
            corrected_output=corrected_output,
            corrections_applied=corrections_applied if corrections_applied else None,
            validation_id=validation_id,
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat()
        )
