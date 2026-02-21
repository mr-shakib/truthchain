"""
Rule Engine - Validates data against business rules and constraints
"""
from typing import Dict, List, Any, Optional
import re
from .validation_engine import Violation, ViolationType
from .semantic_validator import SemanticValidator


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
