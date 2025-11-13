/**
 * Security Dashboard Component
 *
 * Displays comprehensive security analytics including:
 * - Real-time threat levels
 * - Security events stream
 * - Vulnerability status
 * - Incident tracking
 * - Compliance metrics
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
  SecurityDashboardSummary,
  SecurityIncident,
  SecurityEvent,
  Severity
} from '@/types/security';

interface SecurityDashboardProps {
  workspaceId: string;
}

export const SecurityDashboard: React.FC<SecurityDashboardProps> = ({ workspaceId }) => {
  const [summary, setSummary] = useState<SecurityDashboardSummary | null>(null);
  const [incidents, setIncidents] = useState<SecurityIncident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSecurityData();

    // Refresh every 30 seconds
    const interval = setInterval(fetchSecurityData, 30000);

    return () => clearInterval(interval);
  }, [workspaceId]);

  const fetchSecurityData = async () => {
    try {
      setLoading(true);

      // Fetch dashboard summary
      const summaryResponse = await fetch(
        `/api/v1/security/dashboard/${workspaceId}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      if (!summaryResponse.ok) {
        throw new Error('Failed to fetch security summary');
      }

      const summaryData = await summaryResponse.json();
      setSummary(summaryData);

      // Fetch recent incidents
      const incidentsResponse = await fetch(
        `/api/v1/security/incidents/${workspaceId}?limit=10`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      if (!incidentsResponse.ok) {
        throw new Error('Failed to fetch incidents');
      }

      const incidentsData = await incidentsResponse.json();
      setIncidents(incidentsData);

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error fetching security data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getThreatLevelColor = (score: number): string => {
    if (score >= 80) return 'bg-red-500';
    if (score >= 60) return 'bg-orange-500';
    if (score >= 40) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getThreatLevelText = (score: number): string => {
    if (score >= 80) return 'Critical';
    if (score >= 60) return 'High';
    if (score >= 40) return 'Medium';
    return 'Low';
  };

  const getSeverityColor = (severity: Severity): string => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-50';
      case 'high': return 'text-orange-600 bg-orange-50';
      case 'medium': return 'text-yellow-600 bg-yellow-50';
      case 'low': return 'text-blue-600 bg-blue-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error: {error}</p>
        <button
          onClick={fetchSecurityData}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Security Dashboard</h1>
        <div className="text-sm text-gray-500">
          Last updated: {new Date(summary.last_updated).toLocaleString()}
        </div>
      </div>

      {/* Threat Level Indicator */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Current Threat Level</h2>
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl font-bold">
                {getThreatLevelText(summary.max_threat_score)}
              </span>
              <span className="text-lg text-gray-600">
                {summary.max_threat_score.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className={`h-4 rounded-full ${getThreatLevelColor(summary.max_threat_score)}`}
                style={{ width: `${summary.max_threat_score}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Security Events */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Security Events (24h)</h3>
          <div className="text-3xl font-bold text-gray-900">{summary.security_events_24h}</div>
          <div className="mt-2 flex items-center space-x-2">
            <span className="text-sm text-red-600">{summary.critical_events} critical</span>
            <span className="text-sm text-orange-600">{summary.high_events} high</span>
          </div>
        </div>

        {/* Open Incidents */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Open Incidents</h3>
          <div className="text-3xl font-bold text-gray-900">{summary.open_incidents}</div>
          <div className="mt-2">
            <span className="text-sm text-red-600">{summary.critical_incidents} critical</span>
          </div>
        </div>

        {/* Vulnerabilities */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Vulnerabilities</h3>
          <div className="text-3xl font-bold text-gray-900">
            {summary.critical_vulnerabilities + summary.high_vulnerabilities}
          </div>
          <div className="mt-2 flex items-center space-x-2">
            <span className="text-sm text-red-600">{summary.critical_vulnerabilities} critical</span>
            <span className="text-sm text-orange-600">{summary.high_vulnerabilities} high</span>
          </div>
        </div>

        {/* Compliance Score */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Compliance Score</h3>
          <div className="text-3xl font-bold text-gray-900">
            {summary.avg_compliance_score.toFixed(1)}%
          </div>
          <div className="mt-2">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-500 h-2 rounded-full"
                style={{ width: `${summary.avg_compliance_score}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Incidents */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Security Incidents</h2>

        {incidents.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No recent incidents</p>
        ) : (
          <div className="space-y-4">
            {incidents.map((incident) => (
              <div
                key={incident.incident_id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <span className="font-mono text-sm text-gray-600">
                        {incident.incident_number}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${getSeverityColor(incident.severity)}`}>
                        {incident.severity}
                      </span>
                      <span className="px-2 py-1 rounded text-xs font-semibold bg-blue-50 text-blue-600">
                        {incident.status}
                      </span>
                    </div>
                    <h3 className="font-semibold text-gray-900 mb-1">
                      {incident.incident_type.replace(/_/g, ' ').toUpperCase()}
                    </h3>
                    <p className="text-sm text-gray-600 mb-2">{incident.description}</p>
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span>Detected: {new Date(incident.timeline.detected_at).toLocaleString()}</span>
                      {incident.timeline.resolved_at && (
                        <span>Resolved: {new Date(incident.timeline.resolved_at).toLocaleString()}</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Run Vulnerability Scan
          </button>
          <button className="px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
            Generate Security Report
          </button>
          <button className="px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
            View Compliance Status
          </button>
        </div>
      </div>
    </div>
  );
};

export default SecurityDashboard;
