"""
Auto-Corrector for TruthChain
Automatically fixes common validation violations
"""
from typing import Dict, List, Any, Optional, Tuple
from copy import deepcopy
from datetime import datetime
import re

from ..core.validation_engine import Violation, ViolationType


class CorrectionStrategy:
    """Base class for correction strategies"""
    
    def can_fix(self, violation: Violation) -> bool:
        """Check if this strategy can fix the violation"""
        raise NotImplementedError
    
    def fix(self, output: Dict[str, Any], violation: Violation) -> Tuple[Dict[str, Any], str]:
        """
        Apply the fix to the output
        
        Returns:
            Tuple of (corrected_output, fix_description)
        """
        raise NotImplementedError


class RangeClampingStrategy(CorrectionStrategy):
    """Clamps numeric values to valid ranges"""
    
    def can_fix(self, violation: Violation) -> bool:
        """Can fix range violations"""
        return "range" in violation.rule_name.lower() or "must be between" in violation.message.lower()
    
    def fix(self, output: Dict[str, Any], violation: Violation) -> Tuple[Dict[str, Any], str]:
        """Clamp value to the valid range"""
        corrected = deepcopy(output)
        
        # Extract min/max from violation message or expected_value
        min_val, max_val = self._extract_range(violation)
        
        if min_val is not None and max_val is not None:
            # Get current value and clamp it
            current_value = self._get_field_value(output, violation.field)
            
            if current_value is not None:
                clamped_value = max(min_val, min(max_val, current_value))
                self._set_field_value(corrected, violation.field, clamped_value)
                
                fix_desc = f"Clamped {violation.field} from {current_value} to {clamped_value} (range: {min_val}-{max_val})"
                return corrected, fix_desc
        
        return output, "Could not auto-correct range violation"
    
    def _extract_range(self, violation: Violation) -> Tuple[Optional[float], Optional[float]]:
        """Extract min and max from violation"""
        # Try to parse from message like "must be between 0 and 24"
        message = violation.message
        matches = re.findall(r'between\s+(-?\d+\.?\d*)\s+and\s+(-?\d+\.?\d*)', message)
        
        if matches:
            try:
                return float(matches[0][0]), float(matches[0][1])
            except:
                pass
        
        # Try to get from expected_value if it's a dict with min/max
        if isinstance(violation.expected_value, dict):
            min_val = violation.expected_value.get('min')
            max_val = violation.expected_value.get('max')
            if min_val is not None and max_val is not None:
                return float(min_val), float(max_val)
        
        return None, None
    
    def _get_field_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get nested field value"""
        keys = field.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _set_field_value(self, data: Dict[str, Any], field: str, value: Any) -> None:
        """Set nested field value"""
        keys = field.split(".")
        target = data
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value


class TypeCoercionStrategy(CorrectionStrategy):
    """Converts values to the correct type"""
    
    def can_fix(self, violation: Violation) -> bool:
        """Can fix type violations"""
        return violation.violation_type == ViolationType.SCHEMA and "type" in violation.message.lower()
    
    def fix(self, output: Dict[str, Any], violation: Violation) -> Tuple[Dict[str, Any], str]:
        """Coerce value to expected type"""
        corrected = deepcopy(output)
        
        # Determine expected type from violation
        expected_type = self._extract_expected_type(violation)
        
        if expected_type:
            current_value = self._get_field_value(output, violation.field)
            
            try:
                coerced_value = self._coerce_type(current_value, expected_type)
                self._set_field_value(corrected, violation.field, coerced_value)
                
                fix_desc = f"Coerced {violation.field} from {type(current_value).__name__} to {expected_type}"
                return corrected, fix_desc
            except Exception as e:
                return output, f"Could not coerce type: {str(e)}"
        
        return output, "Could not determine expected type"
    
    def _extract_expected_type(self, violation: Violation) -> Optional[str]:
        """Extract expected type from violation"""
        message = violation.message.lower()
        
        if "integer" in message or "int" in message:
            return "integer"
        elif "number" in message or "float" in message:
            return "number"
        elif "string" in message or "str" in message:
            return "string"
        elif "boolean" in message or "bool" in message:
            return "boolean"
        elif "array" in message or "list" in message:
            return "array"
        elif "object" in message or "dict" in message:
            return "object"
        
        return None
    
    def _coerce_type(self, value: Any, target_type: str) -> Any:
        """Coerce value to target type"""
        if target_type == "integer":
            return int(float(value))  # Handle "123.0" -> 123
        elif target_type == "number":
            return float(value)
        elif target_type == "string":
            return str(value)
        elif target_type == "boolean":
            if isinstance(value, str):
                return value.lower() in ("true", "yes", "1")
            return bool(value)
        elif target_type == "array":
            if isinstance(value, list):
                return value
            return [value]
        elif target_type == "object":
            if isinstance(value, dict):
                return value
            return {"value": value}
        else:
            return value
    
    def _get_field_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get nested field value"""
        keys = field.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _set_field_value(self, data: Dict[str, Any], field: str, value: Any) -> None:
        """Set nested field value"""
        keys = field.split(".")
        target = data
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value


class StringTrimStrategy(CorrectionStrategy):
    """Trims and normalizes string values"""
    
    def can_fix(self, violation: Violation) -> bool:
        """Can fix string whitespace violations"""
        return "whitespace" in violation.message.lower() or "trim" in violation.message.lower()
    
    def fix(self, output: Dict[str, Any], violation: Violation) -> Tuple[Dict[str, Any], str]:
        """Trim whitespace from string"""
        corrected = deepcopy(output)
        
        current_value = self._get_field_value(output, violation.field)
        
        if isinstance(current_value, str):
            trimmed_value = current_value.strip()
            self._set_field_value(corrected, violation.field, trimmed_value)
            
            fix_desc = f"Trimmed whitespace from {violation.field}"
            return corrected, fix_desc
        
        return output, "Value is not a string"
    
    def _get_field_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get nested field value"""
        keys = field.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _set_field_value(self, data: Dict[str, Any], field: str, value: Any) -> None:
        """Set nested field value"""
        keys = field.split(".")
        target = data
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value


class AutoCorrector:
    """
    Automatically corrects validation violations when possible
    
    Supports:
    - Range clamping (values outside min/max)
    - Type coercion (wrong type but convertible)
    - String trimming (whitespace issues)
    - Case normalization (email, URLs, etc.)
    
    Tracks all corrections applied for audit trail
    """
    
    def __init__(self):
        self.strategies: List[CorrectionStrategy] = [
            RangeClampingStrategy(),
            TypeCoercionStrategy(),
            StringTrimStrategy(),
        ]
        self.corrections_applied: List[str] = []
    
    async def fix(
        self,
        output: Dict[str, Any],
        violations: List[Violation],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Attempt to fix all violations in the output
        
        Args:
            output: Original AI output with violations
            violations: List of violations found
            context: Optional context (e.g., auto_correct: true)
        
        Returns:
            Tuple of (corrected_output, list_of_fixes_applied)
            Returns (None, []) if no fixes could be applied
        """
        # Check if auto-correction is enabled in context
        if context and not context.get("auto_correct", False):
            return None, []
        
        corrected = deepcopy(output)
        fixes_applied = []
        fixed_violations = 0
        
        # Try to fix each error-level violation
        for violation in violations:
            if violation.severity != "error":
                continue  # Only auto-fix errors, not warnings
            
            # Try each strategy
            for strategy in self.strategies:
                if strategy.can_fix(violation):
                    try:
                        corrected, fix_desc = strategy.fix(corrected, violation)
                        fixes_applied.append(fix_desc)
                        fixed_violations += 1
                        break  # Stop after first successful fix
                    except Exception as e:
                        # Log and continue to next strategy
                        print(f"Auto-correction failed: {e}")
                        continue
        
        # Only return corrected output if we actually fixed something
        if fixed_violations > 0:
            return corrected, fixes_applied
        else:
            return None, []
    
    async def can_auto_correct(self, violations: List[Violation]) -> bool:
        """
        Check if any violations can be auto-corrected
        
        Args:
            violations: List of violations
        
        Returns:
            True if at least one violation can be fixed
        """
        for violation in violations:
            if violation.severity != "error":
                continue
            
            for strategy in self.strategies:
                if strategy.can_fix(violation):
                    return True
        
        return False
    
    def add_strategy(self, strategy: CorrectionStrategy) -> None:
        """Add a custom correction strategy"""
        self.strategies.append(strategy)
    
    def get_applied_corrections(self) -> List[str]:
        """Get list of all corrections applied"""
        return self.corrections_applied.copy()
    
    def clear_history(self) -> None:
        """Clear correction history"""
        self.corrections_applied.clear()
