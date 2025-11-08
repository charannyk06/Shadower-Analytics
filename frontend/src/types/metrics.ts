export interface ExecutiveMetrics {
  mrr: number
  churn_rate: number
  ltv: number
  dau: number
  wau: number
  mau: number
  total_executions: number
  success_rate: number
}

export interface MetricValue {
  timestamp: string
  value: number
  metric_name: string
}

export interface MetricTrend {
  metric_name: string
  values: MetricValue[]
  trend_direction: 'up' | 'down' | 'stable'
  change_percentage: number
}
