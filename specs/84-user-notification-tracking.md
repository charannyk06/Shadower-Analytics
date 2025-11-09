# User Notification Tracking Specification

## Overview
Track notification delivery and user engagement without complex notification infrastructure. Simple tracking of what notifications users receive and how they respond.

## TypeScript Interfaces

```typescript
// Notification event
interface NotificationEvent {
  notification_id: string;
  user_id: string;
  type: 'email' | 'push' | 'in-app' | 'sms';
  category: string;
  subject: string;
  status: 'sent' | 'delivered' | 'opened' | 'clicked' | 'failed';
  sent_at: Date;
  delivered_at?: Date;
  opened_at?: Date;
  clicked_at?: Date;
}

// Notification preference
interface NotificationPreference {
  user_id: string;
  channel: string;
  category: string;
  enabled: boolean;
  frequency: 'immediate' | 'daily' | 'weekly' | 'never';
  quiet_hours_start?: number;
  quiet_hours_end?: number;
}

// Notification metrics
interface NotificationMetrics {
  user_id: string;
  total_sent: number;
  total_opened: number;
  total_clicked: number;
  open_rate: number;
  click_rate: number;
  opt_out_count: number;
}

// Daily notification summary
interface DailyNotificationSummary {
  date: string;
  type: string;
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  total_clicked: number;
  total_failed: number;
  avg_time_to_open: number;
}
```

## SQL Schema

```sql
-- Notification events table
CREATE TABLE notification_events (
    notification_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,
    category VARCHAR(50),
    subject TEXT,
    status VARCHAR(20) DEFAULT 'sent',
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP,
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP,
    metadata JSONB
);

-- Notification preferences
CREATE TABLE notification_preferences (
    user_id VARCHAR(255) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    frequency VARCHAR(20) DEFAULT 'immediate',
    quiet_hours_start INTEGER,
    quiet_hours_end INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, channel, category)
);

-- User notification metrics
CREATE TABLE user_notification_metrics (
    user_id VARCHAR(255) PRIMARY KEY,
    total_sent INTEGER DEFAULT 0,
    total_delivered INTEGER DEFAULT 0,
    total_opened INTEGER DEFAULT 0,
    total_clicked INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    last_sent TIMESTAMP,
    last_opened TIMESTAMP,
    opt_out_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily notification statistics
CREATE TABLE daily_notification_stats (
    date DATE NOT NULL,
    type VARCHAR(20) NOT NULL,
    category VARCHAR(50),
    total_sent INTEGER DEFAULT 0,
    total_delivered INTEGER DEFAULT 0,
    total_opened INTEGER DEFAULT 0,
    total_clicked INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    avg_time_to_open INTEGER,
    PRIMARY KEY (date, type, category)
);

-- Basic indexes
CREATE INDEX idx_notifications_user ON notification_events(user_id);
CREATE INDEX idx_notifications_status ON notification_events(status);
CREATE INDEX idx_notifications_sent ON notification_events(sent_at DESC);
CREATE INDEX idx_preferences_user ON notification_preferences(user_id);
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import uuid
import json

@dataclass
class NotificationResult:
    """Result of notification send"""
    success: bool
    notification_id: str
    message: str
    delivered_at: Optional[datetime] = None

class NotificationTracker:
    """Simple notification tracking"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def send_notification(
        self,
        user_id: str,
        type: str,
        category: str,
        subject: str,
        metadata: Optional[Dict] = None
    ) -> NotificationResult:
        """Track notification send"""
        # Check user preferences first
        if not self.check_preferences(user_id, type, category):
            return NotificationResult(
                success=False,
                notification_id="",
                message="User has disabled this notification type"
            )
        
        # Check quiet hours
        if self.is_quiet_hours(user_id):
            return NotificationResult(
                success=False,
                notification_id="",
                message="Within user's quiet hours"
            )
        
        notification_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO notification_events
        (notification_id, user_id, type, category, subject, metadata)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        try:
            self.db.execute(query, (
                notification_id, user_id, type, category,
                subject, json.dumps(metadata) if metadata else None
            ))
            
            # Update user metrics
            self.update_user_metrics(user_id, 'sent')
            
            return NotificationResult(
                success=True,
                notification_id=notification_id,
                message="Notification sent successfully",
                delivered_at=datetime.now()
            )
        except Exception as e:
            return NotificationResult(
                success=False,
                notification_id="",
                message=f"Failed to send: {str(e)}"
            )
    
    def check_preferences(self, user_id: str, channel: str, category: str) -> bool:
        """Check if user has enabled this notification type"""
        query = """
        SELECT enabled 
        FROM notification_preferences
        WHERE user_id = %s AND channel = %s AND category = %s
        """
        
        result = self.db.fetchone(query, (user_id, channel, category))
        
        # Default to enabled if no preference set
        return result['enabled'] if result else True
    
    def is_quiet_hours(self, user_id: str) -> bool:
        """Check if current time is within user's quiet hours"""
        query = """
        SELECT quiet_hours_start, quiet_hours_end
        FROM notification_preferences
        WHERE user_id = %s
        AND quiet_hours_start IS NOT NULL
        LIMIT 1
        """
        
        result = self.db.fetchone(query, (user_id,))
        
        if not result:
            return False
        
        current_hour = datetime.now().hour
        start = result['quiet_hours_start']
        end = result['quiet_hours_end']
        
        if start <= end:
            return start <= current_hour < end
        else:  # Crosses midnight
            return current_hour >= start or current_hour < end
    
    def track_delivery(self, notification_id: str) -> bool:
        """Track notification delivery"""
        query = """
        UPDATE notification_events
        SET 
            status = 'delivered',
            delivered_at = CURRENT_TIMESTAMP
        WHERE notification_id = %s
        AND status = 'sent'
        """
        
        result = self.db.execute(query, (notification_id,))
        
        if result.rowcount > 0:
            # Update user metrics
            user_id = self.get_notification_user(notification_id)
            if user_id:
                self.update_user_metrics(user_id, 'delivered')
            return True
        
        return False
    
    def track_open(self, notification_id: str) -> bool:
        """Track notification open"""
        query = """
        UPDATE notification_events
        SET 
            status = 'opened',
            opened_at = CURRENT_TIMESTAMP
        WHERE notification_id = %s
        AND status IN ('delivered', 'sent')
        """
        
        result = self.db.execute(query, (notification_id,))
        
        if result.rowcount > 0:
            user_id = self.get_notification_user(notification_id)
            if user_id:
                self.update_user_metrics(user_id, 'opened')
            return True
        
        return False
    
    def track_click(self, notification_id: str) -> bool:
        """Track notification click"""
        query = """
        UPDATE notification_events
        SET 
            status = 'clicked',
            clicked_at = CURRENT_TIMESTAMP
        WHERE notification_id = %s
        """
        
        result = self.db.execute(query, (notification_id,))
        
        if result.rowcount > 0:
            user_id = self.get_notification_user(notification_id)
            if user_id:
                self.update_user_metrics(user_id, 'clicked')
            return True
        
        return False
    
    def track_failure(self, notification_id: str, reason: str = "") -> bool:
        """Track notification failure"""
        query = """
        UPDATE notification_events
        SET 
            status = 'failed',
            metadata = jsonb_set(
                COALESCE(metadata, '{}'::jsonb),
                '{failure_reason}',
                %s::jsonb
            )
        WHERE notification_id = %s
        """
        
        result = self.db.execute(query, (json.dumps(reason), notification_id))
        
        if result.rowcount > 0:
            user_id = self.get_notification_user(notification_id)
            if user_id:
                self.update_user_metrics(user_id, 'failed')
            return True
        
        return False
    
    def get_notification_user(self, notification_id: str) -> Optional[str]:
        """Get user ID for notification"""
        query = """
        SELECT user_id FROM notification_events
        WHERE notification_id = %s
        """
        result = self.db.fetchone(query, (notification_id,))
        return result['user_id'] if result else None
    
    def update_user_metrics(self, user_id: str, event_type: str) -> None:
        """Update user notification metrics"""
        update_fields = []
        
        if event_type == 'sent':
            update_fields.append("total_sent = total_sent + 1")
            update_fields.append("last_sent = CURRENT_TIMESTAMP")
        elif event_type == 'delivered':
            update_fields.append("total_delivered = total_delivered + 1")
        elif event_type == 'opened':
            update_fields.append("total_opened = total_opened + 1")
            update_fields.append("last_opened = CURRENT_TIMESTAMP")
        elif event_type == 'clicked':
            update_fields.append("total_clicked = total_clicked + 1")
        elif event_type == 'failed':
            update_fields.append("total_failed = total_failed + 1")
        
        if update_fields:
            query = f"""
            INSERT INTO user_notification_metrics (user_id)
            VALUES (%s)
            ON CONFLICT (user_id)
            DO UPDATE SET
                {', '.join(update_fields)},
                updated_at = CURRENT_TIMESTAMP
            """
            self.db.execute(query, (user_id,))
    
    def set_preference(
        self,
        user_id: str,
        channel: str,
        category: str,
        enabled: bool,
        frequency: str = 'immediate'
    ) -> bool:
        """Set notification preference"""
        query = """
        INSERT INTO notification_preferences
        (user_id, channel, category, enabled, frequency)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, channel, category)
        DO UPDATE SET
            enabled = EXCLUDED.enabled,
            frequency = EXCLUDED.frequency,
            updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            self.db.execute(query, (user_id, channel, category, enabled, frequency))
            
            # Track opt-out
            if not enabled:
                self.track_opt_out(user_id)
            
            return True
        except Exception as e:
            print(f"Error setting preference: {e}")
            return False
    
    def set_quiet_hours(
        self,
        user_id: str,
        start_hour: Optional[int],
        end_hour: Optional[int]
    ) -> bool:
        """Set quiet hours for user"""
        query = """
        UPDATE notification_preferences
        SET 
            quiet_hours_start = %s,
            quiet_hours_end = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
        """
        
        result = self.db.execute(query, (start_hour, end_hour, user_id))
        
        if result.rowcount == 0:
            # Create default preference with quiet hours
            query = """
            INSERT INTO notification_preferences
            (user_id, channel, category, quiet_hours_start, quiet_hours_end)
            VALUES (%s, 'all', 'all', %s, %s)
            """
            self.db.execute(query, (user_id, start_hour, end_hour))
        
        return True
    
    def track_opt_out(self, user_id: str) -> None:
        """Track user opt-out"""
        query = """
        UPDATE user_notification_metrics
        SET opt_out_count = opt_out_count + 1
        WHERE user_id = %s
        """
        self.db.execute(query, (user_id,))
    
    def get_user_metrics(self, user_id: str) -> Dict:
        """Get notification metrics for user"""
        query = """
        SELECT 
            total_sent,
            total_delivered,
            total_opened,
            total_clicked,
            total_failed,
            CASE 
                WHEN total_sent > 0 
                THEN (total_opened::FLOAT / total_sent * 100)
                ELSE 0 
            END as open_rate,
            CASE 
                WHEN total_opened > 0 
                THEN (total_clicked::FLOAT / total_opened * 100)
                ELSE 0 
            END as click_rate,
            opt_out_count,
            last_sent,
            last_opened
        FROM user_notification_metrics
        WHERE user_id = %s
        """
        
        result = self.db.fetchone(query, (user_id,))
        return result if result else {
            'total_sent': 0,
            'total_opened': 0,
            'total_clicked': 0,
            'open_rate': 0,
            'click_rate': 0
        }
    
    def get_notification_history(
        self,
        user_id: str,
        days: int = 7,
        status: Optional[str] = None
    ) -> List[Dict]:
        """Get user's notification history"""
        where_conditions = ["user_id = %s"]
        params = [user_id]
        
        where_conditions.append("sent_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'")
        params.append(days)
        
        if status:
            where_conditions.append("status = %s")
            params.append(status)
        
        query = f"""
        SELECT 
            notification_id,
            type,
            category,
            subject,
            status,
            sent_at,
            opened_at,
            clicked_at,
            EXTRACT(EPOCH FROM (opened_at - sent_at))/60 as time_to_open_minutes
        FROM notification_events
        WHERE {' AND '.join(where_conditions)}
        ORDER BY sent_at DESC
        LIMIT 100
        """
        
        return self.db.fetchall(query, tuple(params))
    
    def calculate_daily_stats(self, date: Optional[datetime] = None) -> None:
        """Calculate daily notification statistics"""
        target_date = date or datetime.now().date()
        
        query = """
        INSERT INTO daily_notification_stats
        (date, type, category, total_sent, total_delivered, total_opened, 
         total_clicked, total_failed, avg_time_to_open)
        SELECT 
            DATE(sent_at) as date,
            type,
            category,
            COUNT(*) as total_sent,
            COUNT(CASE WHEN status IN ('delivered', 'opened', 'clicked') THEN 1 END) as total_delivered,
            COUNT(CASE WHEN status IN ('opened', 'clicked') THEN 1 END) as total_opened,
            COUNT(CASE WHEN status = 'clicked' THEN 1 END) as total_clicked,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as total_failed,
            AVG(EXTRACT(EPOCH FROM (opened_at - sent_at))/60)::INTEGER as avg_time_to_open
        FROM notification_events
        WHERE DATE(sent_at) = %s
        GROUP BY DATE(sent_at), type, category
        ON CONFLICT (date, type, category)
        DO UPDATE SET
            total_sent = EXCLUDED.total_sent,
            total_delivered = EXCLUDED.total_delivered,
            total_opened = EXCLUDED.total_opened,
            total_clicked = EXCLUDED.total_clicked,
            total_failed = EXCLUDED.total_failed,
            avg_time_to_open = EXCLUDED.avg_time_to_open
        """
        
        self.db.execute(query, (target_date,))
```

## API Endpoints

```python
from fastapi import APIRouter, Query, HTTPException, Body
from typing import List, Optional

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.post("/send")
async def send_notification(
    user_id: str = Body(...),
    type: str = Body(...),
    category: str = Body(...),
    subject: str = Body(...),
    metadata: Optional[Dict] = Body(None)
):
    """Send notification to user"""
    valid_types = ['email', 'push', 'in-app', 'sms']
    
    if type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of {valid_types}")
    
    tracker = NotificationTracker(db)
    result = tracker.send_notification(user_id, type, category, subject, metadata)
    
    return {
        "success": result.success,
        "notification_id": result.notification_id,
        "message": result.message
    }

@router.post("/track/{notification_id}/delivery")
async def track_delivery(notification_id: str):
    """Track notification delivery"""
    tracker = NotificationTracker(db)
    success = tracker.track_delivery(notification_id)
    return {"success": success}

@router.post("/track/{notification_id}/open")
async def track_open(notification_id: str):
    """Track notification open"""
    tracker = NotificationTracker(db)
    success = tracker.track_open(notification_id)
    return {"success": success}

@router.post("/track/{notification_id}/click")
async def track_click(notification_id: str):
    """Track notification click"""
    tracker = NotificationTracker(db)
    success = tracker.track_click(notification_id)
    return {"success": success}

@router.post("/track/{notification_id}/failure")
async def track_failure(
    notification_id: str,
    reason: str = Body("")
):
    """Track notification failure"""
    tracker = NotificationTracker(db)
    success = tracker.track_failure(notification_id, reason)
    return {"success": success}

@router.get("/user/{user_id}/metrics")
async def get_user_metrics(user_id: str):
    """Get notification metrics for user"""
    tracker = NotificationTracker(db)
    metrics = tracker.get_user_metrics(user_id)
    return metrics

@router.get("/user/{user_id}/history")
async def get_notification_history(
    user_id: str,
    days: int = Query(7, ge=1, le=30),
    status: Optional[str] = Query(None)
):
    """Get user's notification history"""
    tracker = NotificationTracker(db)
    history = tracker.get_notification_history(user_id, days, status)
    
    return {
        "user_id": user_id,
        "history": history,
        "count": len(history)
    }

@router.post("/preferences")
async def set_notification_preference(
    user_id: str = Body(...),
    channel: str = Body(...),
    category: str = Body(...),
    enabled: bool = Body(...),
    frequency: str = Body("immediate")
):
    """Set notification preference"""
    tracker = NotificationTracker(db)
    success = tracker.set_preference(user_id, channel, category, enabled, frequency)
    
    return {
        "success": success,
        "user_id": user_id,
        "preference": {
            "channel": channel,
            "category": category,
            "enabled": enabled,
            "frequency": frequency
        }
    }

@router.post("/preferences/quiet-hours")
async def set_quiet_hours(
    user_id: str = Body(...),
    start_hour: Optional[int] = Body(None),
    end_hour: Optional[int] = Body(None)
):
    """Set quiet hours for user"""
    if start_hour is not None and (start_hour < 0 or start_hour > 23):
        raise HTTPException(status_code=400, detail="Start hour must be between 0 and 23")
    
    if end_hour is not None and (end_hour < 0 or end_hour > 23):
        raise HTTPException(status_code=400, detail="End hour must be between 0 and 23")
    
    tracker = NotificationTracker(db)
    success = tracker.set_quiet_hours(user_id, start_hour, end_hour)
    
    return {
        "success": success,
        "user_id": user_id,
        "quiet_hours": {
            "start": start_hour,
            "end": end_hour
        }
    }

@router.get("/preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """Get notification preferences for user"""
    query = """
    SELECT 
        channel,
        category,
        enabled,
        frequency,
        quiet_hours_start,
        quiet_hours_end
    FROM notification_preferences
    WHERE user_id = %s
    ORDER BY channel, category
    """
    
    preferences = db.fetchall(query, (user_id,))
    
    return {
        "user_id": user_id,
        "preferences": preferences
    }

@router.get("/stats/daily")
async def get_daily_notification_stats(
    date: Optional[str] = Query(None),
    type: Optional[str] = Query(None)
):
    """Get daily notification statistics"""
    target_date = date or datetime.now().date().isoformat()
    
    where_conditions = ["date = %s"]
    params = [target_date]
    
    if type:
        where_conditions.append("type = %s")
        params.append(type)
    
    query = f"""
    SELECT 
        type,
        category,
        total_sent,
        total_delivered,
        total_opened,
        total_clicked,
        total_failed,
        avg_time_to_open,
        CASE 
            WHEN total_sent > 0 
            THEN (total_opened::FLOAT / total_sent * 100)
            ELSE 0 
        END as open_rate,
        CASE 
            WHEN total_opened > 0 
            THEN (total_clicked::FLOAT / total_opened * 100)
            ELSE 0 
        END as click_rate
    FROM daily_notification_stats
    WHERE {' AND '.join(where_conditions)}
    ORDER BY total_sent DESC
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
import { Bell, Mail, Smartphone, MessageSquare, X, Clock } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface NotificationMetrics {
  totalSent: number;
  totalOpened: number;
  totalClicked: number;
  openRate: number;
  clickRate: number;
  optOutCount: number;
}

interface NotificationHistory {
  notificationId: string;
  type: string;
  category: string;
  subject: string;
  status: string;
  sentAt: string;
  openedAt?: string;
  timeToOpenMinutes?: number;
}

interface NotificationPreference {
  channel: string;
  category: string;
  enabled: boolean;
  frequency: string;
  quietHoursStart?: number;
  quietHoursEnd?: number;
}

export const NotificationTrackingDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<NotificationMetrics | null>(null);
  const [history, setHistory] = useState<NotificationHistory[]>([]);
  const [preferences, setPreferences] = useState<NotificationPreference[]>([]);
  const [dailyStats, setDailyStats] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId] = useState('current-user');

  useEffect(() => {
    fetchNotificationData();
  }, []);

  const fetchNotificationData = async () => {
    try {
      const [metricsRes, historyRes, prefsRes, statsRes] = await Promise.all([
        fetch(`/api/notifications/user/${userId}/metrics`),
        fetch(`/api/notifications/user/${userId}/history?days=7`),
        fetch(`/api/notifications/preferences/${userId}`),
        fetch('/api/notifications/stats/daily')
      ]);

      const metricsData = await metricsRes.json();
      const historyData = await historyRes.json();
      const prefsData = await prefsRes.json();
      const statsData = await statsRes.json();

      setMetrics(metricsData);
      setHistory(historyData.history);
      setPreferences(prefsData.preferences);
      setDailyStats(statsData.stats);
    } catch (error) {
      console.error('Error fetching notification data:', error);
    } finally {
      setLoading(false);
    }
  };

  const updatePreference = async (channel: string, category: string, enabled: boolean) => {
    try {
      await fetch('/api/notifications/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          channel,
          category,
          enabled,
          frequency: 'immediate'
        })
      });
      
      fetchNotificationData();
    } catch (error) {
      console.error('Error updating preference:', error);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'email':
        return <Mail className="w-4 h-4" />;
      case 'push':
        return <Smartphone className="w-4 h-4" />;
      case 'in-app':
        return <Bell className="w-4 h-4" />;
      case 'sms':
        return <MessageSquare className="w-4 h-4" />;
      default:
        return <Bell className="w-4 h-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'sent':
        return 'text-gray-500';
      case 'delivered':
        return 'text-blue-500';
      case 'opened':
        return 'text-green-500';
      case 'clicked':
        return 'text-purple-500';
      case 'failed':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  if (loading) return <div>Loading notification data...</div>;

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Notification Tracking</h2>

      {/* Metrics Summary */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Total Sent</div>
            <div className="text-2xl font-bold">{metrics.totalSent}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Total Opened</div>
            <div className="text-2xl font-bold text-green-600">{metrics.totalOpened}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Total Clicked</div>
            <div className="text-2xl font-bold text-purple-600">{metrics.totalClicked}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Open Rate</div>
            <div className="text-2xl font-bold">{metrics.openRate.toFixed(1)}%</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Click Rate</div>
            <div className="text-2xl font-bold">{metrics.clickRate.toFixed(1)}%</div>
          </div>
        </div>
      )}

      {/* Notification Preferences */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Notification Preferences</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {['email', 'push', 'in-app', 'sms'].map(channel => (
            <div key={channel} className="border rounded p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  {getTypeIcon(channel)}
                  <span className="font-medium capitalize">{channel}</span>
                </div>
              </div>
              {['system', 'marketing', 'updates', 'alerts'].map(category => {
                const pref = preferences.find(
                  p => p.channel === channel && p.category === category
                );
                const enabled = pref ? pref.enabled : true;
                
                return (
                  <label key={category} className="flex items-center justify-between py-2">
                    <span className="text-sm capitalize">{category}</span>
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={(e) => updatePreference(channel, category, e.target.checked)}
                      className="rounded"
                    />
                  </label>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Recent Notifications */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Recent Notifications</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Type</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Subject</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Category</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Status</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Sent</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Time to Open</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {history.slice(0, 10).map((notification) => (
                <tr key={notification.notificationId} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <div className="flex items-center space-x-2">
                      {getTypeIcon(notification.type)}
                      <span className="text-sm">{notification.type}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-sm">{notification.subject}</td>
                  <td className="px-4 py-2 text-sm">{notification.category}</td>
                  <td className="px-4 py-2">
                    <span className={`text-sm capitalize ${getStatusColor(notification.status)}`}>
                      {notification.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {new Date(notification.sentAt).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {notification.timeToOpenMinutes
                      ? `${Math.round(notification.timeToOpenMinutes)} min`
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Daily Statistics */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Channel Performance</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium mb-2">Delivery by Channel</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={dailyStats}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="type" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="total_sent" fill="#3b82f6" />
                <Bar dataKey="total_opened" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div>
            <h4 className="text-sm font-medium mb-2">Open Rates</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={dailyStats}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="type" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="open_rate" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
```

## Implementation Priority
- **Phase 1**: Basic notification tracking
- **Phase 2**: Preference management
- **Phase 3**: Metrics and analytics
- **Phase 4**: Quiet hours and advanced preferences

## Performance Considerations
- Async notification sending
- Batch processing for metrics
- Daily aggregation for statistics
- Efficient preference checking

## Security Considerations
- No sensitive content in notifications table
- User permission validation
- Rate limiting on notification sending
- Preference privacy protection

## Monitoring and Alerts
- Alert on low open rates (<20%)
- Alert on high failure rates
- Daily notification performance report
- Weekly engagement summary

## Dependencies
- PostgreSQL with JSONB support
- FastAPI for REST endpoints
- UUID for notification IDs
- React with Recharts for visualization