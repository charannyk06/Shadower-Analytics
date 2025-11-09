/**
 * Throughput Chart Component
 * Displays execution throughput trends over time
 */

'use client'

import { useMemo } from 'react'
import { ThroughputMetrics } from '@/types/execution'
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

interface ThroughputChartProps {
  data: ThroughputMetrics
}

export function ThroughputChart({ data }: ThroughputChartProps) {
  const chartData = useMemo(
    () => ({
      labels: data.throughputTrend.map((point) => {
        const date = new Date(point.timestamp)
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
      }),
      datasets: [
        {
          label: 'Executions',
          data: data.throughputTrend.map((point) => point.value),
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4,
        },
      ],
    }),
    [data.throughputTrend]
  )

  const options: ChartOptions<'line'> = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        title: {
          display: false,
        },
        tooltip: {
          mode: 'index',
          intersect: false,
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
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false,
      },
    }),
    []
  )

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Throughput</h3>
        <div className="mt-2 grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-gray-500">Per Minute</div>
            <div className="text-xl font-semibold text-gray-900">
              {data.executionsPerMinute.toFixed(1)}
            </div>
          </div>
          <div>
            <div className="text-gray-500">Per Hour</div>
            <div className="text-xl font-semibold text-gray-900">
              {data.executionsPerHour.toFixed(0)}
            </div>
          </div>
          <div>
            <div className="text-gray-500">Peak</div>
            <div className="text-xl font-semibold text-blue-600">
              {data.peakThroughput.value}
            </div>
          </div>
        </div>
      </div>

      <div style={{ height: '250px' }}>
        <Line data={chartData} options={options} />
      </div>

      {/* Capacity utilization */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm text-gray-500">Capacity Utilization</span>
          <span className="text-sm font-semibold text-gray-900">
            {data.capacityUtilization.toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="h-2 rounded-full bg-blue-600 transition-all duration-500"
            style={{ width: `${data.capacityUtilization}%` }}
          />
        </div>
      </div>
    </div>
  )
}
