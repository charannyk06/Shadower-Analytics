export interface AgentMetrics {
  agent_id: string
  agent_name: string
  total_executions: number
  success_rate: number
  avg_duration: number
  last_execution: string | null
}

export interface AgentPerformance {
  agent_id: string
  agent_name: string
  total_executions: number
  successful_executions: number
  failed_executions: number
  success_rate: number
  avg_duration: number
  p95_duration: number
  p99_duration: number
  error_rate: number
  trends?: any[]
}
