/**
 * DashboardHeader Component
 * Top bar with timeframe selector, refresh button, and export options
 */

import React, { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Timeframe } from '@/types/executive'

interface DashboardHeaderProps {
  timeframe: Timeframe
  onTimeframeChange: (timeframe: Timeframe) => void
  onRefresh: () => void
  onExport?: (format: 'pdf' | 'csv') => void
  loading?: boolean
}

export function DashboardHeader({
  timeframe,
  onTimeframeChange,
  onRefresh,
  onExport,
  loading = false,
}: DashboardHeaderProps) {
  const [exportMenuOpen, setExportMenuOpen] = useState(false)

  const timeframes: { value: Timeframe; label: string }[] = [
    { value: '24h', label: 'Last 24 Hours' },
    { value: '7d', label: 'Last 7 Days' },
    { value: '30d', label: 'Last 30 Days' },
    { value: '90d', label: 'Last 90 Days' },
    { value: 'all', label: 'All Time' },
  ]

  return (
    <div className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          {/* Title */}
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Executive Dashboard
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              Comprehensive business metrics and KPIs
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center space-x-4">
            {/* Timeframe Selector */}
            <div className="flex items-center space-x-2">
              <label
                htmlFor="timeframe"
                className="text-sm font-medium text-gray-700"
              >
                Period:
              </label>
              <select
                id="timeframe"
                value={timeframe}
                onChange={(e) => onTimeframeChange(e.target.value as Timeframe)}
                className="block w-40 rounded-md border-gray-300 py-2 pl-3 pr-10 text-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                disabled={loading}
              >
                {timeframes.map((tf) => (
                  <option key={tf.value} value={tf.value}>
                    {tf.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Refresh Button */}
            <Button
              variant="outline"
              size="md"
              onClick={onRefresh}
              disabled={loading}
              className="flex items-center"
            >
              <svg
                className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Refresh
            </Button>

            {/* Export Menu */}
            {onExport && (
              <div className="relative">
                <Button
                  variant="primary"
                  size="md"
                  onClick={() => setExportMenuOpen(!exportMenuOpen)}
                  className="flex items-center"
                >
                  <svg
                    className="h-4 w-4 mr-2"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  Export
                </Button>

                {exportMenuOpen && (
                  <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-10">
                    <div
                      className="py-1"
                      role="menu"
                      aria-orientation="vertical"
                    >
                      <button
                        onClick={() => {
                          onExport('pdf')
                          setExportMenuOpen(false)
                        }}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        role="menuitem"
                      >
                        Export as PDF
                      </button>
                      <button
                        onClick={() => {
                          onExport('csv')
                          setExportMenuOpen(false)
                        }}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        role="menuitem"
                      >
                        Export as CSV
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
