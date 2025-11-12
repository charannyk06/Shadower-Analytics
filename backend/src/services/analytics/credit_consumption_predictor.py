"""
Credit Consumption Predictor

Predicts future credit consumption using Prophet and ARIMA ensemble models.

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
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error

logger = logging.getLogger(__name__)


class CreditConsumptionPredictor:
    """
    Predicts credit consumption using ensemble of Prophet and ARIMA models.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.prophet_model = None
        self.arima_model = None

    async def predict(
        self,
        workspace_id: str,
        days_ahead: int,
        historical_data: pd.DataFrame,
        granularity: str = "daily"
    ) -> Dict[str, Any]:
        """
        Generate credit consumption predictions.

        Args:
            workspace_id: Workspace identifier
            days_ahead: Number of days to predict
            historical_data: Historical credit consumption data
            granularity: Prediction granularity

        Returns:
            Dictionary with predictions, confidence intervals, and insights
        """
        try:
            logger.info(f"Predicting credit consumption for workspace {workspace_id}, {days_ahead} days ahead")

            # Prepare data
            df = self._prepare_data(historical_data)

            if len(df) < 30:
                return {
                    "error": "Insufficient data",
                    "message": "At least 30 days of historical data required",
                    "predictions": []
                }

            # Train Prophet model
            prophet_predictions = await self._predict_with_prophet(df, days_ahead)

            # Train ARIMA model
            arima_predictions = await self._predict_with_arima(df, days_ahead)

            # Ensemble predictions (weighted average)
            ensemble_predictions = self._ensemble_predictions(
                prophet_predictions,
                arima_predictions,
                prophet_weight=0.6,
                arima_weight=0.4
            )

            # Calculate insights
            insights = self._generate_insights(df, ensemble_predictions)

            # Store predictions in database
            await self._store_predictions(
                workspace_id,
                ensemble_predictions,
                "credit_consumption",
                "credits"
            )

            return {
                "workspace_id": workspace_id,
                "prediction_type": "credit_consumption",
                "granularity": granularity,
                "days_ahead": days_ahead,
                "predictions": ensemble_predictions,
                "prophet_predictions": prophet_predictions,
                "arima_predictions": arima_predictions,
                "insights": insights,
                "model_versions": {
                    "prophet": "1.0.0",
                    "arima": "1.0.0",
                    "ensemble": "1.0.0"
                },
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error predicting credit consumption: {e}", exc_info=True)
            raise

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for modeling."""
        df = data.copy()

        # Ensure date column is datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        else:
            raise ValueError("Data must have 'date' column")

        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)

        # Fill missing dates with 0
        date_range = pd.date_range(start=df['date'].min(), end=df['date'].max(), freq='D')
        df = df.set_index('date').reindex(date_range, fill_value=0).reset_index()
        df.columns = ['date', 'credits']

        # Handle outliers (cap at 99th percentile)
        upper_limit = df['credits'].quantile(0.99)
        df['credits'] = df['credits'].clip(upper=upper_limit)

        return df

    async def _predict_with_prophet(
        self,
        data: pd.DataFrame,
        days_ahead: int
    ) -> List[Dict[str, Any]]:
        """Generate predictions using Facebook Prophet."""
        try:
            # Prepare data for Prophet (requires 'ds' and 'y' columns)
            prophet_df = data.copy()
            prophet_df.columns = ['ds', 'y']

            # Initialize Prophet with optimized parameters
            model = Prophet(
                changepoint_prior_scale=0.05,  # Flexibility of trend changes
                seasonality_prior_scale=10.0,  # Strength of seasonality
                seasonality_mode='additive',
                yearly_seasonality=False,      # Not enough data for yearly
                weekly_seasonality=True,
                daily_seasonality=False,
                interval_width=0.95            # 95% confidence interval
            )

            # Add custom seasonality if we have enough data
            if len(prophet_df) >= 60:
                model.add_seasonality(name='monthly', period=30.5, fourier_order=5)

            # Fit model
            model.fit(prophet_df)
            self.prophet_model = model

            # Make future predictions
            future = model.make_future_dataframe(periods=days_ahead, freq='D')
            forecast = model.predict(future)

            # Extract future predictions only
            future_forecast = forecast.tail(days_ahead)

            # Format predictions
            predictions = []
            for _, row in future_forecast.iterrows():
                predictions.append({
                    "date": row['ds'].strftime('%Y-%m-%d'),
                    "predicted_value": float(max(0, row['yhat'])),  # Credits can't be negative
                    "confidence_lower": float(max(0, row['yhat_lower'])),
                    "confidence_upper": float(max(0, row['yhat_upper'])),
                    "model": "prophet"
                })

            # Calculate model performance on training data
            train_predictions = forecast.head(len(prophet_df))
            mape = mean_absolute_percentage_error(
                prophet_df['y'],
                train_predictions['yhat']
            )
            logger.info(f"Prophet model MAPE: {mape:.4f}")

            return predictions

        except Exception as e:
            logger.error(f"Error in Prophet prediction: {e}", exc_info=True)
            raise

    async def _predict_with_arima(
        self,
        data: pd.DataFrame,
        days_ahead: int
    ) -> List[Dict[str, Any]]:
        """Generate predictions using ARIMA."""
        try:
            # Prepare data
            series = data['credits'].values

            # Auto-select ARIMA order (p, d, q) based on data characteristics
            # For simplicity, using (1, 1, 1) which works well for many cases
            order = (1, 1, 1)

            # Fit ARIMA model
            model = ARIMA(series, order=order)
            fitted_model = model.fit()
            self.arima_model = fitted_model

            # Generate forecast
            forecast_result = fitted_model.forecast(steps=days_ahead)

            # Get confidence intervals
            forecast_df = fitted_model.get_forecast(steps=days_ahead)
            confidence_intervals = forecast_df.conf_int(alpha=0.05)  # 95% CI

            # Format predictions
            predictions = []
            last_date = data['date'].max()

            for i in range(days_ahead):
                pred_date = last_date + timedelta(days=i+1)
                predictions.append({
                    "date": pred_date.strftime('%Y-%m-%d'),
                    "predicted_value": float(max(0, forecast_result.iloc[i])),
                    "confidence_lower": float(max(0, confidence_intervals.iloc[i, 0])),
                    "confidence_upper": float(max(0, confidence_intervals.iloc[i, 1])),
                    "model": "arima"
                })

            # Calculate model performance
            fitted_values = fitted_model.fittedvalues
            # Skip first value due to differencing
            mape = mean_absolute_percentage_error(
                series[1:],
                fitted_values[1:]
            )
            logger.info(f"ARIMA model MAPE: {mape:.4f}, AIC: {fitted_model.aic:.2f}")

            return predictions

        except Exception as e:
            logger.error(f"Error in ARIMA prediction: {e}", exc_info=True)
            # Fallback to simple moving average if ARIMA fails
            return await self._fallback_simple_forecast(data, days_ahead)

    async def _fallback_simple_forecast(
        self,
        data: pd.DataFrame,
        days_ahead: int
    ) -> List[Dict[str, Any]]:
        """Fallback to simple moving average forecast."""
        logger.warning("Using fallback simple forecast method")

        # Calculate 7-day moving average
        ma_7 = data['credits'].tail(7).mean()
        # Calculate 30-day moving average
        ma_30 = data['credits'].tail(30).mean()

        # Use weighted average
        prediction_value = 0.7 * ma_7 + 0.3 * ma_30

        # Simple confidence interval (±20%)
        confidence_range = prediction_value * 0.2

        predictions = []
        last_date = data['date'].max()

        for i in range(days_ahead):
            pred_date = last_date + timedelta(days=i+1)
            predictions.append({
                "date": pred_date.strftime('%Y-%m-%d'),
                "predicted_value": float(max(0, prediction_value)),
                "confidence_lower": float(max(0, prediction_value - confidence_range)),
                "confidence_upper": float(max(0, prediction_value + confidence_range)),
                "model": "simple_ma"
            })

        return predictions

    def _ensemble_predictions(
        self,
        prophet_preds: List[Dict],
        arima_preds: List[Dict],
        prophet_weight: float = 0.6,
        arima_weight: float = 0.4
    ) -> List[Dict[str, Any]]:
        """Combine predictions from multiple models."""
        ensemble = []

        for p_pred, a_pred in zip(prophet_preds, arima_preds):
            # Weighted average of predictions
            predicted_value = (
                prophet_weight * p_pred['predicted_value'] +
                arima_weight * a_pred['predicted_value']
            )

            # Conservative confidence intervals (take wider bounds)
            confidence_lower = min(
                p_pred['confidence_lower'],
                a_pred['confidence_lower']
            )
            confidence_upper = max(
                p_pred['confidence_upper'],
                a_pred['confidence_upper']
            )

            ensemble.append({
                "date": p_pred['date'],
                "predicted_value": float(predicted_value),
                "confidence_lower": float(confidence_lower),
                "confidence_upper": float(confidence_upper),
                "confidence_level": 0.95,
                "model": "ensemble"
            })

        return ensemble

    def _generate_insights(
        self,
        historical_data: pd.DataFrame,
        predictions: List[Dict]
    ) -> Dict[str, Any]:
        """Generate insights from predictions."""
        try:
            # Calculate historical average
            historical_avg = historical_data['credits'].mean()

            # Calculate predicted average
            predicted_avg = np.mean([p['predicted_value'] for p in predictions])

            # Calculate trend
            trend_pct = ((predicted_avg - historical_avg) / historical_avg) * 100

            # Identify peak days
            pred_df = pd.DataFrame(predictions)
            peak_day_idx = pred_df['predicted_value'].idxmax()
            peak_day = pred_df.iloc[peak_day_idx]

            # Identify low usage days
            low_day_idx = pred_df['predicted_value'].idxmin()
            low_day = pred_df.iloc[low_day_idx]

            # Calculate total predicted consumption
            total_predicted = pred_df['predicted_value'].sum()

            # Volatility analysis
            predicted_std = pred_df['predicted_value'].std()
            coefficient_of_variation = (predicted_std / predicted_avg) * 100

            insights = {
                "summary": {
                    "historical_daily_avg": float(historical_avg),
                    "predicted_daily_avg": float(predicted_avg),
                    "trend_percentage": float(trend_pct),
                    "trend_direction": "increasing" if trend_pct > 5 else "decreasing" if trend_pct < -5 else "stable",
                    "total_predicted_consumption": float(total_predicted)
                },
                "peak_usage": {
                    "date": peak_day['date'],
                    "predicted_credits": float(peak_day['predicted_value']),
                    "confidence_range": [
                        float(peak_day['confidence_lower']),
                        float(peak_day['confidence_upper'])
                    ]
                },
                "low_usage": {
                    "date": low_day['date'],
                    "predicted_credits": float(low_day['predicted_value'])
                },
                "volatility": {
                    "standard_deviation": float(predicted_std),
                    "coefficient_of_variation": float(coefficient_of_variation),
                    "stability": "stable" if coefficient_of_variation < 20 else "moderate" if coefficient_of_variation < 40 else "volatile"
                },
                "recommendations": self._generate_recommendations(
                    trend_pct,
                    coefficient_of_variation,
                    total_predicted
                )
            }

            return insights

        except Exception as e:
            logger.error(f"Error generating insights: {e}", exc_info=True)
            return {}

    def _generate_recommendations(
        self,
        trend_pct: float,
        volatility: float,
        total_predicted: float
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if trend_pct > 20:
            recommendations.append(
                "⚠️ Credit consumption is predicted to increase by {:.1f}%. "
                "Consider reviewing resource allocation.".format(trend_pct)
            )
        elif trend_pct < -20:
            recommendations.append(
                "📉 Credit consumption is predicted to decrease by {:.1f}%. "
                "This may indicate reduced activity.".format(abs(trend_pct))
            )
        else:
            recommendations.append(
                "✅ Credit consumption is predicted to remain stable."
            )

        if volatility > 40:
            recommendations.append(
                "📊 High volatility detected. Consider implementing usage smoothing strategies."
            )

        if total_predicted > 100000:
            recommendations.append(
                "💡 High credit consumption expected. Consider bulk credit purchases for better rates."
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
                        model_version = EXCLUDED.model_version,
                        created_at = CURRENT_TIMESTAMP
                """)

                await self.db.execute(query, {
                    "workspace_id": workspace_id,
                    "prediction_type": prediction_type,
                    "target_metric": target_metric,
                    "prediction_date": pred['date'],
                    "predicted_value": pred['predicted_value'],
                    "confidence_lower": pred['confidence_lower'],
                    "confidence_upper": pred['confidence_upper'],
                    "confidence_level": pred.get('confidence_level', 0.95),
                    "model_version": "ensemble_v1.0.0",
                    "metadata": json.dumps({"model": pred.get('model', 'ensemble')})
                })

            await self.db.commit()
            logger.info(f"Stored {len(predictions)} predictions for workspace {workspace_id}")

        except Exception as e:
            logger.error(f"Error storing predictions: {e}", exc_info=True)
            await self.db.rollback()
            raise
