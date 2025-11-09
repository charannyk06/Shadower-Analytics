# User Permission Tracking Specification

## Overview
Track user permissions and access patterns without complex RBAC systems. Focus on what users can access and what they actually use.

## TypeScript Interfaces

```typescript
// Permission assignment
interface UserPermission {
  user_id: string;
  permission_key: string;
  granted_at: Date;
  granted_by: string;
  expires_at?: Date;
  is_active: boolean;
}

// Permission usage event
interface PermissionUsage {
  user_id: string;
  permission_key: string;
  resource_type: string;
  resource_id: string;
  action: string;
  timestamp: Date;
  success: boolean;
}

// Daily permission summary
interface DailyPermissionSummary {
  date: string;
  permission_key: string;
  total_users: number;
  total_uses: number;
  success_rate: number;
  unique_resources: number;
}

// User access pattern
interface UserAccessPattern {
  user_id: string;
  most_used_permissions: string[];
  unused_permissions: string[];
  access_frequency: number;
  last_access: Date;
}
```

## SQL Schema

```sql
-- User permissions table
CREATE TABLE user_permissions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    permission_key VARCHAR(100) NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by VARCHAR(255),
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(user_id, permission_key)
);

-- Permission usage tracking
CREATE TABLE permission_usage (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    permission_key VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    action VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT true
);

-- Daily permission aggregates
CREATE TABLE daily_permission_summary (
    date DATE NOT NULL,
    permission_key VARCHAR(100) NOT NULL,
    total_users INTEGER DEFAULT 0,
    total_uses INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    unique_resources INTEGER DEFAULT 0,
    PRIMARY KEY (date, permission_key)
);

-- User access patterns
CREATE TABLE user_access_patterns (
    user_id VARCHAR(255) PRIMARY KEY,
    most_used_permissions TEXT[],
    unused_permissions TEXT[],
    access_frequency INTEGER DEFAULT 0,
    last_access TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Basic indexes
CREATE INDEX idx_permissions_user ON user_permissions(user_id);
CREATE INDEX idx_usage_user_date ON permission_usage(user_id, timestamp DESC);
CREATE INDEX idx_usage_permission ON permission_usage(permission_key);
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from collections import Counter

@dataclass
class PermissionMetrics:
    """Simple permission usage metrics"""
    permission_key: str
    usage_count: int
    user_count: int
    success_rate: float
    most_common_resources: List[str]

class PermissionTracker:
    """Simple permission tracking without complex RBAC"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def grant_permission(self, user_id: str, permission_key: str, 
                        granted_by: str, expires_at: Optional[datetime] = None) -> bool:
        """Grant permission to user"""
        query = """
        INSERT INTO user_permissions 
        (user_id, permission_key, granted_by, expires_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, permission_key)
        DO UPDATE SET 
            is_active = true,
            granted_at = CURRENT_TIMESTAMP,
            granted_by = EXCLUDED.granted_by,
            expires_at = EXCLUDED.expires_at
        """
        
        try:
            self.db.execute(query, (user_id, permission_key, granted_by, expires_at))
            return True
        except Exception as e:
            print(f"Error granting permission: {e}")
            return False
    
    def revoke_permission(self, user_id: str, permission_key: str) -> bool:
        """Revoke permission from user"""
        query = """
        UPDATE user_permissions
        SET is_active = false
        WHERE user_id = %s AND permission_key = %s
        """
        
        try:
            self.db.execute(query, (user_id, permission_key))
            return True
        except Exception as e:
            print(f"Error revoking permission: {e}")
            return False
    
    def track_usage(self, user_id: str, permission_key: str, 
                   resource_type: str, resource_id: str, 
                   action: str, success: bool = True) -> None:
        """Track permission usage"""
        query = """
        INSERT INTO permission_usage
        (user_id, permission_key, resource_type, resource_id, action, success)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        self.db.execute(query, (
            user_id, permission_key, resource_type, 
            resource_id, action, success
        ))
        
        # Update user access pattern
        self.update_access_pattern(user_id)
    
    def check_permission(self, user_id: str, permission_key: str) -> bool:
        """Check if user has active permission"""
        query = """
        SELECT is_active
        FROM user_permissions
        WHERE user_id = %s 
        AND permission_key = %s
        AND is_active = true
        AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        """
        
        result = self.db.fetchone(query, (user_id, permission_key))
        return bool(result) if result else False
    
    def get_user_permissions(self, user_id: str) -> List[Dict]:
        """Get all permissions for a user"""
        query = """
        SELECT 
            permission_key,
            granted_at,
            granted_by,
            expires_at,
            is_active
        FROM user_permissions
        WHERE user_id = %s
        ORDER BY granted_at DESC
        """
        
        return self.db.fetchall(query, (user_id,))
    
    def update_access_pattern(self, user_id: str) -> None:
        """Update user access pattern"""
        # Get most used permissions
        most_used_query = """
        SELECT permission_key, COUNT(*) as usage_count
        FROM permission_usage
        WHERE user_id = %s
        AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
        GROUP BY permission_key
        ORDER BY usage_count DESC
        LIMIT 5
        """
        
        most_used = self.db.fetchall(most_used_query, (user_id,))
        most_used_perms = [row['permission_key'] for row in most_used]
        
        # Get unused permissions
        unused_query = """
        SELECT p.permission_key
        FROM user_permissions p
        LEFT JOIN permission_usage u 
            ON p.user_id = u.user_id 
            AND p.permission_key = u.permission_key
            AND u.timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
        WHERE p.user_id = %s
        AND p.is_active = true
        AND u.id IS NULL
        """
        
        unused = self.db.fetchall(unused_query, (user_id,))
        unused_perms = [row['permission_key'] for row in unused]
        
        # Update pattern
        update_query = """
        INSERT INTO user_access_patterns 
        (user_id, most_used_permissions, unused_permissions, access_frequency, last_access)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id)
        DO UPDATE SET
            most_used_permissions = EXCLUDED.most_used_permissions,
            unused_permissions = EXCLUDED.unused_permissions,
            access_frequency = user_access_patterns.access_frequency + 1,
            last_access = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        """
        
        self.db.execute(update_query, (
            user_id, most_used_perms, unused_perms, 1
        ))
    
    def calculate_daily_summary(self, date: Optional[datetime] = None) -> None:
        """Calculate daily permission usage summary"""
        target_date = date or datetime.now().date()
        
        query = """
        INSERT INTO daily_permission_summary 
        (date, permission_key, total_users, total_uses, success_count, 
         failure_count, unique_resources)
        SELECT 
            %s as date,
            permission_key,
            COUNT(DISTINCT user_id) as total_users,
            COUNT(*) as total_uses,
            COUNT(CASE WHEN success THEN 1 END) as success_count,
            COUNT(CASE WHEN NOT success THEN 1 END) as failure_count,
            COUNT(DISTINCT resource_id) as unique_resources
        FROM permission_usage
        WHERE DATE(timestamp) = %s
        GROUP BY permission_key
        ON CONFLICT (date, permission_key)
        DO UPDATE SET
            total_users = EXCLUDED.total_users,
            total_uses = EXCLUDED.total_uses,
            success_count = EXCLUDED.success_count,
            failure_count = EXCLUDED.failure_count,
            unique_resources = EXCLUDED.unique_resources
        """
        
        self.db.execute(query, (target_date, target_date))
    
    def get_permission_analytics(self, permission_key: str, days: int = 30) -> Dict:
        """Get analytics for specific permission"""
        query = """
        WITH usage_stats AS (
            SELECT 
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(*) as total_uses,
                AVG(CASE WHEN success THEN 100.0 ELSE 0.0 END) as success_rate,
                COUNT(DISTINCT resource_id) as unique_resources
            FROM permission_usage
            WHERE permission_key = %s
            AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        ),
        top_users AS (
            SELECT user_id, COUNT(*) as usage_count
            FROM permission_usage
            WHERE permission_key = %s
            AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            GROUP BY user_id
            ORDER BY usage_count DESC
            LIMIT 10
        )
        SELECT 
            us.unique_users,
            us.total_uses,
            us.success_rate,
            us.unique_resources,
            ARRAY_AGG(tu.user_id) as top_users
        FROM usage_stats us, top_users tu
        GROUP BY us.unique_users, us.total_uses, 
                 us.success_rate, us.unique_resources
        """
        
        return self.db.fetchone(query, (permission_key, days, permission_key, days))
    
    def find_overprivileged_users(self, threshold_days: int = 30) -> List[Dict]:
        """Find users with unused permissions"""
        query = """
        SELECT 
            user_id,
            COUNT(*) as total_permissions,
            ARRAY_LENGTH(unused_permissions, 1) as unused_count,
            unused_permissions,
            last_access
        FROM user_access_patterns
        WHERE ARRAY_LENGTH(unused_permissions, 1) > 0
        AND last_access < CURRENT_TIMESTAMP - INTERVAL '%s days'
        ORDER BY unused_count DESC
        LIMIT 50
        """
        
        return self.db.fetchall(query, (threshold_days,))
    
    def get_permission_usage_trend(self, permission_key: str, days: int = 30) -> List[Dict]:
        """Get usage trend for permission"""
        query = """
        SELECT 
            date,
            total_users,
            total_uses,
            CASE 
                WHEN (success_count + failure_count) > 0
                THEN success_count::FLOAT / (success_count + failure_count) * 100
                ELSE 100 
            END as success_rate
        FROM daily_permission_summary
        WHERE permission_key = %s
        AND date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY date DESC
        """
        
        return self.db.fetchall(query, (permission_key, days))
```

## API Endpoints

```python
from fastapi import APIRouter, Query, HTTPException, Body
from datetime import datetime, date
from typing import List, Optional

router = APIRouter(prefix="/api/permissions", tags=["permissions"])

@router.post("/grant")
async def grant_permission(
    user_id: str = Body(...),
    permission_key: str = Body(...),
    granted_by: str = Body(...),
    expires_at: Optional[datetime] = Body(None)
):
    """Grant permission to user"""
    tracker = PermissionTracker(db)
    success = tracker.grant_permission(user_id, permission_key, granted_by, expires_at)
    return {
        "success": success,
        "user_id": user_id,
        "permission": permission_key
    }

@router.post("/revoke")
async def revoke_permission(
    user_id: str = Body(...),
    permission_key: str = Body(...)
):
    """Revoke permission from user"""
    tracker = PermissionTracker(db)
    success = tracker.revoke_permission(user_id, permission_key)
    return {
        "success": success,
        "user_id": user_id,
        "permission": permission_key
    }

@router.post("/track-usage")
async def track_permission_usage(
    user_id: str = Body(...),
    permission_key: str = Body(...),
    resource_type: str = Body(...),
    resource_id: str = Body(...),
    action: str = Body(...),
    success: bool = Body(True)
):
    """Track permission usage"""
    tracker = PermissionTracker(db)
    
    # Check permission first
    has_permission = tracker.check_permission(user_id, permission_key)
    
    # Track usage
    tracker.track_usage(
        user_id, permission_key, resource_type,
        resource_id, action, success and has_permission
    )
    
    return {
        "tracked": True,
        "has_permission": has_permission
    }

@router.get("/check/{user_id}/{permission_key}")
async def check_permission(user_id: str, permission_key: str):
    """Check if user has permission"""
    tracker = PermissionTracker(db)
    has_permission = tracker.check_permission(user_id, permission_key)
    return {
        "user_id": user_id,
        "permission": permission_key,
        "has_permission": has_permission
    }

@router.get("/user/{user_id}")
async def get_user_permissions(user_id: str):
    """Get all permissions for user"""
    tracker = PermissionTracker(db)
    permissions = tracker.get_user_permissions(user_id)
    return {
        "user_id": user_id,
        "permissions": permissions,
        "count": len(permissions)
    }

@router.get("/analytics/{permission_key}")
async def get_permission_analytics(
    permission_key: str,
    days: int = Query(30, ge=1, le=90)
):
    """Get analytics for permission"""
    tracker = PermissionTracker(db)
    analytics = tracker.get_permission_analytics(permission_key, days)
    return analytics

@router.get("/overprivileged")
async def get_overprivileged_users(
    threshold_days: int = Query(30, ge=7, le=90)
):
    """Find users with unused permissions"""
    tracker = PermissionTracker(db)
    users = tracker.find_overprivileged_users(threshold_days)
    return {
        "users": users,
        "count": len(users),
        "threshold_days": threshold_days
    }

@router.get("/usage-trend/{permission_key}")
async def get_permission_usage_trend(
    permission_key: str,
    days: int = Query(30, ge=7, le=90)
):
    """Get usage trend for permission"""
    tracker = PermissionTracker(db)
    trend = tracker.get_permission_usage_trend(permission_key, days)
    return {
        "permission": permission_key,
        "trend": trend,
        "days": days
    }

@router.post("/calculate-daily")
async def calculate_daily_summary(
    date: Optional[date] = Body(None)
):
    """Calculate daily permission summary"""
    tracker = PermissionTracker(db)
    tracker.calculate_daily_summary(date)
    return {"status": "calculated", "date": str(date or datetime.now().date())}
```

## React Dashboard Component

```tsx
import React, { useState, useEffect } from 'react';
import { Line, Bar, Pie } from 'recharts';

interface Permission {
  permissionKey: string;
  grantedAt: string;
  grantedBy: string;
  expiresAt?: string;
  isActive: boolean;
}

interface OverprivilegedUser {
  userId: string;
  totalPermissions: number;
  unusedCount: number;
  unusedPermissions: string[];
  lastAccess: string;
}

interface PermissionAnalytics {
  uniqueUsers: number;
  totalUses: number;
  successRate: number;
  uniqueResources: number;
  topUsers: string[];
}

export const PermissionDashboard: React.FC = () => {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [overprivileged, setOverprivileged] = useState<OverprivilegedUser[]>([]);
  const [selectedPermission, setSelectedPermission] = useState<string>('');
  const [analytics, setAnalytics] = useState<PermissionAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPermissionData();
  }, []);

  const fetchPermissionData = async () => {
    try {
      const [overprivRes] = await Promise.all([
        fetch('/api/permissions/overprivileged?threshold_days=30')
      ]);

      const overpriv = await overprivRes.json();
      setOverprivileged(overpriv.users);
    } catch (error) {
      console.error('Error fetching permission data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchPermissionAnalytics = async (permissionKey: string) => {
    try {
      const res = await fetch(`/api/permissions/analytics/${permissionKey}?days=30`);
      const data = await res.json();
      setAnalytics(data);
    } catch (error) {
      console.error('Error fetching permission analytics:', error);
    }
  };

  const handleGrantPermission = async (userId: string, permissionKey: string) => {
    try {
      const res = await fetch('/api/permissions/grant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          permission_key: permissionKey,
          granted_by: 'admin'
        })
      });
      const data = await res.json();
      if (data.success) {
        fetchPermissionData();
      }
    } catch (error) {
      console.error('Error granting permission:', error);
    }
  };

  const handleRevokePermission = async (userId: string, permissionKey: string) => {
    try {
      const res = await fetch('/api/permissions/revoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          permission_key: permissionKey
        })
      });
      const data = await res.json();
      if (data.success) {
        fetchPermissionData();
      }
    } catch (error) {
      console.error('Error revoking permission:', error);
    }
  };

  if (loading) return <div>Loading permission data...</div>;

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Permission Tracking</h2>

      {/* Permission Analytics Summary */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Unique Users</div>
            <div className="text-2xl font-bold">{analytics.uniqueUsers}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Total Uses</div>
            <div className="text-2xl font-bold">{analytics.totalUses}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Success Rate</div>
            <div className="text-2xl font-bold">
              {analytics.successRate.toFixed(1)}%
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Unique Resources</div>
            <div className="text-2xl font-bold">{analytics.uniqueResources}</div>
          </div>
        </div>
      )}

      {/* Permission Search */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Permission Analytics</h3>
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="Enter permission key..."
            className="flex-1 p-2 border rounded"
            value={selectedPermission}
            onChange={(e) => setSelectedPermission(e.target.value)}
          />
          <button
            onClick={() => fetchPermissionAnalytics(selectedPermission)}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Analyze
          </button>
        </div>
      </div>

      {/* Overprivileged Users */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Overprivileged Users</h3>
        <div className="text-sm text-gray-600 mb-2">
          Users with unused permissions in the last 30 days
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  User ID
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Total Permissions
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Unused
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Last Access
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Unused Permissions
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {overprivileged.slice(0, 10).map((user) => (
                <tr key={user.userId} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm">{user.userId}</td>
                  <td className="px-4 py-2 text-sm">{user.totalPermissions}</td>
                  <td className="px-4 py-2 text-sm">
                    <span className="text-yellow-600 font-semibold">
                      {user.unusedCount}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {new Date(user.lastAccess).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <div className="max-w-xs truncate">
                      {user.unusedPermissions.join(', ')}
                    </div>
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <button
                      onClick={() => {
                        // Revoke unused permissions
                        user.unusedPermissions.forEach(perm => 
                          handleRevokePermission(user.userId, perm)
                        );
                      }}
                      className="text-red-600 hover:text-red-800"
                    >
                      Revoke Unused
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Permission Usage Trend */}
      <PermissionUsageTrend permission={selectedPermission} />

      {/* Quick Actions */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={() => fetch('/api/permissions/calculate-daily', { method: 'POST' })}
            className="p-3 bg-gray-100 rounded hover:bg-gray-200"
          >
            Calculate Daily Summary
          </button>
          <button
            onClick={fetchPermissionData}
            className="p-3 bg-gray-100 rounded hover:bg-gray-200"
          >
            Refresh Data
          </button>
        </div>
      </div>
    </div>
  );
};

const PermissionUsageTrend: React.FC<{ permission: string }> = ({ permission }) => {
  const [trend, setTrend] = useState<any[]>([]);

  useEffect(() => {
    if (permission) {
      fetch(`/api/permissions/usage-trend/${permission}?days=30`)
        .then(res => res.json())
        .then(data => setTrend(data.trend))
        .catch(console.error);
    }
  }, [permission]);

  if (!permission || trend.length === 0) return null;

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">
        Usage Trend: {permission}
      </h3>
      <div className="h-64">
        <Line
          data={trend}
          xKey="date"
          yKey="total_uses"
          stroke="#3b82f6"
          strokeWidth={2}
        />
      </div>
    </div>
  );
};
```

## Implementation Priority
- **Phase 1**: Basic permission tracking and checking
- **Phase 2**: Usage tracking and patterns
- **Phase 3**: Overprivilege detection
- **Phase 4**: Automated permission cleanup

## Performance Considerations
- Simple permission checks with minimal joins
- Daily batch processing for analytics
- Cached permission lookups for frequent checks
- Limited permission history (90 days)

## Security Considerations
- Permission checks at API gateway level
- Audit trail for all permission changes
- No sensitive data in usage logs
- Rate limiting on permission checks

## Monitoring and Alerts
- Alert on excessive permission failures
- Daily report of overprivileged users
- Weekly permission usage summary
- Monthly permission audit report

## Dependencies
- PostgreSQL for data storage
- FastAPI for REST endpoints
- React with Recharts for visualization
- Daily cron job for analytics