"""
Rule Engine - Validates data against business rules and constraints
"""
from typing import Dict, List, Any, Optional
import re
from .validation_engine import Violation, ViolationType
from .semantic_validator import SemanticValidator
from .web_verifier import WebVerifier
from .ml_anomaly_detector import get_ml_anomaly_detector
from .external_reference import ExternalReferenceValidator, ConnectorResult

_web_verifier: WebVerifier | None = None


def _get_web_verifier() -> WebVerifier | None:
    """Lazy-initialise WebVerifier using TAVILY_API_KEY from settings."""
    global _web_verifier
    if _web_verifier is None:
        try:
            from ..config.settings import settings
            api_key = settings.TAVILY_API_KEY
            if api_key:
                _web_verifier = WebVerifier(api_key=api_key)
        except Exception:
            pass  # No API key configured — web_verify rules will return warning
    return _web_verifier


class RuleEngine:
    """Validates output against business rules (ranges, constraints, patterns, semantic alignment)"""

    def __init__(self):
        # SemanticValidator is a singleton — model loads lazily on first use
        self._semantic_validator = SemanticValidator()
    
    async def validate(
        self,
        output: Dict[str, Any],
        rules: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Violation]:
        """
        Validate output against business rules
        
        Args:
            output: The data to validate
            rules: List of validation rules
            context: Optional context for validation
        
        Returns:
            List of violations found
        """
        violations = []
        
        for rule in rules:
            rule_type = rule.get('type')
            
            if rule_type == 'range':
                range_violations = self._validate_range(output, rule)
                violations.extend(range_violations)
            
            elif rule_type == 'constraint':
                constraint_violations = self._validate_constraint(output, rule)
                violations.extend(constraint_violations)
            
            elif rule_type == 'pattern':
                pattern_violations = self._validate_pattern(output, rule)
                violations.extend(pattern_violations)

            elif rule_type == 'semantic':
                semantic_violations = self._validate_semantic(output, rule, context)
                violations.extend(semantic_violations)

            elif rule_type == 'web_verify':
                web_violations = await self._validate_web_verify(output, rule)
                violations.extend(web_violations)

            elif rule_type == 'anomaly_ml':
                ml_violations = self._validate_anomaly_ml(output, rule, context)
                violations.extend(ml_violations)

            elif rule_type == 'enum':
                enum_violations = self._validate_enum(output, rule)
                violations.extend(enum_violations)

            elif rule_type == 'required':
                required_violations = self._validate_required(output, rule)
                violations.extend(required_violations)

            elif rule_type == 'external_ref':
                ext_violations = await self._validate_external_ref(output, rule)
                violations.extend(ext_violations)

        return violations
    
    def _validate_range(
        self,
        output: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> List[Violation]:
        """
        Validate numeric ranges
        
        Args:
            output: Data to validate
            rule: Range rule with min/max values
        
        Returns:
            List of violations
        """
        violations = []
        field = rule.get('field')
        min_val = rule.get('min')
        max_val = rule.get('max')
        
        value = self._get_nested_value(output, field)
        
        # Skip if field not found
        if value is None:
            return violations
        
        # Check if value is out of range
        is_invalid = False
        try:
            num_value = float(value)
            if min_val is not None and num_value < float(min_val):
                is_invalid = True
            if max_val is not None and num_value > float(max_val):
                is_invalid = True
        except (ValueError, TypeError):
            violations.append(Violation(
                rule_name=rule.get('name', f'{field}_range_check'),
                violation_type=ViolationType.CONSTRAINT,
                field=field,
                message=f"{field} must be a number",
                severity='error',
                found_value=value,
                expected_value="numeric value"
            ))
            return violations
        
        # If out of range, create violation with min/max info for auto-correction
        if is_invalid:
            # Build message
            if min_val is not None and max_val is not None:
                message = f"{field} must be between {min_val} and {max_val}"
                expected = {"min": min_val, "max": max_val}
            elif min_val is not None:
                message = f"{field} must be >= {min_val}"
                expected = {"min": min_val}
            elif max_val is not None:
                message = f"{field} must be <= {max_val}"
                expected = {"max": max_val}
            else:
                return violations
            
            violations.append(Violation(
                rule_name=rule.get('name', f'{field}_range_check'),
                violation_type=ViolationType.CONSTRAINT,
                field=field,
                message=message,
                severity=rule.get('severity', 'error'),
                found_value=value,
                expected_value=expected
            ))
        
        return violations
    
    def _validate_constraint(
        self,
        output: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> List[Violation]:
        """
        Validate custom constraints using expressions
        
        Args:
            output: Data to validate
            rule: Constraint rule with expression
        
        Returns:
            List of violations
        """
        violations = []
        field = rule.get('field')
        expression = rule.get('expression')  # e.g., "value > 0 and value < 100"
        
        value = self._get_nested_value(output, field)
        if value is None:
            return violations
        
        try:
            # Safe eval with limited scope
            # Only allow 'value' variable and basic operations
            allowed_names = {
                "__builtins__": {},
                "abs": abs,
                "len": len,
                "min": min,
                "max": max,
                "sum": sum,
            }
            result = eval(expression, allowed_names, {"value": value})
            
            if not result:
                violations.append(Violation(
                    rule_name=rule.get('name', f'{field}_constraint'),
                    violation_type=ViolationType.CONSTRAINT,
                    field=field,
                    message=rule.get('message', f"Constraint failed: {expression}"),
                    severity=rule.get('severity', 'error'),
                    found_value=value,
                    expected_value=expression
                ))
        except Exception as e:
            # Log error but create violation for invalid expression
            violations.append(Violation(
                rule_name=rule.get('name', f'{field}_constraint'),
                violation_type=ViolationType.CONSTRAINT,
                field=field,
                message=f"Constraint evaluation error: {str(e)}",
                severity='warning',
                found_value=value
            ))
        
        return violations
    
    def _validate_pattern(
        self,
        output: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> List[Violation]:
        """
        Validate regex patterns
        
        Args:
            output: Data to validate
            rule: Pattern rule with regex
        
        Returns:
            List of violations
        """
        violations = []
        field = rule.get('field')
        pattern = rule.get('pattern')
        
        value = self._get_nested_value(output, field)
        
        # Skip if field not found
        if value is None:
            return violations
        
        # Value must be string for pattern matching
        if not isinstance(value, str):
            violations.append(Violation(
                rule_name=rule.get('name', f'{field}_pattern_check'),
                violation_type=ViolationType.CONSTRAINT,
                field=field,
                message=f"{field} must be a string for pattern matching",
                severity='error',
                found_value=value,
                expected_value="string"
            ))
            return violations
        
        try:
            if not re.match(pattern, value):
                violations.append(Violation(
                    rule_name=rule.get('name', f'{field}_pattern_check'),
                    violation_type=ViolationType.CONSTRAINT,
                    field=field,
                    message=rule.get('message', f"Value must match pattern: {pattern}"),
                    severity=rule.get('severity', 'error'),
                    found_value=value,
                    expected_value=f"Pattern: {pattern}",
                    suggestion=rule.get('suggestion')
                ))
        except re.error as e:
            violations.append(Violation(
                rule_name=rule.get('name', f'{field}_pattern_check'),
                violation_type=ViolationType.CONSTRAINT,
                field=field,
                message=f"Invalid regex pattern: {str(e)}",
                severity='warning',
                found_value=value
            ))
        
        return violations
    
    def _validate_semantic(
        self,
        output: Dict[str, Any],
        rule: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> List[Violation]:
        """
        Validate semantic alignment between an output field and a context field.

        Rule shape:
            {
                "type": "semantic",
                "output_field": "recommendation",   # key in output dict
                "context_field": "patient_history", # key in context dict
                "min_alignment": 0.5,               # cosine similarity threshold
                "severity": "error"                 # default: "error"
            }
        """
        violations = []

        output_field = rule.get("output_field")
        context_field = rule.get("context_field")
        min_alignment = float(rule.get("min_alignment", 0.5))
        severity = rule.get("severity", "error")
        rule_name = rule.get("name", f"{output_field}_semantic_check")

        if not output_field or not context_field:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.SEMANTIC,
                field=output_field or "unknown",
                message="Semantic rule must specify both 'output_field' and 'context_field'",
                severity="warning",
                found_value=None,
            ))
            return violations

        # Retrieve the output text
        output_text = self._get_nested_value(output, output_field)
        if output_text is None:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.SEMANTIC,
                field=output_field,
                message=f"Field '{output_field}' not found in output",
                severity="warning",
                found_value=None,
            ))
            return violations

        # Retrieve the context text
        context_text = None
        if context:
            context_text = context.get(context_field)
        if context_text is None:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.SEMANTIC,
                field=output_field,
                message=f"Context field '{context_field}' not provided — cannot run semantic check",
                severity="warning",
                found_value=str(output_text),
            ))
            return violations

        # Run cosine similarity check
        try:
            result = self._semantic_validator.check_alignment(
                output_text=str(output_text),
                context_text=str(context_text),
                min_alignment=min_alignment,
            )
        except Exception as exc:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.SEMANTIC,
                field=output_field,
                message=f"Semantic validation error: {exc}",
                severity="warning",
                found_value=str(output_text),
            ))
            return violations

        if result.is_contradiction:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.SEMANTIC,
                field=output_field,
                message=(
                    f"Semantic contradiction detected: {result.explanation} "
                    f"Output may contradict or ignore the provided '{context_field}'."
                ),
                severity=severity,
                found_value=str(output_text)[:200],  # truncate for readability
                expected_value=f"Alignment >= {min_alignment} (got {result.score:.4f})",
                suggestion="Review the output — it may contradict the context.",
            ))

        return violations

    async def _validate_web_verify(
        self,
        output: Dict[str, Any],
        rule: Dict[str, Any],
    ) -> List[Violation]:
        """
        Validate a field value against live web sources via Tavily.

        Rule shape::

            {
                "type": "web_verify",
                "field": "ai_response",        # claim text is in this output field
                "confidence_threshold": 0.7,    # below this → violation (default 0.7)
                "search_depth": "basic",         # "basic" | "advanced"
                "max_results": 5,
                "severity": "error"
            }
        """
        violations = []

        field = rule.get("field")
        threshold = float(rule.get("confidence_threshold", 0.7))
        search_depth = rule.get("search_depth", "basic")
        max_results = int(rule.get("max_results", 5))
        severity = rule.get("severity", "error")
        rule_name = rule.get("name", f"{field}_web_verify")

        if not field:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.REFERENCE,
                field="unknown",
                message="web_verify rule must specify 'field'",
                severity="warning",
                found_value=None,
            ))
            return violations

        claim_text = self._get_nested_value(output, field)
        if claim_text is None:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.REFERENCE,
                field=field,
                message=f"Field '{field}' not found in output — cannot run web_verify",
                severity="warning",
                found_value=None,
            ))
            return violations

        verifier = _get_web_verifier()
        if verifier is None:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.REFERENCE,
                field=field,
                message=(
                    "web_verify rule requires TAVILY_API_KEY in .env — "
                    "sign up at https://app.tavily.com"
                ),
                severity="warning",
                found_value=str(claim_text),
            ))
            return violations

        # Run the web fact-check
        try:
            result = await verifier.verify(
                claim=str(claim_text),
                search_depth=search_depth,
                max_results=max_results,
            )
        except Exception as exc:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.REFERENCE,
                field=field,
                message=f"Web verification error: {exc}",
                severity="warning",
                found_value=str(claim_text),
            ))
            return violations

        # If Tavily itself errored, degrade gracefully
        if result.error and not result.sources:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.REFERENCE,
                field=field,
                message=f"Web search unavailable: {result.error}",
                severity="warning",
                found_value=str(claim_text),
            ))
            return violations

        # Raise violation if confidence is below threshold
        if result.web_confidence < threshold:
            source_summaries = " | ".join(
                f"{s.title[:60]} ({s.url[:60]})"
                for s in result.sources[:3]
            )
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.REFERENCE,
                field=field,
                message=(
                    f"Web grounding confidence {result.web_confidence:.2f} "
                    f"(threshold {threshold}) — verdict: {result.verdict}. "
                    f"Sources: {source_summaries or 'none found'}"
                ),
                severity=severity,
                found_value=str(claim_text)[:200],
                expected_value=f"Web confidence >= {threshold}",
                suggestion=(
                    "Review this claim — web sources do not strongly support it."
                    if result.verdict == "UNCERTAIN"
                    else "This claim appears to be contradicted by web sources."
                ),
                metadata={
                    "web_confidence": round(result.web_confidence, 3),
                    "verdict": result.verdict,
                    "sources": [
                        {"title": s.title[:100], "url": s.url}
                        for s in result.sources[:5]
                    ],
                },
            ))

        return violations

    def _validate_anomaly_ml(
        self,
        output: Dict[str, Any],
        rule: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> List[Violation]:
        """
        Run IsolationForest anomaly detection on the output's numeric fields.

        Rule shape::

            {
                "type": "anomaly_ml",
                "name": "hours_anomaly",
                "fields": ["hours", "total_cost"],   # numeric output fields to watch
                "org_id": "org_abc",                  # overrides context.organization_id
                "min_samples": 50,                    # skip if model not trained yet
                "severity": "warning"                 # default: warning
            }

        The model is auto-loaded from disk if it has been previously trained and
        saved. Call ``MLAnomalyDetector.train()`` on your org's historical data
        to enable this rule type.
        """
        violations = []

        fields = rule.get("fields") or []
        severity = rule.get("severity", "warning")
        rule_name = rule.get("name", "anomaly_ml_check")

        # Determine org_id: explicit in rule > from context
        org_id = rule.get("org_id")
        if not org_id and context:
            org_id = context.get("org_id") or context.get("organization_id")

        if not org_id:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.STATISTICAL,
                field="*",
                message=(
                    "anomaly_ml rule requires 'org_id' in the rule or context "
                    "(e.g. context={'org_id': 'org_abc'})"
                ),
                severity="warning",
                found_value=None,
            ))
            return violations

        if not fields:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.STATISTICAL,
                field="*",
                message="anomaly_ml rule must specify 'fields' — list of numeric fields to monitor",
                severity="warning",
                found_value=None,
            ))
            return violations

        detector = get_ml_anomaly_detector()

        if not detector.is_trained(org_id):
            # Try loading from disk silently — if still not trained, skip gracefully
            if not detector._load(org_id):
                violations.append(Violation(
                    rule_name=rule_name,
                    violation_type=ViolationType.STATISTICAL,
                    field="*",
                    message=(
                        f"IsolationForest model not yet trained for org='{org_id}'. "
                        f"Call MLAnomalyDetector.train() after collecting "
                        f"{rule.get('min_samples', 50)}+ records."
                    ),
                    severity="warning",
                    found_value=None,
                ))
                return violations

        result = detector.score(
            org_id=org_id,
            sample=output,
            fields=fields,
            severity=severity,
        )

        if result.is_anomaly:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.STATISTICAL,
                field=", ".join(fields),
                message=(
                    f"ML anomaly detected for org='{org_id}': {result.reason}"
                ),
                severity=severity,
                found_value={f: self._get_nested_value(output, f) for f in fields},
                expected_value=f"Normal range learned from historical data (IF score >= 0, got {result.raw_score:.4f})",
                suggestion="This output pattern deviates significantly from historical norms — review for hallucination.",
            ))

        return violations

    async def _validate_external_ref(
        self,
        output: Dict[str, Any],
        rule: Dict[str, Any],
    ) -> List[Violation]:
        """
        Call a registered external-reference connector and produce a violation
        when the connector returns ``exists=False``.

        Rule shape::

            {
                "type": "external_ref",
                "field": "sehri_time",         # field whose value is passed to the connector
                "connector": "aladhan_fajr_in_range",
                "params": {                     # optional kwargs forwarded to the connector
                    "city": "Dhaka",
                    "country": "Bangladesh",
                    "tolerance_minutes": 15
                },
                "severity": "error"
            }
        """
        violations: List[Violation] = []
        field = rule.get("field")
        connector_name = rule.get("connector", "")
        params: Dict[str, Any] = rule.get("params") or {}
        severity = rule.get("severity", "error")
        rule_name = rule.get("name", f"{field}_external_ref")
        timeout = float(rule.get("timeout", 10.0))

        if not field:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.REFERENCE,
                field="unknown",
                message="external_ref rule must specify 'field'",
                severity="warning",
                found_value=None,
            ))
            return violations

        if not connector_name:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.REFERENCE,
                field=field,
                message="external_ref rule must specify 'connector'",
                severity="warning",
                found_value=None,
            ))
            return violations

        value = self._get_nested_value(output, field)

        # Connector not registered — soft warning, never crash
        if connector_name not in ExternalReferenceValidator.registered_names():
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.REFERENCE,
                field=field,
                message=(
                    f"Connector '{connector_name}' is not registered. "
                    f"Available: {ExternalReferenceValidator.registered_names()}"
                ),
                severity="warning",
                found_value=value,
            ))
            return violations

        try:
            result: ConnectorResult = await ExternalReferenceValidator.check(
                connector_name=connector_name,
                value=value,
                params=params,
                timeout=timeout,
            )
        except Exception as exc:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.REFERENCE,
                field=field,
                message=f"External reference check failed: {exc}",
                severity="warning",
                found_value=value,
            ))
            return violations

        if not result.exists:
            violations.append(Violation(
                rule_name=rule_name,
                violation_type=ViolationType.REFERENCE,
                field=field,
                message=(
                    rule.get("message")
                    or f"External reference check failed ({connector_name}): {result.detail}"
                ),
                severity=severity,
                found_value=value,
                expected_value=f"Connector '{connector_name}' must return exists=True",
                suggestion=result.detail,
            ))

        return violations

    def _validate_enum(
        self,
        output: Dict[str, Any],
        rule: Dict[str, Any],
    ) -> List[Violation]:
        """
        Check that a field's value is one of a fixed set of allowed values.
        Emits `expected_value={"valid_options": [...]}` so FuzzyMatchStrategy
        can suggest the closest match and auto-correct.

        Rule shape::
            {
                "type": "enum",
                "field": "status",
                "valid_options": ["pending", "approved", "rejected"],
                "severity": "error"
            }
        """
        violations: List[Violation] = []
        field = rule.get("field")
        valid_options: List[str] = rule.get("valid_options", [])

        if not field or not valid_options:
            return violations

        value = self._get_nested_value(output, field)
        if value is None:
            return violations  # missing field is a `required` concern, not enum

        if str(value) not in [str(v) for v in valid_options]:
            violations.append(Violation(
                rule_name=rule.get("name", f"{field}_enum_check"),
                violation_type=ViolationType.CONSTRAINT,
                field=field,
                message=(
                    f"{field} value '{value}' is not in allowed list: "
                    f"{valid_options}"
                ),
                severity=rule.get("severity", "error"),
                found_value=value,
                expected_value={"valid_options": valid_options},
                suggestion=f"Use one of: {', '.join(str(v) for v in valid_options)}",
            ))

        return violations

    def _validate_required(
        self,
        output: Dict[str, Any],
        rule: Dict[str, Any],
    ) -> List[Violation]:
        """
        Check that a required field is present and non-null.
        Optionally carry `default_value` in `expected_value` so
        DefaultValueStrategy can fill it in automatically.

        Rule shape::
            {
                "type": "required",
                "field": "currency",
                "default_value": "USD",   # optional — enables auto-correct
                "severity": "error"
            }
        """
        violations: List[Violation] = []
        field = rule.get("field")
        if not field:
            return violations

        value = self._get_nested_value(output, field)
        if value is not None:
            return violations  # present and non-null — OK

        default_value = rule.get("default_value")
        expected: Any = (
            {"default_value": default_value} if default_value is not None else "non-null value"
        )

        violations.append(Violation(
            rule_name=rule.get("name", f"{field}_required"),
            violation_type=ViolationType.SCHEMA,
            field=field,
            message=f"Required field '{field}' is missing or null",
            severity=rule.get("severity", "error"),
            found_value=value,
            expected_value=expected,
            suggestion=(
                f"Set '{field}' to '{default_value}'" if default_value is not None
                else f"Provide a value for '{field}'"
            ),
        ))

        return violations

    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """
        Get value from nested dict using dot notation
        
        Args:
            obj: Dictionary to traverse
            path: Dot-separated path (e.g., 'user.address.city')
        
        Returns:
            Value at path or None if not found
        """
        keys = path.split('.')
        value = obj
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
