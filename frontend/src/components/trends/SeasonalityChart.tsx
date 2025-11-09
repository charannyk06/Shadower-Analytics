/**
 * Seasonality Chart Component
 *
 * Displays seasonal patterns and cycles detected in the data
 */

import React from 'react';
import type { Patterns } from '@/types/trend-analysis';

interface SeasonalityChartProps {
  patterns: Patterns;
  className?: string;
}

export function SeasonalityChart({ patterns, className = '' }: SeasonalityChartProps) {
  const { seasonality, growth, cycles } = patterns;

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <h3 className="text-lg font-semibold mb-4">Patterns & Seasonality</h3>

      {/* Seasonality Section */}
      <div className="mb-6">
        <h4 className="font-medium text-gray-700 mb-3">Seasonality</h4>
        {seasonality.detected ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
              <div>
                <div className="font-semibold text-green-800">
                  {seasonality.type?.toUpperCase()} Pattern Detected
                </div>
                <div className="text-sm text-green-600">
                  Strength: {seasonality.strength.toFixed(1)}%
                </div>
              </div>
              <div className="text-2xl">📅</div>
            </div>

            {seasonality.peakPeriods.length > 0 && (
              <div className="p-3 bg-blue-50 rounded-lg">
                <div className="text-sm font-medium text-gray-700 mb-1">Peak Periods:</div>
                <div className="text-sm text-blue-800">
                  {seasonality.peakPeriods.join(', ')}
                </div>
              </div>
            )}

            {seasonality.lowPeriods.length > 0 && (
              <div className="p-3 bg-gray-100 rounded-lg">
                <div className="text-sm font-medium text-gray-700 mb-1">Low Periods:</div>
                <div className="text-sm text-gray-600">
                  {seasonality.lowPeriods.join(', ')}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 bg-gray-50 rounded-lg text-center text-gray-500">
            No significant seasonality detected
          </div>
        )}
      </div>

      {/* Growth Pattern Section */}
      <div className="mb-6">
        <h4 className="font-medium text-gray-700 mb-3">Growth Pattern</h4>
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-500">Type</div>
            <div className="font-semibold capitalize">{growth.type}</div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-500">Rate</div>
            <div className="font-semibold">{growth.rate.toFixed(2)}%</div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-500">Acceleration</div>
            <div className="font-semibold">{growth.acceleration.toFixed(4)}</div>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-500">30d Projection</div>
            <div className="font-semibold">{growth.projectedGrowth.toFixed(2)}%</div>
          </div>
        </div>
      </div>

      {/* Cycles Section */}
      {cycles.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-700 mb-3">Cyclical Patterns</h4>
          <div className="space-y-2">
            {cycles.map((cycle, index) => (
              <div key={index} className="p-3 bg-purple-50 rounded-lg border border-purple-200">
                <div className="flex justify-between items-center">
                  <div>
                    <div className="text-sm font-medium">
                      {cycle.period.toFixed(1)}-day cycle
                    </div>
                    <div className="text-xs text-gray-600">
                      Amplitude: {cycle.amplitude.toFixed(2)}
                    </div>
                  </div>
                  <div className="text-sm font-semibold text-purple-700">
                    {(cycle.significance * 100).toFixed(0)}% sig.
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
