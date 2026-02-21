"""
Statistical Analyzer for TruthChain
Calculates statistics and detects outliers in validated data
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from pydantic import BaseModel
import statistics
import math

from ..models.validation_log import ValidationLog
from ..core.validation_engine import Violation, ViolationType


class StatisticalMetrics(BaseModel):
    """Statistical metrics for a numeric field"""
    field: str
    count: int
    mean: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    q1: float  # 25th percentile
    q3: float  # 75th percentile
    iqr: float  # Interquartile range
    outlier_count: int
    timestamp: str


class OutlierDetectionResult(BaseModel):
    """Result of outlier detection"""
    field: str
    value: Any
    is_outlier: bool
    method: str  # z-score, iqr, or custom
    score: float
    threshold: float
    severity: str  # warning or error


class StatisticalAnalyzer:
    """
    Analyzes validated data for statistical patterns and outliers
    
    Capabilities:
    - Calculate descriptive statistics (mean, median, std dev, quartiles)
    - Detect outliers using z-score method
    - Detect outliers using IQR (Interquartile Range) method
    - Compare current values against historical baselines
    - Identify unusual patterns in AI outputs
    """
    
    def __init__(self, db: AsyncSession = None):
        """
        Initialize statistical analyzer
        
        Args:
            db: Optional database session for historical analysis
        """
        self.db = db
        
        # Configuration
        self.z_score_threshold = 3.0  # Standard: 3 standard deviations
        self.iqr_multiplier = 1.5     # Standard: 1.5 * IQR
        self.min_sample_size = 10     # Minimum samples for statistical analysis
    
    async def analyze_field(
        self,
        field: str,
        values: List[float],
        detect_outliers: bool = True
    ) -> StatisticalMetrics:
        """
        Calculate statistical metrics for a numeric field
        
        Args:
            field: Field name
            values: List of numeric values
            detect_outliers: Whether to detect outliers
        
        Returns:
            StatisticalMetrics with all calculated statistics
        """
        if not values:
            raise ValueError(f"No values provided for field '{field}'")
        
        if len(values) < 2:
            # Not enough data for statistics
            return StatisticalMetrics(
                field=field,
                count=len(values),
                mean=values[0],
                median=values[0],
                std_dev=0.0,
                min_value=values[0],
                max_value=values[0],
                q1=values[0],
                q3=values[0],
                iqr=0.0,
                outlier_count=0,
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Calculate statistics
        sorted_values = sorted(values)
        count = len(values)
        mean_val = statistics.mean(values)
        median_val = statistics.median(values)
        std_dev = statistics.stdev(values) if count > 1 else 0.0
        min_val = min(values)
        max_val = max(values)
        
        # Calculate quartiles
        q1 = self._calculate_quartile(sorted_values, 0.25)
        q3 = self._calculate_quartile(sorted_values, 0.75)
        iqr = q3 - q1
        
        # Detect outliers if requested
        outlier_count = 0
        if detect_outliers and count >= self.min_sample_size:
            outlier_count = self._count_outliers_iqr(values, q1, q3, iqr)
        
        return StatisticalMetrics(
            field=field,
            count=count,
            mean=mean_val,
            median=median_val,
            std_dev=std_dev,
            min_value=min_val,
            max_value=max_val,
            q1=q1,
            q3=q3,
            iqr=iqr,
            outlier_count=outlier_count,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def detect_outlier_zscore(
        self,
        field: str,
        value: float,
        mean: float,
        std_dev: float,
        threshold: Optional[float] = None
    ) -> OutlierDetectionResult:
        """
        Detect outlier using z-score method
        
        Z-score = (value - mean) / std_dev
        Outlier if |z-score| > threshold (default: 3.0)
        
        Args:
            field: Field name
            value: Value to check
            mean: Mean of the dataset
            std_dev: Standard deviation
            threshold: Custom z-score threshold
        
        Returns:
            OutlierDetectionResult
        """
        if threshold is None:
            threshold = self.z_score_threshold
        
        if std_dev == 0:
            # No variation - any different value is an outlier
            z_score = 0.0 if value == mean else float('inf')
        else:
            z_score = abs((value - mean) / std_dev)
        
        is_outlier = z_score > threshold
        
        # Determine severity
        if z_score > threshold * 1.5:
            severity = "error"
        elif z_score > threshold:
            severity = "warning"
        else:
            severity = "info"
        
        return OutlierDetectionResult(
            field=field,
            value=value,
            is_outlier=is_outlier,
            method="z-score",
            score=z_score,
            threshold=threshold,
            severity=severity
        )
    
    def detect_outlier_iqr(
        self,
        field: str,
        value: float,
        q1: float,
        q3: float,
        iqr: float,
        multiplier: Optional[float] = None
    ) -> OutlierDetectionResult:
        """
        Detect outlier using IQR (Interquartile Range) method
        
        Outlier if value < Q1 - k*IQR or value > Q3 + k*IQR
        Default k = 1.5
        
        Args:
            field: Field name
            value: Value to check
            q1: First quartile (25th percentile)
            q3: Third quartile (75th percentile)
            iqr: Interquartile range (Q3 - Q1)
            multiplier: Custom IQR multiplier (default: 1.5)
        
        Returns:
            OutlierDetectionResult
        """
        if multiplier is None:
            multiplier = self.iqr_multiplier
        
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        is_outlier = value < lower_bound or value > upper_bound
        
        # Calculate distance from bounds as score
        if value < lower_bound:
            score = abs(value - lower_bound)
        elif value > upper_bound:
            score = abs(value - upper_bound)
        else:
            score = 0.0
        
        # Normalize score by IQR for severity
        normalized_score = score / iqr if iqr > 0 else 0.0
        
        if normalized_score > 2.0:
            severity = "error"
        elif normalized_score > 1.0:
            severity = "warning"
        else:
            severity = "info"
        
        return OutlierDetectionResult(
            field=field,
            value=value,
            is_outlier=is_outlier,
            method="iqr",
            score=score,
            threshold=multiplier * iqr,
            severity=severity
        )
    
    async def get_historical_statistics(
        self,
        organization_id: str,
        field: str,
        days: int = 30
    ) -> Optional[StatisticalMetrics]:
        """
        Calculate statistics from historical validation logs
        
        Args:
            organization_id: Organization ID for filtering
            field: Field to analyze
            days: Number of days of history to analyze
        
        Returns:
            StatisticalMetrics or None if insufficient data
        """
        if not self.db:
            return None
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Query validation logs
            query = select(ValidationLog).where(
                ValidationLog.organization_id == organization_id,
                ValidationLog.created_at >= cutoff_date
            ).order_by(ValidationLog.created_at.desc())
            
            result = await self.db.execute(query)
            logs = result.scalars().all()
            
            if not logs:
                return None
            
            # Extract field values from output_data
            values = []
            for log in logs:
                output_data = log.output_data
                if isinstance(output_data, dict):
                    value = self._extract_field_value(output_data, field)
                    if value is not None and isinstance(value, (int, float)):
                        values.append(float(value))
            
            if len(values) < self.min_sample_size:
                return None
            
            # Calculate statistics
            return await self.analyze_field(field, values, detect_outliers=True)
        
        except Exception as e:
            print(f"Error getting historical statistics: {e}")
            return None
    
    async def detect_drift(
        self,
        current_metrics: StatisticalMetrics,
        historical_metrics: StatisticalMetrics,
        threshold: float = 0.2
    ) -> Dict[str, Any]:
        """
        Detect statistical drift between current and historical data
        
        Args:
            current_metrics: Current statistical metrics
            historical_metrics: Historical baseline metrics
            threshold: Drift threshold (e.g., 0.2 = 20% change)
        
        Returns:
            Dict with drift detection results
        """
        drifts = []
        
        # Check mean drift
        mean_drift = abs(current_metrics.mean - historical_metrics.mean) / historical_metrics.mean if historical_metrics.mean != 0 else 0
        if mean_drift > threshold:
            drifts.append({
                "metric": "mean",
                "current": current_metrics.mean,
                "historical": historical_metrics.mean,
                "drift_percentage": mean_drift * 100,
                "severity": "error" if mean_drift > threshold * 2 else "warning"
            })
        
        # Check std dev drift
        std_drift = abs(current_metrics.std_dev - historical_metrics.std_dev) / historical_metrics.std_dev if historical_metrics.std_dev != 0 else 0
        if std_drift > threshold:
            drifts.append({
                "metric": "std_dev",
                "current": current_metrics.std_dev,
                "historical": historical_metrics.std_dev,
                "drift_percentage": std_drift * 100,
                "severity": "warning"
            })
        
        return {
            "field": current_metrics.field,
            "has_drift": len(drifts) > 0,
            "drift_count": len(drifts),
            "drifts": drifts,
            "threshold_percentage": threshold * 100
        }
    
    def _calculate_quartile(self, sorted_values: List[float], percentile: float) -> float:
        """
        Calculate quartile using linear interpolation
        
        Args:
            sorted_values: List of values (must be sorted)
            percentile: Percentile to calculate (0.0 to 1.0)
        
        Returns:
            Quartile value
        """
        n = len(sorted_values)
        if n == 0:
            return 0.0
        if n == 1:
            return sorted_values[0]
        
        # Linear interpolation
        index = percentile * (n - 1)
        lower_index = int(math.floor(index))
        upper_index = int(math.ceil(index))
        
        if lower_index == upper_index:
            return sorted_values[lower_index]
        
        fraction = index - lower_index
        return sorted_values[lower_index] + fraction * (sorted_values[upper_index] - sorted_values[lower_index])
    
    def _count_outliers_iqr(
        self,
        values: List[float],
        q1: float,
        q3: float,
        iqr: float
    ) -> int:
        """Count outliers using IQR method"""
        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr
        
        outliers = [v for v in values if v < lower_bound or v > upper_bound]
        return len(outliers)
    
    def _extract_field_value(self, data: Dict[str, Any], field: str) -> Any:
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
