'use client';

import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { motion, AnimatePresence } from 'framer-motion';

interface Execution {
  agent_id: string;
  run_id: string;
  user_id: string;
  started_at: string;
}

interface ConnectionIndicatorProps {
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
}

function ConnectionIndicator({ status }: ConnectionIndicatorProps) {
  const colors = {
    connected: 'bg-green-500',
    connecting: 'bg-yellow-500',
    disconnected: 'bg-red-500',
    error: 'bg-red-500',
  };

  const labels = {
    connected: 'Live',
    connecting: 'Connecting',
    disconnected: 'Offline',
    error: 'Error',
  };

  return (
    <div className="flex items-center gap-2">
      <div
        className={`w-2 h-2 rounded-full ${colors[status]} ${
          status === 'connected' ? 'animate-pulse' : ''
        }`}
      />
      <span className="text-xs text-gray-500 capitalize">{labels[status]}</span>
    </div>
  );
}

export interface LiveExecutionCounterProps {
  workspaceId: string;
}

export function LiveExecutionCounter({ workspaceId }: LiveExecutionCounterProps) {
  const [executionCount, setExecutionCount] = useState(0);
  const [recentExecutions, setRecentExecutions] = useState<Execution[]>([]);
  const [completedCount, setCompletedCount] = useState(0);

  const { connectionStatus } = useWebSocket({
    workspaceId,
    onMessage: (event) => {
      const data = JSON.parse(event.data);

      if (data.event === 'execution_started') {
        setExecutionCount((prev) => prev + 1);
        setRecentExecutions((prev) => [
          data.data,
          ...prev.slice(0, 9), // Keep last 10
        ]);
      } else if (data.event === 'execution_completed') {
        setCompletedCount((prev) => prev + 1);
      }
    },
  });

  return (
    <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Live Executions
        </h3>
        <ConnectionIndicator status={connectionStatus} />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
            <motion.span
              key={executionCount}
              initial={{ scale: 1.2, color: '#3b82f6' }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              {executionCount.toLocaleString()}
            </motion.span>
          </div>
          <div className="text-sm font-normal text-gray-500 dark:text-gray-400">
            started today
          </div>
        </div>

        <div>
          <div className="text-3xl font-bold text-green-600 dark:text-green-400">
            <motion.span
              key={completedCount}
              initial={{ scale: 1.2, color: '#10b981' }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              {completedCount.toLocaleString()}
            </motion.span>
          </div>
          <div className="text-sm font-normal text-gray-500 dark:text-gray-400">
            completed
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Recent Activity
        </h4>
        <AnimatePresence mode="popLayout">
          {recentExecutions.length === 0 ? (
            <div className="text-sm text-gray-400 dark:text-gray-500 italic">
              Waiting for executions...
            </div>
          ) : (
            recentExecutions.map((execution, index) => (
              <motion.div
                key={execution.run_id}
                initial={{ opacity: 0, x: -20, height: 0 }}
                animate={{ opacity: 1, x: 0, height: 'auto' }}
                exit={{ opacity: 0, x: 20, height: 0 }}
                transition={{ delay: index * 0.05 }}
                className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2 py-1 px-2 rounded hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <span className="flex-1">
                  Agent{' '}
                  <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">
                    {execution.agent_id.slice(0, 8)}
                  </code>{' '}
                  started
                </span>
                <span className="text-xs text-gray-400">
                  {new Date(execution.started_at).toLocaleTimeString()}
                </span>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
