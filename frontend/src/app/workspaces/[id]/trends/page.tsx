/**
 * Trends Analysis Page
 *
 * Displays comprehensive trend analysis and forecasting for workspace metrics.
 */

import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Trends Analysis | Shadower Analytics',
  description: 'Comprehensive time-series analysis, pattern detection, and forecasting for workspace metrics',
};

'use client';

import { use, Suspense } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { TrendAnalysisDashboard } from '@/components/trends';

interface TrendsPageProps {
  params: Promise<{
    id: string;
  }>;
}

function TrendAnalysisLoading() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        {/* Header Skeleton */}
        <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-200">
          <div className="animate-pulse space-y-3">
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>

        {/* Content Skeleton */}
        <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TrendAnalysisError({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-red-900 mb-2">
          Error Loading Trend Analysis
        </h2>
        <p className="text-red-700 mb-4">
          {error.message || 'An unexpected error occurred while loading the trend analysis.'}
        </p>
        <button
          onClick={resetErrorBoundary}
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}

function TrendsPageContent({ params }: TrendsPageProps) {
  const resolvedParams = use(params);
  const workspaceId = resolvedParams.id;

  return (
    <div className="container mx-auto px-4 py-8">
      <TrendAnalysisDashboard workspaceId={workspaceId} />
    </div>
  );
}

export default function TrendsPage({ params }: TrendsPageProps) {
  return (
    <ErrorBoundary FallbackComponent={TrendAnalysisError}>
      <Suspense fallback={<TrendAnalysisLoading />}>
        <TrendsPageContent params={params} />
      </Suspense>
    </ErrorBoundary>
  );
}
