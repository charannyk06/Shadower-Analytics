/**
 * Health Score Card Component
 *
 * Displays agent health score and component breakdown
 */

'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { HealthScore } from '@/types/agent-lifecycle';

export interface HealthScoreCardProps {
  healthScore: HealthScore;
  trend?: string;
  className?: string;
}

export function HealthScoreCard({
  healthScore,
  trend,
  className = '',
}: HealthScoreCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getTrendIcon = (trendValue?: string) => {
    if (trendValue === 'improving') return '↑';
    if (trendValue === 'declining') return '↓';
    return '→';
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Health Score</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-baseline gap-2">
            <span className={`text-4xl font-bold ${getScoreColor(healthScore.overallScore)}`}>
              {healthScore.overallScore.toFixed(1)}
            </span>
            <span className="text-muted-foreground">/ 100</span>
            {trend && (
              <span className="text-lg ml-2">{getTrendIcon(trend)}</span>
            )}
          </div>

          <p className="text-sm text-muted-foreground capitalize">
            Status: {healthScore.healthStatus}
          </p>

          <div className="space-y-2 pt-4 border-t">
            {healthScore.performanceScore !== undefined && (
              <ScoreBar
                label="Performance"
                score={healthScore.performanceScore}
              />
            )}
            {healthScore.reliabilityScore !== undefined && (
              <ScoreBar
                label="Reliability"
                score={healthScore.reliabilityScore}
              />
            )}
            {healthScore.usageScore !== undefined && (
              <ScoreBar label="Usage" score={healthScore.usageScore} />
            )}
            {healthScore.maintenanceScore !== undefined && (
              <ScoreBar
                label="Maintenance"
                score={healthScore.maintenanceScore}
              />
            )}
            {healthScore.costScore !== undefined && (
              <ScoreBar label="Cost" score={healthScore.costScore} />
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface ScoreBarProps {
  label: string;
  score: number;
}

function ScoreBar({ label, score }: ScoreBarProps) {
  const getBarColor = (scoreValue: number) => {
    if (scoreValue >= 80) return 'bg-green-500';
    if (scoreValue >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{score.toFixed(0)}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${getBarColor(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
