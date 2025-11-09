/**
 * Performance Metrics Component
 * Displays key performance indicators for an agent
 */

import React from 'react';
import { PerformanceMetrics as PerformanceMetricsType } from '@/types/agent-analytics';
import { Card } from '@/components/ui/Card';

interface PerformanceMetricsProps {
  metrics: PerformanceMetricsType;
}

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: number;
  color?: 'blue' | 'green' | 'red' | 'yellow';
}

function MetricCard({ title, value, subtitle, trend, color = 'blue' }: MetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    red: 'bg-red-50 text-red-700',
    yellow: 'bg-yellow-50 text-yellow-700',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        {trend !== undefined && (
          <span className={`text-xs font-medium px-2 py-1 rounded-full ${
            trend > 0 ? 'bg-green-100 text-green-800' : trend < 0 ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
          }`}>
            {trend > 0 ? '+' : ''}{trend.toFixed(1)}%
          </span>
        )}
      </div>
      <div className="mt-2">
        <div className={`text-3xl font-bold ${colorClasses[color]}`}>
          {value}
        </div>
        {subtitle && (
          <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
        )}
      </div>
    </div>
  );
}

export function PerformanceMetrics({ metrics }: PerformanceMetricsProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Performance Overview</h2>

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Runs"
            value={metrics.totalRuns.toLocaleString()}
            subtitle={`${metrics.throughput.runsPerDay.toFixed(1)} runs/day`}
            color="blue"
          />

          <MetricCard
            title="Success Rate"
            value={`${metrics.successRate.toFixed(1)}%`}
            subtitle={`${metrics.successfulRuns.toLocaleString()} successful`}
            color={metrics.successRate >= 95 ? 'green' : metrics.successRate >= 85 ? 'yellow' : 'red'}
          />

          <MetricCard
            title="Avg Runtime"
            value={`${metrics.runtime.average.toFixed(2)}s`}
            subtitle={`Median: ${metrics.runtime.median.toFixed(2)}s`}
            color="blue"
          />

          <MetricCard
            title="Availability"
            value={`${metrics.availabilityRate.toFixed(1)}%`}
            subtitle={`${metrics.failedRuns} failed runs`}
            color={metrics.availabilityRate >= 99 ? 'green' : metrics.availabilityRate >= 95 ? 'yellow' : 'red'}
          />
        </div>
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Execution Breakdown">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Successful</span>
              <span className="text-sm font-semibold text-green-600">
                {metrics.successfulRuns.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Failed</span>
              <span className="text-sm font-semibold text-red-600">
                {metrics.failedRuns.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Cancelled</span>
              <span className="text-sm font-semibold text-yellow-600">
                {metrics.cancelledRuns.toLocaleString()}
              </span>
            </div>
          </div>
        </Card>

        <Card title="Throughput & Concurrency">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Runs per Hour</span>
              <span className="text-sm font-semibold">
                {metrics.throughput.runsPerHour.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Peak Concurrency</span>
              <span className="text-sm font-semibold">
                {metrics.throughput.peakConcurrency}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Avg Concurrency</span>
              <span className="text-sm font-semibold">
                {metrics.throughput.avgConcurrency.toFixed(2)}
              </span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
