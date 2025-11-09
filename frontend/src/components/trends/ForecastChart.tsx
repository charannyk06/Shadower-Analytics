/**
 * Forecast Chart Component
 *
 * Displays short-term and long-term forecasts with accuracy metrics
 */

import React from 'react';
import type { Forecast } from '@/types/trend-analysis';

interface ForecastChartProps {
  forecast: Forecast;
  className?: string;
}

export function ForecastChart({ forecast, className = '' }: ForecastChartProps) {
  const { shortTerm, longTerm, accuracy } = forecast;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  const getAccuracyColor = (r2: number) => {
    if (r2 >= 0.8) return 'text-green-600';
    if (r2 >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (!shortTerm || shortTerm.length === 0) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <h3 className="text-lg font-semibold mb-4">Forecast</h3>
        <p className="text-gray-500 text-center py-8">
          Insufficient data for forecasting
        </p>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <h3 className="text-lg font-semibold mb-4">Forecast</h3>

      {/* Accuracy Metrics */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <div className="text-sm font-medium text-gray-700 mb-3">Model Accuracy</div>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-xs text-gray-500">R² Score</div>
            <div className={`text-lg font-bold ${getAccuracyColor(accuracy.r2)}`}>
              {accuracy.r2.toFixed(3)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">MAPE</div>
            <div className="text-lg font-bold text-gray-700">
              {accuracy.mape.toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">RMSE</div>
            <div className="text-lg font-bold text-gray-700">
              {accuracy.rmse.toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      {/* Short-term Forecast (7 days) */}
      <div className="mb-6">
        <h4 className="font-medium text-gray-700 mb-3">7-Day Forecast</h4>
        <div className="space-y-2">
          {shortTerm.map((item, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div className="flex-1">
                <div className="text-sm font-medium">
                  {formatDate(item.timestamp)}
                </div>
                <div className="text-xs text-gray-600">
                  Range: {item.lower.toFixed(0)} - {item.upper.toFixed(0)}
                </div>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold text-blue-700">
                  {item.predicted.toFixed(0)}
                </div>
                <div className="text-xs text-gray-600">
                  {(item.confidence * 100).toFixed(0)}% conf.
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Long-term Forecast (3 months) */}
      {longTerm && longTerm.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-700 mb-3">Long-term Forecast (Monthly)</h4>
          <div className="space-y-2">
            {longTerm.map((item, index) => (
              <div key={index} className="p-3 bg-purple-50 rounded-lg">
                <div className="flex justify-between items-start mb-2">
                  <div className="font-medium">{item.period}</div>
                  <div className="text-lg font-bold text-purple-700">
                    {item.predicted.toFixed(0)}
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <div className="text-gray-500">Optimistic</div>
                    <div className="font-semibold text-green-600">
                      {item.range.optimistic.toFixed(0)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Realistic</div>
                    <div className="font-semibold text-blue-600">
                      {item.range.realistic.toFixed(0)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Pessimistic</div>
                    <div className="font-semibold text-red-600">
                      {item.range.pessimistic.toFixed(0)}
                    </div>
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
