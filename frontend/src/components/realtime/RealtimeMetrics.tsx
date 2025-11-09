'use client';

import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { motion } from 'framer-motion';

interface Metrics {
  total_executions: number;
  active_agents: number;
  credits_consumed: number;
  avg_runtime: number;
}

export interface RealtimeMetricsProps {
  workspaceId: string;
}

export function RealtimeMetrics({ workspaceId }: RealtimeMetricsProps) {
  const [metrics, setMetrics] = useState<Metrics>({
    total_executions: 0,
    active_agents: 0,
    credits_consumed: 0,
    avg_runtime: 0,
  });

  const { connectionStatus, sendMessage } = useWebSocket({
    workspaceId,
    onMessage: (event) => {
      const data = JSON.parse(event.data);

      if (data.event === 'metrics_update') {
        setMetrics((prev) => ({
          ...prev,
          ...data.data,
        }));
      }
    },
  });

  // Request metrics update on mount
  useEffect(() => {
    if (connectionStatus === 'connected') {
      sendMessage({
        type: 'request_metrics',
      });
    }
  }, [connectionStatus, sendMessage]);

  const metricCards = [
    {
      label: 'Total Executions',
      value: metrics.total_executions.toLocaleString(),
      icon: '🚀',
      color: 'blue',
    },
    {
      label: 'Active Agents',
      value: metrics.active_agents.toLocaleString(),
      icon: '🤖',
      color: 'green',
    },
    {
      label: 'Credits Used',
      value: metrics.credits_consumed.toFixed(2),
      icon: '💳',
      color: 'purple',
    },
    {
      label: 'Avg Runtime',
      value: `${metrics.avg_runtime.toFixed(1)}s`,
      icon: '⏱️',
      color: 'orange',
    },
  ];

  const colorClasses = {
    blue: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20',
    green: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20',
    purple:
      'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20',
    orange:
      'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20',
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {metricCards.map((card, index) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
              {card.label}
            </span>
            <span className="text-2xl">{card.icon}</span>
          </div>
          <div
            className={`text-2xl font-bold ${
              colorClasses[card.color as keyof typeof colorClasses]
            } p-2 rounded`}
          >
            <motion.span
              key={card.value}
              initial={{ scale: 1.2 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              {card.value}
            </motion.span>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
