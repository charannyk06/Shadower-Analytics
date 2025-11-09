/**
 * LeaderboardFilters component for filtering leaderboard view
 */

'use client';

import React from 'react';
import {
  TimeFrame,
  AgentCriteria,
  UserCriteria,
  WorkspaceCriteria,
  LeaderboardType,
} from '@/types/leaderboards';

export interface LeaderboardFiltersProps {
  type: LeaderboardType;
  timeframe: TimeFrame;
  criteria: AgentCriteria | UserCriteria | WorkspaceCriteria;
  onTimeframeChange: (timeframe: TimeFrame) => void;
  onCriteriaChange: (criteria: AgentCriteria | UserCriteria | WorkspaceCriteria) => void;
}

const timeframeOptions: { value: TimeFrame; label: string }[] = [
  { value: '24h', label: 'Last 24 Hours' },
  { value: '7d', label: 'Last 7 Days' },
  { value: '30d', label: 'Last 30 Days' },
  { value: '90d', label: 'Last 90 Days' },
  { value: 'all', label: 'All Time' },
];

const agentCriteriaOptions: { value: AgentCriteria; label: string; description: string }[] = [
  { value: 'success_rate', label: 'Success Rate', description: 'Highest success rate' },
  { value: 'runs', label: 'Total Runs', description: 'Most executions' },
  { value: 'speed', label: 'Speed', description: 'Fastest execution time' },
  { value: 'efficiency', label: 'Efficiency', description: 'Best cost & performance' },
  { value: 'popularity', label: 'Popularity', description: 'Most used by users' },
];

const userCriteriaOptions: { value: UserCriteria; label: string; description: string }[] = [
  { value: 'activity', label: 'Activity', description: 'Most active users' },
  { value: 'efficiency', label: 'Efficiency', description: 'Best success rate' },
  { value: 'contribution', label: 'Contribution', description: 'Highest contribution' },
  { value: 'savings', label: 'Savings', description: 'Most cost-effective' },
];

const workspaceCriteriaOptions: { value: WorkspaceCriteria; label: string; description: string }[] = [
  { value: 'activity', label: 'Activity', description: 'Most active workspaces' },
  { value: 'efficiency', label: 'Efficiency', description: 'Best performance' },
  { value: 'growth', label: 'Growth', description: 'Fastest growing' },
  { value: 'innovation', label: 'Innovation', description: 'Most innovative' },
];

export function LeaderboardFilters({
  type,
  timeframe,
  criteria,
  onTimeframeChange,
  onCriteriaChange,
}: LeaderboardFiltersProps) {
  const getCriteriaOptions = () => {
    switch (type) {
      case 'agents':
        return agentCriteriaOptions;
      case 'users':
        return userCriteriaOptions;
      case 'workspaces':
        return workspaceCriteriaOptions;
      default:
        return [];
    }
  };

  const criteriaOptions = getCriteriaOptions();

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Timeframe Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Time Period
          </label>
          <select
            value={timeframe}
            onChange={(e) => onTimeframeChange(e.target.value as TimeFrame)}
            className="block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
          >
            {timeframeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Criteria Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Ranking Criteria
          </label>
          <select
            value={criteria}
            onChange={(e) => onCriteriaChange(e.target.value as any)}
            className="block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
          >
            {criteriaOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label} - {option.description}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
