/**
 * LiveActivityFeed Component
 * Real-time feed of recent activities and events
 */

import React, { useState, useEffect } from 'react'
import { format } from 'date-fns'

interface Activity {
  id: string
  type: 'execution' | 'user' | 'agent' | 'alert'
  message: string
  timestamp: string
  status?: 'success' | 'failure' | 'info'
}

interface LiveActivityFeedProps {
  workspaceId?: string
}

export function LiveActivityFeed({ workspaceId }: LiveActivityFeedProps) {
  const [activities, setActivities] = useState<Activity[]>([])

  // Mock data - in production, this would use WebSocket
  useEffect(() => {
    const mockActivities: Activity[] = [
      {
        id: '1',
        type: 'execution',
        message: 'Agent "Data Analyzer Pro" completed successfully',
        timestamp: new Date(Date.now() - 2 * 60000).toISOString(),
        status: 'success',
      },
      {
        id: '2',
        type: 'user',
        message: 'New user Alice Johnson joined workspace',
        timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
        status: 'info',
      },
      {
        id: '3',
        type: 'execution',
        message: 'Agent "Report Generator" failed with error',
        timestamp: new Date(Date.now() - 8 * 60000).toISOString(),
        status: 'failure',
      },
      {
        id: '4',
        type: 'agent',
        message: 'Agent "Email Campaign Manager" was updated',
        timestamp: new Date(Date.now() - 12 * 60000).toISOString(),
        status: 'info',
      },
      {
        id: '5',
        type: 'alert',
        message: 'Credit usage approaching 80% of monthly limit',
        timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
        status: 'info',
      },
    ]

    setActivities(mockActivities)

    // Simulate real-time updates
    const interval = setInterval(() => {
      const newActivity: Activity = {
        id: `${Date.now()}`,
        type: ['execution', 'user', 'agent'][Math.floor(Math.random() * 3)] as any,
        message: 'New activity detected',
        timestamp: new Date().toISOString(),
        status: ['success', 'info'][Math.floor(Math.random() * 2)] as any,
      }

      setActivities((prev) => [newActivity, ...prev].slice(0, 10))
    }, 30000) // Update every 30 seconds

    return () => clearInterval(interval)
  }, [workspaceId])

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'execution':
        return (
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
              clipRule="evenodd"
            />
          </svg>
        )
      case 'user':
        return (
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" />
          </svg>
        )
      case 'agent':
        return (
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
          </svg>
        )
      default:
        return (
          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
        )
    }
  }

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'success':
        return 'text-green-600'
      case 'failure':
        return 'text-red-600'
      default:
        return 'text-blue-600'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Live Activity</h3>
          <div className="flex items-center text-green-600">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
            <span className="ml-2 text-xs font-medium">Live</span>
          </div>
        </div>
      </div>

      <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
        {activities.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500">
            No recent activity
          </div>
        ) : (
          activities.map((activity) => (
            <div key={activity.id} className="px-6 py-4 hover:bg-gray-50">
              <div className="flex items-start">
                <div className={`flex-shrink-0 ${getStatusColor(activity.status)}`}>
                  {getActivityIcon(activity.type)}
                </div>
                <div className="ml-3 flex-1">
                  <p className="text-sm text-gray-900">{activity.message}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    {format(new Date(activity.timestamp), 'MMM d, HH:mm:ss')}
                  </p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
