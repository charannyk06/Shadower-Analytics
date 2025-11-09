/**
 * Queue Depth Indicator Component
 * Displays queue depth and wait time metrics
 */

'use client'

interface QueueDepthIndicatorProps {
  depth: number
  waitTime: number
}

export function QueueDepthIndicator({ depth, waitTime }: QueueDepthIndicatorProps) {
  const getSeverityColor = (depth: number) => {
    if (depth === 0) return 'text-gray-600'
    if (depth < 5) return 'text-green-600'
    if (depth < 10) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="text-center">
      <div className={`text-2xl font-bold ${getSeverityColor(depth)}`}>{depth}</div>
      <div className="text-sm text-gray-500">Queue Depth</div>
      {depth > 0 && (
        <div className="text-xs text-gray-400 mt-1">
          ~{Math.round(waitTime)}s wait
        </div>
      )}
    </div>
  )
}
