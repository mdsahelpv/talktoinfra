"""Anomaly detection service using statistical methods and ML-like algorithms."""

import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy import and_, desc

from app.config import get_settings
from app.database import get_db_session
from app.models import BaselineMetric, Metric

logger = structlog.get_logger(__name__)


class AnomalyDetector:
    """ML-based anomaly detection service."""

    def __init__(self) -> None:
        """Initialize anomaly detector."""
        self.settings = get_settings().anomaly_detection
        self._cache: Dict[str, Dict[datetime, float]] = defaultdict(dict)

    def detect_anomaly(
        self,
        metric_name: str,
        labels: Dict[str, str],
        current_value: float,
    ) -> Tuple[bool, float]:
        """Detect if a metric value is anomalous.

        Args:
            metric_name: Name of the metric
            labels: Labels associated with the metric
            current_value: Current value to check

        Returns:
            Tuple of (is_anomaly, z_score)
        """
        if not self.settings.enabled:
            return False, 0.0

        # Get baseline for this metric
        baseline = self._get_baseline(metric_name, labels)

        if baseline is None:
            # Not enough data yet - learn from this value
            self._learn_baseline(metric_name, labels, current_value)
            return False, 0.0

        # Calculate z-score
        z_score = self._calculate_z_score(current_value, baseline)

        # Check if anomalous
        is_anomaly = abs(z_score) > self.settings.sensitivity

        if is_anomaly:
            logger.warning(
                "anomaly_detected",
                metric_name=metric_name,
                labels=labels,
                value=current_value,
                z_score=z_score,
                threshold=self.settings.sensitivity
            )

        return is_anomaly, z_score

    def _get_baseline(
        self,
        metric_name: str,
        labels: Dict[str, str],
    ) -> Optional[BaselineMetric]:
        """Get baseline metric for a given metric and labels."""
        import json

        db_session = get_db_session()
        try:
            # Build query for baseline
            query = db_session.query(BaselineMetric).filter(
                BaselineMetric.metric_name == metric_name
            )

            # Match labels
            labels_json = json.dumps(labels)
            query = query.filter(BaselineMetric.labels == labels_json)

            # Order by sample count to get most learned baseline
            query = query.order_by(desc(BaselineMetric.sample_count)).limit(1)

            result = query.first()

            if result and result.sample_count >= self.settings.min_data_points:
                return result

            return None

        finally:
            db_session.close()

    def _learn_baseline(
        self,
        metric_name: str,
        labels: Dict[str, str],
        value: float,
    ) -> None:
        """Learn baseline from collected metric values."""
        import json

        db_session = get_db_session()
        try:
            # Check if we have enough recent data points
            cutoff_time = datetime.utcnow() - timedelta(hours=self.settings.baseline_window_hours)

            recent_metrics = db_session.query(Metric).filter(
                Metric.name == metric_name,
                Metric.timestamp >= cutoff_time
            ).all()

            if len(recent_metrics) < self.settings.min_data_points:
                logger.debug(
                    "learning_baseline_not_enough_data",
                    metric_name=metric_name,
                    current_count=len(recent_metrics),
                    required=self.settings.min_data_points
                )
                return

            # Calculate statistics
            values = [m.value for m in recent_metrics]
            mean_value = sum(values) / len(values)

            # Calculate standard deviation
            variance = sum((v - mean_value) ** 2 for v in values) / len(values)
            std_deviation = math.sqrt(variance)

            # Calculate percentiles
            sorted_values = sorted(values)
            percentile_95_idx = int(len(sorted_values) * 0.95)
            percentile_95 = sorted_values[percentile_95_idx]

            # Create or update baseline
            labels_json = json.dumps(labels)
            now = datetime.utcnow()

            # Calculate time-based features if seasonal patterns enabled
            hour_of_day = now.hour if self.settings.seasonal_patterns else None
            day_of_week = now.weekday() if self.settings.seasonal_patterns else None

            # Check for existing baseline
            existing = db_session.query(BaselineMetric).filter(
                BaselineMetric.metric_name == metric_name,
                BaselineMetric.labels == labels_json
            ).first()

            if existing:
                # Update existing baseline with weighted average
                alpha = 0.1  # Learning rate
                existing.mean_value = (1 - alpha) * \
                    existing.mean_value + alpha * mean_value
                existing.std_deviation = (
                    1 - alpha) * existing.std_deviation + alpha * std_deviation
                existing.percentile_95 = (
                    1 - alpha) * existing.percentile_95 + alpha * percentile_95
                existing.sample_count += len(recent_metrics)
                existing.last_updated = now
            else:
                # Create new baseline
                baseline = BaselineMetric(
                    metric_name=metric_name,
                    labels=labels_json,
                    mean_value=mean_value,
                    std_deviation=std_deviation,
                    min_value=min(values),
                    max_value=max(values),
                    percentile_95=percentile_95,
                    sample_count=len(recent_metrics),
                    hour_of_day=hour_of_day,
                    day_of_week=day_of_week,
                    last_updated=now,
                )
                db_session.add(baseline)

            db_session.commit()

            logger.info(
                "baseline_learned",
                metric_name=metric_name,
                mean=mean_value,
                std=std_deviation,
                sample_count=len(recent_metrics)
            )

        except Exception as e:
            db_session.rollback()
            logger.error("baseline_learning_failed", error=str(e))
        finally:
            db_session.close()

    def _calculate_z_score(
        self,
        value: float,
        baseline: BaselineMetric,
    ) -> float:
        """Calculate z-score for a value given a baseline."""
        if baseline.std_deviation == 0:
            if baseline.mean_value == 0:
                return 0.0
            return abs(value - baseline.mean_value) / abs(baseline.mean_value) * 3

        return (value - baseline.mean_value) / baseline.std_deviation

    async def get_prediction(
        self,
        metric_name: str,
        labels: Dict[str, str],
        horizon_seconds: int = 3600,
    ) -> Optional[Dict[str, Any]]:
        """Predict future metric values.

        Args:
            metric_name: Name of the metric
            labels: Labels associated with the metric
            horizon_seconds: How far into the future to predict

        Returns:
            Prediction dictionary with predicted value and confidence interval
        """
        baseline = self._get_baseline(metric_name, labels)

        if baseline is None:
            return None

        # Simple linear prediction based on trend
        # This can be extended with more sophisticated models

        prediction = {
            "predicted_value": baseline.mean_value,
            "lower_bound": baseline.mean_value - (self.settings.sensitivity * baseline.std_deviation),
            "upper_bound": baseline.mean_value + (self.settings.sensitivity * baseline.std_deviation),
            "confidence": 0.95,
            "baseline_mean": baseline.mean_value,
            "baseline_std": baseline.std_deviation,
        }

        return prediction

    def detect_seasonal_patterns(
        self,
        metric_name: str,
        labels: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """Detect seasonal patterns in metric data."""
        import json

        db_session = get_db_session()
        try:
            labels_json = json.dumps(labels)

            # Get baselines for different time periods
            hourly_baselines = db_session.query(BaselineMetric).filter(
                BaselineMetric.metric_name == metric_name,
                BaselineMetric.labels == labels_json,
                BaselineMetric.hour_of_day.isnot(None)
            ).all()

            if not hourly_baselines:
                return None

            # Group by hour of day
            hourly_patterns = defaultdict(list)
            for baseline in hourly_baselines:
                if baseline.hour_of_day is not None:
                    hourly_patterns[baseline.hour_of_day].append(
                        baseline.mean_value)

            # Calculate average for each hour
            hourly_averages = {
                hour: sum(values) / len(values)
                for hour, values in hourly_patterns.items()
            }

            # Find peak hours
            peak_hour = max(
                hourly_averages, key=hourly_averages.get) if hourly_averages else None
            low_hour = min(
                hourly_averages, key=hourly_averages.get) if hourly_averages else None

            return {
                "hourly_patterns": hourly_averages,
                "peak_hour": peak_hour,
                "low_hour": low_hour,
                "variation_coefficient": (
                    std_dev := (sum((v - sum(hourly_averages.values()) / len(hourly_averages)) ** 2
                                    for v in hourly_averages.values()) / len(hourly_averages)) ** 0.5 /
                    (sum(hourly_averages.values()) / len(hourly_averages))
                    if hourly_averages else 0
                ),
            }

        finally:
            db_session.close()


# Global detector instance
_anomaly_detector: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create global anomaly detector instance."""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector
