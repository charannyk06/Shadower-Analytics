/**
 * Agent Lifecycle Dashboard Component
 *
 * Displays comprehensive lifecycle analytics including:
 * - Current state and status
 * - State transition history
 * - Version comparison
 * - Deployment metrics
 * - Health score
 */

'use client';

import React from 'react';
import { useAgentLifecycle } from '@/hooks/api/useAgentLifecycle';
import { LifecycleTimeframe } from '@/types/agent-lifecycle';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LifecycleStatusCard } from './LifecycleStatusCard';
import { StateTransitionTimeline } from './StateTransitionTimeline';
import { VersionPerformanceChart } from './VersionPerformanceChart';
import { DeploymentMetricsCard } from './DeploymentMetricsCard';
import { HealthScoreCard } from './HealthScoreCard';

export interface AgentLifecycleDashboardProps {
  agentId: string;
  workspaceId: string;
  timeframe?: LifecycleTimeframe;
  className?: string;
}

/**
 * Main dashboard component for agent lifecycle analytics
 */
export function AgentLifecycleDashboard({
  agentId,
  workspaceId,
  timeframe = '30d',
  className = '',
}: AgentLifecycleDashboardProps) {
  const { data, isLoading, error } = useAgentLifecycle({
    agentId,
    workspaceId,
    timeframe,
    includeVersions: true,
    includeDeployments: true,
    includeHealth: true,
  });

  if (isLoading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${className}`}>
        <ErrorAlert error={error} />
      </div>
    );
  }

  if (!data) {
    return (
      <div className={`${className}`}>
        <EmptyState />
      </div>
    );
  }

  const {
    currentState,
    currentStateSince,
    lifecycleMetrics,
    stateDurations,
    transitions,
    timeline,
    versionComparison,
    deploymentMetrics,
    currentHealthScore,
    healthTrend,
    retirementRisk,
  } = data;

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header with Current State */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Lifecycle Analytics</h2>
          <p className="text-muted-foreground mt-1">
            Comprehensive lifecycle tracking and analysis
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm text-muted-foreground">Agent ID</p>
          <p className="font-mono text-sm">{agentId}</p>
        </div>
      </div>

      {/* Current Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <LifecycleStatusCard
          currentState={currentState}
          currentStateSince={currentStateSince}
          daysInCurrentState={lifecycleMetrics.daysInCurrentState}
        />

        <MetricCard
          title="Total Lifecycle"
          value={`${lifecycleMetrics.totalDaysSinceCreation.toFixed(0)} days`}
          subtitle={`${lifecycleMetrics.totalTransitions} transitions`}
        />

        <MetricCard
          title="Versions"
          value={lifecycleMetrics.totalVersions.toString()}
          subtitle={`${lifecycleMetrics.productionVersions} in production`}
        />

        <MetricCard
          title="Deployments"
          value={`${lifecycleMetrics.deploymentSuccessRate.toFixed(1)}%`}
          subtitle={`${lifecycleMetrics.totalDeployments} total`}
          valueClassName={
            lifecycleMetrics.deploymentSuccessRate >= 90
              ? 'text-green-600'
              : lifecycleMetrics.deploymentSuccessRate >= 70
              ? 'text-yellow-600'
              : 'text-red-600'
          }
        />
      </div>

      {/* State Transition Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>State Transition History</CardTitle>
        </CardHeader>
        <CardContent>
          <StateTransitionTimeline transitions={transitions} timeline={timeline} />
        </CardContent>
      </Card>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Version Performance */}
        {versionComparison && versionComparison.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Version Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <VersionPerformanceChart versions={versionComparison} />
            </CardContent>
          </Card>
        )}

        {/* Deployment Metrics */}
        {deploymentMetrics && (
          <DeploymentMetricsCard metrics={deploymentMetrics} />
        )}
      </div>

      {/* Health Score and Retirement Risk */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {currentHealthScore && (
          <HealthScoreCard
            healthScore={currentHealthScore}
            trend={healthTrend}
          />
        )}

        {retirementRisk && (
          <RetirementRiskCard risk={retirementRisk} />
        )}
      </div>

      {/* State Durations */}
      <Card>
        <CardHeader>
          <CardTitle>Time in Each State</CardTitle>
        </CardHeader>
        <CardContent>
          <StateDurationsTable durations={stateDurations} />
        </CardContent>
      </Card>
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  valueClassName?: string;
}

function MetricCard({ title, value, subtitle, valueClassName = '' }: MetricCardProps) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className={`text-3xl font-bold ${valueClassName}`}>{value}</p>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

interface StateDurationsTableProps {
  durations: Array<{
    state: string;
    totalDurationSeconds: number;
    averageDurationSeconds: number;
    totalOccurrences: number;
    percentageOfLifetime: number;
  }>;
}

function StateDurationsTable({ durations }: StateDurationsTableProps) {
  const formatDuration = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    return days > 0 ? `${days}d ${hours}h` : `${hours}h`;
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th className="text-left py-3 px-4 font-medium">State</th>
            <th className="text-right py-3 px-4 font-medium">Total Time</th>
            <th className="text-right py-3 px-4 font-medium">Avg Duration</th>
            <th className="text-right py-3 px-4 font-medium">Occurrences</th>
            <th className="text-right py-3 px-4 font-medium">% of Lifetime</th>
          </tr>
        </thead>
        <tbody>
          {durations.map((duration, index) => (
            <tr key={index} className="border-b last:border-0">
              <td className="py-3 px-4 font-medium capitalize">{duration.state}</td>
              <td className="text-right py-3 px-4">
                {formatDuration(duration.totalDurationSeconds)}
              </td>
              <td className="text-right py-3 px-4">
                {formatDuration(duration.averageDurationSeconds)}
              </td>
              <td className="text-right py-3 px-4">{duration.totalOccurrences}</td>
              <td className="text-right py-3 px-4">
                {duration.percentageOfLifetime.toFixed(1)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface RetirementRiskCardProps {
  risk: string;
}

function RetirementRiskCard({ risk }: RetirementRiskCardProps) {
  const riskColors = {
    low: 'bg-green-100 text-green-800 border-green-300',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    high: 'bg-orange-100 text-orange-800 border-orange-300',
    critical: 'bg-red-100 text-red-800 border-red-300',
  };

  const riskColor = riskColors[risk as keyof typeof riskColors] || riskColors.low;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Retirement Risk</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className={`px-4 py-3 rounded-lg border-2 ${riskColor}`}>
            <p className="text-sm font-medium">Risk Level</p>
            <p className="text-2xl font-bold capitalize mt-1">{risk}</p>
          </div>
          <p className="text-sm text-muted-foreground">
            {risk === 'low' && 'Agent is actively used and performing well.'}
            {risk === 'medium' && 'Agent usage has decreased. Monitor closely.'}
            {risk === 'high' && 'Agent is underutilized. Consider deprecation.'}
            {risk === 'critical' && 'Agent is a strong candidate for retirement.'}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <>
      <div className="h-8 bg-gray-200 rounded animate-pulse w-1/3" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-32 bg-gray-200 rounded animate-pulse" />
        ))}
      </div>
      <div className="h-64 bg-gray-200 rounded animate-pulse" />
    </>
  );
}

interface ErrorAlertProps {
  error: Error;
}

function ErrorAlert({ error }: ErrorAlertProps) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <h3 className="text-red-800 font-semibold mb-2">Error Loading Lifecycle Data</h3>
      <p className="text-red-700 text-sm">{error.message}</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
      <p className="text-gray-600">No lifecycle data available for this agent.</p>
    </div>
  );
}
