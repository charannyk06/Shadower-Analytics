import { Optimization } from '@/hooks/api/useCreditConsumption'
import {
  LightBulbIcon,
  ArrowTrendingDownIcon,
  ChartBarIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline'

interface CostOptimizationProps {
  optimizations: Optimization[]
  currentCost: number
}

export function CostOptimization({ optimizations, currentCost }: CostOptimizationProps) {
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'model_switch':
        return <CpuChipIcon className="h-6 w-6" />
      case 'caching':
        return <ChartBarIcon className="h-6 w-6" />
      case 'batch_processing':
        return <ArrowTrendingDownIcon className="h-6 w-6" />
      case 'prompt_optimization':
        return <LightBulbIcon className="h-6 w-6" />
      default:
        return <LightBulbIcon className="h-6 w-6" />
    }
  }

  const getEffortColor = (effort: string) => {
    switch (effort) {
      case 'low':
        return 'bg-green-100 text-green-800'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800'
      case 'high':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const totalPotentialSavings = optimizations.reduce(
    (sum, opt) => sum + opt.potentialSavings,
    0
  )

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Cost Optimization</h3>
        <p className="text-sm text-gray-500">
          Recommendations to reduce your credit consumption
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-blue-50 rounded-lg">
        <div>
          <p className="text-sm text-gray-600">Total Potential Savings</p>
          <p className="text-2xl font-bold text-blue-600">
            ${totalPotentialSavings.toFixed(2)}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {optimizations.length} optimization{optimizations.length !== 1 ? 's' : ''}{' '}
            available
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Current Monthly Cost</p>
          <p className="text-2xl font-bold text-gray-900">${currentCost.toFixed(2)}</p>
          <p className="text-xs text-gray-500 mt-1">
            Could be ${(currentCost - totalPotentialSavings).toFixed(2)}
          </p>
        </div>
      </div>

      {/* Optimization Cards */}
      <div className="space-y-4">
        {optimizations.length === 0 ? (
          <div className="text-center py-8">
            <LightBulbIcon className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <p className="text-sm text-gray-600">No optimization recommendations available</p>
            <p className="text-xs text-gray-500 mt-1">
              Your credit usage is already optimized
            </p>
          </div>
        ) : (
          optimizations.map((opt, index) => (
            <div
              key={index}
              className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 p-2 bg-blue-100 text-blue-600 rounded-lg">
                  {getTypeIcon(opt.type)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h4 className="text-base font-semibold text-gray-900">{opt.title}</h4>
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full whitespace-nowrap ${getEffortColor(
                        opt.effort
                      )}`}
                    >
                      {opt.effort.toUpperCase()} effort
                    </span>
                  </div>

                  <p className="text-sm text-gray-600 mb-3">{opt.description}</p>

                  {/* Savings Metrics */}
                  <div className="grid grid-cols-3 gap-3 mb-3">
                    <div className="text-center p-2 bg-gray-50 rounded">
                      <p className="text-xs text-gray-500">Current Cost</p>
                      <p className="text-sm font-semibold text-gray-900">
                        ${opt.currentCost.toFixed(2)}
                      </p>
                    </div>
                    <div className="text-center p-2 bg-gray-50 rounded">
                      <p className="text-xs text-gray-500">Projected Cost</p>
                      <p className="text-sm font-semibold text-green-600">
                        ${opt.projectedCost.toFixed(2)}
                      </p>
                    </div>
                    <div className="text-center p-2 bg-green-50 rounded">
                      <p className="text-xs text-gray-500">Savings</p>
                      <p className="text-sm font-bold text-green-700">
                        ${opt.potentialSavings.toFixed(2)}
                      </p>
                      <p className="text-xs text-green-600">
                        {opt.savingsPercentage}%
                      </p>
                    </div>
                  </div>

                  {/* Implementation */}
                  <div className="mb-3">
                    <p className="text-xs font-medium text-gray-700 mb-1">
                      Implementation:
                    </p>
                    <p className="text-xs text-gray-600 bg-gray-50 p-2 rounded">
                      {opt.implementation}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <button className="flex-1 px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors">
                      Implement
                    </button>
                    <button className="px-3 py-1.5 border border-gray-300 text-gray-700 text-sm rounded hover:bg-gray-50 transition-colors">
                      Learn More
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
