"""
Growth Metrics Predictor

Predicts growth trajectory for DAU/WAU/MAU using ensemble models.

Author: Claude Code
Date: 2025-11-12
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from prophet import Prophet
from sklearn.metrics import mean_absolute_percentage_error

logger = logging.getLogger(__name__)


class GrowthMetricsPredictor:
    """
    Predicts growth metrics (DAU, WAU, MAU, MRR) using ensemble of time-series models.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def predict(
        self,
        workspace_id: str,
        metric: str,
        horizon_days: int,
        historical_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Generate growth metric predictions with multiple scenarios.

        Args:
            workspace_id: Workspace identifier
            metric: Metric to predict (dau, wau, mau, mrr)
            horizon_days: Prediction horizon in days
            historical_data: Historical metric data

        Returns:
            Dictionary with predictions and growth scenarios
        """
        try:
            logger.info(f"Predicting {metric} for workspace {workspace_id}, {horizon_days} days ahead")

            # Prepare data
            df = self._prepare_data(historical_data)

            if len(df) < 30:
                return {
                    "error": "Insufficient data",
                    "message": "At least 30 days of historical data required",
                    "predictions": []
                }

            # Generate base predictions
            base_predictions = await self._predict_with_prophet(df, horizon_days, metric)

            # Generate growth scenarios
            scenarios = self._generate_growth_scenarios(df, base_predictions, horizon_days)

            # Calculate milestones
            milestones = self._calculate_milestones(df, base_predictions, metric)

            # Generate insights
            insights = self._generate_growth_insights(df, base_predictions, metric)

            # Store predictions
            await self._store_predictions(
                workspace_id,
                base_predictions,
                "growth_metrics",
                metric
            )

            return {
                "workspace_id": workspace_id,
                "metric": metric,
                "horizon_days": horizon_days,
                "base_predictions": base_predictions,
                "scenarios": scenarios,
                "milestones": milestones,
                "insights": insights,
                "model_version": "prophet_ensemble_v1.0.0",
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error predicting growth metrics: {e}", exc_info=True)
            raise

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for modeling."""
        df = data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        # Fill missing dates
        date_range = pd.date_range(start=df['date'].min(), end=df['date'].max(), freq='D')
        df = df.set_index('date').reindex(date_range, fill_value=0).reset_index()
        df.columns = ['date', 'value']

        # Smooth outliers
        upper_limit = df['value'].quantile(0.99)
        df['value'] = df['value'].clip(upper=upper_limit)

        return df

    async def _predict_with_prophet(
        self,
        data: pd.DataFrame,
        days_ahead: int,
        metric: str
    ) -> List[Dict[str, Any]]:
        """Generate predictions using Prophet."""
        try:
            # Prepare for Prophet
            prophet_df = data.copy()
            prophet_df.columns = ['ds', 'y']

            # Configure Prophet based on metric type
            model = Prophet(
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10.0,
                seasonality_mode='multiplicative' if metric == 'mrr' else 'additive',
                yearly_seasonality=False,
                weekly_seasonality=True,
                daily_seasonality=False,
                interval_width=0.95
            )

            # Add monthly seasonality
            if len(prophet_df) >= 60:
                model.add_seasonality(name='monthly', period=30.5, fourier_order=5)

            # Fit model
            model.fit(prophet_df)

            # Make predictions
            future = model.make_future_dataframe(periods=days_ahead, freq='D')
            forecast = model.predict(future)

            # Extract future predictions
            future_forecast = forecast.tail(days_ahead)

            predictions = []
            for _, row in future_forecast.iterrows():
                predictions.append({
                    "date": row['ds'].strftime('%Y-%m-%d'),
                    "predicted_value": float(max(0, row['yhat'])),
                    "confidence_lower": float(max(0, row['yhat_lower'])),
                    "confidence_upper": float(max(0, row['yhat_upper'])),
                    "trend": float(row.get('trend', 0)),
                    "weekly_component": float(row.get('weekly', 0))
                })

            return predictions

        except Exception as e:
            logger.error(f"Error in Prophet prediction: {e}", exc_info=True)
            raise

    def _generate_growth_scenarios(
        self,
        historical_data: pd.DataFrame,
        base_predictions: List[Dict],
        horizon_days: int
    ) -> Dict[str, List[Dict]]:
        """Generate best/worst/likely growth scenarios."""
        try:
            # Calculate historical growth rate
            historical_avg = historical_data['value'].tail(30).mean()
            historical_std = historical_data['value'].tail(30).std()

            scenarios = {}

            # Optimistic scenario (+20% growth)
            optimistic = []
            for pred in base_predictions:
                optimistic.append({
                    "date": pred['date'],
                    "predicted_value": float(pred['predicted_value'] * 1.2),
                    "scenario": "optimistic"
                })
            scenarios['optimistic'] = optimistic

            # Base case (original predictions)
            scenarios['base'] = [
                {
                    "date": p['date'],
                    "predicted_value": float(p['predicted_value']),
                    "scenario": "base"
                }
                for p in base_predictions
            ]

            # Pessimistic scenario (-10% growth)
            pessimistic = []
            for pred in base_predictions:
                pessimistic.append({
                    "date": pred['date'],
                    "predicted_value": float(pred['predicted_value'] * 0.9),
                    "scenario": "pessimistic"
                })
            scenarios['pessimistic'] = pessimistic

            return scenarios

        except Exception as e:
            logger.error(f"Error generating scenarios: {e}", exc_info=True)
            return {}

    def _calculate_milestones(
        self,
        historical_data: pd.DataFrame,
        predictions: List[Dict],
        metric: str
    ) -> List[Dict[str, Any]]:
        """Calculate when key milestones will be reached."""
        try:
            current_value = historical_data['value'].iloc[-1]

            milestones = []

            # Define milestone targets based on current value
            targets = [
                current_value * 1.5,   # 50% growth
                current_value * 2.0,   # 100% growth
                current_value * 3.0,   # 200% growth
            ]

            for target in targets:
                # Find when target will be reached
                for pred in predictions:
                    if pred['predicted_value'] >= target:
                        growth_pct = ((target - current_value) / current_value) * 100
                        milestones.append({
                            "target_value": float(target),
                            "growth_percentage": float(growth_pct),
                            "expected_date": pred['date'],
                            "confidence": "high" if pred['predicted_value'] < pred['confidence_upper'] else "medium"
                        })
                        break

            return milestones

        except Exception as e:
            logger.error(f"Error calculating milestones: {e}", exc_info=True)
            return []

    def _generate_growth_insights(
        self,
        historical_data: pd.DataFrame,
        predictions: List[Dict],
        metric: str
    ) -> Dict[str, Any]:
        """Generate insights about growth trajectory."""
        try:
            # Historical metrics
            historical_avg = historical_data['value'].mean()
            recent_avg = historical_data['value'].tail(30).mean()

            # Predicted metrics
            pred_df = pd.DataFrame(predictions)
            predicted_avg = pred_df['predicted_value'].mean()

            # Growth rate
            growth_rate = ((predicted_avg - recent_avg) / recent_avg) * 100

            # Volatility
            predicted_std = pred_df['predicted_value'].std()
            cv = (predicted_std / predicted_avg) * 100

            # Trend direction
            if growth_rate > 10:
                trend = "strong_growth"
                trend_description = f"Strong growth trajectory with {growth_rate:.1f}% increase expected"
            elif growth_rate > 5:
                trend = "moderate_growth"
                trend_description = f"Moderate growth expected with {growth_rate:.1f}% increase"
            elif growth_rate > -5:
                trend = "stable"
                trend_description = "Stable performance expected"
            else:
                trend = "decline"
                trend_description = f"Decline expected with {abs(growth_rate):.1f}% decrease"

            return {
                "current_value": float(recent_avg),
                "predicted_avg": float(predicted_avg),
                "growth_rate": float(growth_rate),
                "trend": trend,
                "trend_description": trend_description,
                "volatility": {
                    "coefficient_of_variation": float(cv),
                    "stability": "stable" if cv < 15 else "moderate" if cv < 30 else "volatile"
                },
                "recommendations": self._generate_growth_recommendations(growth_rate, cv)
            }

        except Exception as e:
            logger.error(f"Error generating insights: {e}", exc_info=True)
            return {}

    def _generate_growth_recommendations(
        self,
        growth_rate: float,
        volatility: float
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if growth_rate > 20:
            recommendations.append(
                "🚀 Exceptional growth predicted. Ensure infrastructure can scale to meet demand."
            )
            recommendations.append(
                "Consider increasing customer success team capacity."
            )
        elif growth_rate > 10:
            recommendations.append(
                "📈 Strong growth expected. Plan for resource scaling."
            )
        elif growth_rate < -10:
            recommendations.append(
                "⚠️ Decline predicted. Investigate root causes and implement retention strategies."
            )

        if volatility > 30:
            recommendations.append(
                "📊 High volatility detected. Focus on consistent user experience."
            )

        if not recommendations:
            recommendations.append(
                "✅ Stable growth trajectory. Continue current strategies."
            )

        return recommendations

    async def _store_predictions(
        self,
        workspace_id: str,
        predictions: List[Dict],
        prediction_type: str,
        target_metric: str
    ) -> None:
        """Store predictions in database."""
        try:
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
                    "prediction_type": prediction_type,
                    "target_metric": target_metric,
                    "prediction_date": pred['date'],
                    "predicted_value": pred['predicted_value'],
                    "confidence_lower": pred.get('confidence_lower', 0),
                    "confidence_upper": pred.get('confidence_upper', 0),
                    "confidence_level": 0.95,
                    "model_version": "prophet_v1.0.0",
                    "metadata": json.dumps({
                        "trend": pred.get('trend'),
                        "weekly_component": pred.get('weekly_component')
                    })
                })

            await self.db.commit()
            logger.info(f"Stored {len(predictions)} growth predictions")

        except Exception as e:
            logger.error(f"Error storing predictions: {e}", exc_info=True)
            await self.db.rollback()
            raise
