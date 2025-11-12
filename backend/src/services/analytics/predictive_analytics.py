"""
Predictive Analytics Service

Implements machine learning models to predict future metrics including credit consumption,
user churn, error rates, and growth trajectories.

Author: Claude Code
Date: 2025-11-12
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
import json

import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_percentage_error, roc_auc_score
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX

from backend.src.core.config import settings
from backend.src.services.cache.cache_service import CacheService

logger = logging.getLogger(__name__)


class PredictiveAnalytics:
    """
    Main predictive analytics service that orchestrates various prediction models.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = CacheService()
        self.models = {}
        self.feature_extractors = {}

    async def predict_credit_consumption(
        self,
        workspace_id: str,
        days_ahead: int = 30,
        granularity: str = "daily"
    ) -> Dict[str, Any]:
        """
        Predict future credit consumption using Prophet/ARIMA ensemble.

        Args:
            workspace_id: Workspace identifier
            days_ahead: Number of days to predict ahead
            granularity: Prediction granularity (daily, weekly)

        Returns:
            Dictionary with predictions and confidence intervals
        """
        try:
            # Check cache first
            cache_key = f"credit_consumption_prediction:{workspace_id}:{days_ahead}:{granularity}"
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for credit consumption prediction: {workspace_id}")
                return json.loads(cached)

            # Load historical credit consumption data
            historical_data = await self._load_credit_consumption_data(workspace_id)

            if len(historical_data) < 30:
                return {
                    "error": "Insufficient data",
                    "message": "At least 30 days of historical data required",
                    "predictions": []
                }

            # Use CreditConsumptionPredictor
            predictor = CreditConsumptionPredictor(self.db)
            predictions = await predictor.predict(
                workspace_id=workspace_id,
                days_ahead=days_ahead,
                historical_data=historical_data,
                granularity=granularity
            )

            # Cache for 6 hours
            await self.cache.set(cache_key, json.dumps(predictions), ttl=21600)

            return predictions

        except Exception as e:
            logger.error(f"Error predicting credit consumption: {e}", exc_info=True)
            raise

    async def predict_user_churn(
        self,
        workspace_id: str,
        users: Optional[List[str]] = None,
        risk_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Predict probability of user churn in next 30 days.
        Uses gradient boosting with behavioral features.

        Args:
            workspace_id: Workspace identifier
            users: Optional list of specific user IDs to predict
            risk_threshold: Threshold for high-risk classification

        Returns:
            Dictionary with user churn predictions
        """
        try:
            # Check cache
            cache_key = f"churn_prediction:{workspace_id}:{risk_threshold}"
            if users:
                cache_key += f":{','.join(sorted(users[:10]))}"  # Limit cache key size

            cached = await self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for churn prediction: {workspace_id}")
                return json.loads(cached)

            # Load user behavioral data
            user_data = await self._load_user_behavioral_data(workspace_id, users)

            if len(user_data) == 0:
                return {
                    "error": "No user data found",
                    "predictions": []
                }

            # Use UserChurnPredictor
            predictor = UserChurnPredictor(self.db)
            predictions = await predictor.predict(
                workspace_id=workspace_id,
                user_data=user_data,
                risk_threshold=risk_threshold
            )

            # Cache for 1 hour (churn risk changes frequently)
            await self.cache.set(cache_key, json.dumps(predictions), ttl=3600)

            return predictions

        except Exception as e:
            logger.error(f"Error predicting user churn: {e}", exc_info=True)
            raise

    async def predict_growth_metrics(
        self,
        workspace_id: str,
        metric: str,
        horizon_days: int = 90
    ) -> Dict[str, Any]:
        """
        Predict growth trajectory for DAU/WAU/MAU.
        Uses ensemble of time-series models.

        Args:
            workspace_id: Workspace identifier
            metric: Metric to predict (dau, wau, mau, mrr)
            horizon_days: Prediction horizon in days

        Returns:
            Dictionary with growth predictions and scenarios
        """
        try:
            # Validate metric
            valid_metrics = ['dau', 'wau', 'mau', 'mrr', 'active_users']
            if metric not in valid_metrics:
                raise ValueError(f"Invalid metric. Must be one of: {valid_metrics}")

            # Check cache
            cache_key = f"growth_prediction:{workspace_id}:{metric}:{horizon_days}"
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for growth prediction: {workspace_id}")
                return json.loads(cached)

            # Load historical growth data
            historical_data = await self._load_growth_data(workspace_id, metric)

            if len(historical_data) < 30:
                return {
                    "error": "Insufficient data",
                    "message": "At least 30 days of historical data required",
                    "predictions": []
                }

            # Use GrowthMetricsPredictor
            predictor = GrowthMetricsPredictor(self.db)
            predictions = await predictor.predict(
                workspace_id=workspace_id,
                metric=metric,
                horizon_days=horizon_days,
                historical_data=historical_data
            )

            # Cache for 12 hours
            await self.cache.set(cache_key, json.dumps(predictions), ttl=43200)

            return predictions

        except Exception as e:
            logger.error(f"Error predicting growth metrics: {e}", exc_info=True)
            raise

    async def predict_peak_usage(
        self,
        workspace_id: str,
        granularity: str = "hourly",
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """
        Predict peak usage times and capacity needs.
        Helps with resource planning.

        Args:
            workspace_id: Workspace identifier
            granularity: Time granularity (hourly, daily)
            days_ahead: Number of days to predict

        Returns:
            Dictionary with peak usage predictions
        """
        try:
            # Check cache
            cache_key = f"peak_usage_prediction:{workspace_id}:{granularity}:{days_ahead}"
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for peak usage prediction: {workspace_id}")
                return json.loads(cached)

            # Load historical usage data
            usage_data = await self._load_usage_data(workspace_id, granularity)

            if len(usage_data) < 168:  # At least 1 week of hourly data
                return {
                    "error": "Insufficient data",
                    "message": "At least 1 week of historical data required",
                    "predictions": []
                }

            # Use PeakUsagePredictor
            predictor = PeakUsagePredictor(self.db)
            predictions = await predictor.predict(
                workspace_id=workspace_id,
                granularity=granularity,
                days_ahead=days_ahead,
                historical_data=usage_data
            )

            # Cache for 3 hours
            await self.cache.set(cache_key, json.dumps(predictions), ttl=10800)

            return predictions

        except Exception as e:
            logger.error(f"Error predicting peak usage: {e}", exc_info=True)
            raise

    async def predict_error_rates(
        self,
        workspace_id: str,
        agent_id: Optional[str] = None,
        days_ahead: int = 14
    ) -> Dict[str, Any]:
        """
        Predict future error rates based on patterns.
        Identifies potential issues before they escalate.

        Args:
            workspace_id: Workspace identifier
            agent_id: Optional specific agent ID
            days_ahead: Number of days to predict

        Returns:
            Dictionary with error rate predictions
        """
        try:
            # Check cache
            cache_key = f"error_rate_prediction:{workspace_id}:{agent_id}:{days_ahead}"
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for error rate prediction: {workspace_id}")
                return json.loads(cached)

            # Load historical error data
            error_data = await self._load_error_data(workspace_id, agent_id)

            if len(error_data) < 30:
                return {
                    "error": "Insufficient data",
                    "message": "At least 30 days of historical data required",
                    "predictions": []
                }

            # Use ErrorRatePredictor
            predictor = ErrorRatePredictor(self.db)
            predictions = await predictor.predict(
                workspace_id=workspace_id,
                agent_id=agent_id,
                days_ahead=days_ahead,
                historical_data=error_data
            )

            # Cache for 2 hours
            await self.cache.set(cache_key, json.dumps(predictions), ttl=7200)

            return predictions

        except Exception as e:
            logger.error(f"Error predicting error rates: {e}", exc_info=True)
            raise

    async def extract_features(
        self,
        data: pd.DataFrame,
        feature_set: str
    ) -> pd.DataFrame:
        """
        Extract features for ML models.
        Handles time-series and behavioral features.

        Args:
            data: Input DataFrame
            feature_set: Type of features to extract

        Returns:
            DataFrame with extracted features
        """
        try:
            if feature_set == "temporal":
                return self._extract_temporal_features(data)
            elif feature_set == "behavioral":
                return self._extract_behavioral_features(data)
            elif feature_set == "engagement":
                return self._extract_engagement_features(data)
            else:
                raise ValueError(f"Unknown feature set: {feature_set}")
        except Exception as e:
            logger.error(f"Error extracting features: {e}", exc_info=True)
            raise

    def _extract_temporal_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract time-series features like lags, rolling stats, etc."""
        features = data.copy()

        # Lag features
        for lag in [1, 7, 14, 30]:
            features[f'lag_{lag}d'] = features['value'].shift(lag)

        # Rolling statistics
        for window in [7, 14, 30]:
            features[f'rolling_mean_{window}d'] = features['value'].rolling(window).mean()
            features[f'rolling_std_{window}d'] = features['value'].rolling(window).std()
            features[f'rolling_min_{window}d'] = features['value'].rolling(window).min()
            features[f'rolling_max_{window}d'] = features['value'].rolling(window).max()

        # Time-based features
        if 'date' in features.columns:
            features['day_of_week'] = pd.to_datetime(features['date']).dt.dayofweek
            features['day_of_month'] = pd.to_datetime(features['date']).dt.day
            features['month'] = pd.to_datetime(features['date']).dt.month
            features['is_weekend'] = features['day_of_week'].isin([5, 6]).astype(int)

        return features

    def _extract_behavioral_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract user behavioral features."""
        features = data.copy()

        # Engagement metrics
        if 'login_count' in features.columns:
            features['avg_daily_logins'] = features['login_count'].rolling(7).mean()
            features['login_trend'] = features['login_count'].diff()

        if 'session_duration' in features.columns:
            features['avg_session_duration'] = features['session_duration'].rolling(7).mean()
            features['session_duration_std'] = features['session_duration'].rolling(7).std()

        # Activity recency
        if 'last_active' in features.columns:
            features['days_since_active'] = (
                datetime.now() - pd.to_datetime(features['last_active'])
            ).dt.days

        return features

    def _extract_engagement_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract engagement-related features."""
        features = data.copy()

        # Feature interactions
        if 'executions' in features.columns and 'errors' in features.columns:
            features['error_rate'] = features['errors'] / (features['executions'] + 1)
            features['success_rate'] = 1 - features['error_rate']

        if 'credits_consumed' in features.columns and 'executions' in features.columns:
            features['avg_credits_per_execution'] = (
                features['credits_consumed'] / (features['executions'] + 1)
            )

        return features

    async def train_model(
        self,
        model_type: str,
        training_data: pd.DataFrame,
        hyperparameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Train predictive model with cross-validation.
        Stores model artifacts for serving.

        Args:
            model_type: Type of model to train
            training_data: Training dataset
            hyperparameters: Optional hyperparameters

        Returns:
            Dictionary with training results and metrics
        """
        try:
            if model_type == "prophet":
                return await self._train_prophet_model(training_data, hyperparameters)
            elif model_type == "arima":
                return await self._train_arima_model(training_data, hyperparameters)
            elif model_type == "gradient_boosting":
                return await self._train_gradient_boosting(training_data, hyperparameters)
            elif model_type == "random_forest":
                return await self._train_random_forest(training_data, hyperparameters)
            else:
                raise ValueError(f"Unknown model type: {model_type}")
        except Exception as e:
            logger.error(f"Error training model: {e}", exc_info=True)
            raise

    async def _train_prophet_model(
        self,
        data: pd.DataFrame,
        hyperparameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Train Facebook Prophet model."""
        try:
            # Prepare data for Prophet
            df = data[['ds', 'y']].copy()

            # Initialize Prophet with hyperparameters
            params = hyperparameters or {}
            model = Prophet(
                changepoint_prior_scale=params.get('changepoint_prior_scale', 0.05),
                seasonality_prior_scale=params.get('seasonality_prior_scale', 10.0),
                seasonality_mode=params.get('seasonality_mode', 'additive'),
                interval_width=params.get('interval_width', 0.95)
            )

            # Fit model
            model.fit(df)

            # Calculate performance metrics
            forecast = model.predict(df)
            mape = mean_absolute_percentage_error(df['y'], forecast['yhat'])

            return {
                "model": model,
                "metrics": {
                    "mape": float(mape),
                    "training_samples": len(df)
                },
                "hyperparameters": params
            }
        except Exception as e:
            logger.error(f"Error training Prophet model: {e}", exc_info=True)
            raise

    async def _train_arima_model(
        self,
        data: pd.DataFrame,
        hyperparameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Train ARIMA model."""
        try:
            # Prepare data
            series = data['y'].values

            # Get ARIMA order
            params = hyperparameters or {}
            order = params.get('order', (1, 1, 1))

            # Fit model
            model = ARIMA(series, order=order)
            fitted_model = model.fit()

            # Calculate performance metrics
            predictions = fitted_model.fittedvalues
            mape = mean_absolute_percentage_error(series[1:], predictions[1:])

            return {
                "model": fitted_model,
                "metrics": {
                    "mape": float(mape),
                    "aic": float(fitted_model.aic),
                    "bic": float(fitted_model.bic),
                    "training_samples": len(series)
                },
                "hyperparameters": params
            }
        except Exception as e:
            logger.error(f"Error training ARIMA model: {e}", exc_info=True)
            raise

    async def _train_gradient_boosting(
        self,
        data: pd.DataFrame,
        hyperparameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Train Gradient Boosting classifier."""
        try:
            # Prepare data
            X = data.drop('target', axis=1)
            y = data['target']

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            params = hyperparameters or {}
            model = GradientBoostingClassifier(
                n_estimators=params.get('n_estimators', 100),
                learning_rate=params.get('learning_rate', 0.1),
                max_depth=params.get('max_depth', 3),
                random_state=42
            )

            model.fit(X_train_scaled, y_train)

            # Calculate metrics
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            auc = roc_auc_score(y_test, y_pred_proba)

            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='roc_auc')

            return {
                "model": model,
                "scaler": scaler,
                "metrics": {
                    "auc": float(auc),
                    "cv_auc_mean": float(cv_scores.mean()),
                    "cv_auc_std": float(cv_scores.std()),
                    "training_samples": len(X_train)
                },
                "feature_importance": dict(zip(X.columns, model.feature_importances_)),
                "hyperparameters": params
            }
        except Exception as e:
            logger.error(f"Error training Gradient Boosting model: {e}", exc_info=True)
            raise

    async def _train_random_forest(
        self,
        data: pd.DataFrame,
        hyperparameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Train Random Forest classifier."""
        try:
            # Prepare data
            X = data.drop('target', axis=1)
            y = data['target']

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Train model
            params = hyperparameters or {}
            model = RandomForestClassifier(
                n_estimators=params.get('n_estimators', 100),
                max_depth=params.get('max_depth', 10),
                min_samples_split=params.get('min_samples_split', 2),
                random_state=42
            )

            model.fit(X_train, y_train)

            # Calculate metrics
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            auc = roc_auc_score(y_test, y_pred_proba)

            # Cross-validation
            cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc')

            return {
                "model": model,
                "metrics": {
                    "auc": float(auc),
                    "cv_auc_mean": float(cv_scores.mean()),
                    "cv_auc_std": float(cv_scores.std()),
                    "training_samples": len(X_train)
                },
                "feature_importance": dict(zip(X.columns, model.feature_importances_)),
                "hyperparameters": params
            }
        except Exception as e:
            logger.error(f"Error training Random Forest model: {e}", exc_info=True)
            raise

    # Data loading methods
    async def _load_credit_consumption_data(self, workspace_id: str) -> pd.DataFrame:
        """Load historical credit consumption data."""
        query = text("""
            SELECT
                date,
                SUM(credits_consumed) as credits
            FROM analytics.daily_metrics
            WHERE workspace_id = :workspace_id
                AND date >= CURRENT_DATE - INTERVAL '180 days'
            GROUP BY date
            ORDER BY date
        """)

        result = await self.db.execute(query, {"workspace_id": workspace_id})
        rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['date', 'credits'])
        df['date'] = pd.to_datetime(df['date'])
        return df

    async def _load_user_behavioral_data(
        self,
        workspace_id: str,
        users: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Load user behavioral data for churn prediction."""
        user_filter = ""
        if users:
            user_ids = "','".join(users)
            user_filter = f"AND user_id IN ('{user_ids}')"

        query = text(f"""
            SELECT
                user_id,
                COUNT(*) as total_sessions,
                SUM(CASE WHEN event_type = 'login' THEN 1 ELSE 0 END) as login_count,
                AVG(session_duration) as avg_session_duration,
                MAX(timestamp) as last_active,
                SUM(credits_consumed) as total_credits,
                COUNT(DISTINCT DATE(timestamp)) as active_days
            FROM analytics.user_activity
            WHERE workspace_id = :workspace_id
                AND timestamp >= CURRENT_DATE - INTERVAL '90 days'
                {user_filter}
            GROUP BY user_id
        """)

        result = await self.db.execute(query, {"workspace_id": workspace_id})
        rows = result.fetchall()

        df = pd.DataFrame(rows, columns=[
            'user_id', 'total_sessions', 'login_count', 'avg_session_duration',
            'last_active', 'total_credits', 'active_days'
        ])
        return df

    async def _load_growth_data(self, workspace_id: str, metric: str) -> pd.DataFrame:
        """Load historical growth data."""
        metric_column_map = {
            'dau': 'active_users',
            'wau': 'weekly_active_users',
            'mau': 'monthly_active_users',
            'mrr': 'total_revenue',
            'active_users': 'active_users'
        }

        column = metric_column_map.get(metric, 'active_users')

        query = text(f"""
            SELECT
                date,
                {column} as value
            FROM analytics.daily_metrics
            WHERE workspace_id = :workspace_id
                AND date >= CURRENT_DATE - INTERVAL '180 days'
            ORDER BY date
        """)

        result = await self.db.execute(query, {"workspace_id": workspace_id})
        rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['date', 'value'])
        df['date'] = pd.to_datetime(df['date'])
        return df

    async def _load_usage_data(self, workspace_id: str, granularity: str) -> pd.DataFrame:
        """Load historical usage data for peak prediction."""
        if granularity == "hourly":
            query = text("""
                SELECT
                    DATE_TRUNC('hour', started_at) as timestamp,
                    COUNT(*) as executions,
                    SUM(credits_consumed) as credits
                FROM analytics.execution_logs
                WHERE workspace_id = :workspace_id
                    AND started_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                GROUP BY DATE_TRUNC('hour', started_at)
                ORDER BY timestamp
            """)
        else:  # daily
            query = text("""
                SELECT
                    date as timestamp,
                    total_executions as executions,
                    SUM(credits_consumed) as credits
                FROM analytics.daily_metrics
                WHERE workspace_id = :workspace_id
                    AND date >= CURRENT_DATE - INTERVAL '90 days'
                GROUP BY date, total_executions
                ORDER BY date
            """)

        result = await self.db.execute(query, {"workspace_id": workspace_id})
        rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['timestamp', 'executions', 'credits'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    async def _load_error_data(
        self,
        workspace_id: str,
        agent_id: Optional[str] = None
    ) -> pd.DataFrame:
        """Load historical error data."""
        agent_filter = ""
        params = {"workspace_id": workspace_id}

        if agent_id:
            agent_filter = "AND agent_id = :agent_id"
            params["agent_id"] = agent_id

        query = text(f"""
            SELECT
                date,
                SUM(error_count) as errors,
                SUM(total_executions) as executions
            FROM analytics.daily_metrics
            WHERE workspace_id = :workspace_id
                AND date >= CURRENT_DATE - INTERVAL '90 days'
                {agent_filter}
            GROUP BY date
            ORDER BY date
        """)

        result = await self.db.execute(query, params)
        rows = result.fetchall()

        df = pd.DataFrame(rows, columns=['date', 'errors', 'executions'])
        df['date'] = pd.to_datetime(df['date'])
        df['error_rate'] = df['errors'] / (df['executions'] + 1)
        return df


# Import specialized predictors
from .credit_consumption_predictor import CreditConsumptionPredictor
from .user_churn_predictor import UserChurnPredictor
from .growth_metrics_predictor import GrowthMetricsPredictor
from .peak_usage_predictor import PeakUsagePredictor
from .error_rate_predictor import ErrorRatePredictor
