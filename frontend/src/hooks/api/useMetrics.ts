import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'
import { endpoints } from '@/lib/api/endpoints'

export function useMetrics() {
  return useQuery({
    queryKey: ['executive-metrics'],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.executiveOverview)
      return response.data
    },
  })
}

export function useMetricsSummary() {
  return useQuery({
    queryKey: ['metrics-summary'],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.metricsSummary)
      return response.data
    },
  })
}

export function useRealtimeMetrics() {
  return useQuery({
    queryKey: ['realtime-metrics'],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.realtimeMetrics)
      return response.data
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  })
}
