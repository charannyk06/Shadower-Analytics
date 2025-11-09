/**
 * Trends Analysis Page
 *
 * Displays comprehensive trend analysis and forecasting for workspace metrics.
 */

'use client';

import { use } from 'react';
import { TrendAnalysisDashboard } from '@/components/trends';

interface TrendsPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default function TrendsPage({ params }: TrendsPageProps) {
  const resolvedParams = use(params);
  const workspaceId = resolvedParams.id;

  return (
    <div className="container mx-auto px-4 py-8">
      <TrendAnalysisDashboard workspaceId={workspaceId} />
    </div>
  );
}
