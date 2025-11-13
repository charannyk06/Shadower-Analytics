/**
 * Version Performance Chart Component
 *
 * Charts performance metrics across different versions
 */

'use client';

import React from 'react';
import { VersionPerformanceComparison } from '@/types/agent-lifecycle';

export interface VersionPerformanceChartProps {
  versions: VersionPerformanceComparison[];
  className?: string;
}

export function VersionPerformanceChart({
  versions,
  className = '',
}: VersionPerformanceChartProps) {
  if (versions.length === 0) {
    return (
      <div className={`text-center py-8 text-muted-foreground ${className}`}>
        No version data available
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {versions.slice(0, 5).map((version) => (
        <div key={version.versionId} className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-semibold">{version.version}</span>
            <span className="text-sm text-muted-foreground">
              {version.totalExecutions} executions
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Success Rate</p>
              <p className="font-medium">
                {(version.successRate * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Avg Duration</p>
              <p className="font-medium">{version.avgDuration.toFixed(2)}s</p>
            </div>
            <div>
              <p className="text-muted-foreground">Avg Cost</p>
              <p className="font-medium">${version.avgCredits.toFixed(2)}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
