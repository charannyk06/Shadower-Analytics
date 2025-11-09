/**
 * Workspace Overview Metrics Component
 * Displays key workspace metrics in a grid layout
 */

import React from 'react';
import { WorkspaceOverview } from '@/types/workspace';
import {
  Users,
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  UserPlus,
  Clock,
} from 'lucide-react';

interface OverviewMetricsProps {
  data: WorkspaceOverview;
}

export function OverviewMetrics({ data }: OverviewMetricsProps) {
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return <TrendingUp className="w-4 h-4 text-green-600" />;
      case 'decreasing':
        return <TrendingDown className="w-4 h-4 text-red-600" />;
      default:
        return <Minus className="w-4 h-4 text-gray-600" />;
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return 'text-green-600';
      case 'decreasing':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  const MetricCard = ({
    title,
    value,
    icon: Icon,
    subtitle,
    trend,
    trendValue,
  }: {
    title: string;
    value: string | number;
    icon: any;
    subtitle?: string;
    trend?: string;
    trendValue?: number;
  }) => (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-2">
        <div className="p-2 bg-blue-100 rounded-lg">
          <Icon className="w-5 h-5 text-blue-600" />
        </div>
        {trend && (
          <div className="flex items-center space-x-1">
            {getTrendIcon(trend)}
            {trendValue !== undefined && (
              <span className={`text-sm font-medium ${getTrendColor(trend)}`}>
                {trendValue > 0 ? '+' : ''}
                {trendValue.toFixed(1)}%
              </span>
            )}
          </div>
        )}
      </div>
      <h3 className="text-2xl font-bold text-gray-900">{value}</h3>
      <p className="text-sm text-gray-600">{title}</p>
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Overview</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Members"
          value={data.totalMembers}
          icon={Users}
          subtitle={`${data.activeMembers} active`}
          trendValue={data.memberGrowth}
          trend={data.memberGrowth > 0 ? 'increasing' : data.memberGrowth < 0 ? 'decreasing' : 'stable'}
        />

        <MetricCard
          title="Active Members"
          value={data.activeMembers}
          icon={Activity}
          subtitle={`${((data.activeMembers / data.totalMembers) * 100 || 0).toFixed(1)}% of total`}
        />

        <MetricCard
          title="Pending Invites"
          value={data.pendingInvites}
          icon={UserPlus}
        />

        <MetricCard
          title="Total Activity"
          value={data.totalActivity}
          icon={Activity}
          trend={data.activityTrend}
          subtitle={`${data.avgActivityPerMember.toFixed(1)} avg per member`}
        />

        <MetricCard
          title="Last Activity"
          value={formatDate(data.lastActivityAt)}
          icon={Clock}
        />

        <MetricCard
          title="Days Active"
          value={data.daysActive}
          icon={Clock}
          subtitle={`Since ${formatDate(data.createdAt)}`}
        />

        <MetricCard
          title="Activity Trend"
          value={data.activityTrend.charAt(0).toUpperCase() + data.activityTrend.slice(1)}
          icon={Activity}
          trend={data.activityTrend}
        />

        <MetricCard
          title="Member Growth"
          value={`${data.memberGrowth > 0 ? '+' : ''}${data.memberGrowth.toFixed(1)}%`}
          icon={TrendingUp}
          trend={data.memberGrowth > 0 ? 'increasing' : data.memberGrowth < 0 ? 'decreasing' : 'stable'}
        />
      </div>
    </div>
  );
}
