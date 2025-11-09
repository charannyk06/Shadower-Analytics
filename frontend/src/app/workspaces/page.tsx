/**
 * Workspaces List Page
 * Lists all available workspaces with quick access to analytics
 */

'use client';

import { useRouter } from 'next/navigation';
import { Building2, TrendingUp, Users, Activity } from 'lucide-react';

export default function WorkspacesPage() {
  const router = useRouter();

  // Mock workspaces for demo
  const workspaces = [
    {
      id: 'workspace-1',
      name: 'Production Workspace',
      plan: 'enterprise',
      members: 45,
      activeAgents: 23,
      healthScore: 92,
    },
    {
      id: 'workspace-2',
      name: 'Development Workspace',
      plan: 'pro',
      members: 12,
      activeAgents: 8,
      healthScore: 78,
    },
    {
      id: 'workspace-3',
      name: 'Testing Workspace',
      plan: 'starter',
      members: 5,
      activeAgents: 3,
      healthScore: 65,
    },
  ];

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-blue-600 bg-blue-100';
    if (score >= 40) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getPlanBadgeColor = (plan: string) => {
    const colors: Record<string, string> = {
      enterprise: 'bg-purple-100 text-purple-800',
      pro: 'bg-blue-100 text-blue-800',
      starter: 'bg-green-100 text-green-800',
      free: 'bg-gray-100 text-gray-800',
    };
    return colors[plan] || colors.free;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Workspaces</h1>
          <p className="mt-2 text-sm text-gray-600">
            Select a workspace to view detailed analytics
          </p>
        </div>

        {/* Workspace Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {workspaces.map((workspace) => (
            <div
              key={workspace.id}
              className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => router.push(`/workspaces/${workspace.id}/analytics`)}
            >
              <div className="p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <Building2 className="w-6 h-6 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {workspace.name}
                      </h3>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPlanBadgeColor(
                          workspace.plan
                        )}`}
                      >
                        {workspace.plan.charAt(0).toUpperCase() + workspace.plan.slice(1)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Health Score */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-600">Health Score</span>
                    <span
                      className={`text-sm font-bold px-2 py-1 rounded ${getHealthColor(
                        workspace.healthScore
                      )}`}
                    >
                      {workspace.healthScore}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        workspace.healthScore >= 80
                          ? 'bg-green-600'
                          : workspace.healthScore >= 60
                          ? 'bg-blue-600'
                          : workspace.healthScore >= 40
                          ? 'bg-yellow-600'
                          : 'bg-red-600'
                      }`}
                      style={{ width: `${workspace.healthScore}%` }}
                    />
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center space-x-2">
                    <Users className="w-4 h-4 text-gray-400" />
                    <div>
                      <div className="text-sm font-semibold text-gray-900">
                        {workspace.members}
                      </div>
                      <div className="text-xs text-gray-500">Members</div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Activity className="w-4 h-4 text-gray-400" />
                    <div>
                      <div className="text-sm font-semibold text-gray-900">
                        {workspace.activeAgents}
                      </div>
                      <div className="text-xs text-gray-500">Active Agents</div>
                    </div>
                  </div>
                </div>

                {/* View Analytics Link */}
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-blue-600 font-medium flex items-center space-x-1">
                      <TrendingUp className="w-4 h-4" />
                      <span>View Analytics</span>
                    </span>
                    <span className="text-gray-400">→</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Empty State */}
        {workspaces.length === 0 && (
          <div className="text-center py-12">
            <Building2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Workspaces</h3>
            <p className="text-gray-500">Get started by creating your first workspace</p>
          </div>
        )}
      </div>
    </div>
  );
}
