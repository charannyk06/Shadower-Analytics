import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'
import { endpoints } from '@/lib/api/endpoints'

export type TimeFrame = '7d' | '30d' | '90d' | '1y'

interface CreditConsumption {
  workspaceId: string
  timeframe: TimeFrame
  currentStatus: CurrentStatus
  breakdown: ConsumptionBreakdown
  trends: ConsumptionTrends
  budget: BudgetStatus
  costAnalysis: CostAnalysis
  optimizations: Optimization[]
  forecast: UsageForecast
}

interface CurrentStatus {
  allocatedCredits: number
  consumedCredits: number
  remainingCredits: number
  utilizationRate: number
  periodStart: string
  periodEnd: string
  daysRemaining: number
  dailyBurnRate: number
  weeklyBurnRate: number
  monthlyBurnRate: number
  projectedExhaustion: string | null
  projectedMonthlyUsage: number
  recommendedTopUp: number | null
}

interface ConsumptionBreakdown {
  byModel: ModelConsumption[]
  byAgent: AgentConsumption[]
  byUser: UserConsumption[]
  byFeature: FeatureConsumption[]
}

interface ModelConsumption {
  model: string
  provider: 'openai' | 'anthropic' | 'google' | 'other'
  credits: number
  percentage: number
  tokens: number
  calls: number
  avgCreditsPerCall: number
  trend: 'increasing' | 'stable' | 'decreasing'
}

interface AgentConsumption {
  agentId: string
  agentName: string
  credits: number
  percentage: number
  runs: number
  avgCreditsPerRun: number
  efficiency: number
}

interface UserConsumption {
  userId: string
  userName: string
  credits: number
  percentage: number
  executions: number
  avgCreditsPerExecution: number
}

interface FeatureConsumption {
  feature: string
  credits: number
  percentage: number
  usage: number
}

interface ConsumptionTrends {
  daily: DailyConsumption[]
  hourlyPattern: HourlyPattern[]
  weeklyPattern: WeeklyPattern[]
  growthRate: GrowthRate
}

interface DailyConsumption {
  date: string
  credits: number
  cumulative: number
  breakdown: { [model: string]: number }
}

interface HourlyPattern {
  hour: number
  avgCredits: number
  peakDay: string
}

interface WeeklyPattern {
  dayOfWeek: string
  avgCredits: number
}

interface GrowthRate {
  daily: number
  weekly: number
  monthly: number
}

interface BudgetStatus {
  monthlyBudget: number | null
  weeklyBudget: number | null
  dailyLimit: number | null
  budgetUtilization: number
  budgetRemaining: number
  isOverBudget: boolean
  projectedOverage: number | null
  alerts: BudgetAlert[]
  agentLimits: AgentLimit[]
}

interface BudgetAlert {
  type: 'approaching_limit' | 'exceeded_limit' | 'unusual_spike'
  threshold: number
  currentValue: number
  message: string
  triggeredAt: string
}

interface AgentLimit {
  agentId: string
  limit: number
  consumed: number
  remaining: number
}

interface CostAnalysis {
  totalCost: number
  avgCostPerDay: number
  avgCostPerRun: number
  avgCostPerUser: number
  successCost: number
  failureCost: number
  wastedCredits: number
  efficiencyRate: number
  modelComparison: ModelComparison[]
}

interface ModelComparison {
  model: string
  costPer1kTokens: number
  avgResponseCost: number
  qualityScore: number
  costEfficiencyScore: number
}

interface Optimization {
  type: 'model_switch' | 'caching' | 'batch_processing' | 'prompt_optimization'
  title: string
  description: string
  currentCost: number
  projectedCost: number
  potentialSavings: number
  savingsPercentage: number
  implementation: string
  effort: 'low' | 'medium' | 'high'
}

interface UsageForecast {
  nextDay: number
  nextWeek: number
  nextMonth: number
  confidence: {
    low: number
    high: number
  }
  seasonalFactors: {
    weekday: number
    weekend: number
    monthEnd: number
  }
  projectedGrowth: ProjectedGrowth[]
}

interface ProjectedGrowth {
  period: string
  credits: number
  cost: number
}

/**
 * Hook to get comprehensive credit consumption analytics
 */
export function useCreditConsumption(workspaceId: string, timeframe: TimeFrame = '30d') {
  return useQuery<CreditConsumption>({
    queryKey: ['credit-consumption', workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.creditConsumption, {
        params: { workspace_id: workspaceId, timeframe }
      })
      return response.data
    },
    enabled: !!workspaceId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to get current credit status only (lightweight)
 */
export function useCreditStatus(workspaceId: string) {
  return useQuery<{ workspaceId: string; currentStatus: CurrentStatus }>({
    queryKey: ['credit-status', workspaceId],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.creditStatus, {
        params: { workspace_id: workspaceId }
      })
      return response.data
    },
    enabled: !!workspaceId,
    refetchInterval: 30 * 1000, // Refresh every 30 seconds
  })
}

/**
 * Hook to get consumption breakdown by model, agent, and user
 */
export function useCreditBreakdown(workspaceId: string, timeframe: TimeFrame = '30d') {
  return useQuery<{ workspaceId: string; timeframe: string; breakdown: ConsumptionBreakdown }>({
    queryKey: ['credit-breakdown', workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.creditBreakdown, {
        params: { workspace_id: workspaceId, timeframe }
      })
      return response.data
    },
    enabled: !!workspaceId,
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Hook to get consumption trends and patterns
 */
export function useCreditTrends(workspaceId: string, timeframe: TimeFrame = '30d') {
  return useQuery<{ workspaceId: string; timeframe: string; trends: ConsumptionTrends }>({
    queryKey: ['credit-trends', workspaceId, timeframe],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.creditTrends, {
        params: { workspace_id: workspaceId, timeframe }
      })
      return response.data
    },
    enabled: !!workspaceId,
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Hook to get budget status and alerts
 */
export function useCreditBudget(workspaceId: string) {
  return useQuery<{ workspaceId: string; budget: BudgetStatus }>({
    queryKey: ['credit-budget', workspaceId],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.creditBudget, {
        params: { workspace_id: workspaceId }
      })
      return response.data
    },
    enabled: !!workspaceId,
    refetchInterval: 60 * 1000, // Refresh every minute
  })
}

/**
 * Hook to get credit optimization recommendations
 */
export function useCreditOptimization(workspaceId: string) {
  return useQuery<{ workspaceId: string; optimizations: Optimization[] }>({
    queryKey: ['credit-optimization', workspaceId],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.creditOptimization, {
        params: { workspace_id: workspaceId }
      })
      return response.data
    },
    enabled: !!workspaceId,
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}

/**
 * Hook to get credit usage forecast
 */
export function useCreditForecast(workspaceId: string) {
  return useQuery<{ workspaceId: string; forecast: UsageForecast }>({
    queryKey: ['credit-forecast', workspaceId],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.creditForecast, {
        params: { workspace_id: workspaceId }
      })
      return response.data
    },
    enabled: !!workspaceId,
    staleTime: 15 * 60 * 1000, // 15 minutes
  })
}

// Export types for use in components
export type {
  CreditConsumption,
  CurrentStatus,
  ConsumptionBreakdown,
  ModelConsumption,
  AgentConsumption,
  UserConsumption,
  ConsumptionTrends,
  BudgetStatus,
  BudgetAlert,
  CostAnalysis,
  Optimization,
  UsageForecast,
}
