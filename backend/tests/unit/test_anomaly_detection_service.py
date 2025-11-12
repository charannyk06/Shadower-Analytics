"""Unit tests for anomaly detection service."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.services.analytics.anomaly_detection import AnomalyDetectionService


class TestAnomalyDetectionService:
    """Test suite for AnomalyDetectionService."""

    def test_calculate_zscore_valid(self):
        """Test z-score calculation with valid inputs."""
        score = AnomalyDetectionService.calculate_zscore(
            value=15.0,
            mean=10.0,
            std_dev=2.0
        )
        assert score == 2.5

    def test_calculate_zscore_negative_deviation(self):
        """Test z-score with value below mean."""
        score = AnomalyDetectionService.calculate_zscore(
            value=5.0,
            mean=10.0,
            std_dev=2.0
        )
        assert score == 2.5  # Should be absolute value

    def test_calculate_zscore_zero_std_raises_error(self):
        """Test z-score raises error with zero std dev."""
        with pytest.raises(ValueError, match="Standard deviation must be positive"):
            AnomalyDetectionService.calculate_zscore(
                value=10.0,
                mean=10.0,
                std_dev=0.0
            )

    def test_detect_zscore_anomalies_global(self):
        """Test global z-score anomaly detection."""
        # Create data with clear outlier
        data = pd.Series(
            [10, 11, 10, 9, 11, 10, 50],  # 50 is clear outlier
            index=pd.date_range('2024-01-01', periods=7, freq='D')
        )

        anomalies = AnomalyDetectionService.detect_zscore_anomalies(
            data=data,
            sensitivity=2.0
        )

        assert len(anomalies) == 1
        assert anomalies[0]['value'] == 50
        assert anomalies[0]['score'] > 2.0
        assert anomalies[0]['method'] == 'zscore_global'

    def test_detect_zscore_anomalies_rolling(self):
        """Test rolling window z-score anomaly detection."""
        # Create data with local spike
        data = pd.Series(
            [10, 10, 10, 25, 10, 10, 10],  # Local spike at index 3
            index=pd.date_range('2024-01-01', periods=7, freq='D')
        )

        anomalies = AnomalyDetectionService.detect_zscore_anomalies(
            data=data,
            sensitivity=2.0,
            window=3
        )

        assert len(anomalies) > 0
        # Should detect the spike
        spike_detected = any(a['value'] == 25 for a in anomalies)
        assert spike_detected

    def test_detect_zscore_anomalies_insufficient_data(self):
        """Test z-score detection with insufficient data."""
        data = pd.Series([10, 11])  # Only 2 points

        anomalies = AnomalyDetectionService.detect_zscore_anomalies(
            data=data,
            sensitivity=2.0
        )

        assert len(anomalies) == 0  # Should return empty list

    def test_detect_isolation_forest_anomalies(self):
        """Test isolation forest anomaly detection."""
        # Create multivariate data with outlier
        np.random.seed(42)
        normal_data = np.random.normal(10, 2, (100, 2))
        outlier = np.array([[50, 50]])
        data_array = np.vstack([normal_data, outlier])

        df = pd.DataFrame(
            data_array,
            columns=['feature1', 'feature2'],
            index=pd.date_range('2024-01-01', periods=101, freq='H')
        )

        anomalies = AnomalyDetectionService.detect_isolation_forest_anomalies(
            data=df,
            contamination=0.01,
            n_estimators=50
        )

        assert len(anomalies) >= 1
        # The outlier should be detected
        assert any(a['score'] > 0 for a in anomalies)

    def test_detect_isolation_forest_insufficient_data(self):
        """Test isolation forest with insufficient data."""
        df = pd.DataFrame(
            {'feature1': [1, 2, 3]},
            index=pd.date_range('2024-01-01', periods=3, freq='D')
        )

        anomalies = AnomalyDetectionService.detect_isolation_forest_anomalies(
            data=df,
            contamination=0.1
        )

        assert len(anomalies) == 0  # Should return empty list

    def test_calculate_anomaly_score_zscore(self):
        """Test anomaly score calculation with z-score method."""
        score = AnomalyDetectionService.calculate_anomaly_score(
            value=15.0,
            mean=10.0,
            std_dev=2.0,
            method="zscore"
        )
        assert score == 2.5

    def test_calculate_anomaly_score_percentile(self):
        """Test anomaly score calculation with percentile method."""
        score = AnomalyDetectionService.calculate_anomaly_score(
            value=15.0,
            mean=10.0,
            std_dev=2.0,
            method="percentile"
        )
        assert score == 5.0  # abs(15 - 10)

    def test_calculate_anomaly_score_unknown_method(self):
        """Test anomaly score with unknown method raises error."""
        with pytest.raises(ValueError, match="Unknown scoring method"):
            AnomalyDetectionService.calculate_anomaly_score(
                value=15.0,
                mean=10.0,
                std_dev=2.0,
                method="unknown"
            )

    def test_determine_severity_low(self):
        """Test severity determination for low anomaly."""
        severity = AnomalyDetectionService.determine_severity(2.1)
        assert severity == 'low'

    def test_determine_severity_medium(self):
        """Test severity determination for medium anomaly."""
        severity = AnomalyDetectionService.determine_severity(2.7)
        assert severity == 'medium'

    def test_determine_severity_high(self):
        """Test severity determination for high anomaly."""
        severity = AnomalyDetectionService.determine_severity(3.2)
        assert severity == 'high'

    def test_determine_severity_critical(self):
        """Test severity determination for critical anomaly."""
        severity = AnomalyDetectionService.determine_severity(4.5)
        assert severity == 'critical'

    @pytest.mark.asyncio
    async def test_detect_metric_anomalies_invalid_metric(self):
        """Test detection with invalid metric type."""
        mock_db = AsyncMock()
        service = AnomalyDetectionService(db=mock_db)

        with pytest.raises(ValueError, match="Invalid metric type"):
            await service.detect_metric_anomalies(
                metric_type="invalid_metric",
                workspace_id="test-workspace",
                lookback_days=30
            )

    @pytest.mark.asyncio
    async def test_detect_metric_anomalies_no_database(self):
        """Test detection without database session."""
        service = AnomalyDetectionService()  # No DB session

        with pytest.raises(ValueError, match="Database session required"):
            await service.detect_metric_anomalies(
                metric_type="runtime_seconds",
                workspace_id="test-workspace",
                lookback_days=30
            )

    @pytest.mark.asyncio
    async def test_detect_metric_anomalies_invalid_lookback(self):
        """Test detection with invalid lookback days."""
        mock_db = AsyncMock()
        service = AnomalyDetectionService(db=mock_db)

        with pytest.raises(ValueError, match="lookback_days must be between"):
            await service.detect_metric_anomalies(
                metric_type="runtime_seconds",
                workspace_id="test-workspace",
                lookback_days=400  # Exceeds MAX_LOOKBACK_DAYS
            )

    @pytest.mark.asyncio
    async def test_detect_metric_anomalies_success(self):
        """Test successful metric anomaly detection."""
        mock_db = AsyncMock()

        # Mock database query result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (datetime(2024, 1, 1, i), 10.0 + (5.0 if i == 12 else 0), 1)
            for i in range(24)
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = AnomalyDetectionService(db=mock_db)

        anomalies = await service.detect_metric_anomalies(
            metric_type="runtime_seconds",
            workspace_id="test-workspace",
            lookback_days=7,
            sensitivity=2.0,
            method="zscore"
        )

        assert isinstance(anomalies, list)
        # Should detect the spike at hour 12
        assert len(anomalies) >= 1

    @pytest.mark.asyncio
    async def test_detect_usage_spikes(self):
        """Test usage spike detection."""
        mock_db = AsyncMock()

        # Mock database query result with spike
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (datetime(2024, 1, 1, i), 100.0 + (500.0 if i == 15 else 0), 1)
            for i in range(24)
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = AnomalyDetectionService(db=mock_db)

        anomalies = await service.detect_usage_spikes(
            workspace_id="test-workspace",
            sensitivity=2.5,
            window_hours=24
        )

        assert isinstance(anomalies, list)

    @pytest.mark.asyncio
    async def test_detect_error_patterns_no_data(self):
        """Test error pattern detection with no data."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = AnomalyDetectionService(db=mock_db)

        anomalies = await service.detect_error_patterns(
            workspace_id="test-workspace",
            window_hours=24
        )

        assert anomalies == []

    @pytest.mark.asyncio
    async def test_train_baseline_model_invalid_metric(self):
        """Test baseline training with invalid metric."""
        mock_db = AsyncMock()
        service = AnomalyDetectionService(db=mock_db)

        with pytest.raises(ValueError, match="Invalid metric type"):
            await service.train_baseline_model(
                metric_type="invalid_metric",
                workspace_id="test-workspace",
                training_days=90
            )

    @pytest.mark.asyncio
    async def test_train_baseline_model_no_data(self):
        """Test baseline training with no data."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = AnomalyDetectionService(db=mock_db)

        with pytest.raises(ValueError, match="No training data available"):
            await service.train_baseline_model(
                metric_type="runtime_seconds",
                workspace_id="test-workspace",
                training_days=90
            )

    @pytest.mark.asyncio
    async def test_train_baseline_model_success(self):
        """Test successful baseline model training."""
        mock_db = AsyncMock()

        # Mock database query result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (datetime(2024, 1, 1) + timedelta(hours=i), 10.0 + np.random.randn())
            for i in range(100)
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        service = AnomalyDetectionService(db=mock_db)

        result = await service.train_baseline_model(
            metric_type="runtime_seconds",
            workspace_id="test-workspace",
            training_days=90,
            model_type="zscore"
        )

        assert 'model_id' in result
        assert 'statistics' in result
        assert 'mean' in result['statistics']
        assert 'std' in result['statistics']
        assert result['metric_type'] == 'runtime_seconds'

    def test_service_initialization_without_db(self):
        """Test service can be initialized without database."""
        service = AnomalyDetectionService()
        assert service.db is None
        assert service.models == {}
        assert service.thresholds == {}

    def test_service_initialization_with_db(self):
        """Test service initialization with database."""
        mock_db = MagicMock()
        service = AnomalyDetectionService(db=mock_db)
        assert service.db == mock_db

    def test_valid_metrics_whitelist(self):
        """Test that VALID_METRICS contains expected metrics."""
        expected_metrics = [
            'runtime_seconds',
            'credits_consumed',
            'tokens_used',
            'executions',
            'error_rate',
            'success_rate',
            'user_activity',
            'api_latency'
        ]

        for metric in expected_metrics:
            assert metric in AnomalyDetectionService.VALID_METRICS

    def test_severity_thresholds_defined(self):
        """Test severity thresholds are properly defined."""
        thresholds = AnomalyDetectionService.SEVERITY_THRESHOLDS

        assert 'low' in thresholds
        assert 'medium' in thresholds
        assert 'high' in thresholds
        assert 'critical' in thresholds

        # Verify ordering (critical should be highest)
        assert thresholds['low'] < thresholds['medium']
        assert thresholds['medium'] < thresholds['high']
        assert thresholds['high'] < thresholds['critical']

    def test_performance_limits_defined(self):
        """Test performance limits are defined."""
        assert hasattr(AnomalyDetectionService, 'MAX_DATA_POINTS')
        assert hasattr(AnomalyDetectionService, 'MAX_LOOKBACK_DAYS')
        assert AnomalyDetectionService.MAX_DATA_POINTS > 0
        assert AnomalyDetectionService.MAX_LOOKBACK_DAYS > 0


class TestAnomalyDetectionEdgeCases:
    """Test edge cases and error handling."""

    def test_zscore_with_constant_values(self):
        """Test z-score detection with constant values (no variance)."""
        data = pd.Series(
            [10, 10, 10, 10, 10],
            index=pd.date_range('2024-01-01', periods=5, freq='D')
        )

        anomalies = AnomalyDetectionService.detect_zscore_anomalies(
            data=data,
            sensitivity=2.0
        )

        # Should return empty as std = 0
        assert len(anomalies) == 0

    def test_isolation_forest_with_nan_values(self):
        """Test isolation forest handles NaN values."""
        df = pd.DataFrame({
            'feature1': [1, 2, np.nan, 4, 5],
            'feature2': [10, 20, 30, np.nan, 50]
        }, index=pd.date_range('2024-01-01', periods=5, freq='D'))

        # Should handle NaN by filling with mean
        anomalies = AnomalyDetectionService.detect_isolation_forest_anomalies(
            data=df,
            contamination=0.2
        )

        # Should not raise error
        assert isinstance(anomalies, list)

    def test_zscore_with_single_value(self):
        """Test z-score detection with single data point."""
        data = pd.Series(
            [10],
            index=pd.date_range('2024-01-01', periods=1, freq='D')
        )

        anomalies = AnomalyDetectionService.detect_zscore_anomalies(
            data=data,
            sensitivity=2.0
        )

        assert len(anomalies) == 0

    def test_detect_zscore_high_sensitivity(self):
        """Test z-score with very high sensitivity (few anomalies)."""
        data = pd.Series(
            [10, 11, 12, 13, 14],
            index=pd.date_range('2024-01-01', periods=5, freq='D')
        )

        anomalies = AnomalyDetectionService.detect_zscore_anomalies(
            data=data,
            sensitivity=10.0  # Very high, should detect nothing
        )

        assert len(anomalies) == 0

    def test_detect_zscore_low_sensitivity(self):
        """Test z-score with low sensitivity (more anomalies)."""
        data = pd.Series(
            [10, 12, 14, 16, 18, 20],
            index=pd.date_range('2024-01-01', periods=6, freq='D')
        )

        anomalies = AnomalyDetectionService.detect_zscore_anomalies(
            data=data,
            sensitivity=0.5  # Very low, should detect multiple
        )

        # Low sensitivity should detect more anomalies
        assert len(anomalies) > 0
