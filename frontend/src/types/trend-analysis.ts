/**
 * Trend Analysis Types
 *
 * TypeScript interfaces for comprehensive time-series analysis and trend detection
 */

export type TimeFrame = '7d' | '30d' | '90d' | '1y';

export type TrendDirection = 'increasing' | 'decreasing' | 'stable' | 'volatile';

export type SeasonalityType = 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';

export type GrowthType = 'linear' | 'exponential' | 'logarithmic' | 'polynomial';

export type InsightType = 'trend' | 'anomaly' | 'pattern' | 'correlation' | 'forecast';

export type ImpactLevel = 'high' | 'medium' | 'low';

export type BenchmarkPosition = 'above' | 'below' | 'at';

export type CorrelationRelationship = 'positive' | 'negative' | 'none';

/**
 * Trend Overview
 * High-level summary of trend characteristics
 */
export interface TrendOverview {
  currentValue: number;
  previousValue: number;
  change: number;
  changePercentage: number;
  trend: TrendDirection;
  trendStrength: number; // 0-100
  confidence: number; // statistical confidence 0-1
}

/**
 * Time Series Data Point
 */
export interface TimeSeriesDataPoint {
  timestamp: string;
  value: number;
  movingAverage: number;
  upperBound: number; // confidence interval
  lowerBound: number;
  isAnomaly: boolean;
}

/**
 * Statistical Measures
 */
export interface TimeSeriesStatistics {
  mean: number;
  median: number;
  stdDev: number;
  variance: number;
  skewness: number;
  kurtosis: number;
  autocorrelation: number;
}

/**
 * Time Series
 */
export interface TimeSeries {
  data: TimeSeriesDataPoint[];
  statistics: TimeSeriesStatistics;
}

/**
 * Decomposition Component
 */
export interface DecompositionComponent {
  timestamp: string;
  value: number | null;
}

/**
 * Seasonal Component (extends Decomposition Component)
 */
export interface SeasonalComponent extends DecompositionComponent {
  period: string; // 'daily', 'weekly', 'monthly'
}

/**
 * Time Series Decomposition
 */
export interface Decomposition {
  trend: DecompositionComponent[];
  seasonal: SeasonalComponent[];
  residual: DecompositionComponent[];
  noise: number; // noise level percentage
}

/**
 * Seasonality Pattern
 */
export interface SeasonalityPattern {
  detected: boolean;
  type: SeasonalityType | null;
  strength: number; // 0-100
  peakPeriods: string[];
  lowPeriods: string[];
}

/**
 * Cyclical Pattern
 */
export interface CyclicalPattern {
  period: number; // days
  amplitude: number;
  phase: number;
  significance: number;
}

/**
 * Growth Pattern
 */
export interface GrowthPattern {
  type: GrowthType;
  rate: number;
  acceleration: number;
  projectedGrowth: number;
}

/**
 * Detected Patterns
 */
export interface Patterns {
  seasonality: SeasonalityPattern;
  cycles: CyclicalPattern[];
  growth: GrowthPattern;
}

/**
 * Period Data (for comparisons)
 */
export interface PeriodData {
  start: string;
  end: string;
  value: number;
  avg: number;
}

/**
 * Period Comparison
 */
export interface PeriodComparison {
  currentPeriod: PeriodData;
  previousPeriod: PeriodData;
  change: number;
  changePercentage: number;
}

/**
 * Monthly Comparison Data
 */
export interface MonthlyComparison {
  month: string;
  current: number;
  previous: number;
  change: number;
}

/**
 * Year over Year Comparison
 */
export interface YearOverYearComparison {
  currentYear: number | null;
  previousYear: number | null;
  change: number | null;
  changePercentage: number | null;
  monthlyComparison: MonthlyComparison[];
}

/**
 * Benchmarks
 */
export interface Benchmarks {
  industryAverage: number | null;
  topPerformers: number | null;
  position: BenchmarkPosition | null;
  percentile: number | null;
}

/**
 * Comparisons
 */
export interface Comparisons {
  periodComparison: PeriodComparison;
  yearOverYear: YearOverYearComparison;
  benchmarks: Benchmarks;
}

/**
 * Correlation
 */
export interface Correlation {
  metric: string;
  correlation: number; // -1 to 1
  lag: number; // time lag in periods
  significance: number;
  relationship: CorrelationRelationship;
}

/**
 * Short-term Forecast Data Point
 */
export interface ShortTermForecast {
  timestamp: string;
  predicted: number;
  upper: number; // confidence interval
  lower: number;
  confidence: number;
}

/**
 * Long-term Forecast Range
 */
export interface ForecastRange {
  optimistic: number;
  realistic: number;
  pessimistic: number;
}

/**
 * Long-term Forecast Data Point
 */
export interface LongTermForecast {
  period: string;
  predicted: number;
  range: ForecastRange;
}

/**
 * Forecast Accuracy Metrics
 */
export interface ForecastAccuracy {
  mape: number; // Mean Absolute Percentage Error
  rmse: number; // Root Mean Square Error
  r2: number; // R-squared
}

/**
 * Forecast
 */
export interface Forecast {
  shortTerm: ShortTermForecast[];
  longTerm: LongTermForecast[];
  accuracy: ForecastAccuracy;
}

/**
 * Insight
 */
export interface Insight {
  type: InsightType;
  title: string;
  description: string;
  impact: ImpactLevel;
  confidence: number;
  recommendation: string;
}

/**
 * Complete Trend Analysis
 */
export interface TrendAnalysis {
  workspaceId: string;
  metric: string;
  timeframe: TimeFrame;

  // Trend Overview
  overview: TrendOverview;

  // Time Series Data
  timeSeries: TimeSeries;

  // Decomposition
  decomposition: Decomposition;

  // Patterns
  patterns: Patterns;

  // Comparisons
  comparisons: Comparisons;

  // Correlations
  correlations: Correlation[];

  // Forecasting
  forecast: Forecast;

  // Insights
  insights: Insight[];

  // Optional error info
  error?: string;
  message?: string;
}

/**
 * Trend Analysis API Request Parameters
 */
export interface TrendAnalysisParams {
  workspaceId: string;
  metric: 'executions' | 'users' | 'credits' | 'errors' | 'success_rate' | 'revenue';
  timeframe: TimeFrame;
}

/**
 * Available Metrics for Trend Analysis
 */
export const AVAILABLE_METRICS = [
  'executions',
  'users',
  'credits',
  'errors',
  'success_rate',
  'revenue'
] as const;

export type AvailableMetric = typeof AVAILABLE_METRICS[number];

/**
 * Metric Display Configuration
 */
export interface MetricConfig {
  value: AvailableMetric;
  label: string;
  description: string;
  unit?: string;
  formatter?: (value: number) => string;
}

/**
 * Timeframe Display Configuration
 */
export interface TimeframeConfig {
  value: TimeFrame;
  label: string;
  days: number;
}
