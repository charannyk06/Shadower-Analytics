import { CurrentStatus } from '@/hooks/api/useCreditConsumption'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'

interface CreditStatusCardProps {
  status: CurrentStatus
}

export function CreditStatusCard({ status }: CreditStatusCardProps) {
  const getUtilizationColor = (rate: number) => {
    if (rate < 50) return '#10b981'
    if (rate < 75) return '#f59e0b'
    if (rate < 90) return '#f97316'
    return '#ef4444'
  }

  const formatCredits = (credits: number) => {
    if (credits >= 1000000) return `${(credits / 1000000).toFixed(1)}M`
    if (credits >= 1000) return `${(credits / 1000).toFixed(1)}K`
    return credits.toFixed(0)
  }

  const utilizationColor = getUtilizationColor(status.utilizationRate)

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Credit Balance */}
        <div className="text-center">
          <div className="w-32 h-32 mx-auto relative">
            <svg className="transform -rotate-90 w-32 h-32">
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="#f3f4f6"
                strokeWidth="12"
                fill="transparent"
              />
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke={utilizationColor}
                strokeWidth="12"
                fill="transparent"
                strokeDasharray={`${(status.utilizationRate / 100) * 2 * Math.PI * 56} ${2 * Math.PI * 56}`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xl font-bold text-gray-900">
                {status.utilizationRate.toFixed(1)}%
              </span>
            </div>
          </div>
          <p className="mt-2 text-sm text-gray-600">Utilization</p>
          <p className="text-lg font-semibold">
            {formatCredits(status.remainingCredits)} / {formatCredits(status.allocatedCredits)}
          </p>
          <p className="text-xs text-gray-500">Credits Remaining</p>
        </div>

        {/* Burn Rate */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-900">Burn Rate</h3>
          <div className="space-y-2">
            <div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Daily</span>
                <span className="font-medium">{formatCredits(status.dailyBurnRate)}</span>
              </div>
              <div className="mt-1 h-2 bg-gray-200 rounded-full">
                <div
                  className="h-2 bg-blue-600 rounded-full transition-all"
                  style={{
                    width: `${Math.min(
                      (status.dailyBurnRate / (status.allocatedCredits / 30)) * 100,
                      100
                    )}%`
                  }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Weekly</span>
                <span className="font-medium">{formatCredits(status.weeklyBurnRate)}</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Monthly</span>
                <span className="font-medium">{formatCredits(status.monthlyBurnRate)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Projections */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-900">Projections</h3>
          <div className="space-y-2">
            {status.projectedExhaustion && (
              <div className="flex items-start gap-2 p-2 bg-red-50 rounded-lg">
                <ExclamationTriangleIcon className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-red-900">Credits will exhaust</p>
                  <p className="text-red-700">
                    {new Date(status.projectedExhaustion).toLocaleDateString()}
                  </p>
                </div>
              </div>
            )}

            <div>
              <p className="text-sm text-gray-500">Projected Monthly</p>
              <p className="text-lg font-semibold">
                {formatCredits(status.projectedMonthlyUsage)}
              </p>
            </div>

            {status.recommendedTopUp && (
              <div>
                <p className="text-sm text-gray-500">Recommended Top-up</p>
                <p className="text-lg font-semibold text-blue-600">
                  {formatCredits(status.recommendedTopUp)}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Period Info */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-900">Current Period</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Start</span>
              <span>{new Date(status.periodStart).toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">End</span>
              <span>{new Date(status.periodEnd).toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Days Remaining</span>
              <span className="font-medium">{status.daysRemaining}</span>
            </div>
          </div>

          <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm transition-colors">
            Purchase Credits
          </button>
        </div>
      </div>
    </div>
  )
}
