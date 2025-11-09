/**
 * Error Analysis Component
 * Displays error patterns, types, and recovery metrics
 */

import React from 'react';
import { ErrorAnalysis as ErrorAnalysisType } from '@/types/agent-analytics';
import { Card } from '@/components/ui/Card';

interface ErrorAnalysisProps {
  errors: ErrorAnalysisType;
}

export function ErrorAnalysis({ errors }: ErrorAnalysisProps) {
  const topErrors = Object.entries(errors.errorsByType)
    .sort(([, a], [, b]) => b.count - a.count)
    .slice(0, 5);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'text-red-600';
      case 'medium':
        return 'text-yellow-600';
      case 'low':
        return 'text-green-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <Card title="Error Analysis" subtitle={`${errors.totalErrors} total errors (${errors.errorRate.toFixed(2)}% error rate)`}>
      <div className="space-y-6">
        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Mean Time to Recovery</div>
            <div className="mt-1 text-2xl font-bold text-gray-900">
              {errors.meanTimeToRecovery.toFixed(2)}s
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Auto Recovery Rate</div>
            <div className="mt-1 text-2xl font-bold text-gray-900">
              {errors.autoRecoveryRate.toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Top Errors */}
        {topErrors.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">
              Top Error Types
            </h4>
            <div className="space-y-2">
              {topErrors.map(([errorType, details]) => (
                <div
                  key={errorType}
                  className="flex items-start justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900 truncate">
                        {errorType}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${getSeverityColor(details.severity)}`}>
                        {details.severity}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-gray-500 line-clamp-2">
                      {details.exampleMessage}
                    </p>
                    <div className="mt-2 flex items-center gap-4 text-xs text-gray-600">
                      <span>{details.count} occurrences ({details.percentage.toFixed(1)}%)</span>
                      <span>Recovery: {details.autoRecoveryRate.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error Patterns */}
        {errors.errorPatterns.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">
              Error Patterns & Solutions
            </h4>
            <div className="space-y-3">
              {errors.errorPatterns.map((pattern, index) => (
                <div
                  key={index}
                  className="border border-gray-200 rounded-lg p-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h5 className="font-medium text-gray-900">
                          {pattern.pattern}
                        </h5>
                        <span className={`text-xs font-semibold ${getImpactColor(pattern.impact)}`}>
                          {pattern.impact} impact
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-gray-700">
                        <span className="font-medium">Suggested Fix:</span>{' '}
                        {pattern.suggestedFix}
                      </p>
                    </div>
                    <div className="ml-4 flex-shrink-0">
                      <div className="text-xs text-gray-500">Frequency</div>
                      <div className="text-lg font-bold text-gray-900">
                        {pattern.frequency}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {errors.totalErrors === 0 && (
          <div className="text-center py-8 text-gray-500">
            <svg className="mx-auto h-12 w-12 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="mt-2 text-sm">No errors detected in this timeframe</p>
          </div>
        )}
      </div>
    </Card>
  );
}
