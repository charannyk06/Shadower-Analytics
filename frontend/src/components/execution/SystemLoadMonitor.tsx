/**
 * System Load Monitor Component
 * Displays current system resource utilization
 */

'use client'

import { SystemLoad } from '@/types/execution'

interface SystemLoadMonitorProps {
  load?: SystemLoad
}

export function SystemLoadMonitor({ load }: SystemLoadMonitorProps) {
  if (!load) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">System Load</h3>
        <p className="text-gray-500 text-sm">No data available</p>
      </div>
    )
  }

  const getLoadColor = (value: number) => {
    if (value < 50) return 'bg-green-500'
    if (value < 75) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getLoadTextColor = (value: number) => {
    if (value < 50) return 'text-green-600'
    if (value < 75) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4 text-gray-900">System Load</h3>

      <div className="space-y-4">
        {/* CPU Usage */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-sm font-medium text-gray-700">CPU</span>
            <span className={`text-sm font-semibold ${getLoadTextColor(load.cpu)}`}>
              {load.cpu.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getLoadColor(load.cpu)} transition-all duration-500`}
              style={{ width: `${load.cpu}%` }}
            />
          </div>
        </div>

        {/* Memory Usage */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-sm font-medium text-gray-700">Memory</span>
            <span className={`text-sm font-semibold ${getLoadTextColor(load.memory)}`}>
              {load.memory.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getLoadColor(load.memory)} transition-all duration-500`}
              style={{ width: `${load.memory}%` }}
            />
          </div>
        </div>

        {/* Workers */}
        <div className="pt-3 border-t border-gray-200">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-700">Workers</span>
            <div className="flex items-center space-x-2 text-sm">
              <span className="text-green-600 font-semibold">{load.workers.busy}</span>
              <span className="text-gray-400">/</span>
              <span className="text-gray-600">{load.workers.total}</span>
            </div>
          </div>
          <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
            <div className="text-center">
              <div className="text-gray-500">Total</div>
              <div className="font-semibold text-gray-900">{load.workers.total}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-500">Busy</div>
              <div className="font-semibold text-green-600">{load.workers.busy}</div>
            </div>
            <div className="text-center">
              <div className="text-gray-500">Idle</div>
              <div className="font-semibold text-gray-600">{load.workers.idle}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
