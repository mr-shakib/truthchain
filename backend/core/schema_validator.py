"""
Schema Validator - Validates data against JSON schemas and type constraints
"""
from typing import Dict, List, Any
import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError
from .validation_engine import Violation, ViolationType


class SchemaValidator:
    """Validates output against JSON Schema specifications"""
    
    async def validate(
        self,
        output: Dict[str, Any],
        rules: List[Dict[str, Any]]
    ) -> List[Violation]:
        """
        Validate output against schema rules
        
        Args:
            output: The data to validate
            rules: List of validation rules (only schema rules will be processed)
        
        Returns:
            List of violations found
        """
        violations = []
        
        # Extract schema rules
        schema_rules = [r for r in rules if r.get('type') == 'schema']
        
        for rule in schema_rules:
            schema = rule.get('schema')
            if not schema:
                continue
            
            try:
                # Validate using jsonschema
                jsonschema.validate(instance=output, schema=schema)
            except JsonSchemaValidationError as e:
                # Build field path from error
                field_path = '.'.join(str(p) for p in e.path) if e.path else 'root'
                
                violations.append(Violation(
                    rule_name=rule.get('name', 'schema_check'),
                    violation_type=ViolationType.SCHEMA,
                    field=field_path,
                    message=e.message,
                    severity=rule.get('severity', 'error'),
                    found_value=e.instance,
                    expected_value=str(e.schema) if hasattr(e, 'schema') else None
                ))
            except Exception as e:
                # Handle other schema validation errors
                violations.append(Violation(
                    rule_name=rule.get('name', 'schema_check'),
                    violation_type=ViolationType.SCHEMA,
                    field='unknown',
                    message=f"Schema validation error: {str(e)}",
                    severity='error',
                    found_value=output
                ))
        
        return violations
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """
        Validate value type
        
        Args:
            value: Value to check
            expected_type: Expected type (int, string, float, bool, array, object)
        
        Returns:
            True if type matches
        """
        type_map = {
            'integer': int,
            'string': str,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict,
            'null': type(None)
        }
        
        expected = type_map.get(expected_type)
        if expected is None:
            return False
        
        return isinstance(value, expected)
    
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
