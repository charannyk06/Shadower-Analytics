'use client';

/**
 * Agent Analytics Dashboard Page
 * Comprehensive analytics view for individual AI agents
 */

import { useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { useAgentAnalytics } from '@/hooks/api/useAgentAnalytics';
import { TimeFrame } from '@/types/agent-analytics';
import { AgentHeader } from '@/components/agents/AgentHeader';
import { PerformanceMetrics } from '@/components/agents/PerformanceMetrics';
import { RuntimeDistribution } from '@/components/agents/RuntimeDistribution';
import { ErrorAnalysis } from '@/components/agents/ErrorAnalysis';
import { UserSatisfaction } from '@/components/agents/UserSatisfaction';
import { CostAnalysis } from '@/components/agents/CostAnalysis';
import { OptimizationSuggestions } from '@/components/agents/OptimizationSuggestions';
import { AgentComparison } from '@/components/agents/AgentComparison';
import { TimeframeSelector } from '@/components/common/TimeframeSelector';

export default function AgentAnalyticsPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const agentId = params?.id as string;

  // Get workspace ID from query params; fail if missing
  const workspaceId = searchParams?.get('workspace_id');

  // Show error if workspace ID is missing
  if (!workspaceId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-gray-800 mb-2">Workspace ID Required</h2>
          <p className="text-gray-600">A valid <code>workspace_id</code> query parameter must be provided to view analytics.</p>
        </div>
      </div>
    );
  }

  const [timeframe, setTimeframe] = useState<TimeFrame>('7d');
  const [compareWith, setCompareWith] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useAgentAnalytics({
    agentId,
    workspaceId,
    timeframe,
  });

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <AgentAnalyticsSkeleton />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <ErrorState error={error} onRetry={() => refetch()} />
      </div>
    );
  }

  // No data state
  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <EmptyState />
      </div>
    );
  }

  // Export analytics data
  const exportAnalytics = () => {
    const dataStr = JSON.stringify(data, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `agent-analytics-${agentId}-${timeframe}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Share analytics
  const shareAnalytics = () => {
    const shareUrl = window.location.href;
    if (navigator.share) {
      navigator.share({
        title: 'Agent Analytics',
        text: `Check out analytics for agent ${agentId}`,
        url: shareUrl,
      });
    } else {
      navigator.clipboard.writeText(shareUrl);
      // You could add a toast notification here
      alert('Link copied to clipboard!');
    }
  };

  // Implement optimization
  const implementOptimization = (suggestion: any) => {
    // This would typically open a modal or navigate to implementation guide
    console.log('Implementing optimization:', suggestion);
    alert(`Implementation guide for: ${suggestion.title}\n\n${suggestion.description}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-12">
      {/* Header with agent info and actions */}
      <AgentHeader
        agent={data}
        onExport={exportAnalytics}
        onShare={shareAnalytics}
      />

      {/* Timeframe selector */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        <div className="flex items-center justify-between">
          <TimeframeSelector
            value={timeframe}
            onChange={setTimeframe}
          />

          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Main content grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6 space-y-8">
        {/* Performance Overview */}
        <PerformanceMetrics metrics={data.performance} />

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RuntimeDistribution runtime={data.performance.runtime} />
          <ErrorAnalysis errors={data.errors} />
        </div>

        {/* User Metrics */}
        <UserSatisfaction userMetrics={data.userMetrics} />

        {/* Cost Analysis */}
        <CostAnalysis resources={data.resources} />

        {/* Comparison */}
        <AgentComparison
          comparison={data.comparison}
          agentId={agentId}
          compareWith={compareWith}
          onCompareChange={setCompareWith}
        />

        {/* Optimization Suggestions */}
        <OptimizationSuggestions
          suggestions={data.optimizations}
          onImplement={implementOptimization}
        />
      </div>
    </div>
  );
}

// Loading skeleton component
function AgentAnalyticsSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="bg-white border-b border-gray-200 h-32" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6 space-y-6">
        <div className="h-48 bg-gray-200 rounded-lg" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-96 bg-gray-200 rounded-lg" />
          <div className="h-96 bg-gray-200 rounded-lg" />
        </div>
        <div className="h-64 bg-gray-200 rounded-lg" />
      </div>
    </div>
  );
}

// Error state component
function ErrorState({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return (
    <div className="text-center">
      <svg
        className="mx-auto h-12 w-12 text-red-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <h3 className="mt-2 text-lg font-medium text-gray-900">Error loading analytics</h3>
      <p className="mt-1 text-sm text-gray-500">{error.message}</p>
      <div className="mt-6">
        <button
          onClick={onRetry}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}

// Empty state component
function EmptyState() {
  return (
    <div className="text-center">
      <svg
        className="mx-auto h-12 w-12 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      <h3 className="mt-2 text-lg font-medium text-gray-900">No analytics data available</h3>
      <p className="mt-1 text-sm text-gray-500">
        This agent hasn't recorded any executions yet.
      </p>
    </div>
  );
}
