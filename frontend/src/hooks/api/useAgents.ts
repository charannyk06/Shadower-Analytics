import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'
import { endpoints } from '@/lib/api/endpoints'

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.agents)
      return response.data
    },
  })
}

export function useAgent(agentId: string) {
  return useQuery({
    queryKey: ['agent', agentId],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.agentDetails(agentId))
      return response.data
    },
    enabled: !!agentId,
  })
}

export function useAgentStats(agentId: string) {
  return useQuery({
    queryKey: ['agent-stats', agentId],
    queryFn: async () => {
      const response = await apiClient.get(endpoints.agentStats(agentId))
      return response.data
    },
    enabled: !!agentId,
  })
}
