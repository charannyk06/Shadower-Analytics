/**
 * Latency Distribution Component
 * Displays latency percentiles and distribution
 */

'use client'

import { LatencyMetrics } from '@/types/execution'
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

interface LatencyDistributionProps {
  data: LatencyMetrics
}

export function LatencyDistribution({ data }: LatencyDistributionProps) {
  const chartData = {
    labels: data.latencyDistribution.map((bucket) => bucket.bucket),
    datasets: [
      {
        label: 'Executions',
        data: data.latencyDistribution.map((bucket) => bucket.count),
        backgroundColor: 'rgba(59, 130, 246, 0.7)',
        borderColor: 'rgb(59, 130, 246)',
        borderWidth: 1,
      },
    ],
  }

  const options: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          afterLabel: (context) => {
            const bucket = data.latencyDistribution[context.dataIndex]
            return `${bucket.percentage.toFixed(1)}% of total`
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          precision: 0,
        },
      },
    },
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Latency Distribution</h3>

        {/* Percentiles */}
        <div className="mt-3 grid grid-cols-4 gap-3 text-xs">
          <div>
            <div className="text-gray-500">p50</div>
            <div className="text-sm font-semibold text-gray-900">
              {data.executionLatency.p50.toFixed(2)}s
            </div>
          </div>
          <div>
            <div className="text-gray-500">p75</div>
            <div className="text-sm font-semibold text-gray-900">
              {data.executionLatency.p75.toFixed(2)}s
            </div>
          </div>
          <div>
            <div className="text-gray-500">p90</div>
            <div className="text-sm font-semibold text-gray-900">
              {data.executionLatency.p90.toFixed(2)}s
            </div>
          </div>
          <div>
            <div className="text-gray-500">p95</div>
            <div className="text-sm font-semibold text-blue-600">
              {data.executionLatency.p95.toFixed(2)}s
            </div>
          </div>
        </div>
      </div>

      <div style={{ height: '250px' }}>
        <Bar data={chartData} options={options} />
      </div>
    </div>
  )
}
