'use client'

import { useAgents } from '@/hooks/api/useAgents'
import Link from 'next/link'

export default function AgentsPage() {
  const { data: agents, isLoading } = useAgents()

  if (isLoading) return <div>Loading agents...</div>

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-8">Agent Analytics</h1>

      <div className="grid gap-4">
        {agents?.map((agent: any) => (
          <Link
            key={agent.agent_id}
            href={`/agents/${agent.agent_id}`}
            className="p-6 bg-white rounded-lg shadow hover:shadow-lg transition"
          >
            <h3 className="text-xl font-semibold">{agent.agent_name}</h3>
            <div className="mt-2 grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Executions:</span>{' '}
                {agent.total_executions}
              </div>
              <div>
                <span className="text-gray-500">Success Rate:</span>{' '}
                {agent.success_rate}%
              </div>
              <div>
                <span className="text-gray-500">Avg Duration:</span>{' '}
                {agent.avg_duration}s
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
