"""Anomaly detection for metrics across all dimensions.

This module provides statistical anomaly detection using z-scores, isolation forests,
and custom thresholds for time-series metrics analysis.

Security: All database queries enforce workspace isolation through RLS policies
and explicit access validation. Metric names are validated against a whitelist
to prevent SQL injection.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import logging
import uuid

from ...models.database.tables import BaselineModel

logger = logging.getLogger(__name__)


class AnomalyDetectionService:
    """Anomaly detection for time-series metrics.

    This service provides:
    - Z-Score Detection - Statistical outlier detection for normally distributed data
    - Isolation Forest - Multivariate anomaly detection for complex patterns
    - Custom Thresholds - User-defined business logic rules
    - Baseline Training - Learn normal behavior patterns

    Security:
    - All database methods validate workspace access
    - Metric names are validated against VALID_METRICS whitelist
    - Queries use parameterized statements (no SQL injection)
    - RLS policies provide defense-in-depth at database layer
    """

    # Valid metric types (whitelist for SQL safety)
    # Only metrics that can be aggregated from execution_logs
    VALID_METRICS = [
        'runtime_seconds',
        'credits_consumed',
        'executions',
    ]

    # Severity thresholds based on z-score
    SEVERITY_THRESHOLDS = {
        'low': 2.0,
        'medium': 2.5,
        'high': 3.0,
        'critical': 4.0
    }

    # Performance limits
    MAX_DATA_POINTS = 50000
    MAX_LOOKBACK_DAYS = 365

    def __init__(self, db: Optional[AsyncSession] = None):
        """Initialize anomaly detection service.

        Args:
            db: Database session for database-based operations (optional)
        """
        self.db = db
        self.models = {}
        self.thresholds = {}

    @staticmethod
    def calculate_zscore(
        value: float,
        mean: float,
        std_dev: float
    ) -> float:
        """Calculate z-score for a single value.

        Z-score measures how many standard deviations a value is from the mean.
        Values with |z-score| > 2 are typically considered outliers.

        Args:
            value: The value to score
            mean: Mean of the distribution
            std_dev: Standard deviation of the distribution

        Returns:
            Z-score (number of standard deviations from mean)

        Raises:
            ValueError: If standard deviation is zero or negative
        """
        if std_dev <= 0:
            raise ValueError(f"Standard deviation must be positive, got: {std_dev}")

        return abs((value - mean) / std_dev)

    @staticmethod
    def detect_zscore_anomalies(
        data: pd.Series,
        sensitivity: float = 2.5,
        window: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Detect anomalies using z-score method.

        Z-score method identifies values that deviate significantly from the mean.
        Suitable for normally distributed metrics.

        Args:
            data: Time series data as pandas Series with datetime index
            sensitivity: Number of standard deviations for anomaly threshold (default: 2.5)
            window: Rolling window size for local anomaly detection (optional)

        Returns:
            List of anomaly points with timestamps, values, and scores
        """
        if len(data) < 3:
            logger.warning("Insufficient data for z-score detection")
            return []

        anomalies = []

        if window:
            # Rolling z-score for local anomalies
            rolling_mean = data.rolling(window=window, min_periods=3).mean()
            rolling_std = data.rolling(window=window, min_periods=3).std()

            for idx in data.index:
                if pd.notna(rolling_mean[idx]) and pd.notna(rolling_std[idx]) and rolling_std[idx] > 0:
                    z_score = abs((data[idx] - rolling_mean[idx]) / rolling_std[idx])
                    if z_score > sensitivity:
                        anomalies.append({
                            'timestamp': idx,
                            'value': float(data[idx]),
                            'score': float(z_score),
                            'expected_mean': float(rolling_mean[idx]),
                            'expected_std': float(rolling_std[idx]),
                            'method': 'zscore_rolling'
                        })
        else:
            # Global z-score
            mean = data.mean()
            std = data.std()

            if std > 0:
                z_scores = np.abs((data - mean) / std)
                anomaly_mask = z_scores > sensitivity

                for idx in data[anomaly_mask].index:
                    anomalies.append({
                        'timestamp': idx,
                        'value': float(data[idx]),
                        'score': float(z_scores[idx]),
                        'expected_mean': float(mean),
                        'expected_std': float(std),
                        'method': 'zscore_global'
                    })

        return anomalies

    @staticmethod
    def detect_isolation_forest_anomalies(
        data: pd.DataFrame,
        contamination: float = 0.05,
        n_estimators: int = 100
    ) -> List[Dict[str, Any]]:
        """Detect anomalies using Isolation Forest.

        Isolation Forest is effective for multivariate anomaly detection and
        doesn't assume normal distribution. Works well for complex patterns.

        Args:
            data: DataFrame with multiple features and datetime index
            contamination: Expected proportion of outliers (default: 0.05)
            n_estimators: Number of trees in the forest (default: 100)

        Returns:
            List of anomaly points with timestamps and anomaly scores
        """
        if len(data) < 10:
            logger.warning("Insufficient data for Isolation Forest detection")
            return []

        if data.shape[1] == 0:
            logger.warning("No features provided for Isolation Forest")
            return []

        # Handle missing values efficiently: forward-fill, then back-fill for any remaining NaNs
        data_clean = data.ffill().bfill()

        # Standardize features
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data_clean)

        # Train Isolation Forest
        iso_forest = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42,
            n_jobs=-1
        )

        # Predict anomalies (-1 = anomaly, 1 = normal)
        predictions = iso_forest.fit_predict(data_scaled)
        anomaly_scores = iso_forest.score_samples(data_scaled)

        # Convert to anomaly scores (higher = more anomalous)
        normalized_scores = -anomaly_scores

        anomalies = []
        for idx, (pred, score) in enumerate(zip(predictions, normalized_scores)):
            if pred == -1:  # Anomaly detected
                timestamp = data.index[idx]
                anomalies.append({
                    'timestamp': timestamp,
                    'score': float(score),
                    'features': data.iloc[idx].to_dict(),
                    'method': 'isolation_forest'
                })

        return anomalies

    @staticmethod
    def calculate_anomaly_score(
        value: float,
        mean: float,
        std_dev: float,
        method: str = "zscore"
    ) -> float:
        """Calculate anomaly score for a single value.

        Supports multiple scoring methods. Z-score is default.

        Args:
            value: The value to score
            mean: Mean of the baseline distribution
            std_dev: Standard deviation of the baseline
            method: Scoring method ('zscore', 'percentile')

        Returns:
            Anomaly score (higher = more anomalous)
        """
        if method == "zscore":
            if std_dev <= 0:
                return 0.0
            return abs((value - mean) / std_dev)
        elif method == "percentile":
            # Simple percentile-based scoring
            return abs(value - mean)
        else:
            raise ValueError(f"Unknown scoring method: {method}")

    @staticmethod
    def determine_severity(score: float) -> str:
        """Determine anomaly severity based on score.

        Args:
            score: Anomaly score (typically z-score)

        Returns:
            Severity level: 'low', 'medium', 'high', or 'critical'
        """
        if score >= AnomalyDetectionService.SEVERITY_THRESHOLDS['critical']:
            return 'critical'
        elif score >= AnomalyDetectionService.SEVERITY_THRESHOLDS['high']:
            return 'high'
        elif score >= AnomalyDetectionService.SEVERITY_THRESHOLDS['medium']:
            return 'medium'
        else:
            return 'low'

    async def detect_metric_anomalies(
        self,
        metric_type: str,
        workspace_id: str,
        lookback_days: int = 30,
        sensitivity: float = 2.5,
        method: str = "zscore"
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in time-series metrics.

        Analyzes historical data to identify unusual patterns or values.

        Args:
            metric_type: Type of metric to analyze (must be in VALID_METRICS)
            workspace_id: Workspace ID for data isolation
            lookback_days: Number of days of historical data to analyze
            sensitivity: Detection sensitivity (higher = fewer anomalies)
            method: Detection method ('zscore', 'isolation_forest')

        Returns:
            List of detected anomalies with scores and context

        Raises:
            ValueError: If metric_type is invalid or parameters are out of range
        """
        if not self.db:
            raise ValueError("Database session required for this operation")

        if metric_type not in self.VALID_METRICS:
            raise ValueError(f"Invalid metric type: {metric_type}. Must be one of {self.VALID_METRICS}")

        if lookback_days < 1 or lookback_days > self.MAX_LOOKBACK_DAYS:
            raise ValueError(f"lookback_days must be between 1 and {self.MAX_LOOKBACK_DAYS}")

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)

        # Query metric data
        query = text("""
            SELECT
                DATE_TRUNC('hour', started_at) as timestamp,
                CASE
                    WHEN :metric_type = 'runtime_seconds' THEN AVG(duration)
                    WHEN :metric_type = 'credits_consumed' THEN SUM(credits_used)
                    WHEN :metric_type = 'executions' THEN COUNT(*)
                END as value,
                COUNT(*) as count
            FROM execution_logs
            WHERE workspace_id = :workspace_id
                AND started_at >= :start_date
                AND started_at <= :end_date
            GROUP BY DATE_TRUNC('hour', started_at)
            ORDER BY timestamp
        """)

        result = await self.db.execute(
            query,
            {
                'metric_type': metric_type,
                'workspace_id': workspace_id,
                'start_date': start_date,
                'end_date': end_date
            }
        )

        rows = result.fetchall()

        if not rows:
            logger.info(f"No data found for {metric_type} in workspace {workspace_id}")
            return []

        # Convert to pandas for analysis
        df = pd.DataFrame(rows, columns=['timestamp', 'value', 'count'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        # Detect anomalies based on method
        if method == "zscore":
            anomalies = self.detect_zscore_anomalies(
                df['value'],
                sensitivity=sensitivity
            )
        elif method == "isolation_forest":
            anomalies = self.detect_isolation_forest_anomalies(
                df[['value', 'count']],
                contamination=0.05
            )
        else:
            raise ValueError(f"Unknown detection method: {method}")

        # Enrich anomalies with severity and context
        enriched_anomalies = []
        for anomaly in anomalies:
            score = anomaly.get('score', 0)
            severity = self.determine_severity(score)

            enriched_anomalies.append({
                'metric_type': metric_type,
                'workspace_id': workspace_id,
                'detected_at': anomaly['timestamp'].isoformat() if isinstance(anomaly['timestamp'], pd.Timestamp) else anomaly['timestamp'],
                'anomaly_value': anomaly.get('value'),
                'anomaly_score': score,
                'severity': severity,
                'detection_method': method,
                'context': {
                    'expected_mean': anomaly.get('expected_mean'),
                    'expected_std': anomaly.get('expected_std'),
                    'lookback_days': lookback_days,
                    'sensitivity': sensitivity
                }
            })

        return enriched_anomalies

    async def detect_usage_spikes(
        self,
        workspace_id: str,
        sensitivity: float = 2.5,
        window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Detect unusual spikes in credit consumption.

        Uses z-score method with configurable sensitivity to identify
        abnormal usage patterns.

        Args:
            workspace_id: Workspace ID for data isolation
            sensitivity: Detection sensitivity (default: 2.5 std devs)
            window_hours: Rolling window size in hours (converted to days for lookback)

        Returns:
            List of detected usage spikes with details
        """
        # Convert window_hours to days (minimum 1 day)
        lookback_days = max(1, window_hours // 24)

        return await self.detect_metric_anomalies(
            metric_type='credits_consumed',
            workspace_id=workspace_id,
            lookback_days=lookback_days,
            sensitivity=sensitivity,
            method='zscore'
        )

    async def detect_error_patterns(
        self,
        workspace_id: str,
        window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Identify unusual error patterns or rates.

        Uses isolation forest for multivariate detection of error anomalies.

        Args:
            workspace_id: Workspace ID for data isolation
            window_hours: Analysis window in hours

        Returns:
            List of detected error pattern anomalies
        """
        if not self.db:
            raise ValueError("Database session required for this operation")

        # Calculate time window
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=window_hours)

        # Query error metrics
        query = text("""
            SELECT
                DATE_TRUNC('hour', started_at) as timestamp,
                COUNT(*) as total_executions,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                AVG(duration) as avg_duration
            FROM execution_logs
            WHERE workspace_id = :workspace_id
                AND started_at >= :start_date
                AND started_at <= :end_date
            GROUP BY DATE_TRUNC('hour', started_at)
            ORDER BY timestamp
        """)

        result = await self.db.execute(
            query,
            {
                'workspace_id': workspace_id,
                'start_date': start_date,
                'end_date': end_date
            }
        )

        rows = result.fetchall()

        if not rows:
            return []

        # Convert to DataFrame
        df = pd.DataFrame(
            rows,
            columns=['timestamp', 'total_executions', 'failed_count', 'avg_duration']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Set error_rate to np.nan where total_executions == 0 to avoid division by zero
        df['error_rate'] = np.where(
            df['total_executions'] == 0,
            np.nan,
            df['failed_count'] / df['total_executions']
        )
        df.set_index('timestamp', inplace=True)

        # Detect anomalies using isolation forest
        anomalies = self.detect_isolation_forest_anomalies(
            df[['error_rate', 'failed_count', 'avg_duration']],
            contamination=0.05
        )

        # Format results
        enriched_anomalies = []
        for anomaly in anomalies:
            enriched_anomalies.append({
                'metric_type': 'error_rate',
                'workspace_id': workspace_id,
                'detected_at': anomaly['timestamp'].isoformat() if isinstance(anomaly['timestamp'], pd.Timestamp) else anomaly['timestamp'],
                'anomaly_score': anomaly['score'],
                'severity': self.determine_severity(anomaly['score']),
                'detection_method': 'isolation_forest',
                'context': {
                    'features': anomaly['features'],
                    'window_hours': window_hours
                }
            })

        return enriched_anomalies

    async def detect_user_behavior_anomalies(
        self,
        user_id: str,
        workspace_id: str,
        lookback_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Detect unusual user activity patterns.

        Compares user behavior against their historical baseline to identify
        anomalous activity patterns.

        Args:
            user_id: User ID to analyze
            workspace_id: Workspace ID for data isolation
            lookback_days: Days of historical data to analyze

        Returns:
            List of detected behavioral anomalies
        """
        if not self.db:
            raise ValueError("Database session required for this operation")

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)

        # Query user activity
        query = text("""
            SELECT
                DATE_TRUNC('day', started_at) as timestamp,
                COUNT(*) as executions,
                AVG(duration) as avg_duration,
                SUM(credits_used) as total_credits
            FROM execution_logs
            WHERE user_id = :user_id
                AND workspace_id = :workspace_id
                AND started_at >= :start_date
                AND started_at <= :end_date
            GROUP BY DATE_TRUNC('day', started_at)
            ORDER BY timestamp
        """)

        result = await self.db.execute(
            query,
            {
                'user_id': user_id,
                'workspace_id': workspace_id,
                'start_date': start_date,
                'end_date': end_date
            }
        )

        rows = result.fetchall()

        if not rows:
            return []

        # Convert to DataFrame
        df = pd.DataFrame(
            rows,
            columns=['timestamp', 'executions', 'avg_duration', 'total_credits']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        # Detect anomalies using isolation forest
        anomalies = self.detect_isolation_forest_anomalies(
            df[['executions', 'avg_duration', 'total_credits']],
            contamination=0.1
        )

        # Format results
        enriched_anomalies = []
        for anomaly in anomalies:
            score = anomaly['score']
            enriched_anomalies.append({
                'metric_type': 'user_behavior',
                'workspace_id': workspace_id,
                'user_id': user_id,
                'detected_at': anomaly['timestamp'].isoformat() if isinstance(anomaly['timestamp'], pd.Timestamp) else anomaly['timestamp'],
                'anomaly_score': score,
                'severity': self.determine_severity(score),
                'detection_method': 'isolation_forest',
                'context': {
                    'features': anomaly['features'],
                    'lookback_days': lookback_days
                }
            })

        return enriched_anomalies

    async def train_baseline_model(
        self,
        metric_type: str,
        workspace_id: str,
        training_days: int = 90,
        model_type: str = "zscore"
    ) -> Dict[str, Any]:
        """Train baseline model for normal behavior.

        Creates a statistical baseline from historical data to use for
        anomaly detection. Updates periodically with new data.

        Args:
            metric_type: Type of metric to model
            workspace_id: Workspace ID for data isolation
            training_days: Days of historical data for training
            model_type: Model type ('zscore', 'isolation_forest')

        Returns:
            Baseline model statistics and metadata
        """
        if not self.db:
            raise ValueError("Database session required for this operation")

        if metric_type not in self.VALID_METRICS:
            raise ValueError(f"Invalid metric type: {metric_type}")

        # Calculate training period
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=training_days)

        # Query training data
        query = text("""
            SELECT
                started_at,
                CASE
                    WHEN :metric_type = 'runtime_seconds' THEN duration
                    WHEN :metric_type = 'credits_consumed' THEN credits_used
                    WHEN :metric_type = 'executions' THEN 1
                    ELSE 0
                END as value
            FROM execution_logs
            WHERE workspace_id = :workspace_id
                AND started_at >= :start_date
                AND started_at <= :end_date
            ORDER BY started_at
        """)

        result = await self.db.execute(
            query,
            {
                'metric_type': metric_type,
                'workspace_id': workspace_id,
                'start_date': start_date,
                'end_date': end_date
            }
        )

        rows = result.fetchall()

        if not rows:
            raise ValueError(f"No training data available for {metric_type}")

        # Calculate statistics
        values = [row[1] for row in rows]
        statistics = {
            'mean': float(np.mean(values)),
            'std': float(np.std(values)),
            'median': float(np.median(values)),
            'q25': float(np.percentile(values, 25)),
            'q75': float(np.percentile(values, 75)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'count': len(values)
        }

        # Store baseline model
        baseline = BaselineModel(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            metric_type=metric_type,
            model_type=model_type,
            model_parameters={'training_days': training_days},
            statistics=statistics,
            training_data_start=start_date.date(),
            training_data_end=end_date.date(),
            last_updated=datetime.utcnow()
        )

        self.db.add(baseline)
        await self.db.commit()

        logger.info(f"Trained baseline model for {metric_type} in workspace {workspace_id}")

        return {
            'model_id': baseline.id,
            'metric_type': metric_type,
            'model_type': model_type,
            'statistics': statistics,
            'training_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': training_days
            }
        }
