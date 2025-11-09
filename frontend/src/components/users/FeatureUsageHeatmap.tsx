/**
 * FeatureUsageHeatmap Component
 * Displays feature usage intensity as a heatmap
 */

import React, { useMemo } from 'react'
import type { FeatureData } from '@/types/user-activity'

interface FeatureUsageHeatmapProps {
  features: FeatureData[]
}

export function FeatureUsageHeatmap({ features }: FeatureUsageHeatmapProps) {
  const heatmapData = useMemo(() => {
    // Group features by category
    const grouped = features.reduce((acc, feature) => {
      if (!acc[feature.category]) {
        acc[feature.category] = []
      }
      acc[feature.category].push(feature)
      return acc
    }, {} as Record<string, FeatureData[]>)

    return grouped
  }, [features])

  const getIntensityColor = (adoptionRate: number): string => {
    if (adoptionRate > 75) return 'bg-green-600'
    if (adoptionRate > 50) return 'bg-green-500'
    if (adoptionRate > 25) return 'bg-yellow-500'
    if (adoptionRate > 10) return 'bg-orange-500'
    return 'bg-red-500'
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Feature Usage Heatmap</h3>

      {Object.keys(heatmapData).length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No feature usage data available
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(heatmapData).map(([category, categoryFeatures]) => (
            <div key={category}>
              <h4 className="text-sm font-medium text-gray-700 mb-2">{category}</h4>
              <div className="grid grid-cols-4 gap-2">
                {categoryFeatures.map((feature) => (
                  <div
                    key={feature.featureName}
                    className={`${getIntensityColor(
                      feature.adoptionRate
                    )} text-white text-xs p-2 rounded cursor-pointer hover:opacity-90 transition-opacity`}
                    title={`${feature.featureName}\nUsage: ${feature.usageCount.toLocaleString()}\nUsers: ${feature.uniqueUsers}\nAdoption: ${feature.adoptionRate}%`}
                  >
                    <div className="truncate">{feature.featureName}</div>
                    <div className="mt-1 font-semibold">{feature.adoptionRate}%</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="mt-6 flex items-center justify-between text-xs">
        <span className="text-gray-500">Low Usage</span>
        <div className="flex gap-1">
          <div className="w-4 h-4 bg-red-500 rounded"></div>
          <div className="w-4 h-4 bg-orange-500 rounded"></div>
          <div className="w-4 h-4 bg-yellow-500 rounded"></div>
          <div className="w-4 h-4 bg-green-500 rounded"></div>
          <div className="w-4 h-4 bg-green-600 rounded"></div>
        </div>
        <span className="text-gray-500">High Usage</span>
      </div>
    </div>
  )
}
