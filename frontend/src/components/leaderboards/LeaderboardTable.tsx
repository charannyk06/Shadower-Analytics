/**
 * LeaderboardTable component for displaying competitive rankings
 */

'use client';

import React from 'react';
import {
  AgentRanking,
  UserRanking,
  WorkspaceRanking,
  LeaderboardType,
  Badge,
  Tier,
  RankChange,
} from '@/types/leaderboards';
import { Card } from '@/components/ui/Card';
import { ArrowUp, ArrowDown, Minus, TrendingUp, Award, Trophy } from 'lucide-react';

// ===================================================================
// TYPES
// ===================================================================

export interface LeaderboardTableProps {
  type: LeaderboardType;
  rankings: (AgentRanking | UserRanking | WorkspaceRanking)[];
  currentUserId?: string;
  loading?: boolean;
  error?: Error | null;
}

// ===================================================================
// UTILITY COMPONENTS
// ===================================================================

function RankChangeIndicator({ change }: { change: RankChange }) {
  if (change === 'new') {
    return (
      <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-700 bg-blue-50 rounded-full">
        <TrendingUp className="w-3 h-3 mr-1" />
        New
      </span>
    );
  }

  if (change === 'up') {
    return (
      <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-green-700 bg-green-50 rounded-full">
        <ArrowUp className="w-3 h-3 mr-1" />
        Up
      </span>
    );
  }

  if (change === 'down') {
    return (
      <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-red-700 bg-red-50 rounded-full">
        <ArrowDown className="w-3 h-3 mr-1" />
        Down
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-gray-700 bg-gray-50 rounded-full">
      <Minus className="w-3 h-3 mr-1" />
      Same
    </span>
  );
}

function BadgeDisplay({ badge }: { badge?: Badge }) {
  if (!badge) return null;

  const badgeConfig = {
    gold: { color: 'text-yellow-600', bg: 'bg-yellow-50', icon: Trophy },
    silver: { color: 'text-gray-600', bg: 'bg-gray-50', icon: Award },
    bronze: { color: 'text-orange-600', bg: 'bg-orange-50', icon: Award },
  };

  const config = badgeConfig[badge];
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center px-2 py-1 text-xs font-medium ${config.color} ${config.bg} rounded-full`}>
      <Icon className="w-3 h-3 mr-1" />
      {badge.charAt(0).toUpperCase() + badge.slice(1)}
    </span>
  );
}

function TierDisplay({ tier }: { tier: Tier }) {
  const tierConfig = {
    platinum: { color: 'text-purple-700', bg: 'bg-purple-50', label: 'Platinum' },
    gold: { color: 'text-yellow-700', bg: 'bg-yellow-50', label: 'Gold' },
    silver: { color: 'text-gray-700', bg: 'bg-gray-50', label: 'Silver' },
    bronze: { color: 'text-orange-700', bg: 'bg-orange-50', label: 'Bronze' },
  };

  const config = tierConfig[tier];

  return (
    <span className={`inline-flex items-center px-2 py-1 text-xs font-medium ${config.color} ${config.bg} rounded-full`}>
      {config.label}
    </span>
  );
}

function PercentileBadge({ percentile }: { percentile: number }) {
  let color = 'text-gray-700 bg-gray-50';

  if (percentile >= 95) {
    color = 'text-purple-700 bg-purple-50';
  } else if (percentile >= 80) {
    color = 'text-blue-700 bg-blue-50';
  } else if (percentile >= 60) {
    color = 'text-green-700 bg-green-50';
  }

  return (
    <span className={`inline-flex items-center px-2 py-1 text-xs font-medium ${color} rounded-full`}>
      Top {(100 - percentile).toFixed(0)}%
    </span>
  );
}

// ===================================================================
// AGENT LEADERBOARD
// ===================================================================

function AgentRow({ ranking, index }: { ranking: AgentRanking; index: number }) {
  return (
    <tr className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
        #{ranking.rank}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex flex-col">
          <div className="text-sm font-medium text-gray-900">{ranking.agent.name}</div>
          <div className="text-xs text-gray-500">{ranking.agent.type}</div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center space-x-2">
          <RankChangeIndicator change={ranking.change} />
          {ranking.badge && <BadgeDisplay badge={ranking.badge} />}
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex flex-col text-sm">
          <div className="text-gray-900">{ranking.metrics.totalRuns} runs</div>
          <div className="text-gray-500">{ranking.metrics.successRate.toFixed(1)}% success</div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex flex-col text-sm">
          <div className="text-gray-900">{ranking.metrics.avgRuntime.toFixed(0)}ms</div>
          <div className="text-gray-500">{ranking.metrics.uniqueUsers} users</div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {ranking.score.toFixed(2)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <PercentileBadge percentile={ranking.percentile} />
      </td>
    </tr>
  );
}

// ===================================================================
// USER LEADERBOARD
// ===================================================================

function UserRow({ ranking, index, isCurrentUser }: { ranking: UserRanking; index: number; isCurrentUser: boolean }) {
  return (
    <tr className={`${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'} ${isCurrentUser ? 'ring-2 ring-blue-500' : ''}`}>
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
        #{ranking.rank}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          {ranking.user.avatar && (
            <img
              className="h-8 w-8 rounded-full mr-3"
              src={ranking.user.avatar}
              alt={ranking.user.name}
            />
          )}
          <div className="flex flex-col">
            <div className="text-sm font-medium text-gray-900">
              {ranking.user.name}
              {isCurrentUser && <span className="ml-2 text-xs text-blue-600">(You)</span>}
            </div>
          </div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <RankChangeIndicator change={ranking.change} />
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex flex-col text-sm">
          <div className="text-gray-900">{ranking.metrics.totalActions} actions</div>
          <div className="text-gray-500">{ranking.metrics.successRate.toFixed(1)}% success</div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex flex-col text-sm">
          <div className="text-gray-900">{ranking.metrics.agentsUsed} agents</div>
          <div className="text-gray-500">{ranking.metrics.creditsUsed.toFixed(0)} credits</div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {ranking.score.toFixed(2)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex flex-col">
          <PercentileBadge percentile={ranking.percentile} />
          {ranking.achievements.length > 0 && (
            <div className="text-xs text-gray-500 mt-1">
              {ranking.achievements.length} achievement{ranking.achievements.length > 1 ? 's' : ''}
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

// ===================================================================
// WORKSPACE LEADERBOARD
// ===================================================================

function WorkspaceRow({ ranking, index }: { ranking: WorkspaceRanking; index: number }) {
  return (
    <tr className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
        #{ranking.rank}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex flex-col">
          <div className="text-sm font-medium text-gray-900">{ranking.workspace.name}</div>
          <div className="text-xs text-gray-500">
            {ranking.workspace.plan} • {ranking.workspace.memberCount} members
          </div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center space-x-2">
          <RankChangeIndicator change={ranking.change} />
          <TierDisplay tier={ranking.tier} />
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex flex-col text-sm">
          <div className="text-gray-900">{ranking.metrics.totalActivity} actions</div>
          <div className="text-gray-500">{ranking.metrics.activeUsers} active users</div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex flex-col text-sm">
          <div className="text-gray-900">{ranking.metrics.agentCount} agents</div>
          <div className="text-gray-500">{ranking.metrics.successRate.toFixed(1)}% success</div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex flex-col text-sm">
          <div className="text-gray-900">{ranking.score.toFixed(2)}</div>
          <div className="text-gray-500">Health: {ranking.metrics.healthScore.toFixed(0)}</div>
        </div>
      </td>
    </tr>
  );
}

// ===================================================================
// MAIN COMPONENT
// ===================================================================

export function LeaderboardTable({
  type,
  rankings,
  currentUserId,
  loading = false,
  error = null,
}: LeaderboardTableProps) {
  if (loading) {
    return (
      <Card>
        <div className="animate-pulse p-6">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <div className="p-6 text-center">
          <p className="text-red-600">Error loading leaderboard: {error.message}</p>
        </div>
      </Card>
    );
  }

  if (!rankings || rankings.length === 0) {
    return (
      <Card>
        <div className="p-6 text-center">
          <p className="text-gray-500">No rankings available yet. Be the first to qualify!</p>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rank
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {type === 'agents' ? 'Agent' : type === 'users' ? 'User' : 'Workspace'}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Activity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Performance
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Score
              </th>
              {type !== 'workspaces' && (
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Percentile
                </th>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {type === 'agents' &&
              rankings.map((ranking, index) => (
                <AgentRow key={ranking.rank} ranking={ranking as AgentRanking} index={index} />
              ))}
            {type === 'users' &&
              rankings.map((ranking, index) => (
                <UserRow
                  key={ranking.rank}
                  ranking={ranking as UserRanking}
                  index={index}
                  isCurrentUser={(ranking as UserRanking).user.id === currentUserId}
                />
              ))}
            {type === 'workspaces' &&
              rankings.map((ranking, index) => (
                <WorkspaceRow key={ranking.rank} ranking={ranking as WorkspaceRanking} index={index} />
              ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
