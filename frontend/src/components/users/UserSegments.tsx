/**
 * UserSegments Component
 * Displays user segments with key metrics
 */

import React from 'react'
import type { UserSegmentData } from '@/types/user-activity'

interface UserSegmentsProps {
  segments: UserSegmentData[]
  selectedSegment: string | null
  onSegmentSelect: (segmentName: string) => void
}

export function UserSegments({
  segments,
  selectedSegment,
  onSegmentSelect,
}: UserSegmentsProps) {
  const getSegmentTypeColor = (type: string): string => {
    switch (type) {
      case 'behavioral':
        return 'bg-blue-100 text-blue-800'
      case 'demographic':
        return 'bg-purple-100 text-purple-800'
      case 'technographic':
        return 'bg-green-100 text-green-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 mt-6">
      <h3 className="text-lg font-semibold mb-4">User Segments</h3>

      {segments.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No user segments defined
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {segments.map((segment) => (
            <div
              key={segment.segmentName}
              onClick={() => onSegmentSelect(segment.segmentName)}
              className={`border rounded-lg p-4 cursor-pointer transition-all ${
                selectedSegment === segment.segmentName
                  ? 'border-purple-500 bg-purple-50 shadow-md'
                  : 'border-gray-200 hover:border-gray-300 hover:shadow'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold text-gray-900">{segment.segmentName}</h4>
                <span
                  className={`text-xs px-2 py-1 rounded-full ${getSegmentTypeColor(
                    segment.segmentType
                  )}`}
                >
                  {segment.segmentType}
                </span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Users:</span>
                  <span className="font-medium text-gray-900">
                    {segment.userCount.toLocaleString()}
                  </span>
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Engagement:</span>
                  <span className="font-medium text-gray-900">
                    {segment.avgEngagement.toFixed(1)}
                  </span>
                </div>

                {segment.avgRevenue > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Avg Revenue:</span>
                    <span className="font-medium text-gray-900">
                      ${segment.avgRevenue.toFixed(2)}
                    </span>
                  </div>
                )}

                {segment.characteristics.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <p className="text-xs text-gray-500 mb-1">Characteristics:</p>
                    <div className="flex flex-wrap gap-1">
                      {segment.characteristics.slice(0, 3).map((char, idx) => (
                        <span
                          key={idx}
                          className="text-xs px-2 py-0.5 bg-gray-100 text-gray-700 rounded"
                        >
                          {char}
                        </span>
                      ))}
                      {segment.characteristics.length > 3 && (
                        <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-700 rounded">
                          +{segment.characteristics.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
