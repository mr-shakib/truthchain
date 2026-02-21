"""
Context Manager for TruthChain
Validates references against database or external sources
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel

from ..core.validation_engine import Violation, ViolationType


class ReferenceRule(BaseModel):
    """Configuration for a reference validation rule"""
    type: str = "reference"
    name: str
    field: str  # Field in the output to validate
    table: str  # Database table to check
    column: str  # Column in the table to match
    severity: str = "error"  # error or warning
    custom_message: Optional[str] = None


class ContextManager:
    """
    Manages context-aware validation including database reference checks
    
    Validates that values in AI output actually exist in the database,
    preventing hallucinated or invalid references.
    
    Examples:
        - Validate user_id exists in users table
        - Validate project_id exists in projects table
        - Validate email belongs to an active account
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_references(
        self,
        output: Dict[str, Any],
        rules: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Violation]:
        """
        Validate all reference rules
        
        Args:
            output: AI output data to validate
            rules: List of validation rules (filters for reference type)
            context: Optional context (organization_id, custom tables, etc.)
        
        Returns:
            List of violations found
        """
        violations = []
        
        # Filter for reference rules
        reference_rules = [r for r in rules if r.get("type") == "reference"]
        
        for rule_dict in reference_rules:
            try:
                rule = ReferenceRule(**rule_dict)
                violation = await self._validate_reference(output, rule, context)
                if violation:
                    violations.append(violation)
            except Exception as e:
                # If rule parsing fails, create a violation
                violations.append(Violation(
                    rule_name=rule_dict.get("name", "unknown"),
                    violation_type=ViolationType.REFERENCE,
                    field=rule_dict.get("field", "unknown"),
                    message=f"Rule parsing error: {str(e)}",
                    severity="error",
                    found_value=None
                ))
        
        return violations
    
    async def _validate_reference(
        self,
        output: Dict[str, Any],
        rule: ReferenceRule,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Violation]:
        """
        Validate a single reference rule
        
        Args:
            output: AI output data
            rule: Reference rule to validate
            context: Optional context data
        
        Returns:
            Violation if reference is invalid, None if valid
        """
        # Get the value from output
        field_value = self._get_nested_field(output, rule.field)
        
        if field_value is None:
            return Violation(
                rule_name=rule.name,
                violation_type=ViolationType.REFERENCE,
                field=rule.field,
                message=rule.custom_message or f"Field '{rule.field}' not found in output",
                severity=rule.severity,
                found_value=None
            )
        
        # Check if the reference exists in the database
        exists = await self._check_reference_exists(
            table=rule.table,
            column=rule.column,
            value=field_value,
            context=context
        )
        
        if not exists:
            return Violation(
                rule_name=rule.name,
                violation_type=ViolationType.REFERENCE,
                field=rule.field,
                message=rule.custom_message or f"{rule.field}={field_value} does not exist in {rule.table}.{rule.column}",
                severity=rule.severity,
                found_value=field_value,
                suggestion=f"Verify that the {rule.field} exists in your database"
            )
        
        return None
    
    async def _check_reference_exists(
        self,
        table: str,
        column: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a reference exists in the database
        
        Args:
            table: Table name to query
            column: Column name to check
            value: Value to look for
            context: Optional context (e.g., organization_id for filtering)
        
        Returns:
            True if reference exists, False otherwise
        """
        try:
            # Build query - using text() for safety with table/column names
            query = f"SELECT 1 FROM {table} WHERE {column} = :value LIMIT 1"
            
            # Add organization filter if provided in context
            # But skip if we're checking the organizations table itself
            if context and "organization_id" in context and table != "organizations":
                query = f"SELECT 1 FROM {table} WHERE {column} = :value AND organization_id = :org_id LIMIT 1"
                result = await self.db.execute(
                    text(query),
                    {"value": value, "org_id": context["organization_id"]}
                )
            else:
                result = await self.db.execute(
                    text(query),
                    {"value": value}
                )
            
            # Check if any row was returned
            row = result.first()
            return row is not None
            
        except Exception as e:
            # Log error in production
            print(f"Reference check error for {table}.{column}: {e}")
            # Rollback to keep transaction healthy
            await self.db.rollback()
            # For safety, return False if query fails
            return False
    
    def _get_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        Get a nested field from data using dot notation
        
        Args:
            data: Dictionary to extract from
            field_path: Path like "user.id" or "project_id"
        
        Returns:
            Field value or None if not found
        """
        keys = field_path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return None
            else:
                return None
        
        return value
    
    async def validate_custom_context(
        self,
        output: Dict[str, Any],
        rules: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Violation]:
        """
        Validate custom context rules (extensible for future use)
        
        This can be extended to support:
        - API calls to external services
        - Complex business logic validation
        - Machine learning model predictions
        
        Args:
            output: AI output data
            rules: List of custom context rules
            context: Context data
        
        Returns:
            List of violations
        """
        violations = []
        
        # Filter for custom context rules
        custom_rules = [r for r in rules if r.get("type") == "custom_context"]
        
        # Placeholder for future custom context validation
        # This could call external APIs, ML models, etc.
        
        return violations


class ContextCache:
    """
    Cache for frequently-accessed reference data
    
    Reduces database load by caching reference checks
    Will be integrated with Redis in the caching layer
    """
    
    def __init__(self):
        self._cache: Dict[str, bool] = {}
    
    def get_cache_key(self, table: str, column: str, value: Any) -> str:
        """Generate cache key for a reference check"""
        return f"ref:{table}:{column}:{value}"
    
    def get(self, table: str, column: str, value: Any) -> Optional[bool]:
        """Get cached reference check result"""
        key = self.get_cache_key(table, column, value)
        return self._cache.get(key)
    
    def set(self, table: str, column: str, value: Any, exists: bool) -> None:
        """Cache reference check result"""
        key = self.get_cache_key(table, column, value)
        self._cache[key] = exists
    
    def clear(self) -> None:
        """Clear all cached data"""
        self._cache.clear()
