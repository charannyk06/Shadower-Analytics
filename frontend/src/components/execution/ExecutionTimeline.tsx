/**
 * Execution Timeline Component
 * Displays execution timeline with anomaly detection
 */

'use client'

import { ExecutionTimelinePoint, ExecutionAnomaly } from '@/types/execution'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface ExecutionTimelineProps {
  timeline: ExecutionTimelinePoint[]
  anomalies: ExecutionAnomaly[]
}

export function ExecutionTimeline({ timeline, anomalies }: ExecutionTimelineProps) {
  const chartData = {
    labels: timeline.map((point) => {
      const date = new Date(point.timestamp)
      return date.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit' })
    }),
    datasets: [
      {
        label: 'Executions',
        data: timeline.map((point) => point.executions),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        yAxisID: 'y',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Success Rate',
        data: timeline.map((point) => point.successRate),
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        yAxisID: 'y1',
        fill: false,
        tension: 0.4,
      },
    ],
  }

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        title: {
          display: true,
          text: 'Executions',
        },
      },
      y1: {
        type: 'linear',
        display: true,
        position: 'right',
        title: {
          display: true,
          text: 'Success Rate (%)',
        },
        grid: {
          drawOnChartArea: false,
        },
      },
    },
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4 text-gray-900">Execution Timeline</h3>

      <div style={{ height: '300px' }}>
        <Line data={chartData} options={options} />
      </div>

      {/* Anomalies */}
      {anomalies.length > 0 && (
        <div className="mt-6 pt-4 border-t border-gray-200">
          <h4 className="text-sm font-semibold text-gray-900 mb-3">Detected Anomalies</h4>
          <div className="space-y-2">
            {anomalies.slice(0, 5).map((anomaly, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border text-sm ${getSeverityColor(anomaly.severity)}`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-medium">{anomaly.type}</span>
                    <p className="text-xs mt-1 opacity-90">{anomaly.description}</p>
                  </div>
                  <span className="text-xs opacity-75">
                    {new Date(anomaly.timestamp).toLocaleString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
