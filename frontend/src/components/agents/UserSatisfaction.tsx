/**
 * User Satisfaction Component
 * Displays user ratings, feedback, and usage patterns
 */

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { UserMetrics } from '@/types/agent-analytics';
import { Card } from '@/components/ui/Card';

interface UserSatisfactionProps {
  userMetrics: UserMetrics;
}

export function UserSatisfaction({ userMetrics }: UserSatisfactionProps) {
  const ratingDistributionData = [
    { rating: '5⭐', count: userMetrics.userRatings.distribution['5'], fill: '#10b981' },
    { rating: '4⭐', count: userMetrics.userRatings.distribution['4'], fill: '#3b82f6' },
    { rating: '3⭐', count: userMetrics.userRatings.distribution['3'], fill: '#f59e0b' },
    { rating: '2⭐', count: userMetrics.userRatings.distribution['2'], fill: '#f97316' },
    { rating: '1⭐', count: userMetrics.userRatings.distribution['1'], fill: '#ef4444' },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">User Satisfaction</h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Key Metrics */}
        <Card>
          <div className="space-y-4">
            <div>
              <div className="text-sm text-gray-600">Unique Users</div>
              <div className="text-3xl font-bold text-gray-900">
                {userMetrics.uniqueUsers.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Total Interactions</div>
              <div className="text-2xl font-semibold text-gray-900">
                {userMetrics.totalInteractions.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Avg per User</div>
              <div className="text-xl font-medium text-gray-900">
                {userMetrics.avgInteractionsPerUser.toFixed(1)}
              </div>
            </div>
          </div>
        </Card>

        {/* Average Rating */}
        <Card>
          <div className="text-center">
            <div className="text-sm text-gray-600 mb-2">Average Rating</div>
            <div className="flex items-center justify-center gap-2">
              <div className="text-5xl font-bold text-yellow-500">
                {userMetrics.userRatings.average.toFixed(1)}
              </div>
              <div className="text-2xl text-yellow-400">★</div>
            </div>
            <div className="mt-2 text-sm text-gray-500">
              Based on {userMetrics.userRatings.total} ratings
            </div>
            <div className="mt-4 space-y-1">
              {[5, 4, 3, 2, 1].map((rating) => {
                const count = userMetrics.userRatings.distribution[rating as keyof typeof userMetrics.userRatings.distribution];
                const percentage = userMetrics.userRatings.total > 0
                  ? (count / userMetrics.userRatings.total) * 100
                  : 0;
                return (
                  <div key={rating} className="flex items-center gap-2 text-xs">
                    <span className="w-8 text-gray-600">{rating}★</span>
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-yellow-400"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className="w-12 text-right text-gray-600">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>

        {/* Rating Distribution */}
        <Card title="Rating Distribution">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={ratingDistributionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="rating" tick={{ fill: '#6b7280', fontSize: 11 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '0.375rem',
                }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {ratingDistributionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Recent Feedback */}
      {userMetrics.feedback.length > 0 && (
        <Card title="Recent Feedback">
          <div className="space-y-3">
            {userMetrics.feedback.slice(0, 5).map((feedback, index) => (
              <div
                key={index}
                className="border-l-4 border-blue-500 bg-blue-50 p-4 rounded-r"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-yellow-400 font-semibold">
                      {'★'.repeat(feedback.rating)}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(feedback.timestamp).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <p className="mt-2 text-sm text-gray-700">{feedback.comment}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Top Users */}
      {userMetrics.topUsers.length > 0 && (
        <Card title="Top Users">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User ID
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Run Count
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Success Rate
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {userMetrics.topUsers.map((user, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-mono text-gray-900">
                      {user.userId.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">
                      {user.runCount.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                      <span className={`font-semibold ${
                        user.successRate >= 95 ? 'text-green-600' :
                        user.successRate >= 85 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {user.successRate.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
