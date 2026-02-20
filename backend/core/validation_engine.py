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
    corrected_output: Optional[Dict[str, Any]]
    validation_id: str
    latency_ms: int
    timestamp: str


def generate_validation_id() -> str:
    """Generate unique validation ID"""
    return f"val_{uuid.uuid4().hex[:16]}"


class ValidationEngine:
    def __init__(self):
        # Import here to avoid circular imports
        from .schema_validator import SchemaValidator
        from .rule_engine import RuleEngine
        
        self.schema_validator = SchemaValidator()
        self.rule_engine = RuleEngine()
        self.context_manager = None  # To be implemented in future
        self.auto_corrector = None    # To be implemented in future
    
    async def validate(
        self,
        output: Dict[str, Any],
        rules: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Main validation orchestration"""
        start_time = time.time()
        violations = []
        
        # Step 1: Schema validation
        schema_violations = await self.schema_validator.validate(output, rules)
        violations.extend(schema_violations)
        
        # Step 2: Business rules validation
        rule_violations = await self.rule_engine.validate(output, rules, context)
        violations.extend(rule_violations)
        
        # Step 3: Reference validation (if context provided)
        # TODO: Implement context manager for database reference validation
        # if context and self.context_manager:
        #     ref_violations = await self.context_manager.validate_references(
        #         output, rules, context
        #     )
        #     violations.extend(ref_violations)
        
        # Step 4: Auto-correction attempt
        corrected_output = None
        auto_corrected = False
        # TODO: Implement auto-corrector
        # if violations and context and context.get('auto_correct'):
        #     corrected_output = await self.auto_corrector.fix(output, violations)
        #     auto_corrected = corrected_output is not None
        
        # Calculate result
        latency_ms = int((time.time() - start_time) * 1000)
        validation_id = generate_validation_id()
        
        # Determine status
        error_count = len([v for v in violations if v.severity == 'error'])
        if error_count == 0:
            status = ValidationStatus.PASSED
        elif len([v for v in violations if v.severity == 'warning']) > 0 and error_count == 0:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAILED
        
        return ValidationResult(
            status=status,
            valid=error_count == 0,
            violations=violations,
            auto_corrected=auto_corrected,
            corrected_output=corrected_output,
            validation_id=validation_id,
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat()
        )
