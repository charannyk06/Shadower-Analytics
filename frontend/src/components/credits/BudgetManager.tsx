import { BudgetStatus } from '@/hooks/api/useCreditConsumption'
import { ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline'

interface BudgetManagerProps {
  budget: BudgetStatus
}

export function BudgetManager({ budget }: BudgetManagerProps) {
  const formatCredits = (credits: number) => {
    if (credits >= 1000000) return `${(credits / 1000000).toFixed(1)}M`
    if (credits >= 1000) return `${(credits / 1000).toFixed(1)}K`
    return credits.toFixed(0)
  }

  const getAlertColor = (type: string) => {
    switch (type) {
      case 'exceeded_limit':
        return 'bg-red-50 border-red-200 text-red-800'
      case 'approaching_limit':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800'
      case 'unusual_spike':
        return 'bg-orange-50 border-orange-200 text-orange-800'
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800'
    }
  }

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'exceeded_limit':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-600" />
      default:
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600" />
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Budget Management</h3>
        <p className="text-sm text-gray-500">Monitor and control your credit spending</p>
      </div>

      {/* Budget Overview */}
      <div className="space-y-4 mb-6">
        {budget.monthlyBudget && (
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600">Monthly Budget</span>
              <span className="font-medium">
                {formatCredits(budget.budgetRemaining)} / {formatCredits(budget.monthlyBudget)}
              </span>
            </div>
            <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  budget.budgetUtilization > 90
                    ? 'bg-red-600'
                    : budget.budgetUtilization > 75
                    ? 'bg-yellow-600'
                    : 'bg-green-600'
                }`}
                style={{ width: `${Math.min(budget.budgetUtilization, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs mt-1">
              <span className="text-gray-500">{budget.budgetUtilization.toFixed(1)}% used</span>
              {budget.isOverBudget && (
                <span className="text-red-600 font-medium">Over budget</span>
              )}
            </div>
          </div>
        )}

        {/* Budget Status Cards */}
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500">Monthly</p>
            <p className="text-lg font-semibold text-gray-900">
              {budget.monthlyBudget ? formatCredits(budget.monthlyBudget) : 'N/A'}
            </p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500">Weekly</p>
            <p className="text-lg font-semibold text-gray-900">
              {budget.weeklyBudget ? formatCredits(budget.weeklyBudget) : 'N/A'}
            </p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500">Daily</p>
            <p className="text-lg font-semibold text-gray-900">
              {budget.dailyLimit ? formatCredits(budget.dailyLimit) : 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* Active Alerts */}
      {budget.alerts.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">Active Alerts</h4>
          <div className="space-y-2">
            {budget.alerts.slice(0, 3).map((alert, index) => (
              <div
                key={index}
                className={`flex items-start gap-2 p-3 rounded-lg border ${getAlertColor(
                  alert.type
                )}`}
              >
                <div className="flex-shrink-0 mt-0.5">{getAlertIcon(alert.type)}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{alert.message}</p>
                  <p className="text-xs mt-1 opacity-75">
                    Threshold: {formatCredits(alert.threshold)} | Current:{' '}
                    {formatCredits(alert.currentValue)}
                  </p>
                  <p className="text-xs mt-1 opacity-75">
                    {new Date(alert.triggeredAt).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Alerts */}
      {budget.alerts.length === 0 && (
        <div className="text-center py-6">
          <CheckCircleIcon className="h-12 w-12 text-green-500 mx-auto mb-2" />
          <p className="text-sm text-gray-600">No active budget alerts</p>
          <p className="text-xs text-gray-500 mt-1">Your spending is within budget limits</p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-6 flex gap-3">
        <button className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
          Configure Budget
        </button>
        <button className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          View All Alerts
        </button>
      </div>
    </div>
  )
}
