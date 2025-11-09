/**
 * Cost Analysis Component
 * Displays resource usage and cost metrics
 */

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { ResourceUsage } from '@/types/agent-analytics';
import { Card } from '@/components/ui/Card';

// Credit to dollar conversion rate
const CREDIT_TO_DOLLAR_RATE = 0.01;

interface CostAnalysisProps {
  resources: ResourceUsage;
}

export function CostAnalysis({ resources }: CostAnalysisProps) {
  const modelUsageData = Object.entries(resources.modelUsage).map(([model, usage]) => ({
    name: model,
    credits: usage.credits,
    tokens: usage.tokens,
    calls: usage.calls,
  }));

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Cost & Resource Analysis</h2>

      {/* Cost Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <div className="text-sm text-gray-600">Total Cost</div>
          <div className="mt-1 text-3xl font-bold text-gray-900">
            ${resources.totalCost.toFixed(2)}
          </div>
          <div className="mt-1 text-xs text-gray-500">
            {resources.totalCreditsConsumed.toLocaleString()} credits
          </div>
        </Card>

        <Card>
          <div className="text-sm text-gray-600">Cost per Run</div>
          <div className="mt-1 text-3xl font-bold text-gray-900">
            ${resources.costPerRun.toFixed(4)}
          </div>
          <div className="mt-1 text-xs text-gray-500">
            {resources.avgCreditsPerRun.toFixed(2)} credits avg
          </div>
        </Card>

        <Card>
          <div className="text-sm text-gray-600">Total Tokens</div>
          <div className="mt-1 text-3xl font-bold text-gray-900">
            {(resources.totalTokensUsed / 1000000).toFixed(2)}M
          </div>
          <div className="mt-1 text-xs text-gray-500">
            {resources.avgTokensPerRun.toFixed(0)} avg per run
          </div>
        </Card>

        <Card>
          <div className="text-sm text-gray-600">Efficiency</div>
          <div className="mt-1 text-2xl font-bold text-green-600">
            {(resources.totalTokensUsed / resources.totalCreditsConsumed).toFixed(0)}
          </div>
          <div className="mt-1 text-xs text-gray-500">tokens per credit</div>
        </Card>
      </div>

      {/* Model Usage Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Cost by Model">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={modelUsageData}
                  dataKey="credits"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={(entry) => `${entry.name}: $${entry.credits.toFixed(2)}`}
                  labelLine={true}
                >
                  {modelUsageData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => `$${value.toFixed(2)}`}
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '0.375rem',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Model Usage Details">
          <div className="space-y-3">
            {modelUsageData.map((model, index) => (
              <div
                key={model.name}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <div>
                    <div className="font-medium text-gray-900">{model.name}</div>
                    <div className="text-xs text-gray-500">
                      {model.calls.toLocaleString()} calls
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-gray-900">
                    ${model.credits.toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {(model.tokens / 1000).toFixed(1)}K tokens
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Cost Breakdown Table */}
      <Card title="Detailed Cost Breakdown">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Model
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Calls
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tokens
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Credits
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cost
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  % of Total
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {modelUsageData.map((model) => {
                const costPercentage = (model.credits / resources.totalCreditsConsumed) * 100;
                return (
                  <tr key={model.name} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                      {model.name}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">
                      {model.calls.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">
                      {model.tokens.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">
                      {model.credits.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right font-semibold text-gray-900">
                      ${(model.credits * CREDIT_TO_DOLLAR_RATE).toFixed(4)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600">
                      {costPercentage.toFixed(1)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
