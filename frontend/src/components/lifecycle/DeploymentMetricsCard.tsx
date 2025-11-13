/**
 * Deployment Metrics Card Component
 *
 * Displays deployment success metrics and statistics
 */

'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DeploymentMetrics } from '@/types/agent-lifecycle';

export interface DeploymentMetricsCardProps {
  metrics: DeploymentMetrics;
  className?: string;
}

export function DeploymentMetricsCard({
  metrics,
  className = '',
}: DeploymentMetricsCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Deployment Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Success Rate</p>
              <p className="text-2xl font-bold">
                {(metrics.successRate * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Avg Time</p>
              <p className="text-2xl font-bold">
                {metrics.avgDeploymentTimeMinutes.toFixed(1)}m
              </p>
            </div>
          </div>

          <div className="space-y-2 pt-4 border-t">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Total Deployments</span>
              <span className="font-medium">{metrics.totalDeployments}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Successful</span>
              <span className="font-medium text-green-600">
                {metrics.successfulDeployments}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Failed</span>
              <span className="font-medium text-red-600">
                {metrics.failedDeployments}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Rollbacks</span>
              <span className="font-medium text-orange-600">
                {metrics.rollbackCount}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
