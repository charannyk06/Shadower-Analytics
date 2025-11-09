/**
 * MetricCard Component
 * Displays a single metric with value, change indicator, and optional icon
 */

import React from 'react'
import { clsx } from 'clsx'
import { MetricFormat } from '@/types/executive'

interface MetricCardProps {
  title: string
  value: number | string
  change?: number
  format?: MetricFormat
  icon?: React.ComponentType<{ className?: string }>
  description?: string
  trend?: 'up' | 'down' | 'neutral'
  loading?: boolean
  className?: string
}

export function MetricCard({
  title,
  value,
  change,
  format = 'number',
  icon: Icon,
  description,
  trend,
  loading = false,
  className,
}: MetricCardProps) {
  const formatValue = (val: number | string): string => {
    if (typeof val === 'string') return val

    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(val)

      case 'percentage':
        return `${val.toFixed(1)}%`

      case 'duration':
        return `${val.toFixed(2)}s`

      default:
        return val.toLocaleString()
    }
  }

  const getTrendColor = (): string => {
    if (!change || trend === 'neutral') return 'text-gray-500'

    // For most metrics, positive change is good
    // For error rate, churn rate, negative change is good
    const isNegativeGood =
      title.toLowerCase().includes('error') ||
      title.toLowerCase().includes('churn') ||
      title.toLowerCase().includes('cost')

    if (change > 0) {
      return isNegativeGood ? 'text-red-600' : 'text-green-600'
    } else {
      return isNegativeGood ? 'text-green-600' : 'text-red-600'
    }
  }

  const getTrendIcon = () => {
    if (!change) return null

    return change > 0 ? (
      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z"
          clipRule="evenodd"
        />
      </svg>
    ) : (
      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z"
          clipRule="evenodd"
        />
      </svg>
    )
  }

  if (loading) {
    return (
      <div className={clsx('bg-white rounded-lg shadow p-6', className)}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="h-8 bg-gray-200 rounded w-1/2 mb-2"></div>
          {description && <div className="h-3 bg-gray-200 rounded w-2/3"></div>}
        </div>
      </div>
    )
  }

  return (
    <div
      className={clsx(
        'bg-white rounded-lg shadow hover:shadow-lg transition-all duration-200 p-6',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        {Icon && <Icon className="h-5 w-5 text-gray-400" />}
      </div>

      {/* Value and Change */}
      <div className="flex items-baseline justify-between">
        <p className="text-2xl font-semibold text-gray-900">
          {formatValue(value)}
        </p>

        {change !== undefined && (
          <div className={clsx('flex items-center text-sm font-medium', getTrendColor())}>
            {getTrendIcon()}
            <span className="ml-1">{Math.abs(change).toFixed(1)}%</span>
          </div>
        )}
      </div>

      {/* Description */}
      {description && (
        <p className="mt-2 text-xs text-gray-500 line-clamp-2" title={description}>
          {description}
        </p>
      )}
    </div>
  )
}
