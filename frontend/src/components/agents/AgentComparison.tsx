/**
 * Agent Comparison Component
 * Compares agent performance against workspace averages and other agents
 */

import React from 'react';
import { ComparisonMetrics } from '@/types/agent-analytics';
import { Card } from '@/components/ui/Card';

interface AgentComparisonProps {
  comparison: ComparisonMetrics;
  agentId: string;
  compareWith?: string | null;
  onCompareChange?: (agentId: string | null) => void;
}

export function AgentComparison({
  comparison,
  agentId,
  compareWith,
  onCompareChange,
}: AgentComparisonProps) {
  const formatChange = (value: number) => {
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%`;
  };

  const getChangeColor = (value: number, inverse: boolean = false) => {
    if (inverse) {
      return value < 0 ? 'text-green-600' : value > 0 ? 'text-red-600' : 'text-gray-600';
    }
    return value > 0 ? 'text-green-600' : value < 0 ? 'text-red-600' : 'text-gray-600';
  };

  const getChangeIcon = (value: number, inverse: boolean = false) => {
    const isPositive = inverse ? value < 0 : value > 0;
    if (Math.abs(value) < 0.1) {
      return (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
        </svg>
      );
    }
    if (isPositive) {
      return (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
        </svg>
      );
    }
    return (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  const getRankBadgeColor = (percentile: number) => {
    if (percentile >= 90) return 'bg-green-100 text-green-800 border-green-200';
    if (percentile >= 75) return 'bg-blue-100 text-blue-800 border-blue-200';
    if (percentile >= 50) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Comparative Analysis</h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Workspace Average Comparison */}
        <Card title="vs Workspace Average">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Success Rate</span>
              <div className={`flex items-center gap-1 font-semibold ${getChangeColor(comparison.vsWorkspaceAverage.successRate)}`}>
                {getChangeIcon(comparison.vsWorkspaceAverage.successRate)}
                <span>{formatChange(comparison.vsWorkspaceAverage.successRate)}</span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Runtime</span>
              <div className={`flex items-center gap-1 font-semibold ${getChangeColor(comparison.vsWorkspaceAverage.runtime, true)}`}>
                {getChangeIcon(comparison.vsWorkspaceAverage.runtime, true)}
                <span>{formatChange(comparison.vsWorkspaceAverage.runtime)}</span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Credit Efficiency</span>
              <div className={`flex items-center gap-1 font-semibold ${getChangeColor(comparison.vsWorkspaceAverage.creditEfficiency, true)}`}>
                {getChangeIcon(comparison.vsWorkspaceAverage.creditEfficiency, true)}
                <span>{formatChange(comparison.vsWorkspaceAverage.creditEfficiency)}</span>
              </div>
            </div>
          </div>

          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-600">
              {comparison.vsWorkspaceAverage.successRate > 0 ? (
                <span className="text-green-600 font-medium">Outperforming</span>
              ) : comparison.vsWorkspaceAverage.successRate < 0 ? (
                <span className="text-red-600 font-medium">Underperforming</span>
              ) : (
                <span className="text-gray-600 font-medium">On par with</span>
              )}{' '}
              workspace average
            </p>
          </div>
        </Card>

        {/* Ranking */}
        <Card title="Overall Ranking">
          <div className="text-center py-4">
            <div className={`inline-flex items-center justify-center w-24 h-24 rounded-full border-4 ${getRankBadgeColor(comparison.vsAllAgents.percentile)}`}>
              <div>
                <div className="text-3xl font-bold">#{comparison.vsAllAgents.rank}</div>
                <div className="text-xs">Rank</div>
              </div>
            </div>
            <div className="mt-4">
              <div className="text-2xl font-bold text-gray-900">
                Top {(100 - comparison.vsAllAgents.percentile).toFixed(0)}%
              </div>
              <div className="text-sm text-gray-600 mt-1">
                {comparison.vsAllAgents.percentile.toFixed(0)}th percentile
              </div>
            </div>
          </div>

          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <p className="text-xs text-center text-blue-800">
              {comparison.vsAllAgents.percentile >= 90
                ? '🏆 Excellent performance!'
                : comparison.vsAllAgents.percentile >= 75
                ? '👍 Above average performance'
                : comparison.vsAllAgents.percentile >= 50
                ? '📊 Average performance'
                : '⚠️ Room for improvement'}
            </p>
          </div>
        </Card>

        {/* Previous Period */}
        <Card title="vs Previous Period">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Runs</span>
              <div className={`flex items-center gap-1 font-semibold ${getChangeColor(comparison.vsPreviousPeriod.runsChange)}`}>
                {getChangeIcon(comparison.vsPreviousPeriod.runsChange)}
                <span>{formatChange(comparison.vsPreviousPeriod.runsChange)}</span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Success Rate</span>
              <div className={`flex items-center gap-1 font-semibold ${getChangeColor(comparison.vsPreviousPeriod.successRateChange)}`}>
                {getChangeIcon(comparison.vsPreviousPeriod.successRateChange)}
                <span>{formatChange(comparison.vsPreviousPeriod.successRateChange)}</span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Runtime</span>
              <div className={`flex items-center gap-1 font-semibold ${getChangeColor(comparison.vsPreviousPeriod.runtimeChange, true)}`}>
                {getChangeIcon(comparison.vsPreviousPeriod.runtimeChange, true)}
                <span>{formatChange(comparison.vsPreviousPeriod.runtimeChange)}</span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Cost</span>
              <div className={`flex items-center gap-1 font-semibold ${getChangeColor(comparison.vsPreviousPeriod.costChange, true)}`}>
                {getChangeIcon(comparison.vsPreviousPeriod.costChange, true)}
                <span>{formatChange(comparison.vsPreviousPeriod.costChange)}</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Trend Summary */}
      <Card>
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">
            <svg className="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900">Performance Summary</h3>
            <p className="mt-1 text-sm text-gray-600">
              {comparison.vsPreviousPeriod.successRateChange > 5
                ? 'Your agent is showing strong improvement with increased success rates and usage.'
                : comparison.vsPreviousPeriod.successRateChange < -5
                ? 'Performance has declined. Review error logs and consider implementing optimization suggestions.'
                : 'Performance is stable. Continue monitoring for any significant changes.'}
            </p>
            {comparison.vsPreviousPeriod.costChange > 20 && (
              <p className="mt-2 text-sm text-yellow-700 bg-yellow-50 p-3 rounded border border-yellow-200">
                ⚠️ Cost has increased significantly. Review the cost analysis section for optimization opportunities.
              </p>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
