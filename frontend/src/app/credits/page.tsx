'use client'

import { useState } from 'react'
import { useCreditConsumption, TimeFrame } from '@/hooks/api/useCreditConsumption'
import { CreditStatusCard } from '@/components/credits/CreditStatusCard'
import { ConsumptionChart } from '@/components/credits/ConsumptionChart'
import { ModelBreakdown } from '@/components/credits/ModelBreakdown'
import { BudgetManager } from '@/components/credits/BudgetManager'
import { CostOptimization } from '@/components/credits/CostOptimization'
import { ArrowDownTrayIcon } from '@heroicons/react/24/outline'

export default function CreditConsumptionDashboard() {
  const [timeframe, setTimeframe] = useState<TimeFrame>('30d')
  const [view, setView] = useState<'overview' | 'breakdown' | 'optimization'>('overview')

  // TODO: Get workspace ID from auth context
  const workspaceId = 'demo-workspace-id'

  const { data, isLoading, error } = useCreditConsumption(workspaceId, timeframe)

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading credit consumption data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-red-900 mb-2">Error Loading Data</h3>
            <p className="text-sm text-red-700">
              Failed to load credit consumption data. Please try again later.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Credit Consumption</h1>
            <p className="mt-1 text-sm text-gray-500">
              Track and optimize your credit usage
            </p>
          </div>

          <div className="flex gap-4">
            {/* Timeframe Selector */}
            <div className="flex bg-white rounded-lg shadow-sm border border-gray-200">
              {(['7d', '30d', '90d', '1y'] as TimeFrame[]).map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    timeframe === tf
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-700 hover:bg-gray-50'
                  } ${tf === '7d' ? 'rounded-l-lg' : ''} ${
                    tf === '1y' ? 'rounded-r-lg' : ''
                  }`}
                >
                  {tf.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Export Button */}
            <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors shadow-sm">
              <ArrowDownTrayIcon className="h-4 w-4" />
              Export
            </button>
          </div>
        </div>

        {/* Credit Status */}
        <CreditStatusCard status={data.currentStatus} />

        {/* View Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {['overview', 'breakdown', 'optimization'].map((v) => (
              <button
                key={v}
                onClick={() => setView(v as any)}
                className={`py-2 px-1 border-b-2 font-medium text-sm capitalize transition-colors ${
                  view === v
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {v}
              </button>
            ))}
          </nav>
        </div>

        {/* Content based on view */}
        {view === 'overview' && (
          <div className="space-y-6">
            {/* Consumption Chart */}
            <ConsumptionChart trends={data.trends} />

            {/* Budget vs Forecast */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <BudgetManager budget={data.budget} />

              {/* Usage Forecast Card */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Usage Forecast</h3>
                  <p className="text-sm text-gray-500">Predicted credit consumption</p>
                </div>

                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm text-gray-600">Next Day</p>
                      <p className="text-lg font-semibold text-gray-900">
                        {data.forecast.nextDay.toLocaleString()} credits
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm text-gray-600">Next Week</p>
                      <p className="text-lg font-semibold text-gray-900">
                        {data.forecast.nextWeek.toLocaleString()} credits
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                    <div>
                      <p className="text-sm text-gray-600">Next Month</p>
                      <p className="text-lg font-semibold text-blue-900">
                        {data.forecast.nextMonth.toLocaleString()} credits
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        95% confidence: {data.forecast.confidence.low.toLocaleString()} -{' '}
                        {data.forecast.confidence.high.toLocaleString()}
                      </p>
                    </div>
                  </div>

                  {/* Seasonal Factors */}
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <p className="text-xs font-medium text-gray-700 mb-2">
                      Seasonal Patterns
                    </p>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="text-center">
                        <p className="text-gray-500">Weekday</p>
                        <p className="font-semibold">
                          {data.forecast.seasonalFactors.weekday.toLocaleString()}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-500">Weekend</p>
                        <p className="font-semibold">
                          {data.forecast.seasonalFactors.weekend.toLocaleString()}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-500">Month End</p>
                        <p className="font-semibold">
                          {data.forecast.seasonalFactors.monthEnd.toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {view === 'breakdown' && (
          <div className="space-y-6">
            {/* Model Breakdown */}
            <ModelBreakdown breakdown={data.breakdown.byModel} />

            {/* Agent and User Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Agent Consumption */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Top Agents</h3>
                  <p className="text-sm text-gray-500">Credit usage by agent</p>
                </div>

                <div className="space-y-2">
                  {data.breakdown.byAgent.slice(0, 10).map((agent, index) => (
                    <div
                      key={agent.agentId}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          {agent.agentName}
                        </p>
                        <p className="text-xs text-gray-500">
                          {agent.runs} runs • {agent.avgCreditsPerRun.toFixed(2)} avg/run
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold text-gray-900">
                          {agent.credits.toLocaleString()}
                        </p>
                        <p className="text-xs text-gray-500">
                          {agent.percentage.toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* User Consumption */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Top Users</h3>
                  <p className="text-sm text-gray-500">Credit usage by user</p>
                </div>

                <div className="space-y-2">
                  {data.breakdown.byUser.slice(0, 10).map((user, index) => (
                    <div
                      key={user.userId}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">{user.userName}</p>
                        <p className="text-xs text-gray-500">
                          {user.executions} executions
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold text-gray-900">
                          {user.credits.toLocaleString()}
                        </p>
                        <p className="text-xs text-gray-500">
                          {user.percentage.toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Cost Analysis */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Cost Analysis</h3>
                <p className="text-sm text-gray-500">Detailed cost breakdown and efficiency</p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">Total Cost</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${data.costAnalysis.totalCost.toFixed(2)}
                  </p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">Avg Cost/Day</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${data.costAnalysis.avgCostPerDay.toFixed(2)}
                  </p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">Avg Cost/Run</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${data.costAnalysis.avgCostPerRun.toFixed(4)}
                  </p>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <p className="text-sm text-gray-600">Efficiency</p>
                  <p className="text-2xl font-bold text-green-700">
                    {data.costAnalysis.efficiencyRate.toFixed(0)}%
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {view === 'optimization' && (
          <CostOptimization
            optimizations={data.optimizations}
            currentCost={data.costAnalysis.totalCost}
          />
        )}
      </div>
    </div>
  )
}
