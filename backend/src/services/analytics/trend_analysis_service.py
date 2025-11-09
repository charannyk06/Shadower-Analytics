"""Comprehensive trend analysis service with time-series decomposition, forecasting, and pattern detection."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging

import numpy as np
import pandas as pd
from scipy import signal
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import acf
from sklearn.linear_model import LinearRegression
from prophet import Prophet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class TrendAnalysisService:
    """Advanced time-series analysis and trend detection service."""

    def __init__(self, db: AsyncSession):
        """Initialize the trend analysis service.

        Args:
            db: Async database session
        """
        self.db = db

    async def analyze_trend(self, workspace_id: str, metric: str, timeframe: str) -> Dict[str, Any]:
        """Perform comprehensive trend analysis on a metric.

        Args:
            workspace_id: The workspace to analyze
            metric: The metric to analyze (e.g., 'executions', 'users', 'credits')
            timeframe: Time window (e.g., '7d', '30d', '90d', '1y')

        Returns:
            Comprehensive trend analysis results
        """
        try:
            # Check cache first
            cached_result = await self._get_cached_analysis(workspace_id, metric, timeframe)
            if cached_result:
                return cached_result

            # Get time series data
            time_series_data = await self._get_time_series(workspace_id, metric, timeframe)

            if not time_series_data or len(time_series_data) < 14:
                return self._insufficient_data_response(workspace_id, metric, timeframe)

            # Convert to pandas DataFrame
            df = pd.DataFrame(time_series_data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
            df.set_index("timestamp", inplace=True)

            # Perform parallel analysis
            results = await asyncio.gather(
                self._calculate_overview(df, metric),
                self._perform_decomposition(df),
                self._detect_patterns(df),
                self._generate_comparisons(df, timeframe),
                self._find_correlations(workspace_id, metric, df),
                self._generate_forecast(df, metric),
                return_exceptions=True,
            )

            # Check for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error in analysis step {i}: {result}", exc_info=True)
                    # Provide fallback for failed step
                    results[i] = self._get_fallback_result(i)

            # Prepare time series with statistics
            time_series_with_stats = self._prepare_time_series(df)

            # Generate insights based on all analyses
            insights = self._generate_insights(df, results[0], results[2], results[3], results[5])

            # Build complete analysis result
            analysis_result = {
                "workspaceId": workspace_id,
                "metric": metric,
                "timeframe": timeframe,
                "overview": results[0],
                "timeSeries": time_series_with_stats,
                "decomposition": results[1],
                "patterns": results[2],
                "comparisons": results[3],
                "correlations": results[4],
                "forecast": results[5],
                "insights": insights,
            }

            # Cache the result
            await self._cache_analysis(workspace_id, metric, timeframe, analysis_result)

            return analysis_result

        except Exception as e:
            logger.error(f"Error in trend analysis: {e}", exc_info=True)
            raise

    async def _get_time_series(
        self, workspace_id: str, metric: str, timeframe: str
    ) -> List[Dict[str, Any]]:
        """Fetch time series data from the database.

        Args:
            workspace_id: Workspace identifier
            metric: Metric name
            timeframe: Time window

        Returns:
            List of timestamp-value pairs
        """
        # Parse timeframe
        days = self._parse_timeframe(timeframe)
        start_date = datetime.utcnow() - timedelta(days=days)

        # Query based on metric type
        query = self._build_time_series_query(metric, workspace_id, start_date)

        result = await self.db.execute(
            text(query), {"workspace_id": workspace_id, "start_date": start_date}
        )
        rows = result.fetchall()

        return [
            {
                "timestamp": row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
                "value": float(row[1]) if row[1] is not None else 0.0,
            }
            for row in rows
        ]

    def _build_time_series_query(self, metric: str, workspace_id: str, start_date: datetime) -> str:
        """Build SQL query for time series data based on metric type."""
        metric_queries = {
            "executions": """
                SELECT
                    DATE_TRUNC('day', created_at) as timestamp,
                    COUNT(*) as value
                FROM analytics.agent_executions
                WHERE workspace_id = :workspace_id
                    AND created_at >= :start_date
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY timestamp
            """,
            "users": """
                SELECT
                    DATE_TRUNC('day', created_at) as timestamp,
                    COUNT(DISTINCT user_id) as value
                FROM analytics.user_activity
                WHERE workspace_id = :workspace_id
                    AND created_at >= :start_date
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY timestamp
            """,
            "credits": """
                SELECT
                    DATE_TRUNC('day', created_at) as timestamp,
                    SUM(credits_consumed) as value
                FROM analytics.agent_executions
                WHERE workspace_id = :workspace_id
                    AND created_at >= :start_date
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY timestamp
            """,
            "errors": """
                SELECT
                    DATE_TRUNC('day', created_at) as timestamp,
                    COUNT(*) as value
                FROM analytics.agent_executions
                WHERE workspace_id = :workspace_id
                    AND status = 'failed'
                    AND created_at >= :start_date
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY timestamp
            """,
            "success_rate": """
                SELECT
                    DATE_TRUNC('day', created_at) as timestamp,
                    (COUNT(*) FILTER (WHERE status = 'completed') * 100.0 /
                     NULLIF(COUNT(*), 0)) as value
                FROM analytics.agent_executions
                WHERE workspace_id = :workspace_id
                    AND created_at >= :start_date
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY timestamp
            """,
        }

        return metric_queries.get(metric, metric_queries["executions"])

    async def _calculate_overview(self, df: pd.DataFrame, metric: str) -> Dict[str, Any]:
        """Calculate trend overview and high-level statistics."""
        if df.empty or len(df) < 2:
            return self._empty_overview()

        current_value = float(df["value"].iloc[-1])
        previous_value = float(df["value"].iloc[0])

        # Calculate change
        change = current_value - previous_value
        change_percentage = (change / previous_value * 100) if previous_value != 0 else 0

        # Determine trend using linear regression
        X = np.arange(len(df)).reshape(-1, 1)
        y = df["value"].values

        model = LinearRegression()
        model.fit(X, y)
        slope = model.coef_[0]
        r_squared = model.score(X, y)

        # Determine trend direction
        if abs(slope) < (np.std(y) * 0.1):
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        # Calculate volatility
        returns = df["value"].pct_change().dropna()
        volatility = float(returns.std() * 100) if len(returns) > 0 else 0

        if volatility > 50:
            trend = "volatile"

        # Trend strength (0-100)
        trend_strength = min(abs(r_squared * 100), 100)

        # Statistical confidence
        confidence = float(r_squared)

        return {
            "currentValue": current_value,
            "previousValue": previous_value,
            "change": change,
            "changePercentage": change_percentage,
            "trend": trend,
            "trendStrength": trend_strength,
            "confidence": confidence,
        }

    async def _perform_decomposition(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Decompose time series into trend, seasonal, and residual components."""
        try:
            if len(df) < 14:
                return self._empty_decomposition()

            # Determine period for decomposition
            period = self._detect_period(df)

            # Handle insufficient data for the detected period
            if len(df) < 2 * period:
                period = max(2, len(df) // 3)

            # Perform decomposition
            decomposition = seasonal_decompose(
                df["value"], model="additive", period=period, extrapolate_trend="freq"
            )

            # Calculate noise level
            residual_std = np.std(decomposition.resid.dropna())
            data_std = np.std(df["value"])
            noise = float(residual_std / data_std * 100) if data_std != 0 else 0

            return {
                "trend": [
                    {"timestamp": ts.isoformat(), "value": float(val) if not pd.isna(val) else None}
                    for ts, val in decomposition.trend.items()
                ],
                "seasonal": [
                    {
                        "timestamp": ts.isoformat(),
                        "value": float(val) if not pd.isna(val) else None,
                        "period": self._get_period_name(period),
                    }
                    for ts, val in decomposition.seasonal.items()
                ],
                "residual": [
                    {"timestamp": ts.isoformat(), "value": float(val) if not pd.isna(val) else None}
                    for ts, val in decomposition.resid.items()
                ],
                "noise": noise,
            }
        except Exception as e:
            logger.warning(f"Decomposition failed: {e}")
            return self._empty_decomposition()

    async def _detect_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect patterns including seasonality, cycles, and growth."""
        seasonality = self._detect_seasonality(df)
        growth = self._detect_growth_pattern(df)
        cycles = self._detect_cycles(df)

        return {"seasonality": seasonality, "growth": growth, "cycles": cycles}

    def _detect_seasonality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect seasonality using autocorrelation analysis."""
        try:
            if len(df) < 14:
                return self._empty_seasonality()

            # Calculate autocorrelation
            acf_values = acf(df["value"], nlags=min(40, len(df) // 2), fft=True)

            # Find peaks in ACF (excluding lag 0)
            peaks, properties = signal.find_peaks(acf_values[1:], height=0.3)

            if len(peaks) > 0:
                # Strongest seasonal period
                strongest_idx = np.argmax(properties["peak_heights"])
                strongest_peak = peaks[strongest_idx]
                period = strongest_peak + 1

                # Determine seasonality type
                season_type = self._classify_seasonality(period)

                # Find peak and low periods
                peak_periods, low_periods = self._find_peak_low_periods(df)

                return {
                    "detected": True,
                    "type": season_type,
                    "strength": float(properties["peak_heights"][strongest_idx] * 100),
                    "peakPeriods": peak_periods,
                    "lowPeriods": low_periods,
                }

            return self._empty_seasonality()

        except Exception as e:
            logger.warning(f"Seasonality detection failed: {e}")
            return self._empty_seasonality()

    def _detect_growth_pattern(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect growth pattern (linear, exponential, etc.)."""
        try:
            if len(df) < 3:
                return self._empty_growth()

            X = np.arange(len(df)).reshape(-1, 1)
            y = df["value"].values

            # Fit linear model
            linear_model = LinearRegression()
            linear_model.fit(X, y)
            linear_r2 = linear_model.score(X, y)
            linear_rate = float(linear_model.coef_[0])

            # Try exponential (using log transform)
            y_positive = y - y.min() + 1  # Ensure positive values
            log_y = np.log(y_positive)
            exp_model = LinearRegression()
            exp_model.fit(X, log_y)
            exp_r2 = exp_model.score(X, log_y)

            # Determine best fit
            if exp_r2 > linear_r2 + 0.1:
                growth_type = "exponential"
                rate = float(np.exp(exp_model.coef_[0]) - 1) * 100
            else:
                growth_type = "linear"
                rate = linear_rate

            # Calculate acceleration (second derivative)
            if len(df) >= 5:
                acceleration = float(np.diff(np.diff(y)).mean())
            else:
                acceleration = 0.0

            # Project growth
            projected_growth = rate * 30  # 30-day projection

            return {
                "type": growth_type,
                "rate": rate,
                "acceleration": acceleration,
                "projectedGrowth": projected_growth,
            }

        except Exception as e:
            logger.warning(f"Growth pattern detection failed: {e}")
            return self._empty_growth()

    def _detect_cycles(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect cyclical patterns using FFT."""
        try:
            if len(df) < 20:
                return []

            # Detrend the data
            X = np.arange(len(df))
            y = df["value"].values
            coeffs = np.polyfit(X, y, 1)
            trend = np.polyval(coeffs, X)
            detrended = y - trend

            # Apply FFT
            fft = np.fft.fft(detrended)
            frequencies = np.fft.fftfreq(len(detrended))

            # Get positive frequencies only
            positive_freq_idx = frequencies > 0
            amplitudes = np.abs(fft[positive_freq_idx])
            frequencies = frequencies[positive_freq_idx]

            # Find significant cycles
            threshold = np.mean(amplitudes) + 2 * np.std(amplitudes)
            significant_indices = amplitudes > threshold

            cycles = []
            for freq, amp in zip(frequencies[significant_indices], amplitudes[significant_indices]):
                if freq > 0:
                    period = 1.0 / freq
                    cycles.append(
                        {
                            "period": float(period),
                            "amplitude": float(amp),
                            "phase": 0.0,  # Simplified
                            "significance": float(amp / np.max(amplitudes)),
                        }
                    )

            # Sort by significance and return top 3
            cycles.sort(key=lambda x: x["significance"], reverse=True)
            return cycles[:3]

        except Exception as e:
            logger.warning(f"Cycle detection failed: {e}")
            return []

    async def _generate_comparisons(self, df: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """Generate period-over-period and year-over-year comparisons."""
        try:
            # Period comparison
            period_comparison = self._calculate_period_comparison(df)

            # Year-over-year (if enough data)
            year_over_year = self._calculate_yoy_comparison(df)

            # Benchmarks (placeholder - would need external data)
            benchmarks = {
                "industryAverage": None,
                "topPerformers": None,
                "position": None,
                "percentile": None,
            }

            return {
                "periodComparison": period_comparison,
                "yearOverYear": year_over_year,
                "benchmarks": benchmarks,
            }

        except Exception as e:
            logger.warning(f"Comparison generation failed: {e}")
            return self._empty_comparisons()

    def _calculate_period_comparison(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate period-over-period comparison."""
        if len(df) < 2:
            return {}

        # Split into two equal periods
        mid_point = len(df) // 2
        current_period = df.iloc[mid_point:]
        previous_period = df.iloc[:mid_point]

        current_value = float(current_period["value"].sum())
        current_avg = float(current_period["value"].mean())
        previous_value = float(previous_period["value"].sum())
        previous_avg = float(previous_period["value"].mean())

        change = current_value - previous_value
        change_percentage = (change / previous_value * 100) if previous_value != 0 else 0

        return {
            "currentPeriod": {
                "start": current_period.index[0].isoformat(),
                "end": current_period.index[-1].isoformat(),
                "value": current_value,
                "avg": current_avg,
            },
            "previousPeriod": {
                "start": previous_period.index[0].isoformat(),
                "end": previous_period.index[-1].isoformat(),
                "value": previous_value,
                "avg": previous_avg,
            },
            "change": change,
            "changePercentage": change_percentage,
        }

    def _calculate_yoy_comparison(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate year-over-year comparison."""
        if len(df) < 365:
            return {
                "currentYear": None,
                "previousYear": None,
                "change": None,
                "changePercentage": None,
                "monthlyComparison": [],
            }

        # This is simplified - would need actual year-based logic
        current_year_data = df.iloc[-365:]
        previous_year_data = df.iloc[-730:-365] if len(df) >= 730 else None

        if previous_year_data is not None:
            current_year = float(current_year_data["value"].sum())
            previous_year = float(previous_year_data["value"].sum())
            change = current_year - previous_year
            change_percentage = (change / previous_year * 100) if previous_year != 0 else 0

            return {
                "currentYear": current_year,
                "previousYear": previous_year,
                "change": change,
                "changePercentage": change_percentage,
                "monthlyComparison": [],  # Would need month-by-month breakdown
            }

        return {
            "currentYear": None,
            "previousYear": None,
            "change": None,
            "changePercentage": None,
            "monthlyComparison": [],
        }

    async def _find_correlations(
        self, workspace_id: str, metric: str, df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Find correlations with other metrics."""
        # This is a placeholder - would need to fetch and compare with other metrics
        return []

    async def _generate_forecast(self, df: pd.DataFrame, metric: str) -> Dict[str, Any]:
        """Generate forecasts using Prophet."""
        try:
            if len(df) < 14:
                return self._empty_forecast()

            # Prepare data for Prophet
            prophet_df = df.reset_index()
            prophet_df.columns = ["ds", "y"]

            # Initialize and fit model
            model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=len(df) >= 14,
                yearly_seasonality=False,
                changepoint_prior_scale=0.05,
            )

            # Suppress Prophet's verbose output
            import logging as prophet_logging

            prophet_logging.getLogger("prophet").setLevel(prophet_logging.WARNING)

            model.fit(prophet_df)

            # Generate future dataframe
            future = model.make_future_dataframe(periods=30, freq="D")
            forecast = model.predict(future)

            # Extract forecasts
            short_term = self._extract_short_term_forecast(forecast, prophet_df)
            long_term = self._extract_long_term_forecast(forecast, prophet_df)
            accuracy = self._calculate_forecast_accuracy(prophet_df, forecast)

            return {"shortTerm": short_term, "longTerm": long_term, "accuracy": accuracy}

        except Exception as e:
            logger.warning(f"Forecast generation failed: {e}")
            return self._empty_forecast()

    def _extract_short_term_forecast(
        self, forecast: pd.DataFrame, historical_df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Extract 7-day short-term forecast."""
        future_forecast = forecast[forecast["ds"] > historical_df["ds"].max()].head(7)

        return [
            {
                "timestamp": row["ds"].isoformat(),
                "predicted": float(max(0, row["yhat"])),
                "upper": float(max(0, row["yhat_upper"])),
                "lower": float(max(0, row["yhat_lower"])),
                "confidence": 0.95,
            }
            for _, row in future_forecast.iterrows()
        ]

    def _extract_long_term_forecast(
        self, forecast: pd.DataFrame, historical_df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Extract long-term monthly forecast."""
        future_forecast = forecast[forecast["ds"] > historical_df["ds"].max()]

        # Resample to monthly
        future_forecast["month"] = future_forecast["ds"].dt.to_period("M")
        monthly = (
            future_forecast.groupby("month")
            .agg({"yhat": "mean", "yhat_lower": "mean", "yhat_upper": "mean"})
            .head(3)
        )

        return [
            {
                "period": str(month),
                "predicted": float(max(0, row["yhat"])),
                "range": {
                    "optimistic": float(max(0, row["yhat_upper"])),
                    "realistic": float(max(0, row["yhat"])),
                    "pessimistic": float(max(0, row["yhat_lower"])),
                },
            }
            for month, row in monthly.iterrows()
        ]

    def _calculate_forecast_accuracy(
        self, historical_df: pd.DataFrame, forecast: pd.DataFrame
    ) -> Dict[str, float]:
        """Calculate forecast accuracy metrics on historical data."""
        # Match historical data with forecast
        merged = historical_df.merge(forecast[["ds", "yhat"]], on="ds", how="inner")

        if len(merged) == 0:
            return {"mape": 0.0, "rmse": 0.0, "r2": 0.0}

        actual = merged["y"].values
        predicted = merged["yhat"].values

        # MAPE (Mean Absolute Percentage Error)
        mape = float(np.mean(np.abs((actual - predicted) / (actual + 1e-10))) * 100)

        # RMSE (Root Mean Square Error)
        rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))

        # R-squared
        ss_res = np.sum((actual - predicted) ** 2)
        ss_tot = np.sum((actual - np.mean(actual)) ** 2)
        r2 = float(1 - (ss_res / (ss_tot + 1e-10)))

        return {
            "mape": min(mape, 100.0),  # Cap at 100%
            "rmse": rmse,
            "r2": max(0.0, min(1.0, r2)),  # Bound between 0 and 1
        }

    def _generate_insights(
        self,
        df: pd.DataFrame,
        overview: Dict[str, Any],
        patterns: Dict[str, Any],
        comparisons: Dict[str, Any],
        forecast: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate actionable insights from analysis."""
        insights = []

        # Trend insight
        if overview.get("trend"):
            insights.append(
                {
                    "type": "trend",
                    "title": f"Metric is {overview['trend']}",
                    "description": f"The metric shows a {overview['trend']} trend with "
                    f"{overview['changePercentage']:.1f}% change.",
                    "impact": "high" if abs(overview.get("changePercentage", 0)) > 20 else "medium",
                    "confidence": overview.get("confidence", 0),
                    "recommendation": self._get_trend_recommendation(
                        overview["trend"], overview.get("changePercentage", 0)
                    ),
                }
            )

        # Seasonality insight
        if patterns.get("seasonality", {}).get("detected"):
            seasonality = patterns["seasonality"]
            insights.append(
                {
                    "type": "pattern",
                    "title": f"{seasonality['type'].capitalize()} seasonality detected",
                    "description": f"Strong {seasonality['type']} pattern with {seasonality['strength']:.1f}% strength.",
                    "impact": "medium",
                    "confidence": seasonality["strength"] / 100,
                    "recommendation": f"Plan capacity for peak periods: {', '.join(seasonality.get('peakPeriods', [])[:3])}",
                }
            )

        # Growth insight
        growth = patterns.get("growth", {})
        if growth.get("type") == "exponential":
            insights.append(
                {
                    "type": "trend",
                    "title": "Exponential growth detected",
                    "description": f"Metric is growing exponentially at {growth.get('rate', 0):.2f}% rate.",
                    "impact": "high",
                    "confidence": 0.8,
                    "recommendation": "Monitor for scalability and resource requirements",
                }
            )

        # Forecast insight
        if forecast.get("shortTerm"):
            next_week = forecast["shortTerm"]
            if len(next_week) > 0:
                avg_forecast = np.mean([f["predicted"] for f in next_week])
                current_avg = df["value"].tail(7).mean()
                forecast_change = (
                    ((avg_forecast - current_avg) / current_avg * 100) if current_avg > 0 else 0
                )

                insights.append(
                    {
                        "type": "forecast",
                        "title": f"Next week forecast: {forecast_change:+.1f}%",
                        "description": f"Predicted {'increase' if forecast_change > 0 else 'decrease'} "
                        f"of {abs(forecast_change):.1f}% in the next 7 days.",
                        "impact": "high" if abs(forecast_change) > 15 else "medium",
                        "confidence": forecast.get("accuracy", {}).get("r2", 0),
                        "recommendation": "Adjust resource allocation accordingly",
                    }
                )

        return insights

    def _prepare_time_series(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Prepare time series data with statistics and anomaly detection."""
        # Calculate moving average
        window_size = min(7, len(df) // 3)
        if window_size >= 2:
            df["moving_average"] = df["value"].rolling(window=window_size, center=True).mean()
        else:
            df["moving_average"] = df["value"]

        # Calculate confidence intervals (mean ± 2 * std)
        mean = df["value"].mean()
        std = df["value"].std()
        df["upper_bound"] = mean + 2 * std
        df["lower_bound"] = mean - 2 * std

        # Detect anomalies (values outside 2 standard deviations)
        df["is_anomaly"] = (df["value"] > df["upper_bound"]) | (df["value"] < df["lower_bound"])

        # Calculate statistics
        statistics = {
            "mean": float(df["value"].mean()),
            "median": float(df["value"].median()),
            "stdDev": float(df["value"].std()),
            "variance": float(df["value"].var()),
            "skewness": float(df["value"].skew()),
            "kurtosis": float(df["value"].kurtosis()),
            "autocorrelation": float(df["value"].autocorr()) if len(df) > 1 else 0.0,
        }

        # Prepare data array
        data = [
            {
                "timestamp": ts.isoformat(),
                "value": float(row["value"]),
                "movingAverage": float(row["moving_average"])
                if not pd.isna(row["moving_average"])
                else float(row["value"]),
                "upperBound": float(row["upper_bound"]),
                "lowerBound": float(row["lower_bound"]),
                "isAnomaly": bool(row["is_anomaly"]),
            }
            for ts, row in df.iterrows()
        ]

        return {"data": data, "statistics": statistics}

    # Helper methods

    def _parse_timeframe(self, timeframe: str) -> int:
        """Parse timeframe string to number of days."""
        mapping = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        return mapping.get(timeframe, 30)

    def _detect_period(self, df: pd.DataFrame) -> int:
        """Detect seasonal period from data."""
        # Try to detect period using ACF
        if len(df) >= 14:
            try:
                acf_values = acf(df["value"], nlags=min(30, len(df) // 2), fft=True)
                peaks, _ = signal.find_peaks(acf_values[1:], height=0.3)
                if len(peaks) > 0:
                    return int(peaks[0] + 1)
            except (ValueError, TypeError):
                # If autocorrelation or peak detection fails, fall back to default period below
                pass

        # Default to weekly if enough data, otherwise smaller period
        return 7 if len(df) >= 14 else max(2, len(df) // 3)

    def _get_period_name(self, period: int) -> str:
        """Get human-readable period name."""
        if period <= 1:
            return "daily"
        elif period <= 7:
            return "weekly"
        elif period <= 31:
            return "monthly"
        elif period <= 92:
            return "quarterly"
        else:
            return "yearly"

    def _classify_seasonality(self, period: int) -> str:
        """Classify seasonality type based on period."""
        if period <= 1:
            return "daily"
        elif period <= 7:
            return "weekly"
        elif period <= 31:
            return "monthly"
        elif period <= 92:
            return "quarterly"
        else:
            return "yearly"

    def _find_peak_low_periods(self, df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        """Find peak and low periods."""
        # Group by day of week
        df_copy = df.copy()
        df_copy["day_of_week"] = df_copy.index.dayofweek
        daily_avg = df_copy.groupby("day_of_week")["value"].mean()

        if len(daily_avg) > 0:
            peak_days = daily_avg.nlargest(2).index.tolist()
            low_days = daily_avg.nsmallest(2).index.tolist()

            day_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            peak_periods = [day_names[d] for d in peak_days if d < len(day_names)]
            low_periods = [day_names[d] for d in low_days if d < len(day_names)]

            return peak_periods, low_periods

        return [], []

    def _get_trend_recommendation(self, trend: str, change_pct: float) -> str:
        """Get recommendation based on trend."""
        recommendations = {
            "increasing": "Monitor for capacity and scaling needs",
            "decreasing": "Investigate root causes and implement corrective actions",
            "stable": "Maintain current strategy and monitor for changes",
            "volatile": "Investigate sources of volatility and implement stabilization measures",
        }
        return recommendations.get(trend, "Continue monitoring")

    # Cache methods

    async def _get_cached_analysis(
        self, workspace_id: str, metric: str, timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis if available and valid."""
        try:
            query = """
                SELECT analysis_data
                FROM analytics.trend_analysis_cache
                WHERE workspace_id = :workspace_id
                    AND metric = :metric
                    AND timeframe = :timeframe
                    AND expires_at > NOW()
                LIMIT 1
            """

            result = await self.db.execute(
                text(query),
                {"workspace_id": workspace_id, "metric": metric, "timeframe": timeframe},
            )
            row = result.fetchone()

            if row:
                return row[0]  # JSONB is automatically parsed

        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")

        return None

    async def _cache_analysis(
        self, workspace_id: str, metric: str, timeframe: str, analysis_data: Dict[str, Any]
    ) -> None:
        """Cache analysis results."""
        try:
            # Determine cache duration based on timeframe
            cache_hours = {"7d": 1, "30d": 6, "90d": 24, "1y": 48}
            hours = cache_hours.get(timeframe, 6)

            query = """
                INSERT INTO analytics.trend_analysis_cache
                    (workspace_id, metric, timeframe, analysis_data, expires_at)
                VALUES
                    (:workspace_id, :metric, :timeframe, :analysis_data, NOW() + :hours * INTERVAL '1 hour')
                ON CONFLICT (workspace_id, metric, timeframe)
                DO UPDATE SET
                    analysis_data = EXCLUDED.analysis_data,
                    calculated_at = NOW(),
                    expires_at = NOW() + :hours * INTERVAL '1 hour'
            """

            await self.db.execute(
                text(query),
                {
                    "workspace_id": workspace_id,
                    "metric": metric,
                    "timeframe": timeframe,
                    "analysis_data": analysis_data,
                    "hours": hours,
                },
            )
            await self.db.commit()

        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")

    # Fallback methods for error handling

    def _get_fallback_result(self, step_index: int) -> Dict[str, Any]:
        """Provide fallback result for failed analysis step."""
        fallbacks = [
            self._empty_overview(),
            self._empty_decomposition(),
            {
                "seasonality": self._empty_seasonality(),
                "growth": self._empty_growth(),
                "cycles": [],
            },
            self._empty_comparisons(),
            [],
            self._empty_forecast(),
        ]
        return fallbacks[step_index] if step_index < len(fallbacks) else {}

    def _insufficient_data_response(
        self, workspace_id: str, metric: str, timeframe: str
    ) -> Dict[str, Any]:
        """Return response for insufficient data."""
        return {
            "workspaceId": workspace_id,
            "metric": metric,
            "timeframe": timeframe,
            "error": "insufficient_data",
            "message": "Not enough data points for trend analysis (minimum 14 required)",
            "overview": self._empty_overview(),
            "timeSeries": {"data": [], "statistics": {}},
            "decomposition": self._empty_decomposition(),
            "patterns": {
                "seasonality": self._empty_seasonality(),
                "growth": self._empty_growth(),
                "cycles": [],
            },
            "comparisons": self._empty_comparisons(),
            "correlations": [],
            "forecast": self._empty_forecast(),
            "insights": [],
        }

    def _empty_overview(self) -> Dict[str, Any]:
        return {
            "currentValue": 0,
            "previousValue": 0,
            "change": 0,
            "changePercentage": 0,
            "trend": "stable",
            "trendStrength": 0,
            "confidence": 0,
        }

    def _empty_decomposition(self) -> Dict[str, Any]:
        return {"trend": [], "seasonal": [], "residual": [], "noise": 0}

    def _empty_seasonality(self) -> Dict[str, Any]:
        return {"detected": False, "type": None, "strength": 0, "peakPeriods": [], "lowPeriods": []}

    def _empty_growth(self) -> Dict[str, Any]:
        return {"type": "linear", "rate": 0, "acceleration": 0, "projectedGrowth": 0}

    def _empty_comparisons(self) -> Dict[str, Any]:
        return {
            "periodComparison": {},
            "yearOverYear": {
                "currentYear": None,
                "previousYear": None,
                "change": None,
                "changePercentage": None,
                "monthlyComparison": [],
            },
            "benchmarks": {
                "industryAverage": None,
                "topPerformers": None,
                "position": None,
                "percentile": None,
            },
        }

    def _empty_forecast(self) -> Dict[str, Any]:
        return {"shortTerm": [], "longTerm": [], "accuracy": {"mape": 0, "rmse": 0, "r2": 0}}
