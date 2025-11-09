/**
 * Workspace Analytics Dashboard Page
 * Comprehensive workspace analytics with health metrics, member activity, and resource utilization
 */

'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useWorkspaceAnalytics } from '@/hooks/api/useWorkspaceAnalytics';
import { WorkspaceHealthScore } from '@/components/workspace/WorkspaceHealthScore';
import { OverviewMetrics } from '@/components/workspace/OverviewMetrics';
import { MemberActivity } from '@/components/workspace/MemberActivity';
import { TimeFrame } from '@/types/workspace';
import { Loader2, Calendar, TrendingUp } from 'lucide-react';

type TabType = 'overview' | 'members' | 'agents' | 'resources' | 'billing';

export default function WorkspaceAnalyticsPage() {
  const params = useParams();
  const workspaceId = params?.id as string;

  const [timeframe, setTimeframe] = useState<TimeFrame>('30d');
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const { data, isLoading, error } = useWorkspaceAnalytics({
    workspaceId,
    timeframe,
    includeComparison: false, // Set to true for admin users
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading workspace analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Error Loading Analytics</h1>
          <p className="text-gray-600">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">No data available</p>
      </div>
    );
  }

  const timeframeOptions: { value: TimeFrame; label: string }[] = [
    { value: '24h', label: 'Last 24 Hours' },
    { value: '7d', label: 'Last 7 Days' },
    { value: '30d', label: 'Last 30 Days' },
    { value: '90d', label: 'Last 90 Days' },
    { value: 'all', label: 'All Time' },
  ];

  const tabs: { id: TabType; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'members', label: 'Members' },
    { id: 'agents', label: 'Agents' },
    { id: 'resources', label: 'Resources' },
    { id: 'billing', label: 'Billing' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{data.workspaceName}</h1>
              <p className="mt-1 text-sm text-gray-500">
                Workspace Analytics • {data.plan.charAt(0).toUpperCase() + data.plan.slice(1)} Plan
              </p>
            </div>

            {/* Timeframe Selector */}
            <div className="mt-4 md:mt-0">
              <div className="flex items-center space-x-2">
                <Calendar className="w-5 h-5 text-gray-400" />
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value as TimeFrame)}
                  className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                >
                  {timeframeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Health Score Card */}
        <WorkspaceHealthScore
          score={data.overview.healthScore}
          factors={data.overview.healthFactors}
          status={data.overview.status}
        />

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm transition-colors
                  ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === 'overview' && (
            <>
              <OverviewMetrics data={data.overview} />
            </>
          )}

          {activeTab === 'members' && <MemberActivity data={data.memberAnalytics} />}

          {activeTab === 'agents' && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-center py-12">
                <TrendingUp className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Agent Analytics</h3>
                <p className="text-gray-500">
                  {data.agentUsage.totalAgents} total agents, {data.agentUsage.activeAgents} active
                </p>
                <div className="mt-4 text-sm text-gray-600">
                  <p>Average Success Rate: {data.agentUsage.agentEfficiency.avgSuccessRate.toFixed(1)}%</p>
                  <p>Average Runtime: {data.agentUsage.agentEfficiency.avgRuntime.toFixed(2)}s</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'resources' && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Resource Utilization</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Credits */}
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-2">Credits</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Allocated:</span>
                      <span className="font-semibold">{data.resourceUtilization.credits.allocated.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Consumed:</span>
                      <span className="font-semibold">{data.resourceUtilization.credits.consumed.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Remaining:</span>
                      <span className="font-semibold text-green-600">
                        {data.resourceUtilization.credits.remaining.toLocaleString()}
                      </span>
                    </div>
                    <div className="mt-3 pt-3 border-t border-blue-200">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Utilization:</span>
                        <span className="font-semibold">{data.resourceUtilization.credits.utilizationRate.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Storage */}
                <div className="p-4 bg-green-50 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-2">Storage</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Used:</span>
                      <span className="font-semibold">
                        {(data.resourceUtilization.storage.used / (1024 * 1024 * 1024)).toFixed(2)} GB
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Limit:</span>
                      <span className="font-semibold">
                        {(data.resourceUtilization.storage.limit / (1024 * 1024 * 1024)).toFixed(0)} GB
                      </span>
                    </div>
                    <div className="mt-3 pt-3 border-t border-green-200">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Utilization:</span>
                        <span className="font-semibold">{data.resourceUtilization.storage.utilizationRate.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* API Usage */}
                <div className="p-4 bg-purple-50 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-2">API Usage</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Total Calls:</span>
                      <span className="font-semibold">{data.resourceUtilization.apiUsage.totalCalls.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Rate Limit:</span>
                      <span className="font-semibold">{data.resourceUtilization.apiUsage.rateLimit.toLocaleString()}</span>
                    </div>
                    <div className="mt-3 pt-3 border-t border-purple-200">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Utilization:</span>
                        <span className="font-semibold">{data.resourceUtilization.apiUsage.utilizationRate.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'billing' && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Billing Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Current Month</div>
                  <div className="text-2xl font-bold text-gray-900">
                    ${data.billing.currentMonthCost.toFixed(2)}
                  </div>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Projected Month</div>
                  <div className="text-2xl font-bold text-gray-900">
                    ${data.billing.projectedMonthCost.toFixed(2)}
                  </div>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Last Month</div>
                  <div className="text-2xl font-bold text-gray-900">
                    ${data.billing.lastMonthCost.toFixed(2)}
                  </div>
                </div>
              </div>
              <div className="mt-6">
                <div className="text-sm text-gray-600 mb-2">Plan: {data.billing.plan}</div>
                <div className="text-sm">
                  Status:{' '}
                  <span
                    className={`font-medium ${
                      data.billing.status === 'active' ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {data.billing.status.toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
