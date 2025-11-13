/**
 * Predictive Analytics Page
 *
 * Comprehensive ML-powered predictions dashboard including:
 * - Credit consumption forecasting
 * - User churn prediction
 * - Growth projections
 * - Peak usage analysis
 * - Error rate predictions
 *
 * Author: Claude Code
 * Date: 2025-11-12
 */

'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import {
  useCreditConsumptionPrediction,
  useChurnPrediction,
  useGrowthPrediction,
  usePeakUsagePrediction,
  useErrorRatePrediction,
} from '@/hooks/usePredictions';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  TrendingUp,
  Users,
  AlertTriangle,
  Activity,
  Zap,
  Brain,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from 'lucide-react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export default function PredictionsPage() {
  const params = useParams();
  const workspaceId = params.id as string;
  const [activeTab, setActiveTab] = useState('consumption');

  // Fetch all predictions
  const creditPrediction = useCreditConsumptionPrediction(workspaceId, 30);
  const churnPrediction = useChurnPrediction(workspaceId);
  const growthPrediction = useGrowthPrediction(workspaceId, 'dau', 90);
  const peakUsagePrediction = usePeakUsagePrediction(workspaceId);
  const errorRatePrediction = useErrorRatePrediction(workspaceId);

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Brain className="h-8 w-8 text-purple-600" />
            Predictive Analytics
          </h1>
          <p className="text-gray-600 mt-2">
            ML-powered forecasts and predictions for proactive decision making
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Credit Consumption Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Credit Forecast
            </CardTitle>
          </CardHeader>
          <CardContent>
            {creditPrediction.isLoading ? (
              <div className="h-16 flex items-center">Loading...</div>
            ) : creditPrediction.data?.insights ? (
              <div>
                <div className="text-2xl font-bold">
                  {creditPrediction.data.insights.summary.total_predicted_consumption?.toLocaleString()}
                </div>
                <div className="flex items-center gap-1 text-sm mt-1">
                  {creditPrediction.data.insights.summary.trend_direction === 'increasing' ? (
                    <>
                      <ArrowUpRight className="h-4 w-4 text-red-500" />
                      <span className="text-red-500">
                        {creditPrediction.data.insights.summary.trend_percentage?.toFixed(1)}%
                      </span>
                    </>
                  ) : creditPrediction.data.insights.summary.trend_direction === 'decreasing' ? (
                    <>
                      <ArrowDownRight className="h-4 w-4 text-green-500" />
                      <span className="text-green-500">
                        {Math.abs(creditPrediction.data.insights.summary.trend_percentage)?.toFixed(1)}%
                      </span>
                    </>
                  ) : (
                    <>
                      <Minus className="h-4 w-4 text-gray-500" />
                      <span className="text-gray-500">Stable</span>
                    </>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-sm text-gray-500">No data</div>
            )}
          </CardContent>
        </Card>

        {/* Churn Risk Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              High Risk Users
            </CardTitle>
          </CardHeader>
          <CardContent>
            {churnPrediction.isLoading ? (
              <div className="h-16 flex items-center">Loading...</div>
            ) : churnPrediction.data ? (
              <div>
                <div className="text-2xl font-bold text-red-600">
                  {churnPrediction.data.high_risk_users || 0}
                </div>
                <div className="text-sm text-gray-600 mt-1">
                  of {churnPrediction.data.total_users} users
                </div>
              </div>
            ) : (
              <div className="text-sm text-gray-500">No data</div>
            )}
          </CardContent>
        </Card>

        {/* Growth Prediction Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Growth Forecast
            </CardTitle>
          </CardHeader>
          <CardContent>
            {growthPrediction.isLoading ? (
              <div className="h-16 flex items-center">Loading...</div>
            ) : growthPrediction.data?.insights ? (
              <div>
                <div className="text-2xl font-bold">
                  {growthPrediction.data.insights.growth_rate?.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-600 mt-1">
                  {growthPrediction.data.insights.trend}
                </div>
              </div>
            ) : (
              <div className="text-sm text-gray-500">No data</div>
            )}
          </CardContent>
        </Card>

        {/* Error Rate Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Error Rate Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            {errorRatePrediction.isLoading ? (
              <div className="h-16 flex items-center">Loading...</div>
            ) : errorRatePrediction.data?.alerts ? (
              <div>
                <div className="text-2xl font-bold">
                  {errorRatePrediction.data.alerts.length}
                </div>
                <div className="text-sm text-gray-600 mt-1">
                  active alerts
                </div>
              </div>
            ) : (
              <div className="text-sm text-gray-500">No alerts</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="consumption">
            <TrendingUp className="h-4 w-4 mr-2" />
            Consumption
          </TabsTrigger>
          <TabsTrigger value="churn">
            <Users className="h-4 w-4 mr-2" />
            Churn Risk
          </TabsTrigger>
          <TabsTrigger value="growth">
            <Activity className="h-4 w-4 mr-2" />
            Growth
          </TabsTrigger>
          <TabsTrigger value="peak">
            <Zap className="h-4 w-4 mr-2" />
            Peak Usage
          </TabsTrigger>
          <TabsTrigger value="errors">
            <AlertTriangle className="h-4 w-4 mr-2" />
            Errors
          </TabsTrigger>
        </TabsList>

        {/* Credit Consumption Tab */}
        <TabsContent value="consumption" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Credit Consumption Forecast</CardTitle>
              <CardDescription>
                30-day prediction using Prophet & ARIMA ensemble
              </CardDescription>
            </CardHeader>
            <CardContent>
              {creditPrediction.isLoading ? (
                <div className="h-64 flex items-center justify-center">
                  Loading predictions...
                </div>
              ) : creditPrediction.data?.predictions ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={creditPrediction.data.predictions}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="confidence_upper"
                        stackId="1"
                        stroke="#9333ea"
                        fill="#9333ea"
                        fillOpacity={0.1}
                        name="Upper Bound"
                      />
                      <Area
                        type="monotone"
                        dataKey="predicted_value"
                        stackId="2"
                        stroke="#9333ea"
                        fill="#9333ea"
                        fillOpacity={0.3}
                        name="Prediction"
                      />
                      <Area
                        type="monotone"
                        dataKey="confidence_lower"
                        stackId="3"
                        stroke="#9333ea"
                        fill="#9333ea"
                        fillOpacity={0.1}
                        name="Lower Bound"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-gray-500">
                  No prediction data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Insights */}
          {creditPrediction.data?.insights?.recommendations && (
            <Card>
              <CardHeader>
                <CardTitle>Recommendations</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {creditPrediction.data.insights.recommendations.map((rec, idx) => (
                    <Alert key={idx}>
                      <AlertDescription>{rec}</AlertDescription>
                    </Alert>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Churn Prediction Tab */}
        <TabsContent value="churn" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>User Churn Risk Analysis</CardTitle>
              <CardDescription>
                Behavioral analysis using Gradient Boosting
              </CardDescription>
            </CardHeader>
            <CardContent>
              {churnPrediction.isLoading ? (
                <div className="h-64 flex items-center justify-center">
                  Loading predictions...
                </div>
              ) : churnPrediction.data?.predictions ? (
                <div className="space-y-4">
                  {/* High Risk Users Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left p-2">User ID</th>
                          <th className="text-left p-2">Risk Score</th>
                          <th className="text-left p-2">Risk Level</th>
                          <th className="text-left p-2">Days Until Churn</th>
                          <th className="text-left p-2">Top Risk Factor</th>
                        </tr>
                      </thead>
                      <tbody>
                        {churnPrediction.data.predictions
                          .filter((p: any) => p.risk_level === 'high' || p.risk_level === 'critical')
                          .slice(0, 10)
                          .map((prediction: any) => (
                            <tr key={prediction.user_id} className="border-b hover:bg-gray-50">
                              <td className="p-2 font-mono text-xs">
                                {prediction.user_id.substring(0, 8)}...
                              </td>
                              <td className="p-2">
                                <div className="flex items-center gap-2">
                                  <div className="w-24 bg-gray-200 rounded-full h-2">
                                    <div
                                      className={`h-2 rounded-full ${
                                        prediction.risk_score > 80
                                          ? 'bg-red-600'
                                          : 'bg-orange-500'
                                      }`}
                                      style={{ width: `${prediction.risk_score}%` }}
                                    />
                                  </div>
                                  <span>{prediction.risk_score.toFixed(0)}</span>
                                </div>
                              </td>
                              <td className="p-2">
                                <span
                                  className={`px-2 py-1 rounded text-xs font-medium ${
                                    prediction.risk_level === 'critical'
                                      ? 'bg-red-100 text-red-800'
                                      : 'bg-orange-100 text-orange-800'
                                  }`}
                                >
                                  {prediction.risk_level}
                                </span>
                              </td>
                              <td className="p-2">
                                {prediction.days_until_churn || 'N/A'}
                              </td>
                              <td className="p-2 text-xs">
                                {prediction.risk_factors[0]?.description || 'N/A'}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-gray-500">
                  No prediction data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Growth Prediction Tab */}
        <TabsContent value="growth" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Growth Trajectory Forecast</CardTitle>
              <CardDescription>
                90-day DAU prediction with multiple scenarios
              </CardDescription>
            </CardHeader>
            <CardContent>
              {growthPrediction.isLoading ? (
                <div className="h-64 flex items-center justify-center">
                  Loading predictions...
                </div>
              ) : growthPrediction.data?.base_predictions ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      {growthPrediction.data.scenarios?.optimistic && (
                        <Line
                          data={growthPrediction.data.scenarios.optimistic}
                          type="monotone"
                          dataKey="predicted_value"
                          stroke="#10b981"
                          strokeDasharray="5 5"
                          name="Optimistic"
                          dot={false}
                        />
                      )}
                      <Line
                        data={growthPrediction.data.base_predictions}
                        type="monotone"
                        dataKey="predicted_value"
                        stroke="#6366f1"
                        strokeWidth={2}
                        name="Base"
                        dot={false}
                      />
                      {growthPrediction.data.scenarios?.pessimistic && (
                        <Line
                          data={growthPrediction.data.scenarios.pessimistic}
                          type="monotone"
                          dataKey="predicted_value"
                          stroke="#ef4444"
                          strokeDasharray="5 5"
                          name="Pessimistic"
                          dot={false}
                        />
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-gray-500">
                  No prediction data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Peak Usage Tab */}
        <TabsContent value="peak" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Peak Usage Prediction</CardTitle>
              <CardDescription>
                Capacity planning with hourly predictions
              </CardDescription>
            </CardHeader>
            <CardContent>
              {peakUsagePrediction.isLoading ? (
                <div className="h-64 flex items-center justify-center">
                  Loading predictions...
                </div>
              ) : peakUsagePrediction.data?.peak_times ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <div className="text-sm text-gray-600">Peak Usage</div>
                      <div className="text-2xl font-bold">
                        {peakUsagePrediction.data.peak_times.peak_executions?.toFixed(0)}
                      </div>
                      <div className="text-xs text-gray-500">executions/hour</div>
                    </div>
                    <div className="p-4 bg-purple-50 rounded-lg">
                      <div className="text-sm text-gray-600">Peak Hours</div>
                      <div className="text-lg font-bold">
                        {peakUsagePrediction.data.peak_times.peak_hours?.join(', ')}
                      </div>
                    </div>
                    <div className="p-4 bg-green-50 rounded-lg">
                      <div className="text-sm text-gray-600">Peak Days</div>
                      <div className="text-sm font-medium">
                        {peakUsagePrediction.data.peak_times.peak_days?.join(', ')}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-gray-500">
                  No prediction data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Error Rate Tab */}
        <TabsContent value="errors" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Error Rate Forecast</CardTitle>
              <CardDescription>
                14-day error rate prediction with anomaly detection
              </CardDescription>
            </CardHeader>
            <CardContent>
              {errorRatePrediction.isLoading ? (
                <div className="h-64 flex items-center justify-center">
                  Loading predictions...
                </div>
              ) : errorRatePrediction.data?.predictions ? (
                <div className="space-y-4">
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={errorRatePrediction.data.predictions}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar
                          dataKey="predicted_error_rate"
                          fill="#ef4444"
                          name="Predicted Error Rate"
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Alerts */}
                  {errorRatePrediction.data.alerts && errorRatePrediction.data.alerts.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-semibold">Active Alerts</h4>
                      {errorRatePrediction.data.alerts.map((alert: any, idx: number) => (
                        <Alert key={idx} variant={alert.severity === 'critical' ? 'destructive' : 'default'}>
                          <AlertTriangle className="h-4 w-4" />
                          <AlertTitle>{alert.type}</AlertTitle>
                          <AlertDescription>{alert.message}</AlertDescription>
                        </Alert>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-gray-500">
                  No prediction data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
