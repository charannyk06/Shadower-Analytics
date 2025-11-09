"""Advanced trend analysis and forecasting service."""

from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import asyncio
import logging

import numpy as np
import pandas as pd
from scipy import stats, signal
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, acf
from sklearn.linear_model import LinearRegression
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    # Warning will be logged at runtime when forecasting is attempted

from . import trend_analysis_constants as const

logger = logging.getLogger(__name__)

# Timeout constants (in seconds)
PROPHET_TIMEOUT = 30
FFT_TIMEOUT = 10
DECOMPOSITION_TIMEOUT = 15


class TrendAnalysisService:
    """Service for comprehensive trend analysis and forecasting."""

    def __init__(self, db: AsyncSession, cache_service=None):
        self.db = db
        self.cache = cache_service

    async def analyze_trend(
        self,
        workspace_id: str,
        metric: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Perform comprehensive trend analysis.

        Args:
            workspace_id: The workspace ID
            metric: Metric to analyze (executions, users, credits, etc.)
            timeframe: Time period (7d, 30d, 90d, 1y)

        Returns:
            Complete trend analysis with insights
        """
        # Check cache first
        if self.cache:
            cached = await self._get_cached_analysis(workspace_id, metric, timeframe)
            if cached:
                return cached

        # Get time series data
        time_series = await self._get_time_series(workspace_id, metric, timeframe)

        if len(time_series) < 14:  # Need minimum data points
            return self._insufficient_data_response(workspace_id, metric, timeframe)

        # Convert to pandas DataFrame
        df = pd.DataFrame(time_series)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        df.set_index('timestamp', inplace=True)

        # Parallel analysis
        results = await asyncio.gather(
            self._calculate_overview(df),
            self._perform_decomposition(df),
            self._detect_patterns(df),
            self._generate_comparisons(df, workspace_id, metric),
            self._find_correlations(workspace_id, metric, df),
            self._generate_forecast(df),
            return_exceptions=True
        )

        # Check for exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in trend analysis step {i}: {result}")
                results[i] = {}

        # Generate insights based on all analysis
        insights = await self._generate_insights(df, *results)

        analysis = {
            "workspaceId": workspace_id,
            "metric": metric,
            "timeframe": timeframe,
            "overview": results[0] if results[0] else {},
            "timeSeries": self._prepare_time_series(df),
            "decomposition": results[1] if results[1] else {},
            "patterns": results[2] if results[2] else {},
            "comparisons": results[3] if results[3] else {},
            "correlations": results[4] if results[4] else [],
            "forecast": results[5] if results[5] else {},
            "insights": insights
        }

        # Cache the results
        if self.cache:
            await self._cache_analysis(workspace_id, metric, timeframe, analysis)

        return analysis

    async def _get_time_series(
        self,
        workspace_id: str,
        metric: str,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        """Fetch time series data from the database."""
        days = self._parse_timeframe(timeframe)
        start_date = datetime.now() - timedelta(days=days)

        # Build query with parameters to prevent SQL injection
        query_text, params = self._build_metric_query(metric)
        params['workspace_id'] = workspace_id
        params['start_date'] = start_date

        result = await self.db.execute(text(query_text), params)
        rows = result.fetchall()

        return [
            {
                'timestamp': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                'value': float(row[1])
            }
            for row in rows
        ]

    def _build_metric_query(self, metric: str) -> Tuple[str, Dict[str, Any]]:
        """
        Build SQL query for specific metric using parameterized queries.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        queries = {
            'executions': """
                SELECT DATE(created_at) as date, COUNT(*) as value
                FROM public.agent_executions
                WHERE workspace_id = :workspace_id
                AND created_at >= :start_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """,
            'users': """
                SELECT DATE(created_at) as date, COUNT(DISTINCT user_id) as value
                FROM public.agent_executions
                WHERE workspace_id = :workspace_id
                AND created_at >= :start_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """,
            'credits': """
                SELECT DATE(created_at) as date, COALESCE(SUM(credits_used), 0) as value
                FROM public.credit_transactions
                WHERE workspace_id = :workspace_id
                AND created_at >= :start_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """,
            'success_rate': """
                SELECT DATE(created_at) as date,
                       (COUNT(*) FILTER (WHERE status = 'completed') * 100.0 / NULLIF(COUNT(*), 0)) as value
                FROM public.agent_executions
                WHERE workspace_id = :workspace_id
                AND created_at >= :start_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """
        }

        query = queries.get(metric, queries['executions'])
        return query, {}

    async def _calculate_overview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate trend overview statistics."""
        if len(df) < 2:
            return {}

        current_value = float(df['value'].iloc[-1])
        previous_value = float(df['value'].iloc[0])
        change = current_value - previous_value
        change_percentage = (change / previous_value * 100) if previous_value != 0 else 0

        # Determine trend using linear regression
        X = np.arange(len(df)).reshape(-1, 1)
        y = df['value'].values
        model = LinearRegression()
        model.fit(X, y)
        slope = model.coef_[0]

        # Calculate trend strength (R-squared)
        y_pred = model.predict(X)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # Determine trend direction
        volatility = df['value'].std() / df['value'].mean() if df['value'].mean() != 0 else 0

        if volatility > 0.5:
            trend_type = 'volatile'
        elif abs(slope) < df['value'].mean() * 0.01:
            trend_type = 'stable'
        elif slope > 0:
            trend_type = 'increasing'
        else:
            trend_type = 'decreasing'

        # Statistical confidence using t-test
        if len(df) > 2:
            _, p_value = stats.ttest_1samp(df['value'].values, previous_value)
            confidence = (1 - p_value) * 100
        else:
            confidence = 50.0

        return {
            "currentValue": current_value,
            "previousValue": previous_value,
            "change": change,
            "changePercentage": change_percentage,
            "trend": trend_type,
            "trendStrength": min(100, r_squared * 100),
            "confidence": min(100, max(0, confidence))
        }

    async def _perform_decomposition(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Decompose time series into trend, seasonal, and residual components."""
        if len(df) < 14:
            return {}

        try:
            # Determine period for decomposition
            period = self._detect_period(df)

            # Perform decomposition
            decomposition = seasonal_decompose(
                df['value'],
                model='additive',
                period=period,
                extrapolate_trend='freq'
            )

            return {
                "trend": [
                    {
                        "timestamp": ts.isoformat(),
                        "value": float(val) if not pd.isna(val) else None
                    }
                    for ts, val in decomposition.trend.items()
                ],
                "seasonal": [
                    {
                        "timestamp": ts.isoformat(),
                        "value": float(val) if not pd.isna(val) else None,
                        "period": self._get_period_name(period)
                    }
                    for ts, val in decomposition.seasonal.items()
                ],
                "residual": [
                    {
                        "timestamp": ts.isoformat(),
                        "value": float(val) if not pd.isna(val) else None
                    }
                    for ts, val in decomposition.resid.items()
                ],
                "noise": float(np.std(decomposition.resid.dropna()) / np.std(df['value']) * 100)
                    if np.std(df['value']) != 0 else 0
            }
        except Exception as e:
            logger.error(f"Decomposition failed: {e}")
            return {}

    async def _detect_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect patterns in time series."""
        return {
            "seasonality": self._detect_seasonality(df),
            "growth": self._detect_growth_pattern(df),
            "cycles": self._detect_cycles(df)
        }

    def _detect_seasonality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect seasonality in data."""
        if len(df) < 14:
            return {
                "detected": False,
                "type": None,
                "strength": 0,
                "peakPeriods": [],
                "lowPeriods": []
            }

        try:
            # Use autocorrelation to detect seasonality
            acf_values = acf(df['value'].values, nlags=min(40, len(df) // 2), fft=True)

            # Find peaks in ACF
            peaks, properties = signal.find_peaks(acf_values[1:], height=0.3)

            if len(peaks) > 0:
                # Strongest seasonal period
                strongest_idx = np.argmax(properties['peak_heights'])
                strongest_peak = peaks[strongest_idx]
                period = strongest_peak + 1

                # Determine seasonality type
                if period <= 1:
                    season_type = 'daily'
                elif period <= 7:
                    season_type = 'weekly'
                elif period <= 31:
                    season_type = 'monthly'
                elif period <= 92:
                    season_type = 'quarterly'
                else:
                    season_type = 'yearly'

                # Find peak and low periods (using day of week as proxy)
                df_with_dow = df.copy()
                df_with_dow['dow'] = df_with_dow.index.dayofweek
                seasonal_avg = df_with_dow.groupby('dow')['value'].mean()

                peak_periods = seasonal_avg.nlargest(2).index.tolist()
                low_periods = seasonal_avg.nsmallest(2).index.tolist()

                day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

                return {
                    "detected": True,
                    "type": season_type,
                    "strength": float(properties['peak_heights'][strongest_idx] * 100),
                    "peakPeriods": [day_names[d] for d in peak_periods],
                    "lowPeriods": [day_names[d] for d in low_periods]
                }
        except Exception as e:
            logger.error(f"Seasonality detection failed: {e}")

        return {
            "detected": False,
            "type": None,
            "strength": 0,
            "peakPeriods": [],
            "lowPeriods": []
        }

    def _detect_growth_pattern(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect growth pattern."""
        if len(df) < 3:
            return {
                "type": "linear",
                "rate": 0,
                "acceleration": 0,
                "projectedGrowth": 0
            }

        X = np.arange(len(df)).reshape(-1, 1)
        y = df['value'].values

        # Try different growth models
        models = {
            'linear': LinearRegression(),
        }

        best_r2 = -np.inf
        best_type = 'linear'

        # Linear model
        linear_model = LinearRegression()
        linear_model.fit(X, y)
        y_pred = linear_model.predict(X)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        if r2 > best_r2:
            best_r2 = r2
            best_type = 'linear'

        # Exponential model (log transform)
        if np.all(y > 0):
            try:
                log_y = np.log(y)
                exp_model = LinearRegression()
                exp_model.fit(X, log_y)
                log_y_pred = exp_model.predict(X)
                y_pred_exp = np.exp(log_y_pred)
                ss_res = np.sum((y - y_pred_exp) ** 2)
                r2_exp = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

                if r2_exp > best_r2:
                    best_r2 = r2_exp
                    best_type = 'exponential'
            except:
                pass

        # Calculate rate and acceleration
        rate = float(linear_model.coef_[0])

        # Calculate acceleration (second derivative)
        if len(df) >= 3:
            diffs = np.diff(y)
            acceleration = float(np.mean(np.diff(diffs)))
        else:
            acceleration = 0

        # Project growth
        projected_growth = rate * 30  # 30 days ahead

        return {
            "type": best_type,
            "rate": rate,
            "acceleration": acceleration,
            "projectedGrowth": projected_growth
        }

    def _detect_cycles(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect cyclical patterns."""
        if len(df) < 20:
            return []

        try:
            # Use FFT to detect cycles
            values = df['value'].values
            values = values - np.mean(values)  # Remove mean

            # Compute FFT
            fft = np.fft.fft(values)
            frequencies = np.fft.fftfreq(len(values))
            power = np.abs(fft) ** 2

            # Find significant peaks
            peaks, properties = signal.find_peaks(power[:len(power)//2], height=np.max(power) * 0.1)

            cycles = []
            for peak in peaks[:3]:  # Top 3 cycles
                if frequencies[peak] > 0:
                    period = 1 / frequencies[peak]
                    amplitude = np.sqrt(power[peak])
                    phase = np.angle(fft[peak])

                    cycles.append({
                        "period": float(period),
                        "amplitude": float(amplitude),
                        "phase": float(phase),
                        "significance": float(power[peak] / np.sum(power))
                    })

            return cycles
        except Exception as e:
            logger.error(f"Cycle detection failed: {e}")
            return []

    async def _generate_comparisons(
        self,
        df: pd.DataFrame,
        workspace_id: str,
        metric: str
    ) -> Dict[str, Any]:
        """Generate period comparisons."""
        # Period over period comparison
        mid_point = len(df) // 2
        current_period = df.iloc[mid_point:]
        previous_period = df.iloc[:mid_point]

        current_value = current_period['value'].sum()
        previous_value = previous_period['value'].sum()
        change = current_value - previous_value
        change_pct = (change / previous_value * 100) if previous_value != 0 else 0

        comparison = {
            "periodComparison": {
                "currentPeriod": {
                    "start": current_period.index[0].isoformat(),
                    "end": current_period.index[-1].isoformat(),
                    "value": float(current_value),
                    "avg": float(current_period['value'].mean())
                },
                "previousPeriod": {
                    "start": previous_period.index[0].isoformat(),
                    "end": previous_period.index[-1].isoformat(),
                    "value": float(previous_value),
                    "avg": float(previous_period['value'].mean())
                },
                "change": float(change),
                "changePercentage": float(change_pct)
            },
            "yearOverYear": {},
            "benchmarks": {
                "industryAverage": 0,
                "topPerformers": 0,
                "position": "at",
                "percentile": 50
            }
        }

        return comparison

    async def _find_correlations(
        self,
        workspace_id: str,
        metric: str,
        df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Find correlations with other metrics."""
        # Placeholder - would need to fetch other metrics
        return []

    async def _generate_forecast(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate time series forecast."""
        if not PROPHET_AVAILABLE:
            logger.warning("Prophet not available. Using simple linear forecasting instead.")
            return self._simple_forecast(df)

        if len(df) < 14:
            return self._simple_forecast(df)

        try:
            # Prepare data for Prophet
            prophet_df = df.reset_index()
            prophet_df.columns = ['ds', 'y']

            # Initialize and fit model
            model = Prophet(
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False,
                seasonality_mode='additive'
            )

            # Suppress Prophet output
            import logging as prophet_logging
            prophet_logging.getLogger('prophet').setLevel(prophet_logging.WARNING)

            model.fit(prophet_df)

            # Generate forecast
            future = model.make_future_dataframe(periods=30, freq='D')
            forecast = model.predict(future)

            # Extract short-term forecast (next 7 days)
            short_term = forecast[forecast['ds'] > prophet_df['ds'].max()].head(7)

            # Calculate accuracy metrics on historical data
            historical_forecast = forecast[forecast['ds'] <= prophet_df['ds'].max()]
            actual = prophet_df['y'].values
            predicted = historical_forecast['yhat'].values[:len(actual)]

            mape = np.mean(np.abs((actual - predicted) / (actual + 1e-10))) * 100
            rmse = np.sqrt(np.mean((actual - predicted) ** 2))
            r2 = 1 - (np.sum((actual - predicted) ** 2) / (np.sum((actual - np.mean(actual)) ** 2) + 1e-10))

            return {
                "shortTerm": [
                    {
                        "timestamp": row['ds'].isoformat(),
                        "predicted": float(row['yhat']),
                        "upper": float(row['yhat_upper']),
                        "lower": float(row['yhat_lower']),
                        "confidence": 0.95
                    }
                    for _, row in short_term.iterrows()
                ],
                "longTerm": [],
                "accuracy": {
                    "mape": float(mape),
                    "rmse": float(rmse),
                    "r2": float(max(0, min(1, r2)))
                }
            }
        except Exception as e:
            logger.error(f"Prophet forecast failed: {e}")
            return self._simple_forecast(df)

    def _simple_forecast(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simple linear forecast when Prophet is unavailable."""
        if len(df) < 2:
            return {"shortTerm": [], "longTerm": [], "accuracy": {}}

        X = np.arange(len(df)).reshape(-1, 1)
        y = df['value'].values
        model = LinearRegression()
        model.fit(X, y)

        # Forecast next 7 days
        future_X = np.arange(len(df), len(df) + 7).reshape(-1, 1)
        predictions = model.predict(future_X)

        # Calculate simple confidence interval
        residuals = y - model.predict(X)
        std_error = np.std(residuals)

        short_term = []
        for i, pred in enumerate(predictions):
            timestamp = df.index[-1] + timedelta(days=i+1)
            short_term.append({
                "timestamp": timestamp.isoformat(),
                "predicted": float(pred),
                "upper": float(pred + 1.96 * std_error),
                "lower": float(max(0, pred - 1.96 * std_error)),
                "confidence": 0.95
            })

        return {
            "shortTerm": short_term,
            "longTerm": [],
            "accuracy": {"mape": 0, "rmse": float(std_error), "r2": 0}
        }

    async def _generate_insights(self, df: pd.DataFrame, *analysis_results) -> List[Dict[str, Any]]:
        """Generate actionable insights from analysis."""
        insights = []

        overview = analysis_results[0] if analysis_results else {}
        patterns = analysis_results[2] if len(analysis_results) > 2 else {}
        forecast = analysis_results[5] if len(analysis_results) > 5 else {}

        # Trend insight
        if overview and overview.get('trend'):
            trend = overview['trend']
            change_pct = overview.get('changePercentage', 0)

            if trend == 'increasing' and change_pct > 20:
                insights.append({
                    "type": "trend",
                    "title": "Strong Growth Detected",
                    "description": f"Metric has increased by {change_pct:.1f}% over the period",
                    "impact": "high",
                    "confidence": overview.get('confidence', 50),
                    "recommendation": "Continue current strategies and monitor for sustainability"
                })
            elif trend == 'decreasing' and change_pct < -20:
                insights.append({
                    "type": "trend",
                    "title": "Significant Decline Detected",
                    "description": f"Metric has decreased by {abs(change_pct):.1f}% over the period",
                    "impact": "high",
                    "confidence": overview.get('confidence', 50),
                    "recommendation": "Investigate root causes and implement corrective measures"
                })

        # Seasonality insight
        if patterns and patterns.get('seasonality', {}).get('detected'):
            seasonality = patterns['seasonality']
            insights.append({
                "type": "pattern",
                "title": f"{seasonality['type'].title()} Seasonality Detected",
                "description": f"Strong {seasonality['type']} pattern with {seasonality['strength']:.1f}% strength",
                "impact": "medium",
                "confidence": seasonality['strength'],
                "recommendation": f"Plan resources around peak periods: {', '.join(seasonality.get('peakPeriods', []))}"
            })

        # Forecast insight
        if forecast and forecast.get('shortTerm'):
            next_week = forecast['shortTerm']
            if next_week:
                avg_forecast = np.mean([p['predicted'] for p in next_week])
                current_avg = df['value'].tail(7).mean()
                forecast_change = ((avg_forecast - current_avg) / current_avg * 100) if current_avg != 0 else 0

                if abs(forecast_change) > 15:
                    insights.append({
                        "type": "forecast",
                        "title": "Significant Change Expected",
                        "description": f"Next week forecast shows {abs(forecast_change):.1f}% {'increase' if forecast_change > 0 else 'decrease'}",
                        "impact": "medium",
                        "confidence": 70,
                        "recommendation": "Prepare for anticipated changes in metric levels"
                    })

        return insights

    def _prepare_time_series(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Prepare time series data with statistics."""
        # Calculate moving average
        ma_window = min(7, len(df) // 3)
        if ma_window > 0:
            df['ma'] = df['value'].rolling(window=ma_window, min_periods=1).mean()
        else:
            df['ma'] = df['value']

        # Calculate confidence intervals
        std = df['value'].std()
        df['upper'] = df['ma'] + 1.96 * std
        df['lower'] = df['ma'] - 1.96 * std

        # Detect anomalies
        df['is_anomaly'] = (df['value'] > df['upper']) | (df['value'] < df['lower'])

        data = [
            {
                "timestamp": ts.isoformat(),
                "value": float(row['value']),
                "movingAverage": float(row['ma']),
                "upperBound": float(row['upper']),
                "lowerBound": float(row['lower']),
                "isAnomaly": bool(row['is_anomaly'])
            }
            for ts, row in df.iterrows()
        ]

        # Calculate statistics
        statistics = {
            "mean": float(df['value'].mean()),
            "median": float(df['value'].median()),
            "stdDev": float(df['value'].std()),
            "variance": float(df['value'].var()),
            "skewness": float(df['value'].skew()),
            "kurtosis": float(df['value'].kurtosis()),
            "autocorrelation": float(df['value'].autocorr()) if len(df) > 1 else 0
        }

        return {
            "data": data,
            "statistics": statistics
        }

    def _detect_period(self, df: pd.DataFrame) -> int:
        """Detect the dominant period in the data."""
        if len(df) < 14:
            return 7

        try:
            acf_values = acf(df['value'].values, nlags=min(40, len(df) // 2), fft=True)
            peaks, _ = signal.find_peaks(acf_values[1:])

            if len(peaks) > 0:
                return min(peaks[0] + 1, len(df) // 2)
        except:
            pass

        return 7  # Default to weekly

    def _get_period_name(self, period: int) -> str:
        """Get human-readable period name."""
        if period <= 1:
            return 'daily'
        elif period <= 7:
            return 'weekly'
        elif period <= 31:
            return 'monthly'
        else:
            return 'quarterly'

    def _parse_timeframe(self, timeframe: str) -> int:
        """Parse timeframe string to days."""
        mapping = {
            '7d': 7,
            '30d': 30,
            '90d': 90,
            '1y': 365
        }
        return mapping.get(timeframe, 30)

    def _insufficient_data_response(
        self,
        workspace_id: str,
        metric: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """Return response when insufficient data."""
        return {
            "workspaceId": workspace_id,
            "metric": metric,
            "timeframe": timeframe,
            "error": "insufficient_data",
            "message": "Not enough data points for comprehensive analysis. Minimum 14 days required.",
            "overview": {},
            "timeSeries": {"data": [], "statistics": {}},
            "decomposition": {},
            "patterns": {},
            "comparisons": {},
            "correlations": [],
            "forecast": {},
            "insights": []
        }

    async def _get_cached_analysis(
        self,
        workspace_id: str,
        metric: str,
        timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached analysis if available and not expired."""
        try:
            query = text("""
                SELECT analysis_data
                FROM analytics.trend_analysis_cache
                WHERE workspace_id = :workspace_id
                AND metric = :metric
                AND timeframe = :timeframe
                AND (expires_at IS NULL OR expires_at > NOW())
            """)

            result = await self.db.execute(
                query,
                {
                    "workspace_id": workspace_id,
                    "metric": metric,
                    "timeframe": timeframe
                }
            )
            row = result.fetchone()

            if row:
                return row[0]
        except Exception as e:
            logger.error(f"Cache retrieval failed: {e}")

        return None

    async def _cache_analysis(
        self,
        workspace_id: str,
        metric: str,
        timeframe: str,
        analysis: Dict[str, Any]
    ):
        """Cache analysis results."""
        try:
            # Cache expires after 1 hour
            expires_at = datetime.now() + timedelta(hours=1)

            query = text("""
                INSERT INTO analytics.trend_analysis_cache
                (workspace_id, metric, timeframe, analysis_data, expires_at)
                VALUES (:workspace_id, :metric, :timeframe, :analysis_data, :expires_at)
                ON CONFLICT (workspace_id, metric, timeframe)
                DO UPDATE SET
                    analysis_data = :analysis_data,
                    expires_at = :expires_at,
                    calculated_at = NOW()
            """)

            await self.db.execute(
                query,
                {
                    "workspace_id": workspace_id,
                    "metric": metric,
                    "timeframe": timeframe,
                    "analysis_data": analysis,
                    "expires_at": expires_at
                }
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Cache storage failed: {e}")


# Backward compatibility functions
async def analyze_metric_trend(
    db: AsyncSession,
    metric_name: str,
    start_date: date,
    end_date: date,
) -> Dict:
    """Analyze trend for a specific metric (legacy interface)."""
    service = TrendAnalysisService(db)
    days = (end_date - start_date).days
    timeframe = '7d' if days <= 7 else '30d' if days <= 30 else '90d'

    result = await service.analyze_trend('default', metric_name, timeframe)
    return result.get('overview', {
        "trend": "stable",
        "rate_of_change": 0.0,
        "confidence": 0.0,
    })


async def detect_seasonality(
    db: AsyncSession,
    metric_name: str,
    start_date: date,
    end_date: date,
) -> Dict:
    """Detect seasonal patterns in metric data (legacy interface)."""
    service = TrendAnalysisService(db)
    days = (end_date - start_date).days
    timeframe = '7d' if days <= 7 else '30d' if days <= 30 else '90d'

    result = await service.analyze_trend('default', metric_name, timeframe)
    seasonality = result.get('patterns', {}).get('seasonality', {})

    return {
        "has_seasonality": seasonality.get('detected', False),
        "period": seasonality.get('type'),
        "strength": seasonality.get('strength', 0.0) / 100,
    }


async def forecast_metric(
    db: AsyncSession,
    metric_name: str,
    periods: int = 30,
) -> List[Dict]:
    """Forecast future values for a metric (legacy interface)."""
    service = TrendAnalysisService(db)
    result = await service.analyze_trend('default', metric_name, '90d')
    forecast = result.get('forecast', {}).get('shortTerm', [])

    return forecast[:periods]
