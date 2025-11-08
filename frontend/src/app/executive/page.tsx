'use client'

import { useMetrics } from '@/hooks/api/useMetrics'

export default function ExecutivePage() {
  const { data: metrics, isLoading, error } = useMetrics()

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error loading metrics</div>

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-8">Executive Dashboard</h1>

      <div className="grid grid-cols-3 gap-6">
        <div className="p-6 bg-white rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">MRR</h3>
          <p className="text-3xl font-bold">${metrics?.mrr || 0}</p>
        </div>

        <div className="p-6 bg-white rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">DAU</h3>
          <p className="text-3xl font-bold">{metrics?.dau || 0}</p>
        </div>

        <div className="p-6 bg-white rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">MAU</h3>
          <p className="text-3xl font-bold">{metrics?.mau || 0}</p>
        </div>
      </div>
    </div>
  )
}
