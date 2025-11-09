# User Form Interaction Specification

## Overview
Track how users interact with forms without complex form builders. Capture form completion rates, field errors, and abandonment patterns.

## TypeScript Interfaces

```typescript
// Form interaction event
interface FormInteraction {
  interaction_id: string;
  user_id: string;
  form_id: string;
  form_name: string;
  field_name: string;
  event_type: 'focus' | 'blur' | 'change' | 'error' | 'submit' | 'abandon';
  timestamp: Date;
  time_spent_ms?: number;
  error_message?: string;
}

// Form submission
interface FormSubmission {
  submission_id: string;
  user_id: string;
  form_id: string;
  started_at: Date;
  submitted_at?: Date;
  abandoned_at?: Date;
  total_time_ms: number;
  field_count: number;
  error_count: number;
  status: 'completed' | 'abandoned' | 'error';
}

// Form field metrics
interface FormFieldMetrics {
  form_id: string;
  field_name: string;
  total_interactions: number;
  error_count: number;
  avg_time_spent_ms: number;
  abandonment_rate: number;
  error_rate: number;
}

// Form conversion funnel
interface FormConversionFunnel {
  form_id: string;
  total_starts: number;
  field_1_completed: number;
  field_2_completed: number;
  field_3_completed: number;
  total_submissions: number;
  conversion_rate: number;
}
```

## SQL Schema

```sql
-- Form interactions table
CREATE TABLE form_interactions (
    interaction_id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255),
    form_id VARCHAR(255) NOT NULL,
    form_name VARCHAR(255),
    field_name VARCHAR(255),
    event_type VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    time_spent_ms INTEGER,
    error_message TEXT,
    field_value_length INTEGER
);

-- Form submissions
CREATE TABLE form_submissions (
    submission_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    form_id VARCHAR(255) NOT NULL,
    form_name VARCHAR(255),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    abandoned_at TIMESTAMP,
    total_time_ms INTEGER,
    field_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'in_progress'
);

-- Form field metrics
CREATE TABLE form_field_metrics (
    form_id VARCHAR(255) NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    total_interactions INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    total_time_spent_ms BIGINT DEFAULT 0,
    abandonment_count INTEGER DEFAULT 0,
    successful_completions INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (form_id, field_name)
);

-- Daily form statistics
CREATE TABLE daily_form_stats (
    date DATE NOT NULL,
    form_id VARCHAR(255) NOT NULL,
    total_starts INTEGER DEFAULT 0,
    total_completions INTEGER DEFAULT 0,
    total_abandons INTEGER DEFAULT 0,
    avg_completion_time_ms INTEGER DEFAULT 0,
    error_rate DECIMAL(5,2) DEFAULT 0,
    conversion_rate DECIMAL(5,2) DEFAULT 0,
    PRIMARY KEY (date, form_id)
);

-- Form templates (for tracking form structure)
CREATE TABLE form_templates (
    form_id VARCHAR(255) PRIMARY KEY,
    form_name VARCHAR(255),
    field_names TEXT[],
    required_fields TEXT[],
    field_types JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Basic indexes
CREATE INDEX idx_interactions_user ON form_interactions(user_id);
CREATE INDEX idx_interactions_form ON form_interactions(form_id);
CREATE INDEX idx_interactions_timestamp ON form_interactions(timestamp DESC);
CREATE INDEX idx_submissions_user ON form_submissions(user_id);
CREATE INDEX idx_submissions_form ON form_submissions(form_id);
CREATE INDEX idx_submissions_status ON form_submissions(status);
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import uuid
import json

@dataclass
class FormMetrics:
    """Form performance metrics"""
    form_id: str
    completion_rate: float
    avg_completion_time: float
    error_rate: float
    abandonment_rate: float
    problem_fields: List[str]

class FormTracker:
    """Track form interactions and performance"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.active_forms = {}  # Track active form sessions
    
    def start_form(
        self,
        user_id: str,
        form_id: str,
        form_name: str,
        field_count: int
    ) -> str:
        """Track form start"""
        submission_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO form_submissions
        (submission_id, user_id, form_id, form_name, field_count)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING submission_id
        """
        
        result = self.db.fetchone(query, (
            submission_id, user_id, form_id, form_name, field_count
        ))
        
        # Track in memory for quick access
        self.active_forms[submission_id] = {
            'user_id': user_id,
            'form_id': form_id,
            'started_at': datetime.now(),
            'field_interactions': {}
        }
        
        return result['submission_id']
    
    def track_field_interaction(
        self,
        user_id: str,
        form_id: str,
        field_name: str,
        event_type: str,
        session_id: Optional[str] = None,
        time_spent_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        field_value_length: Optional[int] = None
    ) -> bool:
        """Track field interaction"""
        query = """
        INSERT INTO form_interactions
        (user_id, session_id, form_id, field_name, event_type, 
         time_spent_ms, error_message, field_value_length)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        try:
            self.db.execute(query, (
                user_id, session_id, form_id, field_name,
                event_type, time_spent_ms, error_message,
                field_value_length
            ))
            
            # Update field metrics
            self.update_field_metrics(form_id, field_name, event_type, time_spent_ms)
            
            # Track errors
            if event_type == 'error':
                self.increment_error_count(form_id, user_id)
            
            return True
        except Exception as e:
            print(f"Error tracking field interaction: {e}")
            return False
    
    def update_field_metrics(
        self,
        form_id: str,
        field_name: str,
        event_type: str,
        time_spent_ms: Optional[int] = None
    ) -> None:
        """Update field-level metrics"""
        query = """
        INSERT INTO form_field_metrics
        (form_id, field_name, total_interactions, total_time_spent_ms)
        VALUES (%s, %s, 1, %s)
        ON CONFLICT (form_id, field_name)
        DO UPDATE SET
            total_interactions = form_field_metrics.total_interactions + 1,
            total_time_spent_ms = form_field_metrics.total_time_spent_ms + COALESCE(%s, 0),
            error_count = form_field_metrics.error_count + CASE WHEN %s = 'error' THEN 1 ELSE 0 END,
            abandonment_count = form_field_metrics.abandonment_count + CASE WHEN %s = 'abandon' THEN 1 ELSE 0 END,
            successful_completions = form_field_metrics.successful_completions + CASE WHEN %s = 'blur' THEN 1 ELSE 0 END,
            updated_at = CURRENT_TIMESTAMP
        """
        
        self.db.execute(query, (
            form_id, field_name, time_spent_ms or 0,
            time_spent_ms or 0, event_type, event_type, event_type
        ))
    
    def submit_form(
        self,
        submission_id: str,
        user_id: str,
        form_id: str
    ) -> bool:
        """Mark form as submitted"""
        query = """
        UPDATE form_submissions
        SET 
            submitted_at = CURRENT_TIMESTAMP,
            total_time_ms = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at)) * 1000,
            status = 'completed'
        WHERE submission_id = %s
        AND user_id = %s
        AND form_id = %s
        """
        
        result = self.db.execute(query, (submission_id, user_id, form_id))
        
        # Remove from active forms
        if submission_id in self.active_forms:
            del self.active_forms[submission_id]
        
        return result.rowcount > 0 if hasattr(result, 'rowcount') else False
    
    def abandon_form(
        self,
        submission_id: str,
        user_id: str,
        form_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Mark form as abandoned"""
        query = """
        UPDATE form_submissions
        SET 
            abandoned_at = CURRENT_TIMESTAMP,
            total_time_ms = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at)) * 1000,
            status = 'abandoned'
        WHERE submission_id = %s
        AND user_id = %s
        AND form_id = %s
        """
        
        result = self.db.execute(query, (submission_id, user_id, form_id))
        
        # Track abandonment in field metrics
        if reason:
            self.track_field_interaction(
                user_id, form_id, 'form', 'abandon',
                error_message=reason
            )
        
        # Remove from active forms
        if submission_id in self.active_forms:
            del self.active_forms[submission_id]
        
        return result.rowcount > 0 if hasattr(result, 'rowcount') else False
    
    def increment_error_count(self, form_id: str, user_id: str) -> None:
        """Increment error count for active submission"""
        query = """
        UPDATE form_submissions
        SET error_count = error_count + 1
        WHERE form_id = %s
        AND user_id = %s
        AND status = 'in_progress'
        ORDER BY started_at DESC
        LIMIT 1
        """
        self.db.execute(query, (form_id, user_id))
    
    def get_form_metrics(self, form_id: str, days: int = 30) -> FormMetrics:
        """Get form performance metrics"""
        query = """
        WITH form_stats AS (
            SELECT 
                COUNT(*) as total_starts,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completions,
                COUNT(CASE WHEN status = 'abandoned' THEN 1 END) as abandons,
                AVG(CASE WHEN status = 'completed' THEN total_time_ms END) as avg_time,
                AVG(error_count) as avg_errors
            FROM form_submissions
            WHERE form_id = %s
            AND started_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        ),
        problem_fields AS (
            SELECT field_name
            FROM form_field_metrics
            WHERE form_id = %s
            AND error_count > 0
            ORDER BY error_count DESC
            LIMIT 5
        )
        SELECT 
            fs.*,
            ARRAY_AGG(pf.field_name) as problem_fields
        FROM form_stats fs, problem_fields pf
        GROUP BY fs.total_starts, fs.completions, fs.abandons, fs.avg_time, fs.avg_errors
        """
        
        result = self.db.fetchone(query, (form_id, days, form_id))
        
        if not result:
            return FormMetrics(
                form_id=form_id,
                completion_rate=0,
                avg_completion_time=0,
                error_rate=0,
                abandonment_rate=0,
                problem_fields=[]
            )
        
        total = result['total_starts'] or 1
        
        return FormMetrics(
            form_id=form_id,
            completion_rate=(result['completions'] or 0) / total * 100,
            avg_completion_time=(result['avg_time'] or 0) / 1000,  # Convert to seconds
            error_rate=(result['avg_errors'] or 0),
            abandonment_rate=(result['abandons'] or 0) / total * 100,
            problem_fields=result['problem_fields'] or []
        )
    
    def get_field_analytics(self, form_id: str) -> List[Dict]:
        """Get analytics for all fields in a form"""
        query = """
        SELECT 
            field_name,
            total_interactions,
            unique_users,
            error_count,
            abandonment_count,
            successful_completions,
            CASE 
                WHEN total_interactions > 0 
                THEN (total_time_spent_ms::FLOAT / total_interactions)
                ELSE 0 
            END as avg_time_spent,
            CASE 
                WHEN total_interactions > 0 
                THEN (error_count::FLOAT / total_interactions * 100)
                ELSE 0 
            END as error_rate,
            CASE 
                WHEN total_interactions > 0 
                THEN (abandonment_count::FLOAT / total_interactions * 100)
                ELSE 0 
            END as abandonment_rate
        FROM form_field_metrics
        WHERE form_id = %s
        ORDER BY field_name
        """
        
        return self.db.fetchall(query, (form_id,))
    
    def get_conversion_funnel(self, form_id: str) -> Dict:
        """Get form conversion funnel"""
        query = """
        WITH funnel AS (
            SELECT 
                form_id,
                COUNT(DISTINCT CASE WHEN event_type = 'focus' THEN user_id END) as started,
                COUNT(DISTINCT CASE WHEN field_name = 'field_1' AND event_type = 'blur' THEN user_id END) as field_1,
                COUNT(DISTINCT CASE WHEN field_name = 'field_2' AND event_type = 'blur' THEN user_id END) as field_2,
                COUNT(DISTINCT CASE WHEN field_name = 'field_3' AND event_type = 'blur' THEN user_id END) as field_3,
                COUNT(DISTINCT CASE WHEN event_type = 'submit' THEN user_id END) as submitted
            FROM form_interactions
            WHERE form_id = %s
            AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            GROUP BY form_id
        )
        SELECT 
            *,
            CASE WHEN started > 0 THEN (submitted::FLOAT / started * 100) ELSE 0 END as conversion_rate
        FROM funnel
        """
        
        result = self.db.fetchone(query, (form_id,))
        
        if not result:
            return {
                'form_id': form_id,
                'funnel': [],
                'conversion_rate': 0
            }
        
        # Build funnel steps
        funnel_steps = [
            {'step': 'Started', 'users': result['started'], 'rate': 100},
            {'step': 'Field 1', 'users': result['field_1'], 
             'rate': (result['field_1'] / result['started'] * 100) if result['started'] > 0 else 0},
            {'step': 'Field 2', 'users': result['field_2'],
             'rate': (result['field_2'] / result['started'] * 100) if result['started'] > 0 else 0},
            {'step': 'Field 3', 'users': result['field_3'],
             'rate': (result['field_3'] / result['started'] * 100) if result['started'] > 0 else 0},
            {'step': 'Submitted', 'users': result['submitted'],
             'rate': result['conversion_rate']}
        ]
        
        return {
            'form_id': form_id,
            'funnel': funnel_steps,
            'conversion_rate': result['conversion_rate']
        }
    
    def get_user_form_history(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user's form interaction history"""
        query = """
        SELECT 
            form_id,
            form_name,
            started_at,
            submitted_at,
            abandoned_at,
            total_time_ms,
            error_count,
            status
        FROM form_submissions
        WHERE user_id = %s
        AND started_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        ORDER BY started_at DESC
        """
        
        return self.db.fetchall(query, (user_id, days))
    
    def identify_problem_forms(self, threshold: float = 50.0) -> List[Dict]:
        """Identify forms with high abandonment rates"""
        query = """
        WITH form_performance AS (
            SELECT 
                form_id,
                COUNT(*) as total_attempts,
                COUNT(CASE WHEN status = 'abandoned' THEN 1 END) as abandonments,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completions,
                AVG(error_count) as avg_errors,
                AVG(CASE WHEN status = 'completed' THEN total_time_ms END) as avg_completion_time
            FROM form_submissions
            WHERE started_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
            GROUP BY form_id
        )
        SELECT 
            form_id,
            total_attempts,
            abandonments,
            completions,
            avg_errors,
            avg_completion_time,
            (abandonments::FLOAT / total_attempts * 100) as abandonment_rate
        FROM form_performance
        WHERE (abandonments::FLOAT / total_attempts * 100) > %s
        ORDER BY abandonment_rate DESC
        """
        
        return self.db.fetchall(query, (threshold,))
    
    def calculate_daily_stats(self, date: Optional[datetime] = None) -> None:
        """Calculate daily form statistics"""
        target_date = date or datetime.now().date()
        
        query = """
        INSERT INTO daily_form_stats
        (date, form_id, total_starts, total_completions, total_abandons,
         avg_completion_time_ms, error_rate, conversion_rate)
        SELECT 
            %s as date,
            form_id,
            COUNT(*) as total_starts,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completions,
            COUNT(CASE WHEN status = 'abandoned' THEN 1 END) as abandons,
            AVG(CASE WHEN status = 'completed' THEN total_time_ms END)::INTEGER as avg_time,
            AVG(error_count) as error_rate,
            CASE 
                WHEN COUNT(*) > 0 
                THEN (COUNT(CASE WHEN status = 'completed' THEN 1 END)::FLOAT / COUNT(*) * 100)
                ELSE 0 
            END as conversion_rate
        FROM form_submissions
        WHERE DATE(started_at) = %s
        GROUP BY form_id
        ON CONFLICT (date, form_id)
        DO UPDATE SET
            total_starts = EXCLUDED.total_starts,
            total_completions = EXCLUDED.total_completions,
            total_abandons = EXCLUDED.total_abandons,
            avg_completion_time_ms = EXCLUDED.avg_completion_time_ms,
            error_rate = EXCLUDED.error_rate,
            conversion_rate = EXCLUDED.conversion_rate
        """
        
        self.db.execute(query, (target_date, target_date))
```

## API Endpoints

```python
from fastapi import APIRouter, Query, HTTPException, Body
from typing import List, Optional, Dict

router = APIRouter(prefix="/api/forms", tags=["forms"])

@router.post("/start")
async def start_form(
    user_id: str = Body(...),
    form_id: str = Body(...),
    form_name: str = Body(...),
    field_count: int = Body(...)
):
    """Start tracking a form"""
    tracker = FormTracker(db)
    submission_id = tracker.start_form(user_id, form_id, form_name, field_count)
    
    return {
        "submission_id": submission_id,
        "form_id": form_id,
        "status": "started"
    }

@router.post("/track-field")
async def track_field_interaction(
    user_id: str = Body(...),
    form_id: str = Body(...),
    field_name: str = Body(...),
    event_type: str = Body(...),
    session_id: Optional[str] = Body(None),
    time_spent_ms: Optional[int] = Body(None),
    error_message: Optional[str] = Body(None),
    field_value_length: Optional[int] = Body(None)
):
    """Track field interaction"""
    valid_events = ['focus', 'blur', 'change', 'error', 'submit', 'abandon']
    
    if event_type not in valid_events:
        raise HTTPException(status_code=400, detail=f"Invalid event type. Must be one of {valid_events}")
    
    tracker = FormTracker(db)
    success = tracker.track_field_interaction(
        user_id, form_id, field_name, event_type,
        session_id, time_spent_ms, error_message, field_value_length
    )
    
    return {"success": success}

@router.post("/submit")
async def submit_form(
    submission_id: str = Body(...),
    user_id: str = Body(...),
    form_id: str = Body(...)
):
    """Submit a form"""
    tracker = FormTracker(db)
    success = tracker.submit_form(submission_id, user_id, form_id)
    
    return {
        "success": success,
        "submission_id": submission_id,
        "status": "completed"
    }

@router.post("/abandon")
async def abandon_form(
    submission_id: str = Body(...),
    user_id: str = Body(...),
    form_id: str = Body(...),
    reason: Optional[str] = Body(None)
):
    """Abandon a form"""
    tracker = FormTracker(db)
    success = tracker.abandon_form(submission_id, user_id, form_id, reason)
    
    return {
        "success": success,
        "submission_id": submission_id,
        "status": "abandoned"
    }

@router.get("/metrics/{form_id}")
async def get_form_metrics(
    form_id: str,
    days: int = Query(30, ge=1, le=90)
):
    """Get form performance metrics"""
    tracker = FormTracker(db)
    metrics = tracker.get_form_metrics(form_id, days)
    
    return {
        "form_id": form_id,
        "completion_rate": metrics.completion_rate,
        "avg_completion_time_seconds": metrics.avg_completion_time,
        "error_rate": metrics.error_rate,
        "abandonment_rate": metrics.abandonment_rate,
        "problem_fields": metrics.problem_fields
    }

@router.get("/fields/{form_id}")
async def get_field_analytics(form_id: str):
    """Get field-level analytics"""
    tracker = FormTracker(db)
    fields = tracker.get_field_analytics(form_id)
    
    return {
        "form_id": form_id,
        "fields": fields
    }

@router.get("/funnel/{form_id}")
async def get_conversion_funnel(form_id: str):
    """Get form conversion funnel"""
    tracker = FormTracker(db)
    funnel = tracker.get_conversion_funnel(form_id)
    
    return funnel

@router.get("/user/{user_id}/history")
async def get_user_form_history(
    user_id: str,
    days: int = Query(30, ge=1, le=90)
):
    """Get user's form history"""
    tracker = FormTracker(db)
    history = tracker.get_user_form_history(user_id, days)
    
    return {
        "user_id": user_id,
        "forms": history,
        "count": len(history)
    }

@router.get("/problems")
async def get_problem_forms(
    threshold: float = Query(50.0, ge=0, le=100)
):
    """Get forms with high abandonment rates"""
    tracker = FormTracker(db)
    problems = tracker.identify_problem_forms(threshold)
    
    return {
        "threshold": threshold,
        "problem_forms": problems,
        "count": len(problems)
    }

@router.get("/stats/daily")
async def get_daily_form_stats(
    date: Optional[str] = Query(None),
    form_id: Optional[str] = Query(None)
):
    """Get daily form statistics"""
    target_date = date or datetime.now().date().isoformat()
    
    where_conditions = ["date = %s"]
    params = [target_date]
    
    if form_id:
        where_conditions.append("form_id = %s")
        params.append(form_id)
    
    query = f"""
    SELECT 
        form_id,
        total_starts,
        total_completions,
        total_abandons,
        avg_completion_time_ms,
        error_rate,
        conversion_rate
    FROM daily_form_stats
    WHERE {' AND '.join(where_conditions)}
    ORDER BY total_starts DESC
    """
    
    stats = db.fetchall(query, tuple(params))
    
    return {
        "date": target_date,
        "stats": stats
    }
```

## React Dashboard Component

```tsx
import React, { useState, useEffect } from 'react';
import { FileText, AlertCircle, CheckCircle, XCircle, TrendingDown } from 'lucide-react';
import { FunnelChart, Funnel, LabelList, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface FormMetrics {
  formId: string;
  completionRate: number;
  avgCompletionTimeSeconds: number;
  errorRate: number;
  abandonmentRate: number;
  problemFields: string[];
}

interface FieldAnalytics {
  fieldName: string;
  totalInteractions: number;
  errorCount: number;
  abandonmentRate: number;
  avgTimeSpent: number;
  errorRate: number;
}

interface FunnelStep {
  step: string;
  users: number;
  rate: number;
}

export const FormInteractionDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<FormMetrics | null>(null);
  const [fieldAnalytics, setFieldAnalytics] = useState<FieldAnalytics[]>([]);
  const [funnel, setFunnel] = useState<FunnelStep[]>([]);
  const [problemForms, setProblemForms] = useState<any[]>([]);
  const [selectedFormId, setSelectedFormId] = useState('checkout-form');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFormData(selectedFormId);
  }, [selectedFormId]);

  const fetchFormData = async (formId: string) => {
    try {
      const [metricsRes, fieldsRes, funnelRes, problemsRes] = await Promise.all([
        fetch(`/api/forms/metrics/${formId}?days=30`),
        fetch(`/api/forms/fields/${formId}`),
        fetch(`/api/forms/funnel/${formId}`),
        fetch('/api/forms/problems?threshold=40')
      ]);

      const metricsData = await metricsRes.json();
      const fieldsData = await fieldsRes.json();
      const funnelData = await funnelRes.json();
      const problemsData = await problemsRes.json();

      setMetrics(metricsData);
      setFieldAnalytics(fieldsData.fields);
      setFunnel(funnelData.funnel);
      setProblemForms(problemsData.problem_forms);
    } catch (error) {
      console.error('Error fetching form data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getFieldStatusColor = (errorRate: number, abandonmentRate: number) => {
    if (errorRate > 20 || abandonmentRate > 30) return 'text-red-600';
    if (errorRate > 10 || abandonmentRate > 20) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getMetricIcon = (value: number, threshold: number, inverse: boolean = false) => {
    const isGood = inverse ? value < threshold : value > threshold;
    return isGood ? (
      <CheckCircle className="w-4 h-4 text-green-500" />
    ) : (
      <XCircle className="w-4 h-4 text-red-500" />
    );
  };

  if (loading) return <div>Loading form data...</div>;

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Form Interaction Analytics</h2>

      {/* Form Selector */}
      <div className="bg-white p-4 rounded-lg shadow">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Form
        </label>
        <select
          value={selectedFormId}
          onChange={(e) => setSelectedFormId(e.target.value)}
          className="w-full p-2 border rounded"
        >
          <option value="checkout-form">Checkout Form</option>
          <option value="registration-form">Registration Form</option>
          <option value="contact-form">Contact Form</option>
          <option value="survey-form">Survey Form</option>
        </select>
      </div>

      {/* Key Metrics */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Completion Rate</span>
              {getMetricIcon(metrics.completionRate, 70)}
            </div>
            <div className="text-2xl font-bold">{metrics.completionRate.toFixed(1)}%</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Avg Completion Time</span>
              {getMetricIcon(metrics.avgCompletionTimeSeconds, 300, true)}
            </div>
            <div className="text-2xl font-bold">
              {Math.round(metrics.avgCompletionTimeSeconds)}s
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Error Rate</span>
              {getMetricIcon(metrics.errorRate, 5, true)}
            </div>
            <div className="text-2xl font-bold">{metrics.errorRate.toFixed(1)}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Abandonment Rate</span>
              {getMetricIcon(metrics.abandonmentRate, 30, true)}
            </div>
            <div className="text-2xl font-bold text-red-600">
              {metrics.abandonmentRate.toFixed(1)}%
            </div>
          </div>
        </div>
      )}

      {/* Conversion Funnel */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Conversion Funnel</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={funnel} layout="horizontal">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="step" type="category" />
            <Tooltip />
            <Bar dataKey="users" fill="#3b82f6">
              <LabelList dataKey="rate" position="right" formatter={(v: number) => `${v.toFixed(0)}%`} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Field Analytics */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Field Performance</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Field Name</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Interactions</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Avg Time</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Error Rate</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Abandon Rate</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {fieldAnalytics.map((field) => (
                <tr key={field.fieldName} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm font-medium">{field.fieldName}</td>
                  <td className="px-4 py-2 text-sm">{field.totalInteractions}</td>
                  <td className="px-4 py-2 text-sm">
                    {(field.avgTimeSpent / 1000).toFixed(1)}s
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <span className={field.errorRate > 10 ? 'text-red-600' : 'text-gray-900'}>
                      {field.errorRate.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <span className={field.abandonmentRate > 20 ? 'text-red-600' : 'text-gray-900'}>
                      {field.abandonmentRate.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span className={`text-sm ${getFieldStatusColor(field.errorRate, field.abandonmentRate)}`}>
                      {field.errorRate > 20 || field.abandonmentRate > 30 ? '⚠️ Issues' : '✓ Good'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Problem Forms */}
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-yellow-500" />
            Problem Forms
          </h3>
          <span className="text-sm text-gray-500">
            Forms with >40% abandonment rate
          </span>
        </div>
        <div className="space-y-3">
          {problemForms.slice(0, 5).map((form) => (
            <div key={form.form_id} className="flex items-center justify-between p-3 bg-red-50 rounded">
              <div>
                <div className="font-medium">{form.form_id}</div>
                <div className="text-sm text-gray-600">
                  {form.total_attempts} attempts, {form.completions} completions
                </div>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold text-red-600">
                  {form.abandonment_rate.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-500">abandonment</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Problem Fields Alert */}
      {metrics && metrics.problemFields.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
          <div className="flex items-start">
            <TrendingDown className="w-5 h-5 text-yellow-600 mt-0.5 mr-2" />
            <div>
              <div className="font-medium text-yellow-900">Fields with High Error Rates</div>
              <div className="text-sm text-yellow-700 mt-1">
                The following fields are causing issues: {metrics.problemFields.join(', ')}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
```

## Implementation Priority
- **Phase 1**: Basic form tracking (start, submit, abandon)
- **Phase 2**: Field-level interaction tracking
- **Phase 3**: Conversion funnel analysis
- **Phase 4**: Problem detection and alerts

## Performance Considerations
- Batch field interaction updates
- Daily aggregation for statistics
- Limited interaction history (30 days)
- Efficient funnel calculations

## Security Considerations
- No storage of actual form values
- Field value length tracking only
- User privacy protection
- Rate limiting on tracking endpoints

## Monitoring and Alerts
- Alert on forms with >50% abandonment rate
- Alert on fields with high error rates
- Daily form performance report
- Weekly conversion funnel analysis

## Dependencies
- PostgreSQL with JSONB support
- FastAPI for REST endpoints
- UUID for submission IDs
- React with Recharts for visualization