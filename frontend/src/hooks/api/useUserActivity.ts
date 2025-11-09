import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'
import { endpoints } from '@/lib/api/endpoints'
import type { UserActivityData, TimeFrame } from '@/types/user-activity'

interface UseUserActivityOptions {
  workspaceId: string
  timeframe?: TimeFrame
  segmentId?: string
  enabled?: boolean
}

export function useUserActivity({
  workspaceId,
  timeframe = '30d',
  segmentId,
  enabled = true,
}: UseUserActivityOptions) {
  return useQuery<UserActivityData>({
    queryKey: ['user-activity', workspaceId, timeframe, segmentId],
    queryFn: async () => {
      const params = new URLSearchParams({ timeframe })
      if (segmentId) {
        params.append('segment_id', segmentId)
      }

      const response = await apiClient.get(
        `${endpoints.userActivityAnalytics(workspaceId)}?${params.toString()}`
      )
      return response.data
    },
    enabled: enabled && !!workspaceId,
    refetchInterval: 300000, // Refresh every 5 minutes
  })
}

interface UseRetentionCurveOptions {
  workspaceId: string
  cohortDate: string
  days?: number
  enabled?: boolean
}

export function useRetentionCurve({
  workspaceId,
  cohortDate,
  days = 90,
  enabled = true,
}: UseRetentionCurveOptions) {
  return useQuery({
    queryKey: ['retention-curve', workspaceId, cohortDate, days],
    queryFn: async () => {
      const params = new URLSearchParams({
        cohort_date: cohortDate,
        days: days.toString(),
      })

      const response = await apiClient.get(
        `${endpoints.retentionCurve(workspaceId)}?${params.toString()}`
      )
      return response.data
    },
    enabled: enabled && !!workspaceId && !!cohortDate,
  })
}

interface UseCohortAnalysisOptions {
  workspaceId: string
  cohortType?: 'daily' | 'weekly' | 'monthly'
  startDate?: string
  endDate?: string
  enabled?: boolean
}

export function useCohortAnalysis({
  workspaceId,
  cohortType = 'monthly',
  startDate,
  endDate,
  enabled = true,
}: UseCohortAnalysisOptions) {
  return useQuery({
    queryKey: ['cohort-analysis', workspaceId, cohortType, startDate, endDate],
    queryFn: async () => {
      const params = new URLSearchParams({ cohort_type: cohortType })
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)

      const response = await apiClient.get(
        `${endpoints.cohortAnalysis(workspaceId)}?${params.toString()}`
      )
      return response.data
    },
    enabled: enabled && !!workspaceId,
  })
}

interface UseChurnAnalysisOptions {
  workspaceId: string
  timeframe?: TimeFrame
  enabled?: boolean
}

export function useChurnAnalysis({
  workspaceId,
  timeframe = '30d',
  enabled = true,
}: UseChurnAnalysisOptions) {
  return useQuery({
    queryKey: ['churn-analysis', workspaceId, timeframe],
    queryFn: async () => {
      const params = new URLSearchParams({ timeframe })

      const response = await apiClient.get(
        `${endpoints.churnAnalysis(workspaceId)}?${params.toString()}`
      )
      return response.data
    },
    enabled: enabled && !!workspaceId,
  })
}
