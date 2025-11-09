/**
 * Member Activity Component
 * Displays member analytics including role breakdown, activity distribution, and top contributors
 */

import React from 'react';
import { MemberAnalytics } from '@/types/workspace';
import { Users, Award, AlertCircle } from 'lucide-react';

interface MemberActivityProps {
  data: MemberAnalytics;
}

export function MemberActivity({ data }: MemberActivityProps) {
  const getEngagementColor = (level: string): string => {
    const colors = {
      high: 'bg-green-100 text-green-800',
      medium: 'bg-blue-100 text-blue-800',
      low: 'bg-yellow-100 text-yellow-800',
      inactive: 'bg-gray-100 text-gray-800',
    };
    return colors[level as keyof typeof colors] || colors.inactive;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Member Analytics</h2>

      {/* Members by Role */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Users className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold">Members by Role</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <div className="text-3xl font-bold text-purple-600">{data.membersByRole.owner}</div>
            <div className="text-sm text-gray-600 mt-1">Owners</div>
          </div>
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <div className="text-3xl font-bold text-blue-600">{data.membersByRole.admin}</div>
            <div className="text-sm text-gray-600 mt-1">Admins</div>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <div className="text-3xl font-bold text-green-600">{data.membersByRole.member}</div>
            <div className="text-sm text-gray-600 mt-1">Members</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-3xl font-bold text-gray-600">{data.membersByRole.viewer}</div>
            <div className="text-sm text-gray-600 mt-1">Viewers</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Contributors */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Award className="w-5 h-5 text-yellow-600" />
            <h3 className="text-lg font-semibold">Top Contributors</h3>
          </div>
          <div className="space-y-3">
            {data.topContributors.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">No contributors yet</p>
            ) : (
              data.topContributors.slice(0, 5).map((contributor, index) => (
                <div
                  key={contributor.userId}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <div className="flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-600 rounded-full font-bold text-sm">
                      {index + 1}
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">{contributor.userName}</div>
                      <div className="text-xs text-gray-500">
                        {contributor.contribution.agentRuns} runs •{' '}
                        {contributor.contribution.successRate.toFixed(1)}% success
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-gray-900">
                      {contributor.contribution.creditsUsed.toFixed(0)} credits
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Inactive Members */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center space-x-2 mb-4">
            <AlertCircle className="w-5 h-5 text-orange-600" />
            <h3 className="text-lg font-semibold">Inactive Members</h3>
          </div>
          <div className="space-y-3">
            {data.inactiveMembers.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">All members are active!</p>
            ) : (
              data.inactiveMembers.slice(0, 5).map((member) => (
                <div
                  key={member.userId}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div>
                    <div className="font-medium text-gray-900">{member.userName}</div>
                    <div className="text-xs text-gray-500">
                      Last active: {formatDate(member.lastActiveAt)}
                    </div>
                  </div>
                  <div className="text-sm font-semibold text-orange-600">
                    {member.daysSinceActive}d ago
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Activity Distribution */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Activity Distribution</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Member
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Activity
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Active
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Engagement
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.activityDistribution.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                    No activity data available
                  </td>
                </tr>
              ) : (
                data.activityDistribution.slice(0, 10).map((item) => (
                  <tr key={item.userId} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {item.userName}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
                      {item.role}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.activityCount}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(item.lastActiveAt)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getEngagementColor(
                          item.engagementLevel
                        )}`}
                      >
                        {item.engagementLevel}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
