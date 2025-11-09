/**
 * EngagementScore Component
 * Displays overall user engagement score with visual indicator
 */

import React from 'react'

interface EngagementScoreProps {
  score: number
  trend?: 'increasing' | 'stable' | 'decreasing'
}

export function EngagementScore({ score, trend = 'stable' }: EngagementScoreProps) {
  const getScoreColor = (score: number): string => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    if (score >= 40) return 'text-orange-600'
    return 'text-red-600'
  }

  const getScoreBgColor = (score: number): string => {
    if (score >= 80) return 'bg-green-100'
    if (score >= 60) return 'bg-yellow-100'
    if (score >= 40) return 'bg-orange-100'
    return 'bg-red-100'
  }

  const getTrendIcon = () => {
    switch (trend) {
      case 'increasing':
        return (
          <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
          </svg>
        )
      case 'decreasing':
        return (
          <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        )
      default:
        return (
          <svg className="w-5 h-5 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M5 10a1 1 0 011-1h8a1 1 0 110 2H6a1 1 0 01-1-1z" clipRule="evenodd" />
          </svg>
        )
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-700">Engagement Score</h3>
        {getTrendIcon()}
      </div>

      <div className="flex items-center space-x-4">
        <div className={`${getScoreBgColor(score)} rounded-full w-20 h-20 flex items-center justify-center`}>
          <span className={`text-3xl font-bold ${getScoreColor(score)}`}>
            {Math.round(score)}
          </span>
        </div>

        <div className="flex-1">
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full ${
                score >= 80
                  ? 'bg-green-600'
                  : score >= 60
                  ? 'bg-yellow-600'
                  : score >= 40
                  ? 'bg-orange-600'
                  : 'bg-red-600'
              }`}
              style={{ width: `${score}%` }}
            ></div>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {score >= 80
              ? 'Excellent engagement'
              : score >= 60
              ? 'Good engagement'
              : score >= 40
              ? 'Moderate engagement'
              : 'Low engagement'}
          </p>
        </div>
      </div>
    </div>
  )
}
