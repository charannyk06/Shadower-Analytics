"""
Error Rate Predictor

Predicts future error rates based on patterns to identify potential issues early.

Author: Claude Code
Date: 2025-11-12
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA

logger = logging.getLogger(__name__)


class ErrorRatePredictor:
    """
    Predicts error rates and identifies potential issues before they escalate.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def predict(
        self,
        workspace_id: str,
        agent_id: Optional[str],
        days_ahead: int,
        historical_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Generate error rate predictions.

        Args:
            workspace_id: Workspace identifier
            agent_id: Optional specific agent ID
            days_ahead: Number of days to predict
            historical_data: Historical error data

        Returns:
            Dictionary with error rate predictions and alerts
        """
        try:
            logger.info(f"Predicting error rates for workspace {workspace_id}, agent {agent_id}")

            # Prepare data
            df = self._prepare_data(historical_data)

            if len(df) < 14:
                return {
                    "error": "Insufficient data",
                    "message": "At least 14 days of historical data required",
                    "predictions": []
                }

            # Predict error rates
            predictions = await self._predict_error_rates(df, days_ahead)

            # Detect anomalies and trends
            anomalies = self._detect_error_anomalies(df, predictions)

            # Generate alerts
            alerts = self._generate_error_alerts(predictions, anomalies)

            # Analyze error patterns
            patterns = self._analyze_error_patterns(df)

            # Generate recommendations
            recommendations = self._generate_error_recommendations(
                predictions,
                anomalies,
                patterns
            )

            # Store predictions
            await self._store_predictions(
                workspace_id,
                agent_id,
                predictions
            )

            return {
                "workspace_id": workspace_id,
                "agent_id": agent_id,
                "days_ahead": days_ahead,
                "predictions": predictions,
                "anomalies": anomalies,
                "alerts": alerts,
                "patterns": patterns,
                "recommendations": recommendations,
                "model_version": "error_rate_v1.0.0",
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error predicting error rates: {e}", exc_info=True)
            raise

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for modeling."""
        df = data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        # Fill missing dates
        date_range = pd.date_range(start=df['date'].min(), end=df['date'].max(), freq='D')
        df = df.set_index('date').reindex(date_range, fill_value=0).reset_index()
        df.columns = ['date', 'errors', 'executions', 'error_rate']

        # Recalculate error rate
        df['error_rate'] = df['errors'] / (df['executions'] + 1)

        return df

    async def _predict_error_rates(
        self,
        data: pd.DataFrame,
        days_ahead: int
    ) -> List[Dict[str, Any]]:
        """Predict future error rates."""
        try:
            # Prepare for Prophet
            prophet_df = data[['date', 'error_rate']].copy()
            prophet_df.columns = ['ds', 'y']

            # Configure Prophet
            model = Prophet(
                changepoint_prior_scale=0.1,  # More sensitive to changes
                seasonality_prior_scale=5.0,
                seasonality_mode='additive',
                yearly_seasonality=False,
                weekly_seasonality=True,
                daily_seasonality=False,
                interval_width=0.95
            )

            # Fit model
            model.fit(prophet_df)

            # Predict
            future = model.make_future_dataframe(periods=days_ahead, freq='D')
            forecast = model.predict(future)

            # Extract predictions
            future_forecast = forecast.tail(days_ahead)

            predictions = []
            for _, row in future_forecast.iterrows():
                # Error rate should be between 0 and 1
                error_rate = max(0, min(1, row['yhat']))
                error_rate_lower = max(0, min(1, row['yhat_lower']))
                error_rate_upper = max(0, min(1, row['yhat_upper']))

                predictions.append({
                    "date": row['ds'].strftime('%Y-%m-%d'),
                    "predicted_error_rate": float(error_rate),
                    "confidence_lower": float(error_rate_lower),
                    "confidence_upper": float(error_rate_upper),
                    "severity": self._classify_severity(error_rate)
                })

            return predictions

        except Exception as e:
            logger.error(f"Error in error rate prediction: {e}", exc_info=True)
            raise

    def _classify_severity(self, error_rate: float) -> str:
        """Classify error severity based on rate."""
        if error_rate > 0.2:  # >20% error rate
            return "critical"
        elif error_rate > 0.1:  # >10% error rate
            return "high"
        elif error_rate > 0.05:  # >5% error rate
            return "medium"
        else:
            return "low"

    def _detect_error_anomalies(
        self,
        historical_data: pd.DataFrame,
        predictions: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in error patterns."""
        try:
            anomalies = []

            # Calculate historical baseline
            baseline_error_rate = historical_data['error_rate'].mean()
            baseline_std = historical_data['error_rate'].std()
            threshold = baseline_error_rate + (2 * baseline_std)

            # Check predictions for anomalies
            for pred in predictions:
                if pred['predicted_error_rate'] > threshold:
                    anomalies.append({
                        "date": pred['date'],
                        "predicted_error_rate": pred['predicted_error_rate'],
                        "baseline": float(baseline_error_rate),
                        "threshold": float(threshold),
                        "severity": pred['severity'],
                        "deviation": float(pred['predicted_error_rate'] - baseline_error_rate)
                    })

            # Check for sustained increases
            pred_df = pd.DataFrame(predictions)
            if len(pred_df) >= 7:
                # Rolling 7-day average
                pred_df['ma_7'] = pred_df['predicted_error_rate'].rolling(7).mean()

                # Check if trend is increasing
                if pred_df['ma_7'].iloc[-1] > pred_df['ma_7'].iloc[0] * 1.5:
                    anomalies.append({
                        "type": "sustained_increase",
                        "description": "Error rate showing sustained increase over prediction period",
                        "severity": "high"
                    })

            return anomalies

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}", exc_info=True)
            return []

    def _generate_error_alerts(
        self,
        predictions: List[Dict],
        anomalies: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Generate actionable alerts."""
        alerts = []

        # Check for critical predictions
        critical_predictions = [p for p in predictions if p['severity'] == 'critical']
        if critical_predictions:
            alerts.append({
                "type": "critical_error_rate",
                "severity": "critical",
                "message": f"Critical error rates predicted on {len(critical_predictions)} days",
                "affected_dates": [p['date'] for p in critical_predictions],
                "action_required": True
            })

        # Check for anomalies
        if anomalies:
            critical_anomalies = [a for a in anomalies if a.get('severity') == 'critical']
            if critical_anomalies:
                alerts.append({
                    "type": "error_spike_detected",
                    "severity": "critical",
                    "message": "Critical error spikes detected in predictions",
                    "anomaly_count": len(critical_anomalies),
                    "action_required": True
                })

        # Check for sustained issues
        sustained_anomalies = [a for a in anomalies if a.get('type') == 'sustained_increase']
        if sustained_anomalies:
            alerts.append({
                "type": "sustained_error_increase",
                "severity": "high",
                "message": "Sustained error rate increase detected",
                "action_required": True
            })

        return alerts

    def _analyze_error_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze historical error patterns."""
        try:
            # Day of week analysis
            data['day_of_week'] = pd.to_datetime(data['date']).dt.dayofweek
            dow_errors = data.groupby('day_of_week')['error_rate'].mean()

            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            worst_day = day_names[dow_errors.idxmax()]

            # Time trends
            recent_7d = data.tail(7)['error_rate'].mean()
            recent_30d = data.tail(30)['error_rate'].mean()
            all_time = data['error_rate'].mean()

            return {
                "day_of_week_patterns": {
                    day_names[i]: float(dow_errors.iloc[i]) for i in range(len(dow_errors))
                },
                "worst_day": worst_day,
                "trends": {
                    "7_day_avg": float(recent_7d),
                    "30_day_avg": float(recent_30d),
                    "all_time_avg": float(all_time),
                    "trend_direction": "increasing" if recent_7d > recent_30d else "decreasing"
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing patterns: {e}", exc_info=True)
            return {}

    def _generate_error_recommendations(
        self,
        predictions: List[Dict],
        anomalies: List[Dict],
        patterns: Dict
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Check for critical predictions
        critical_count = len([p for p in predictions if p['severity'] in ['critical', 'high']])
        if critical_count > 0:
            recommendations.append(
                f"⚠️ {critical_count} days with high error rates predicted. "
                "Review code quality and implement additional error handling."
            )

        # Check for anomalies
        if anomalies:
            recommendations.append(
                "🔍 Error anomalies detected. Investigate root causes immediately."
            )

        # Pattern-based recommendations
        if patterns.get('trends', {}).get('trend_direction') == 'increasing':
            recommendations.append(
                "📈 Error rates trending upward. Consider code review and testing improvements."
            )

        # Day-specific recommendations
        if 'worst_day' in patterns:
            recommendations.append(
                f"📅 Highest error rates on {patterns['worst_day']}. "
                "Investigate load patterns or deployment schedules on this day."
            )

        if not recommendations:
            recommendations.append(
                "✅ Error rates within acceptable ranges. Continue monitoring."
            )

        return recommendations

    async def _store_predictions(
        self,
        workspace_id: str,
        agent_id: Optional[str],
        predictions: List[Dict]
    ) -> None:
        """Store error rate predictions."""
        try:
            target_metric = f"error_rate_{agent_id}" if agent_id else "error_rate_all"

            for pred in predictions:
                query = text("""
                    INSERT INTO analytics.predictions
                    (workspace_id, prediction_type, target_metric, prediction_date,
                     predicted_value, confidence_lower, confidence_upper, confidence_level,
                     model_version, metadata)
                    VALUES
                    (:workspace_id, :prediction_type, :target_metric, :prediction_date,
                     :predicted_value, :confidence_lower, :confidence_upper, :confidence_level,
                     :model_version, :metadata)
                    ON CONFLICT (workspace_id, prediction_type, target_metric, prediction_date)
                    DO UPDATE SET
                        predicted_value = EXCLUDED.predicted_value,
                        confidence_lower = EXCLUDED.confidence_lower,
                        confidence_upper = EXCLUDED.confidence_upper,
                        created_at = CURRENT_TIMESTAMP
                """)

                await self.db.execute(query, {
                    "workspace_id": workspace_id,
                    "prediction_type": "error_rate",
                    "target_metric": target_metric,
                    "prediction_date": pred['date'],
                    "predicted_value": pred['predicted_error_rate'],
                    "confidence_lower": pred['confidence_lower'],
                    "confidence_upper": pred['confidence_upper'],
                    "confidence_level": 0.95,
                    "model_version": "prophet_v1.0.0",
                    "metadata": json.dumps({"severity": pred['severity']})
                })

            await self.db.commit()
            logger.info(f"Stored {len(predictions)} error rate predictions")

        except Exception as e:
            logger.error(f"Error storing predictions: {e}", exc_info=True)
            await self.db.rollback()
            raise
