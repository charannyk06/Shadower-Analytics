/**
 * Optimization Suggestions Component
 * Displays AI-generated optimization recommendations
 */

import React from 'react';
import { OptimizationSuggestion } from '@/types/agent-analytics';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface OptimizationSuggestionsProps {
  suggestions: OptimizationSuggestion[];
  onImplement?: (suggestion: OptimizationSuggestion) => void;
}

export function OptimizationSuggestions({
  suggestions,
  onImplement,
}: OptimizationSuggestionsProps) {
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'performance':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        );
      case 'cost':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'reliability':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'performance':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'cost':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'reliability':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'user_experience':
        return 'bg-pink-100 text-pink-700 border-pink-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const getEffortColor = (effort: string) => {
    switch (effort) {
      case 'low':
        return 'text-green-600 bg-green-50';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50';
      case 'high':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <Card title="Optimization Suggestions" subtitle="AI-generated recommendations to improve agent performance">
      <div className="space-y-4">
        {suggestions.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <svg className="mx-auto h-12 w-12 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="mt-2 text-sm">Your agent is already well-optimized!</p>
            <p className="text-xs text-gray-400 mt-1">No critical optimization opportunities detected</p>
          </div>
        )}

        {suggestions.map((suggestion, index) => (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start gap-4">
              {/* Icon & Type */}
              <div className={`flex-shrink-0 p-3 rounded-lg border ${getTypeColor(suggestion.type)}`}>
                {getTypeIcon(suggestion.type)}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h4 className="text-base font-semibold text-gray-900">
                      {suggestion.title}
                    </h4>
                    <p className="mt-1 text-sm text-gray-600">
                      {suggestion.description}
                    </p>
                  </div>

                  {/* Effort Badge */}
                  <span className={`flex-shrink-0 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getEffortColor(suggestion.effort)}`}>
                    {suggestion.effort} effort
                  </span>
                </div>

                {/* Impact & Action */}
                <div className="mt-4 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                    <span className="text-gray-700">
                      <span className="font-medium">Impact:</span> {suggestion.estimatedImpact}
                    </span>
                  </div>

                  {onImplement && (
                    <Button
                      onClick={() => onImplement(suggestion)}
                      variant="primary"
                      size="sm"
                    >
                      Learn More
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {suggestions.length > 0 && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-sm text-blue-800">
              <p className="font-medium">Optimization Tip</p>
              <p className="mt-1">
                Start with low-effort, high-impact suggestions for quick wins. Monitor performance
                after each change to measure effectiveness.
              </p>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
