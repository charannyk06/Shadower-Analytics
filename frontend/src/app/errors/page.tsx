'use client';

import { useState } from 'react';
import { useErrorTracking, useResolveError, useIgnoreError } from '@/hooks/api/useErrorTracking';
import { TimeFrame } from '@/types/error-tracking';
import {
  ErrorOverview,
  ErrorTimeline,
  ErrorList,
  ErrorDetails,
  ErrorCorrelations,
  RecoveryAnalysis,
} from '@/components/errors/ErrorComponents';

export default function ErrorTrackingDashboard() {
  const [timeframe, setTimeframe] = useState<TimeFrame>('7d');
  const [selectedError, setSelectedError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  // For demo purposes, using a hardcoded workspace ID
  // In production, this would come from auth context or route params
  const workspaceId = 'demo-workspace';

  const { data, isLoading, error } = useErrorTracking({
    workspaceId,
    timeframe,
    severityFilter,
  });

  const resolveErrorMutation = useResolveError();
  const ignoreErrorMutation = useIgnoreError();

  const handleResolveError = (errorId: string, resolution: string) => {
    resolveErrorMutation.mutate({
      errorId,
      resolutionData: {
        resolvedBy: 'current-user', // Would come from auth context
        resolution,
      },
    });
  };

  const handleIgnoreError = (errorId: string) => {
    ignoreErrorMutation.mutate(errorId);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading error tracking data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center bg-white rounded-lg shadow p-8 max-w-md">
          <div className="text-red-600 mb-4">
            <svg
              className="h-12 w-12 mx-auto"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Data</h2>
          <p className="text-gray-600">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const selectedErrorData = selectedError
    ? data.errors.find((e) => e.errorId === selectedError)
    : null;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Error Tracking</h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor and resolve system errors and exceptions
          </p>
        </div>

        {/* Filters */}
        <div className="flex gap-4 mb-6">
          {/* Timeframe Selector */}
          <div className="flex gap-2">
            {(['24h', '7d', '30d', '90d'] as TimeFrame[]).map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-4 py-2 rounded-lg font-medium text-sm ${
                  timeframe === tf
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* Overview Cards */}
        <ErrorOverview overview={data.overview} />

        {/* Error Timeline */}
        <ErrorTimeline timeline={data.timeline} />

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Error List */}
          <div className="lg:col-span-2">
            <ErrorList
              errors={data.errors}
              topErrors={data.topErrors}
              onErrorSelect={setSelectedError}
              selectedError={selectedError}
            />
          </div>

          {/* Error Details Panel */}
          <div>
            {selectedErrorData ? (
              <ErrorDetails
                error={selectedErrorData}
                onResolve={handleResolveError}
                onIgnore={handleIgnoreError}
              />
            ) : (
              <ErrorCorrelations correlations={data.correlations} />
            )}
          </div>
        </div>

        {/* Recovery Analysis */}
        <RecoveryAnalysis recovery={data.recovery} />
      </div>
    </div>
  );
}
