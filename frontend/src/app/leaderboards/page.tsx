/**
 * Leaderboards page - Competitive rankings for agents, users, and workspaces
 */

'use client';

import React, { useState } from 'react';
import { LeaderboardTable } from '@/components/leaderboards/LeaderboardTable';
import { LeaderboardFilters } from '@/components/leaderboards/LeaderboardFilters';
import { Card } from '@/components/ui/Card';
import {
  useAgentLeaderboard,
  useUserLeaderboard,
  useWorkspaceLeaderboard,
  useRefreshLeaderboards,
} from '@/hooks/api/useLeaderboards';
import {
  TimeFrame,
  AgentCriteria,
  UserCriteria,
  WorkspaceCriteria,
  LeaderboardType,
} from '@/types/leaderboards';
import { Trophy, Users, Building2, RefreshCw } from 'lucide-react';

export default function LeaderboardsPage() {
  // TODO: Get from auth context or props
  const workspaceId = 'workspace-123'; // Replace with actual workspace ID
  const currentUserId = 'user-123'; // Replace with actual user ID

  // State
  const [activeTab, setActiveTab] = useState<LeaderboardType>('agents');
  const [timeframe, setTimeframe] = useState<TimeFrame>('7d');
  const [agentCriteria, setAgentCriteria] = useState<AgentCriteria>('success_rate');
  const [userCriteria, setUserCriteria] = useState<UserCriteria>('activity');
  const [workspaceCriteria, setWorkspaceCriteria] = useState<WorkspaceCriteria>('activity');

  // Fetch leaderboards
  const agentLeaderboard = useAgentLeaderboard({
    workspaceId,
    timeframe,
    criteria: agentCriteria,
    enabled: activeTab === 'agents',
  });

  const userLeaderboard = useUserLeaderboard({
    workspaceId,
    timeframe,
    criteria: userCriteria,
    enabled: activeTab === 'users',
  });

  const workspaceLeaderboard = useWorkspaceLeaderboard({
    timeframe,
    criteria: workspaceCriteria,
    enabled: activeTab === 'workspaces',
  });

  const refreshMutation = useRefreshLeaderboards();

  // Handlers
  const handleRefresh = () => {
    refreshMutation.mutate(workspaceId);
  };

  const handleCriteriaChange = (criteria: any) => {
    switch (activeTab) {
      case 'agents':
        setAgentCriteria(criteria as AgentCriteria);
        break;
      case 'users':
        setUserCriteria(criteria as UserCriteria);
        break;
      case 'workspaces':
        setWorkspaceCriteria(criteria as WorkspaceCriteria);
        break;
    }
  };

  const getCurrentCriteria = () => {
    switch (activeTab) {
      case 'agents':
        return agentCriteria;
      case 'users':
        return userCriteria;
      case 'workspaces':
        return workspaceCriteria;
    }
  };

  const getCurrentLeaderboard = () => {
    switch (activeTab) {
      case 'agents':
        return agentLeaderboard;
      case 'users':
        return userLeaderboard;
      case 'workspaces':
        return workspaceLeaderboard;
    }
  };

  const currentLeaderboard = getCurrentLeaderboard();

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center">
                <Trophy className="w-8 h-8 mr-3 text-yellow-500" />
                Leaderboards
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                Competitive rankings and performance metrics
              </p>
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              <RefreshCw
                className={`w-4 h-4 mr-2 ${refreshMutation.isPending ? 'animate-spin' : ''}`}
              />
              Refresh
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('agents')}
                className={`${
                  activeTab === 'agents'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center`}
              >
                <Trophy className="w-5 h-5 mr-2" />
                Agents
              </button>
              <button
                onClick={() => setActiveTab('users')}
                className={`${
                  activeTab === 'users'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center`}
              >
                <Users className="w-5 h-5 mr-2" />
                Users
              </button>
              <button
                onClick={() => setActiveTab('workspaces')}
                className={`${
                  activeTab === 'workspaces'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center`}
              >
                <Building2 className="w-5 h-5 mr-2" />
                Workspaces
              </button>
            </nav>
          </div>
        </div>

        {/* Filters */}
        <LeaderboardFilters
          type={activeTab}
          timeframe={timeframe}
          criteria={getCurrentCriteria()}
          onTimeframeChange={setTimeframe}
          onCriteriaChange={handleCriteriaChange}
        />

        {/* Stats Cards */}
        {currentLeaderboard.data && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <Card>
              <div className="p-6">
                <div className="text-sm font-medium text-gray-500">Total Participants</div>
                <div className="mt-2 text-3xl font-semibold text-gray-900">
                  {currentLeaderboard.data.total}
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-6">
                <div className="text-sm font-medium text-gray-500">Top Score</div>
                <div className="mt-2 text-3xl font-semibold text-gray-900">
                  {currentLeaderboard.data.rankings[0]?.score.toFixed(2) || 'N/A'}
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-6">
                <div className="text-sm font-medium text-gray-500">Updated</div>
                <div className="mt-2 text-lg font-medium text-gray-900">
                  {currentLeaderboard.data.calculatedAt
                    ? new Date(currentLeaderboard.data.calculatedAt).toLocaleTimeString()
                    : 'N/A'}
                </div>
                {currentLeaderboard.data.cached && (
                  <div className="mt-1 text-xs text-gray-500">(Cached)</div>
                )}
              </div>
            </Card>
          </div>
        )}

        {/* Leaderboard Table */}
        <LeaderboardTable
          type={activeTab}
          rankings={currentLeaderboard.data?.rankings || []}
          currentUserId={currentUserId}
          loading={currentLeaderboard.isLoading}
          error={currentLeaderboard.error}
        />

        {/* Pagination (if needed) */}
        {currentLeaderboard.data && currentLeaderboard.data.total > currentLeaderboard.data.limit && (
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-gray-700">
              Showing {currentLeaderboard.data.offset + 1} to{' '}
              {Math.min(
                currentLeaderboard.data.offset + currentLeaderboard.data.limit,
                currentLeaderboard.data.total
              )}{' '}
              of {currentLeaderboard.data.total} results
            </div>
            <div className="flex space-x-2">
              <button
                disabled={currentLeaderboard.data.offset === 0}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                disabled={
                  currentLeaderboard.data.offset + currentLeaderboard.data.limit >=
                  currentLeaderboard.data.total
                }
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
