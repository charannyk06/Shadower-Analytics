/**
 * Workspace Health Score Component
 * Displays overall workspace health with individual factor scores
 */

import React from 'react';
import { HealthFactors, WorkspaceStatus } from '@/types/workspace';

interface WorkspaceHealthScoreProps {
  score: number;
  factors: HealthFactors;
  status: WorkspaceStatus;
}

export function WorkspaceHealthScore({ score, factors, status }: WorkspaceHealthScoreProps) {
  const getScoreColor = (score: number): string => {
    if (score >= 80) return 'text-green-600 bg-green-100 border-green-300';
    if (score >= 60) return 'text-blue-600 bg-blue-100 border-blue-300';
    if (score >= 40) return 'text-yellow-600 bg-yellow-100 border-yellow-300';
    return 'text-red-600 bg-red-100 border-red-300';
  };

  const getStatusBadgeColor = (status: WorkspaceStatus): string => {
    const colors = {
      active: 'bg-green-100 text-green-800',
      idle: 'bg-yellow-100 text-yellow-800',
      at_risk: 'bg-red-100 text-red-800',
      churned: 'bg-gray-100 text-gray-800',
    };
    return colors[status] || colors.idle;
  };

  const getStatusLabel = (status: WorkspaceStatus): string => {
    return status.replace(/_/g, ' ').toUpperCase();
  };

  const HealthCircle = ({ value, label }: { value: number; label: string }) => {
    const colorClass = getScoreColor(value);
    return (
      <div className="flex flex-col items-center">
        <div
          className={`relative w-24 h-24 rounded-full border-4 flex items-center justify-center ${colorClass}`}
        >
          <span className="text-2xl font-bold">{value}</span>
        </div>
        <p className="mt-2 text-sm text-gray-600 capitalize">{label}</p>
      </div>
    );
  };

  const getHealthInsights = (score: number, factors: HealthFactors): string[] => {
    const insights: string[] = [];
    if (score < 60) insights.push('Consider increasing member engagement');
    if (factors.efficiency < 60) insights.push('Agent success rates could be improved');
    if (factors.activity < 60) insights.push('Workspace activity is below average');
    if (factors.reliability < 60) insights.push('High error rates detected');
    if (insights.length === 0) insights.push('Workspace is performing well!');
    return insights;
  };

  const insights = getHealthInsights(score, factors);

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Workspace Health</h2>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusBadgeColor(status)}`}>
          {getStatusLabel(status)}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
        {/* Overall Score */}
        <div className="flex flex-col items-center">
          <div
            className={`relative w-32 h-32 rounded-full border-8 flex items-center justify-center ${getScoreColor(
              score
            )}`}
          >
            <span className="text-3xl font-bold">{score}</span>
          </div>
          <p className="mt-2 text-sm font-medium text-gray-600">Overall Health</p>
        </div>

        {/* Factor Scores */}
        <HealthCircle value={factors.activity} label="Activity" />
        <HealthCircle value={factors.engagement} label="Engagement" />
        <HealthCircle value={factors.efficiency} label="Efficiency" />
        <HealthCircle value={factors.reliability} label="Reliability" />
      </div>

      {/* Health Insights */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h3 className="text-sm font-medium text-blue-900 mb-2">Health Insights</h3>
        <ul className="space-y-1 text-sm text-blue-700">
          {insights.map((insight, index) => (
            <li key={index}>• {insight}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
