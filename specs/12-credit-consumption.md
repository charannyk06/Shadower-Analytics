# Specification: Credit Consumption Tracking

## Feature Overview
Comprehensive tracking and analysis of credit usage across models, agents, and users with forecasting, budgeting, and optimization recommendations.

## Technical Requirements
- Real-time credit tracking
- Model-based consumption breakdown  
- Usage forecasting and projections
- Budget alerts and limits
- Cost optimization suggestions
- Historical consumption analysis

## Implementation Details

### Data Structure
```typescript
interface CreditConsumption {
  workspaceId: string;
  timeframe: TimeFrame;
  
  // Current Status
  currentStatus: {
    // Balance
    allocatedCredits: number;
    consumedCredits: number;
    remainingCredits: number;
    utilizationRate: number; // percentage
    
    // Period Metrics
    periodStart: string;
    periodEnd: string;
    daysRemaining: number;
    
    // Burn Rate
    dailyBurnRate: number;
    weeklyBurnRate: number;
    monthlyBurnRate: number;
    
    // Projections
    projectedExhaustion: string | null;
    projectedMonthlyUsage: number;
    recommendedTopUp: number | null;
  };
  
  // Consumption Breakdown
  breakdown: {
    // By Model
    byModel: Array<{
      model: string;
      provider: 'openai' | 'anthropic' | 'google' | 'other';
      credits: number;
      percentage: number;
      tokens: number;
      calls: number;
      avgCreditsPerCall: number;
      trend: 'increasing' | 'stable' | 'decreasing';
    }>;
    
    // By Agent
    byAgent: Array<{
      agentId: string;
      agentName: string;
      credits: number;
      percentage: number;
      runs: number;
      avgCreditsPerRun: number;
      efficiency: number; // credits per successful run
    }>;
    
    // By User
    byUser: Array<{
      userId: string;
      userName: string;
      credits: number;
      percentage: number;
      executions: number;
      avgCreditsPerExecution: number;
    }>;
    
    // By Feature
    byFeature: Array<{
      feature: string;
      credits: number;
      percentage: number;
      usage: number;
    }>;
  };
  
  // Consumption Trends
  trends: {
    // Daily Consumption
    daily: Array<{
      date: string;
      credits: number;
      cumulative: number;
      
      // Breakdown
      breakdown: {
        [model: string]: number;
      };
    }>;
    
    // Hourly Pattern
    hourlyPattern: Array<{
      hour: number;
      avgCredits: number;
      peakDay: string;
    }>;
    
    // Weekly Pattern
    weeklyPattern: Array<{
      dayOfWeek: string;
      avgCredits: number;
    }>;
    
    // Growth Rate
    growthRate: {
      daily: number; // percentage
      weekly: number;
      monthly: number;
    };
  };
  
  // Budget Management
  budget: {
    // Budget Settings
    monthlyBudget: number | null;
    weeklyBudget: number | null;
    dailyLimit: number | null;
    
    // Budget Status
    budgetUtilization: number; // percentage
    budgetRemaining: number;
    isOverBudget: boolean;
    projectedOverage: number | null;
    
    // Alerts
    alerts: Array<{
      type: 'approaching_limit' | 'exceeded_limit' | 'unusual_spike';
      threshold: number;
      currentValue: number;
      message: string;
      triggeredAt: string;
    }>;
    
    // Spending Limits by Agent
    agentLimits: Array<{
      agentId: string;
      limit: number;
      consumed: number;
      remaining: number;
    }>;
  };
  
  // Cost Analysis
  costAnalysis: {
    // Total Costs
    totalCost: number;
    avgCostPerDay: number;
    avgCostPerRun: number;
    avgCostPerUser: number;
    
    // Cost Efficiency
    successCost: number; // cost of successful runs
    failureCost: number; // cost of failed runs
    wastedCredits: number;
    efficiencyRate: number; // percentage
    
    // Model Cost Comparison
    modelComparison: Array<{
      model: string;
      costPer1kTokens: number;
      avgResponseCost: number;
      qualityScore: number; // 0-100
      costEfficiencyScore: number;
    }>;
  };
  
  // Optimization Recommendations
  optimizations: Array<{
    type: 'model_switch' | 'caching' | 'batch_processing' | 'prompt_optimization';
    title: string;
    description: string;
    currentCost: number;
    projectedCost: number;
    potentialSavings: number;
    savingsPercentage: number;
    implementation: string;
    effort: 'low' | 'medium' | 'high';
  }>;
  
  // Forecasting
  forecast: {
    // Next Period Predictions
    nextDay: number;
    nextWeek: number;
    nextMonth: number;
    
    // Confidence Intervals
    confidence: {
      low: number; // 95% CI lower bound
      high: number; // 95% CI upper bound
    };
    
    // Seasonal Adjustments
    seasonalFactors: {
      weekday: number;
      weekend: number;
      monthEnd: number;
    };
    
    // Growth Projections
    projectedGrowth: Array<{
      period: string;
      credits: number;
      cost: number;
    }>;
  };
}
```

### Frontend Components

#### Credit Consumption Dashboard
```typescript
// frontend/src/app/credits/page.tsx
'use client';

import { useState } from 'react';
import { useCreditConsumption } from '@/hooks/api/useCreditConsumption';
import { CreditStatusCard } from '@/components/credits/CreditStatusCard';
import { ConsumptionChart } from '@/components/credits/ConsumptionChart';
import { ModelBreakdown } from '@/components/credits/ModelBreakdown';
import { BudgetManager } from '@/components/credits/BudgetManager';
import { CostOptimization } from '@/components/credits/CostOptimization';
import { UsageForecast } from '@/components/credits/UsageForecast';
import { CreditAlerts } from '@/components/credits/CreditAlerts';

export default function CreditConsumptionDashboard() {
  const [timeframe, setTimeframe] = useState<TimeFrame>('30d');
  const [view, setView] = useState<'overview' | 'breakdown' | 'optimization'>('overview');
  const { workspaceId } = useAuth();
  
  const { data, isLoading, error } = useCreditConsumption(workspaceId, timeframe);
  
  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState error={error} />;
  
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Credit Consumption</h1>
            <p className="mt-1 text-sm text-gray-500">
              Track and optimize your credit usage
            </p>
          </div>
          
          <div className="flex gap-4">
            <TimeframeSelector value={timeframe} onChange={setTimeframe} />
            <ExportButton data={data} />
          </div>
        </div>
        
        {/* Credit Status */}
        <CreditStatusCard status={data.currentStatus} />
        
        {/* Active Alerts */}
        {data.budget.alerts.length > 0 && (
          <CreditAlerts alerts={data.budget.alerts} />
        )}
        
        {/* View Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {['overview', 'breakdown', 'optimization'].map((v) => (
              <button
                key={v}
                onClick={() => setView(v as any)}
                className={`
                  py-2 px-1 border-b-2 font-medium text-sm capitalize
                  ${view === v 
                    ? 'border-blue-500 text-blue-600' 
                    : 'border-transparent text-gray-500 hover:text-gray-700'}
                `}
              >
                {v}
              </button>
            ))}
          </nav>
        </div>
        
        {/* Content based on view */}
        {view === 'overview' && (
          <div className="space-y-6">
            {/* Consumption Chart */}
            <ConsumptionChart trends={data.trends} />
            
            {/* Budget vs Actual */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <BudgetManager budget={data.budget} />
              <UsageForecast forecast={data.forecast} />
            </div>
          </div>
        )}
        
        {view === 'breakdown' && (
          <div className="space-y-6">
            {/* Model Breakdown */}
            <ModelBreakdown breakdown={data.breakdown.byModel} />
            
            {/* Agent and User Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <AgentConsumption agents={data.breakdown.byAgent} />
              <UserConsumption users={data.breakdown.byUser} />
            </div>
            
            {/* Cost Analysis */}
            <CostAnalysis analysis={data.costAnalysis} />
          </div>
        )}
        
        {view === 'optimization' && (
          <CostOptimization 
            optimizations={data.optimizations}
            currentCost={data.costAnalysis.totalCost}
          />
        )}
      </div>
    </div>
  );
}
```

#### Credit Status Card
```typescript
// frontend/src/components/credits/CreditStatusCard.tsx
import { CircularProgressbar, buildStyles } from 'react-circular-progressbar';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

interface CreditStatusCardProps {
  status: CreditConsumption['currentStatus'];
}

export function CreditStatusCard({ status }: CreditStatusCardProps) {
  const getUtilizationColor = (rate: number) => {
    if (rate < 50) return '#10b981';
    if (rate < 75) return '#f59e0b';
    if (rate < 90) return '#f97316';
    return '#ef4444';
  };
  
  const formatCredits = (credits: number) => {
    if (credits >= 1000000) return `${(credits / 1000000).toFixed(1)}M`;
    if (credits >= 1000) return `${(credits / 1000).toFixed(1)}K`;
    return credits.toFixed(0);
  };
  
  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Credit Balance */}
        <div className="text-center">
          <div className="w-32 h-32 mx-auto">
            <CircularProgressbar
              value={status.utilizationRate}
              text={`${status.utilizationRate.toFixed(1)}%`}
              styles={buildStyles({
                textSize: '20px',
                pathColor: getUtilizationColor(status.utilizationRate),
                textColor: '#1f2937',
                trailColor: '#f3f4f6'
              })}
            />
          </div>
          <p className="mt-2 text-sm text-gray-600">Utilization</p>
          <p className="text-lg font-semibold">
            {formatCredits(status.remainingCredits)} / {formatCredits(status.allocatedCredits)}
          </p>
          <p className="text-xs text-gray-500">Credits Remaining</p>
        </div>
        
        {/* Burn Rate */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-900">Burn Rate</h3>
          <div className="space-y-2">
            <div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Daily</span>
                <span className="font-medium">{formatCredits(status.dailyBurnRate)}</span>
              </div>
              <div className="mt-1 h-2 bg-gray-200 rounded-full">
                <div 
                  className="h-2 bg-blue-600 rounded-full"
                  style={{ 
                    width: `${Math.min(
                      (status.dailyBurnRate / (status.allocatedCredits / 30)) * 100, 
                      100
                    )}%` 
                  }}
                />
              </div>
            </div>
            
            <div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Weekly</span>
                <span className="font-medium">{formatCredits(status.weeklyBurnRate)}</span>
              </div>
            </div>
            
            <div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Monthly</span>
                <span className="font-medium">{formatCredits(status.monthlyBurnRate)}</span>
              </div>
            </div>
          </div>
        </div>
        
        {/* Projections */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-900">Projections</h3>
          <div className="space-y-2">
            {status.projectedExhaustion && (
              <div className="flex items-start gap-2 p-2 bg-red-50 rounded-lg">
                <ExclamationTriangleIcon className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-red-900">Credits will exhaust</p>
                  <p className="text-red-700">{status.projectedExhaustion}</p>
                </div>
              </div>
            )}
            
            <div>
              <p className="text-sm text-gray-500">Projected Monthly</p>
              <p className="text-lg font-semibold">{formatCredits(status.projectedMonthlyUsage)}</p>
            </div>
            
            {status.recommendedTopUp && (
              <div>
                <p className="text-sm text-gray-500">Recommended Top-up</p>
                <p className="text-lg font-semibold text-blue-600">
                  {formatCredits(status.recommendedTopUp)}
                </p>
              </div>
            )}
          </div>
        </div>
        
        {/* Period Info */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-900">Current Period</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Start</span>
              <span>{new Date(status.periodStart).toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">End</span>
              <span>{new Date(status.periodEnd).toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Days Remaining</span>
              <span className="font-medium">{status.daysRemaining}</span>
            </div>
          </div>
          
          <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm">
            Purchase Credits
          </button>
        </div>
      </div>
    </div>
  );
}
```

### Backend Implementation

#### Credit Consumption Service
```python
# backend/src/services/analytics/credit_consumption.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
import pandas as pd

class CreditConsumptionService:
    def __init__(self, db, cache_service):
        self.db = db
        self.cache = cache_service
    
    async def get_credit_consumption(
        self,
        workspace_id: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """Get comprehensive credit consumption analytics"""
        
        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(timeframe)
        
        # Parallel fetch all data
        results = await asyncio.gather(
            self._get_current_status(workspace_id),
            self._get_consumption_breakdown(workspace_id, start_date, end_date),
            self._get_consumption_trends(workspace_id, start_date, end_date),
            self._get_budget_status(workspace_id),
            self._get_cost_analysis(workspace_id, start_date, end_date),
            self._get_optimization_recommendations(workspace_id),
            self._forecast_usage(workspace_id)
        )
        
        return {
            "workspaceId": workspace_id,
            "timeframe": timeframe,
            "currentStatus": results[0],
            "breakdown": results[1],
            "trends": results[2],
            "budget": results[3],
            "costAnalysis": results[4],
            "optimizations": results[5],
            "forecast": results[6]
        }
    
    async def _get_current_status(
        self,
        workspace_id: str
    ) -> Dict[str, Any]:
        """Get current credit status and projections"""
        
        query = """
            WITH credit_data AS (
                SELECT 
                    wc.allocated_credits,
                    wc.consumed_credits,
                    wc.period_start,
                    wc.period_end,
                    wc.allocated_credits - wc.consumed_credits as remaining_credits
                FROM public.workspace_credits wc
                WHERE wc.workspace_id = $1
            ),
            burn_rate AS (
                SELECT 
                    DATE(started_at) as date,
                    SUM(credits_consumed) as daily_credits
                FROM public.agent_runs
                WHERE workspace_id = $1
                    AND started_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(started_at)
            )
            SELECT 
                cd.*,
                AVG(br.daily_credits) as avg_daily_burn,
                AVG(br.daily_credits) * 7 as avg_weekly_burn,
                AVG(br.daily_credits) * 30 as avg_monthly_burn
            FROM credit_data cd
            CROSS JOIN burn_rate br
            GROUP BY cd.allocated_credits, cd.consumed_credits, 
                     cd.period_start, cd.period_end, cd.remaining_credits
        """
        
        result = await self.db.fetch_one(query, workspace_id)
        
        # Calculate projections
        days_remaining = (result['period_end'] - datetime.utcnow()).days
        projected_exhaustion = None
        recommended_top_up = None
        
        if result['avg_daily_burn'] > 0:
            days_until_exhaustion = result['remaining_credits'] / result['avg_daily_burn']
            
            if days_until_exhaustion < days_remaining:
                projected_exhaustion = (
                    datetime.utcnow() + timedelta(days=days_until_exhaustion)
                ).isoformat()
                
                recommended_top_up = (
                    result['avg_daily_burn'] * days_remaining - 
                    result['remaining_credits']
                )
        
        return {
            "allocatedCredits": result['allocated_credits'],
            "consumedCredits": result['consumed_credits'],
            "remainingCredits": result['remaining_credits'],
            "utilizationRate": round(
                (result['consumed_credits'] / result['allocated_credits'] * 100)
                if result['allocated_credits'] > 0 else 0, 2
            ),
            "periodStart": result['period_start'].isoformat(),
            "periodEnd": result['period_end'].isoformat(),
            "daysRemaining": days_remaining,
            "dailyBurnRate": round(result['avg_daily_burn'] or 0, 2),
            "weeklyBurnRate": round(result['avg_weekly_burn'] or 0, 2),
            "monthlyBurnRate": round(result['avg_monthly_burn'] or 0, 2),
            "projectedExhaustion": projected_exhaustion,
            "projectedMonthlyUsage": round(result['avg_monthly_burn'] or 0, 2),
            "recommendedTopUp": round(recommended_top_up, 2) if recommended_top_up else None
        }
    
    async def _get_optimization_recommendations(
        self,
        workspace_id: str
    ) -> List[Dict[str, Any]]:
        """Generate credit optimization recommendations"""
        
        recommendations = []
        
        # Analyze model usage efficiency
        model_analysis = await self._analyze_model_efficiency(workspace_id)
        
        for model in model_analysis:
            if model['efficiency_score'] < 0.7:  # Low efficiency
                recommendations.append({
                    "type": "model_switch",
                    "title": f"Switch from {model['model']} to more efficient model",
                    "description": f"{model['model']} has low efficiency ({model['efficiency_score']:.2f}). Consider using a smaller model for similar tasks.",
                    "currentCost": model['monthly_cost'],
                    "projectedCost": model['monthly_cost'] * 0.6,
                    "potentialSavings": model['monthly_cost'] * 0.4,
                    "savingsPercentage": 40,
                    "implementation": "Review agent configurations and update model selections",
                    "effort": "low"
                })
        
        # Check for caching opportunities
        repeat_analysis = await self._analyze_repeat_queries(workspace_id)
        
        if repeat_analysis['repeat_rate'] > 0.2:  # >20% repeat queries
            savings = repeat_analysis['repeat_credits'] * 0.9  # 90% savings with caching
            
            recommendations.append({
                "type": "caching",
                "title": "Implement response caching",
                "description": f"{repeat_analysis['repeat_rate']*100:.1f}% of queries are repeated. Implement caching to reduce costs.",
                "currentCost": repeat_analysis['repeat_credits'],
                "projectedCost": repeat_analysis['repeat_credits'] * 0.1,
                "potentialSavings": savings,
                "savingsPercentage": 90,
                "implementation": "Add Redis caching layer for frequently repeated queries",
                "effort": "medium"
            })
        
        # Batch processing opportunities
        concurrent_analysis = await self._analyze_concurrent_usage(workspace_id)
        
        if concurrent_analysis['could_batch'] > 0.3:  # >30% could be batched
            recommendations.append({
                "type": "batch_processing",
                "title": "Batch similar requests",
                "description": "Multiple similar requests could be processed in batches for efficiency.",
                "currentCost": concurrent_analysis['individual_cost'],
                "projectedCost": concurrent_analysis['batch_cost'],
                "potentialSavings": concurrent_analysis['potential_savings'],
                "savingsPercentage": round(
                    (concurrent_analysis['potential_savings'] / 
                     concurrent_analysis['individual_cost'] * 100), 2
                ),
                "implementation": "Implement request queuing and batch processing",
                "effort": "high"
            })
        
        return recommendations
    
    async def _forecast_usage(
        self,
        workspace_id: str
    ) -> Dict[str, Any]:
        """Forecast future credit usage using time series analysis"""
        
        # Get historical data
        history_query = """
            SELECT 
                DATE(started_at) as date,
                SUM(credits_consumed) as credits
            FROM public.agent_runs
            WHERE workspace_id = $1
                AND started_at >= NOW() - INTERVAL '90 days'
            GROUP BY DATE(started_at)
            ORDER BY date
        """
        
        history = await self.db.fetch_all(history_query, workspace_id)
        
        if len(history) < 14:  # Need at least 2 weeks of data
            return self._default_forecast()
        
        # Prepare data for forecasting
        df = pd.DataFrame(history)
        df['date'] = pd.to_datetime(df['date'])
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_month'] = df['date'].dt.day
        df['days_since_start'] = (df['date'] - df['date'].min()).dt.days
        
        # Simple linear regression with seasonal factors
        X = df[['days_since_start', 'day_of_week', 'day_of_month']].values
        y = df['credits'].values
        
        model = LinearRegression()
        model.fit(X, y)
        
        # Generate forecasts
        today = datetime.utcnow().date()
        days_since_start = (today - df['date'].min().date()).days
        
        # Next day forecast
        next_day_features = [[
            days_since_start + 1,
            (today + timedelta(days=1)).weekday(),
            (today + timedelta(days=1)).day
        ]]
        next_day = model.predict(next_day_features)[0]
        
        # Next week forecast (sum of 7 days)
        next_week = sum(
            model.predict([[
                days_since_start + i,
                (today + timedelta(days=i)).weekday(),
                (today + timedelta(days=i)).day
            ]])[0]
            for i in range(1, 8)
        )
        
        # Next month forecast (sum of 30 days)
        next_month = sum(
            model.predict([[
                days_since_start + i,
                (today + timedelta(days=i)).weekday(),
                (today + timedelta(days=i)).day
            ]])[0]
            for i in range(1, 31)
        )
        
        # Calculate confidence intervals (simplified)
        residuals = y - model.predict(X)
        std_error = np.std(residuals)
        
        return {
            "nextDay": round(max(0, next_day), 2),
            "nextWeek": round(max(0, next_week), 2),
            "nextMonth": round(max(0, next_month), 2),
            "confidence": {
                "low": round(max(0, next_month - 1.96 * std_error * 30), 2),
                "high": round(next_month + 1.96 * std_error * 30, 2)
            },
            "seasonalFactors": {
                "weekday": round(df[df['day_of_week'] < 5]['credits'].mean(), 2),
                "weekend": round(df[df['day_of_week'] >= 5]['credits'].mean(), 2),
                "monthEnd": round(df[df['day_of_month'] > 25]['credits'].mean(), 2)
            },
            "projectedGrowth": [
                {
                    "period": f"Month {i+1}",
                    "credits": round(next_month * (1 + 0.1 * i), 2),  # 10% growth assumption
                    "cost": round(next_month * (1 + 0.1 * i) * 0.001, 2)  # $0.001 per credit
                }
                for i in range(3)
            ]
        }
```

### Database Schema
```sql
-- Credit consumption tracking
CREATE TABLE analytics.credit_consumption (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES public.workspaces(id),
    
    -- Consumption details
    model VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    credits_consumed NUMERIC(15,2) NOT NULL,
    tokens_used INTEGER,
    
    -- Context
    agent_id UUID REFERENCES public.agents(id),
    user_id UUID REFERENCES public.users(id),
    run_id UUID,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    consumed_at TIMESTAMPTZ DEFAULT NOW(),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_credit_consumption_workspace_time 
    ON analytics.credit_consumption(workspace_id, consumed_at DESC);

CREATE INDEX idx_credit_consumption_model 
    ON analytics.credit_consumption(model, consumed_at DESC);

-- Daily credit aggregation
CREATE TABLE analytics.credit_consumption_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES public.workspaces(id),
    date DATE NOT NULL,
    
    -- Totals
    total_credits NUMERIC(15,2) DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_calls INTEGER DEFAULT 0,
    
    -- Breakdown by model
    model_breakdown JSONB DEFAULT '{}',
    
    -- Breakdown by agent
    agent_breakdown JSONB DEFAULT '{}',
    
    -- Breakdown by user
    user_breakdown JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_credit_daily UNIQUE(workspace_id, date)
);
```

## Testing Requirements
- Forecast accuracy tests
- Budget alert trigger tests
- Optimization recommendation tests
- Consumption tracking accuracy
- Performance tests for large datasets

## Performance Targets
- Credit status query: <200ms
- Breakdown calculation: <500ms
- Forecast generation: <1 second
- Optimization analysis: <2 seconds
- Dashboard load: <1.5 seconds

## Security Considerations
- Cost data access restrictions
- Budget limit enforcement
- Audit logging for credit purchases
- Rate limiting on expensive calculations