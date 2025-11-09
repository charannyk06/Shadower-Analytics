import { ConsumptionTrends } from '@/hooks/api/useCreditConsumption'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts'

interface ConsumptionChartProps {
  trends: ConsumptionTrends
}

export function ConsumptionChart({ trends }: ConsumptionChartProps) {
  // Format data for chart
  const chartData = trends.daily.map(d => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    credits: d.credits,
    cumulative: d.cumulative
  }))

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Credit Consumption Trend</h3>
        <p className="text-sm text-gray-500">Daily credit usage over time</p>
      </div>

      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorCredits" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              stroke="#6b7280"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              stroke="#6b7280"
              tickFormatter={(value) => {
                if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
                if (value >= 1000) return `${(value / 1000).toFixed(1)}K`
                return value.toString()
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
              formatter={(value: number) => [value.toLocaleString(), 'Credits']}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="credits"
              stroke="#3b82f6"
              fill="url(#colorCredits)"
              strokeWidth={2}
              name="Daily Credits"
            />
            <Line
              type="monotone"
              dataKey="cumulative"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              name="Cumulative"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Growth Rate Indicators */}
      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="text-center">
          <p className="text-sm text-gray-500">Daily Growth</p>
          <p className={`text-lg font-semibold ${
            trends.growthRate.daily > 0 ? 'text-red-600' : 'text-green-600'
          }`}>
            {trends.growthRate.daily > 0 ? '+' : ''}
            {trends.growthRate.daily.toFixed(1)}%
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-500">Weekly Growth</p>
          <p className={`text-lg font-semibold ${
            trends.growthRate.weekly > 0 ? 'text-red-600' : 'text-green-600'
          }`}>
            {trends.growthRate.weekly > 0 ? '+' : ''}
            {trends.growthRate.weekly.toFixed(1)}%
          </p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-500">Monthly Growth</p>
          <p className={`text-lg font-semibold ${
            trends.growthRate.monthly > 0 ? 'text-red-600' : 'text-green-600'
          }`}>
            {trends.growthRate.monthly > 0 ? '+' : ''}
            {trends.growthRate.monthly.toFixed(1)}%
          </p>
        </div>
      </div>
    </div>
  )
}
