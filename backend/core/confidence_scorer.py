"""
Confidence Scorer for TruthChain
Calculates confidence scores for validation results
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..core.validation_engine import Violation, ValidationResult, ValidationStatus


class ConfidenceFactors(BaseModel):
    """Factors contributing to confidence score"""
    violation_count: float  # 0.0-1.0 (fewer violations = higher score)
    severity_score: float   # 0.0-1.0 (lower severity = higher score)
    auto_correction_penalty: float  # Penalty for auto-corrected results
    statistical_confidence: float  # Based on statistical analysis
    reference_confidence: float  # Based on reference validation
    overall_confidence: float  # Combined score 0.0-1.0


class ConfidenceScorer:
    """
    Calculates confidence scores for validation results
    
    Confidence score (0.0 to 1.0) indicates how confident we are that:
    - The AI output is valid and accurate
    - No hallucinations or errors are present
    - The data matches expected patterns
    
    High confidence (>0.8): Very likely valid
    Medium confidence (0.5-0.8): Probably valid, some concerns
    Low confidence (<0.5): Likely has issues, review recommended
    """
    
    def __init__(self):
        """Initialize confidence scorer"""
        # Weighting factors for different components
        self.weights = {
            "violation_count": 0.30,       # 30% weight
            "severity": 0.25,              # 25% weight
            "auto_correction": 0.15,       # 15% weight
            "statistical": 0.20,           # 20% weight
            "reference": 0.10              # 10% weight
        }
    
    def calculate_confidence(
        self,
        result: ValidationResult,
        statistical_score: Optional[float] = None,
        has_reference_violations: bool = False
    ) -> ConfidenceFactors:
        """
        Calculate overall confidence score for a validation result
        
        Args:
            result: ValidationResult to score
            statistical_score: Optional statistical confidence (0.0-1.0)
            has_reference_violations: Whether reference violations were found
        
        Returns:
            ConfidenceFactors with detailed scoring
        """
        # Factor 1: Violation count score
        violation_score = self._calculate_violation_score(result.violations)
        
        # Factor 2: Severity score
        severity_score = self._calculate_severity_score(result.violations)
        
        # Factor 3: Auto-correction penalty
        auto_correction_penalty = self._calculate_auto_correction_penalty(
            result.auto_corrected,
            result.corrections_applied
        )
        
        # Factor 4: Statistical confidence
        statistical_confidence = statistical_score if statistical_score is not None else 1.0
        
        # Factor 5: Reference confidence
        reference_confidence = 0.0 if has_reference_violations else 1.0
        
        # Calculate weighted overall confidence
        overall_confidence = (
            violation_score * self.weights["violation_count"] +
            severity_score * self.weights["severity"] +
            (1.0 - auto_correction_penalty) * self.weights["auto_correction"] +
            statistical_confidence * self.weights["statistical"] +
            reference_confidence * self.weights["reference"]
        )
        
        # Clamp to 0.0-1.0
        overall_confidence = max(0.0, min(1.0, overall_confidence))
        
        return ConfidenceFactors(
            violation_count=violation_score,
            severity_score=severity_score,
            auto_correction_penalty=auto_correction_penalty,
            statistical_confidence=statistical_confidence,
            reference_confidence=reference_confidence,
            overall_confidence=overall_confidence
        )
    
    def get_confidence_level(self, confidence: float) -> str:
        """
        Get human-readable confidence level
        
        Args:
            confidence: Confidence score 0.0-1.0
        
        Returns:
            Confidence level: very_high, high, medium, low, very_low
        """
        if confidence >= 0.9:
            return "very_high"
        elif confidence >= 0.75:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        elif confidence >= 0.25:
            return "low"
        else:
            return "very_low"
    
    def get_recommendation(self, confidence: float) -> str:
        """
        Get recommendation based on confidence score
        
        Args:
            confidence: Confidence score 0.0-1.0
        
        Returns:
            Recommendation string
        """
        if confidence >= 0.9:
            return "Output appears highly reliable. Safe to use."
        elif confidence >= 0.75:
            return "Output is likely valid. Minor review recommended."
        elif confidence >= 0.5:
            return "Output has some concerns. Review recommended before use."
        elif confidence >= 0.25:
            return "Output has significant issues. Manual review required."
        else:
            return "Output is unreliable. Do not use without thorough validation."
    
    def _calculate_violation_score(self, violations: List[Violation]) -> float:
        """
        Calculate score based on number of violations
        
        Args:
            violations: List of violations
        
        Returns:
            Score 0.0-1.0 (fewer violations = higher score)
        """
        if not violations:
            return 1.0
        
        # Exponential decay: score = e^(-violations/3)
        # 0 violations = 1.0
        # 3 violations = 0.37
        # 6 violations = 0.14
        import math
        score = math.exp(-len(violations) / 3.0)
        return score
    
    def _calculate_severity_score(self, violations: List[Violation]) -> float:
        """
        Calculate score based on violation severity
        
        Args:
            violations: List of violations
        
        Returns:
            Score 0.0-1.0 (lower severity = higher score)
        """
        if not violations:
            return 1.0
        
        # Weight different severities
        severity_weights = {
            "error": 1.0,
            "warning": 0.5,
            "info": 0.1
        }
        
        # Calculate total severity points
        total_severity = sum(
            severity_weights.get(v.severity, 0.5)
            for v in violations
        )
        
        # Normalize by max possible severity
        max_severity = len(violations) * 1.0
        
        if max_severity == 0:
            return 1.0
        
        # Invert so higher = better
        score = 1.0 - min(total_severity / max_severity, 1.0)
        return score
    
    def _calculate_auto_correction_penalty(
        self,
        auto_corrected: bool,
        corrections: Optional[List[str]]
    ) -> float:
        """
        Calculate penalty for auto-corrected results
        
        Args:
            auto_corrected: Whether output was auto-corrected
            corrections: List of corrections applied
        
        Returns:
            Penalty 0.0-1.0 (higher = more penalty)
        """
        if not auto_corrected or not corrections:
            return 0.0
        
        # Light penalty for corrections (0.1 per correction, max 0.5)
        correction_count = len(corrections)
        penalty = min(correction_count * 0.1, 0.5)
        
        return penalty
    
    def calculate_statistical_confidence(
        self,
        outlier_results: List[Any],
        total_fields: int
    ) -> float:
        """
        Calculate confidence based on statistical analysis
        
        Args:
            outlier_results: List of outlier detection results
            total_fields: Total number of fields analyzed
        
        Returns:
            Statistical confidence 0.0-1.0
        """
        if total_fields == 0:
            return 1.0
        
        outlier_count = len(outlier_results)
        
        if outlier_count == 0:
            return 1.0
        
        # Penalize based on percentage of outlier fields
        outlier_ratio = outlier_count / total_fields
        
        # Exponential decay
        import math
        confidence = math.exp(-outlier_ratio * 2)
        return confidence
    
    def calculate_pattern_confidence(
        self,
        patterns_detected: List[Any]
    ) -> float:
        """
        Calculate confidence based on pattern detection
        
        Args:
            patterns_detected: List of detected anomaly patterns
        
        Returns:
            Pattern confidence 0.0-1.0
        """
        if not patterns_detected:
            return 1.0
        
        # Each pattern reduces confidence
        import math
        confidence = math.exp(-len(patterns_detected) * 0.3)
        return confidence
