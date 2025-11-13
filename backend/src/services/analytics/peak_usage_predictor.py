"""
Peak Usage Predictor

Predicts peak usage times and capacity needs for resource planning.

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

logger = logging.getLogger(__name__)


class PeakUsagePredictor:
    """
    Predicts peak usage times and capacity needs for resource planning.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def predict(
        self,
        workspace_id: str,
        granularity: str,
        days_ahead: int,
        historical_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Generate peak usage predictions for capacity planning.

        Args:
            workspace_id: Workspace identifier
            granularity: Time granularity (hourly, daily)
            days_ahead: Number of days to predict
            historical_data: Historical usage data

        Returns:
            Dictionary with peak usage predictions and capacity recommendations
        """
        try:
            logger.info(f"Predicting peak usage for workspace {workspace_id}")

            # Prepare data
            df = self._prepare_data(historical_data, granularity)

            if len(df) < 7:
                return {
                    "error": "Insufficient data",
                    "message": f"At least 1 week of {granularity} data required",
                    "predictions": []
                }

            # Predict usage patterns
            usage_predictions = await self._predict_usage(df, days_ahead, granularity)

            # Identify peak times
            peak_times = self._identify_peak_times(usage_predictions, granularity)

            # Calculate capacity recommendations
            capacity_recommendations = self._calculate_capacity_needs(
                df,
                usage_predictions,
                peak_times
            )

            # Generate insights
            insights = self._generate_capacity_insights(df, usage_predictions, peak_times)

            return {
                "workspace_id": workspace_id,
                "granularity": granularity,
                "days_ahead": days_ahead,
                "predictions": usage_predictions,
                "peak_times": peak_times,
                "capacity_recommendations": capacity_recommendations,
                "insights": insights,
                "model_version": "peak_usage_v1.0.0",
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error predicting peak usage: {e}", exc_info=True)
            raise

    def _prepare_data(self, data: pd.DataFrame, granularity: str) -> pd.DataFrame:
        """Prepare data for modeling."""
        df = data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Aggregate if needed
        if granularity == "hourly":
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek

        return df

    async def _predict_usage(
        self,
        data: pd.DataFrame,
        days_ahead: int,
        granularity: str
    ) -> List[Dict[str, Any]]:
        """Predict future usage patterns."""
        try:
            # Use executions as the primary metric
            prophet_df = data[['timestamp', 'executions']].copy()
            prophet_df.columns = ['ds', 'y']

            # Configure Prophet
            model = Prophet(
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=15.0,
                seasonality_mode='multiplicative',
                yearly_seasonality=False,
                weekly_seasonality=True,
                daily_seasonality=granularity == 'hourly',
                interval_width=0.90
            )

            # Fit model
            model.fit(prophet_df)

            # Predict
            if granularity == 'hourly':
                periods = days_ahead * 24
                freq = 'H'
            else:
                periods = days_ahead
                freq = 'D'

            future = model.make_future_dataframe(periods=periods, freq=freq)
            forecast = model.predict(future)

            # Extract predictions
            future_forecast = forecast.tail(periods)

            predictions = []
            for _, row in future_forecast.iterrows():
                predictions.append({
                    "timestamp": row['ds'].isoformat(),
                    "predicted_executions": float(max(0, row['yhat'])),
                    "confidence_lower": float(max(0, row['yhat_lower'])),
                    "confidence_upper": float(max(0, row['yhat_upper'])),
                    "hour": row['ds'].hour if granularity == 'hourly' else None,
                    "day_of_week": row['ds'].dayofweek
                })

            return predictions

        except Exception as e:
            logger.error(f"Error predicting usage: {e}", exc_info=True)
            raise

    def _identify_peak_times(
        self,
        predictions: List[Dict],
        granularity: str
    ) -> Dict[str, Any]:
        """Identify peak usage times."""
        try:
            pred_df = pd.DataFrame(predictions)

            # Find overall peak
            peak_idx = pred_df['predicted_executions'].idxmax()
            peak_time = pred_df.iloc[peak_idx]

            # If hourly, find peak hours
            if granularity == 'hourly' and 'hour' in pred_df.columns:
                hourly_avg = pred_df.groupby('hour')['predicted_executions'].mean()
                peak_hours = hourly_avg.nlargest(3).index.tolist()

                # Find peak days of week
                daily_avg = pred_df.groupby('day_of_week')['predicted_executions'].mean()
                peak_days = daily_avg.nlargest(2).index.tolist()

                day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                peak_day_names = [day_names[d] for d in peak_days]

                return {
                    "peak_timestamp": peak_time['timestamp'],
                    "peak_executions": float(peak_time['predicted_executions']),
                    "peak_hours": [int(h) for h in peak_hours],
                    "peak_days": peak_day_names,
                    "hourly_pattern": hourly_avg.to_dict()
                }
            else:
                # Daily granularity
                daily_avg = pred_df.groupby('day_of_week')['predicted_executions'].mean()
                peak_days = daily_avg.nlargest(2).index.tolist()

                day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                peak_day_names = [day_names[d] for d in peak_days]

                return {
                    "peak_timestamp": peak_time['timestamp'],
                    "peak_executions": float(peak_time['predicted_executions']),
                    "peak_days": peak_day_names,
                    "daily_pattern": daily_avg.to_dict()
                }

        except Exception as e:
            logger.error(f"Error identifying peak times: {e}", exc_info=True)
            return {}

    def _calculate_capacity_needs(
        self,
        historical_data: pd.DataFrame,
        predictions: List[Dict],
        peak_times: Dict
    ) -> Dict[str, Any]:
        """Calculate capacity recommendations."""
        try:
            # Current capacity (based on historical peak)
            current_peak = historical_data['executions'].max()

            # Predicted peak
            predicted_peak = peak_times.get('peak_executions', 0)

            # Recommended capacity (with 20% buffer)
            recommended_capacity = predicted_peak * 1.2

            # Calculate growth
            capacity_increase = ((predicted_peak - current_peak) / current_peak) * 100

            return {
                "current_peak_capacity": float(current_peak),
                "predicted_peak_usage": float(predicted_peak),
                "recommended_capacity": float(recommended_capacity),
                "capacity_increase_needed": float(capacity_increase),
                "buffer_percentage": 20.0,
                "scaling_recommendation": self._get_scaling_recommendation(capacity_increase)
            }

        except Exception as e:
            logger.error(f"Error calculating capacity needs: {e}", exc_info=True)
            return {}

    def _get_scaling_recommendation(self, capacity_increase: float) -> str:
        """Get scaling recommendation based on capacity increase."""
        if capacity_increase > 50:
            return "critical_scaling_needed"
        elif capacity_increase > 25:
            return "significant_scaling_needed"
        elif capacity_increase > 10:
            return "moderate_scaling_needed"
        elif capacity_increase > 0:
            return "minor_scaling_needed"
        else:
            return "no_scaling_needed"

    def _generate_capacity_insights(
        self,
        historical_data: pd.DataFrame,
        predictions: List[Dict],
        peak_times: Dict
    ) -> Dict[str, Any]:
        """Generate insights about capacity planning."""
        try:
            pred_df = pd.DataFrame(predictions)

            # Calculate metrics
            avg_usage = pred_df['predicted_executions'].mean()
            peak_usage = pred_df['predicted_executions'].max()
            utilization_ratio = avg_usage / peak_usage if peak_usage > 0 else 0

            insights = {
                "average_usage": float(avg_usage),
                "peak_usage": float(peak_usage),
                "utilization_ratio": float(utilization_ratio),
                "utilization_efficiency": "high" if utilization_ratio > 0.7 else "medium" if utilization_ratio > 0.5 else "low",
                "recommendations": []
            }

            # Generate recommendations
            if utilization_ratio < 0.5:
                insights["recommendations"].append(
                    "⚠️ Low utilization ratio. Consider load balancing or usage optimization."
                )

            if 'peak_hours' in peak_times:
                insights["recommendations"].append(
                    f"📊 Peak hours: {', '.join(map(str, peak_times['peak_hours']))}. "
                    f"Ensure adequate resources during these times."
                )

            if 'peak_days' in peak_times:
                insights["recommendations"].append(
                    f"📅 Peak days: {', '.join(peak_times['peak_days'])}. "
                    f"Plan capacity scaling accordingly."
                )

            return insights

        except Exception as e:
            logger.error(f"Error generating insights: {e}", exc_info=True)
            return {}
