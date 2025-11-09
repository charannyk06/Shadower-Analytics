/**
 * Error Tracking Components
 * Simplified components for error tracking dashboard
 */

import React from 'react';
import {
  ErrorOverview as ErrorOverviewType,
  ErrorDetail,
  ErrorTimeline as ErrorTimelineType,
  TopErrors,
  ErrorCorrelations as ErrorCorrelationsType,
  RecoveryAnalysis as RecoveryAnalysisType,
  ErrorSeverity,
} from '@/types/error-tracking';

// ============================================================================
// Error Overview Component
// ============================================================================

interface ErrorOverviewProps {
  overview: ErrorOverviewType;
}

export function ErrorOverview({ overview }: ErrorOverviewProps) {
  const getImpactColor = (impact: string) => {
    const colors = {
      critical: 'bg-red-100 text-red-800 border-red-200',
      high: 'bg-orange-100 text-orange-800 border-orange-200',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      low: 'bg-green-100 text-green-800 border-green-200',
    };
    return colors[impact as keyof typeof colors] || colors.medium;
  };

  const stats = [
    { label: 'Total Errors', value: overview.totalErrors.toLocaleString(), change: overview.errorRateChange },
    { label: 'Unique Errors', value: overview.uniqueErrors.toLocaleString() },
    { label: 'Affected Users', value: overview.affectedUsers.toLocaleString() },
    { label: 'Affected Agents', value: overview.affectedAgents.toLocaleString() },
    { label: 'Critical Rate', value: `${overview.criticalErrorRate}%` },
    { label: 'Avg Recovery', value: `${Math.round(overview.avgRecoveryTime)}s` },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
      {stats.map((stat, index) => (
        <div key={index} className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500 mb-1">{stat.label}</div>
          <div className="flex items-baseline gap-2">
            <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
            {stat.change !== undefined && (
              <span
                className={`text-sm ${
                  stat.change > 0 ? 'text-red-600' : 'text-green-600'
                }`}
              >
                {stat.change > 0 ? '+' : ''}
                {stat.change.toFixed(1)}%
              </span>
            )}
          </div>
        </div>
      ))}

      {/* System Impact Card */}
      <div className={`rounded-lg shadow p-4 border-2 ${getImpactColor(overview.systemImpact)}`}>
        <div className="text-sm font-medium mb-1">System Impact</div>
        <div className="text-2xl font-bold uppercase">{overview.systemImpact}</div>
        {overview.estimatedRevenueLoss > 0 && (
          <div className="text-sm mt-1">
            Est. Loss: ${overview.estimatedRevenueLoss.toFixed(2)}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Error Timeline Component
// ============================================================================

interface ErrorTimelineProps {
  timeline: ErrorTimelineType;
}

export function ErrorTimeline({ timeline }: ErrorTimelineProps) {
  const maxCount = Math.max(...timeline.errorsByTime.map((p) => p.count), 1);

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Error Timeline</h3>

      {/* Simple bar chart */}
      <div className="space-y-2 mb-6">
        {timeline.errorsByTime.slice(-24).map((point, index) => (
          <div key={index} className="flex items-center gap-2">
            <div className="text-xs text-gray-500 w-32">
              {new Date(point.timestamp).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
              })}
            </div>
            <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
              <div
                className="bg-blue-500 h-full rounded-full flex items-center px-2"
                style={{ width: `${(point.count / maxCount) * 100}%` }}
              >
                {point.count > 0 && (
                  <span className="text-xs text-white font-medium">{point.count}</span>
                )}
              </div>
            </div>
            {point.criticalCount > 0 && (
              <div className="text-xs text-red-600 font-medium w-16">
                {point.criticalCount} critical
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Spikes */}
      {timeline.spikes.length > 0 && (
        <div className="mt-6">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Recent Spikes</h4>
          <div className="space-y-2">
            {timeline.spikes.slice(0, 3).map((spike, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border ${
                  spike.resolved ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {spike.totalErrors} errors ({spike.peakErrors} peak)
                    </div>
                    <div className="text-xs text-gray-600 mt-1">
                      {new Date(spike.startTime).toLocaleString()}
                    </div>
                  </div>
                  <span
                    className={`text-xs px-2 py-1 rounded-full ${
                      spike.resolved
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {spike.resolved ? 'Resolved' : 'Active'}
                  </span>
                </div>
                {spike.primaryCause && (
                  <div className="text-xs text-gray-600 mt-1">
                    Cause: {spike.primaryCause}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Error List Component
// ============================================================================

interface ErrorListProps {
  errors: ErrorDetail[];
  topErrors: TopErrors;
  selectedError: string | null;
  onErrorSelect: (errorId: string) => void;
}

export function ErrorList({ errors, topErrors, selectedError, onErrorSelect }: ErrorListProps) {
  const getSeverityColor = (severity: ErrorSeverity) => {
    const colors = {
      critical: 'bg-red-100 text-red-800',
      high: 'bg-orange-100 text-orange-800',
      medium: 'bg-yellow-100 text-yellow-800',
      low: 'bg-green-100 text-green-800',
    };
    return colors[severity];
  };

  const getStatusColor = (status: string) => {
    const colors = {
      new: 'bg-blue-100 text-blue-800',
      acknowledged: 'bg-purple-100 text-purple-800',
      investigating: 'bg-yellow-100 text-yellow-800',
      resolved: 'bg-green-100 text-green-800',
      ignored: 'bg-gray-100 text-gray-800',
    };
    return colors[status as keyof typeof colors] || colors.new;
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b">
        <h3 className="text-lg font-semibold text-gray-900">Errors</h3>
      </div>

      {/* Top Errors Summary */}
      {topErrors.byOccurrence.length > 0 && (
        <div className="p-4 bg-gray-50 border-b">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Top Errors</h4>
          <div className="space-y-1">
            {topErrors.byOccurrence.slice(0, 5).map((error) => (
              <div
                key={error.errorId}
                className="text-xs text-gray-600 flex justify-between cursor-pointer hover:text-gray-900"
                onClick={() => onErrorSelect(error.errorId)}
              >
                <span className="truncate flex-1">{error.type}</span>
                <span className="font-medium ml-2">{error.count}x</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error List */}
      <div className="divide-y max-h-[600px] overflow-y-auto">
        {errors.slice(0, 50).map((error) => (
          <div
            key={error.errorId}
            className={`p-4 cursor-pointer hover:bg-gray-50 ${
              selectedError === error.errorId ? 'bg-blue-50' : ''
            }`}
            onClick={() => onErrorSelect(error.errorId)}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 text-sm truncate">
                  {error.type}
                </div>
                <div className="text-xs text-gray-600 truncate mt-1">
                  {error.message}
                </div>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <span className={`px-2 py-1 text-xs rounded-full ${getSeverityColor(error.severity)}`}>
                  {error.severity}
                </span>
                <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(error.status)}`}>
                  {error.status}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span>{error.occurrences} occurrences</span>
              <span>{error.impact.usersAffected} users</span>
              <span>Last: {new Date(error.lastSeen).toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Error Details Component
// ============================================================================

interface ErrorDetailsProps {
  error: ErrorDetail | null;
  onResolve: (errorId: string, resolution: string) => void;
  onIgnore: (errorId: string) => void;
}

export function ErrorDetails({ error, onResolve, onIgnore }: ErrorDetailsProps) {
  const [isResolving, setIsResolving] = React.useState(false);
  const [resolution, setResolution] = React.useState('');

  if (!error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center text-gray-500">
          Select an error to view details
        </div>
      </div>
    );
  }

  const getSeverityColor = (severity: ErrorSeverity) => {
    const colors = {
      critical: 'bg-red-100 text-red-800',
      high: 'bg-orange-100 text-orange-800',
      medium: 'bg-yellow-100 text-yellow-800',
      low: 'bg-green-100 text-green-800',
    };
    return colors[severity];
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b">
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Error Details</h3>
          <span className={`px-2 py-1 text-xs rounded-full ${getSeverityColor(error.severity)}`}>
            {error.severity.toUpperCase()}
          </span>
        </div>

        <p className="text-sm font-mono text-gray-700 mb-2">{error.type}</p>
        <p className="text-sm text-gray-600">{error.message}</p>

        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Occurrences:</span>
            <span className="ml-2 text-gray-900 font-medium">{error.occurrences}</span>
          </div>
          <div>
            <span className="text-gray-500">Users affected:</span>
            <span className="ml-2 text-gray-900 font-medium">{error.impact.usersAffected}</span>
          </div>
          <div>
            <span className="text-gray-500">First seen:</span>
            <span className="ml-2 text-gray-900">{new Date(error.firstSeen).toLocaleString()}</span>
          </div>
          <div>
            <span className="text-gray-500">Last seen:</span>
            <span className="ml-2 text-gray-900">{new Date(error.lastSeen).toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Stack Trace */}
      {error.stackTrace && (
        <div className="p-6 border-b">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Stack Trace</h4>
          <pre className="text-xs bg-gray-900 text-gray-100 p-3 rounded overflow-x-auto max-h-48">
            {error.stackTrace}
          </pre>
        </div>
      )}

      {/* Impact */}
      <div className="p-6 border-b">
        <h4 className="text-sm font-semibold text-gray-900 mb-3">Impact</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">Affected Executions:</span>
            <span className="text-gray-900">{error.impact.executionsAffected}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Credits Lost:</span>
            <span className="text-gray-900">{error.impact.creditsLost}</span>
          </div>
          {error.impact.cascadingFailures > 0 && (
            <div className="flex justify-between">
              <span className="text-gray-500">Cascading Failures:</span>
              <span className="text-gray-900">{error.impact.cascadingFailures}</span>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      {error.status !== 'resolved' && (
        <div className="p-6">
          {!isResolving ? (
            <div className="flex gap-2">
              <button
                onClick={() => setIsResolving(true)}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Mark as Resolved
              </button>
              <button
                onClick={() => onIgnore(error.errorId)}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Ignore
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                placeholder="Describe the resolution..."
                className="w-full px-3 py-2 border rounded-lg resize-none"
                rows={3}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    onResolve(error.errorId, resolution);
                    setIsResolving(false);
                    setResolution('');
                  }}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Confirm
                </button>
                <button
                  onClick={() => {
                    setIsResolving(false);
                    setResolution('');
                  }}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Error Correlations Component
// ============================================================================

interface ErrorCorrelationsProps {
  correlations: ErrorCorrelationsType;
}

export function ErrorCorrelations({ correlations }: ErrorCorrelationsProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Error Correlations</h3>

      {correlations.agentCorrelation.length === 0 &&
       correlations.userCorrelation.length === 0 &&
       correlations.errorChains.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          No significant correlations detected
        </div>
      ) : (
        <div className="text-sm text-gray-600">
          Correlation analysis in progress...
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Recovery Analysis Component
// ============================================================================

interface RecoveryAnalysisProps {
  recovery: RecoveryAnalysisType;
}

export function RecoveryAnalysis({ recovery }: RecoveryAnalysisProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 mt-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Recovery Analysis</h3>

      {recovery.recoveryMethods.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          No recovery data available
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Automatic Recovery</h4>
            <div className="text-sm text-gray-600 space-y-1">
              <div>Avg: {recovery.recoveryTimes.automatic.avg}s</div>
              <div>P95: {recovery.recoveryTimes.automatic.p95}s</div>
            </div>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Manual Recovery</h4>
            <div className="text-sm text-gray-600 space-y-1">
              <div>Avg: {recovery.recoveryTimes.manual.avg}s</div>
              <div>P95: {recovery.recoveryTimes.manual.p95}s</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
