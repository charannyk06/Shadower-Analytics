# User Device Tracking Specification

## Overview
Simple device tracking for users without complex fingerprinting or device management systems. Track what devices users use to access the system.

## TypeScript Interfaces

```typescript
// User device
interface UserDevice {
  device_id: string;
  user_id: string;
  device_type: 'desktop' | 'mobile' | 'tablet' | 'other';
  browser: string;
  browser_version: string;
  os: string;
  os_version: string;
  screen_resolution: string;
  first_seen: Date;
  last_seen: Date;
  session_count: number;
  is_active: boolean;
}

// Device session
interface DeviceSession {
  session_id: string;
  device_id: string;
  user_id: string;
  ip_address: string;
  user_agent: string;
  start_time: Date;
  end_time?: Date;
  page_views: number;
}

// Device usage summary
interface DeviceUsageSummary {
  user_id: string;
  total_devices: number;
  primary_device_type: string;
  primary_browser: string;
  mobile_usage_percent: number;
  desktop_usage_percent: number;
}

// Browser statistics
interface BrowserStats {
  browser: string;
  user_count: number;
  session_count: number;
  avg_session_duration: number;
  market_share: number;
}
```

## SQL Schema

```sql
-- User devices table
CREATE TABLE user_devices (
    device_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    device_type VARCHAR(20) NOT NULL,
    browser VARCHAR(50),
    browser_version VARCHAR(20),
    os VARCHAR(50),
    os_version VARCHAR(20),
    screen_resolution VARCHAR(20),
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_count INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true
);

-- Device sessions
CREATE TABLE device_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    device_id VARCHAR(255) REFERENCES user_devices(device_id),
    user_id VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    page_views INTEGER DEFAULT 0
);

-- Daily device statistics
CREATE TABLE daily_device_stats (
    date DATE NOT NULL,
    device_type VARCHAR(20) NOT NULL,
    browser VARCHAR(50),
    total_users INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    avg_session_duration INTEGER DEFAULT 0,
    PRIMARY KEY (date, device_type, browser)
);

-- User device summary
CREATE TABLE user_device_summary (
    user_id VARCHAR(255) PRIMARY KEY,
    total_devices INTEGER DEFAULT 0,
    primary_device_type VARCHAR(20),
    primary_browser VARCHAR(50),
    mobile_sessions INTEGER DEFAULT 0,
    desktop_sessions INTEGER DEFAULT 0,
    tablet_sessions INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Basic indexes
CREATE INDEX idx_devices_user ON user_devices(user_id);
CREATE INDEX idx_devices_last_seen ON user_devices(last_seen DESC);
CREATE INDEX idx_sessions_device ON device_sessions(device_id);
CREATE INDEX idx_sessions_user_time ON device_sessions(user_id, start_time DESC);
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
import re
from user_agents import parse

@dataclass
class DeviceInfo:
    """Device information extracted from user agent"""
    device_type: str
    browser: str
    browser_version: str
    os: str
    os_version: str
    is_mobile: bool
    is_tablet: bool
    is_pc: bool

class DeviceTracker:
    """Simple device tracking"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def generate_device_id(self, user_id: str, user_agent: str, ip: str) -> str:
        """Generate consistent device ID"""
        # Simple hash of user + user agent for device identification
        device_string = f"{user_id}:{user_agent}:{ip[:ip.rfind('.')]}"
        return hashlib.md5(device_string.encode()).hexdigest()
    
    def parse_user_agent(self, user_agent_string: str) -> DeviceInfo:
        """Parse user agent to get device info"""
        ua = parse(user_agent_string)
        
        # Determine device type
        if ua.is_mobile:
            device_type = 'mobile'
        elif ua.is_tablet:
            device_type = 'tablet'
        elif ua.is_pc:
            device_type = 'desktop'
        else:
            device_type = 'other'
        
        return DeviceInfo(
            device_type=device_type,
            browser=ua.browser.family,
            browser_version=ua.browser.version_string,
            os=ua.os.family,
            os_version=ua.os.version_string,
            is_mobile=ua.is_mobile,
            is_tablet=ua.is_tablet,
            is_pc=ua.is_pc
        )
    
    def track_device(
        self,
        user_id: str,
        user_agent: str,
        ip_address: str,
        screen_resolution: Optional[str] = None
    ) -> Tuple[str, str]:
        """Track user device and create session"""
        device_id = self.generate_device_id(user_id, user_agent, ip_address)
        device_info = self.parse_user_agent(user_agent)
        
        # Check if device exists
        existing = self.get_device(device_id)
        
        if not existing:
            # Create new device
            query = """
            INSERT INTO user_devices
            (device_id, user_id, device_type, browser, browser_version, 
             os, os_version, screen_resolution)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            self.db.execute(query, (
                device_id, user_id, device_info.device_type,
                device_info.browser, device_info.browser_version,
                device_info.os, device_info.os_version,
                screen_resolution
            ))
        else:
            # Update existing device
            query = """
            UPDATE user_devices
            SET 
                last_seen = CURRENT_TIMESTAMP,
                session_count = session_count + 1,
                is_active = true
            WHERE device_id = %s
            """
            self.db.execute(query, (device_id,))
        
        # Create session
        session_id = self.create_session(device_id, user_id, ip_address, user_agent)
        
        # Update user summary
        self.update_user_summary(user_id)
        
        return device_id, session_id
    
    def create_session(
        self,
        device_id: str,
        user_id: str,
        ip_address: str,
        user_agent: str
    ) -> str:
        """Create new device session"""
        import uuid
        session_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO device_sessions
        (session_id, device_id, user_id, ip_address, user_agent)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING session_id
        """
        
        result = self.db.fetchone(query, (
            session_id, device_id, user_id, ip_address, user_agent
        ))
        
        return result['session_id']
    
    def end_session(self, session_id: str) -> None:
        """End device session"""
        query = """
        UPDATE device_sessions
        SET end_time = CURRENT_TIMESTAMP
        WHERE session_id = %s AND end_time IS NULL
        """
        self.db.execute(query, (session_id,))
    
    def track_page_view(self, session_id: str) -> None:
        """Track page view in session"""
        query = """
        UPDATE device_sessions
        SET page_views = page_views + 1
        WHERE session_id = %s
        """
        self.db.execute(query, (session_id,))
    
    def get_device(self, device_id: str) -> Optional[Dict]:
        """Get device information"""
        query = """
        SELECT * FROM user_devices
        WHERE device_id = %s
        """
        return self.db.fetchone(query, (device_id,))
    
    def get_user_devices(self, user_id: str) -> List[Dict]:
        """Get all devices for user"""
        query = """
        SELECT 
            device_id,
            device_type,
            browser,
            browser_version,
            os,
            os_version,
            screen_resolution,
            first_seen,
            last_seen,
            session_count,
            is_active
        FROM user_devices
        WHERE user_id = %s
        ORDER BY last_seen DESC
        """
        return self.db.fetchall(query, (user_id,))
    
    def update_user_summary(self, user_id: str) -> None:
        """Update user device summary"""
        query = """
        WITH device_stats AS (
            SELECT 
                COUNT(DISTINCT d.device_id) as total_devices,
                MODE() WITHIN GROUP (ORDER BY d.device_type) as primary_device_type,
                MODE() WITHIN GROUP (ORDER BY d.browser) as primary_browser,
                COUNT(CASE WHEN d.device_type = 'mobile' THEN 1 END) as mobile_sessions,
                COUNT(CASE WHEN d.device_type = 'desktop' THEN 1 END) as desktop_sessions,
                COUNT(CASE WHEN d.device_type = 'tablet' THEN 1 END) as tablet_sessions
            FROM user_devices d
            JOIN device_sessions s ON d.device_id = s.device_id
            WHERE d.user_id = %s
        )
        INSERT INTO user_device_summary
        (user_id, total_devices, primary_device_type, primary_browser, 
         mobile_sessions, desktop_sessions, tablet_sessions)
        SELECT %s, total_devices, primary_device_type, primary_browser,
               mobile_sessions, desktop_sessions, tablet_sessions
        FROM device_stats
        ON CONFLICT (user_id)
        DO UPDATE SET
            total_devices = EXCLUDED.total_devices,
            primary_device_type = EXCLUDED.primary_device_type,
            primary_browser = EXCLUDED.primary_browser,
            mobile_sessions = EXCLUDED.mobile_sessions,
            desktop_sessions = EXCLUDED.desktop_sessions,
            tablet_sessions = EXCLUDED.tablet_sessions,
            updated_at = CURRENT_TIMESTAMP
        """
        
        self.db.execute(query, (user_id, user_id))
    
    def get_device_statistics(self, days: int = 30) -> Dict:
        """Get device usage statistics"""
        query = """
        WITH stats AS (
            SELECT 
                d.device_type,
                d.browser,
                COUNT(DISTINCT d.user_id) as user_count,
                COUNT(DISTINCT s.session_id) as session_count,
                AVG(EXTRACT(EPOCH FROM (s.end_time - s.start_time))/60)::INTEGER as avg_duration_minutes
            FROM user_devices d
            JOIN device_sessions s ON d.device_id = s.device_id
            WHERE s.start_time >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            GROUP BY d.device_type, d.browser
        )
        SELECT 
            device_type,
            browser,
            user_count,
            session_count,
            avg_duration_minutes,
            (user_count::FLOAT / SUM(user_count) OVER () * 100) as market_share
        FROM stats
        ORDER BY user_count DESC
        """
        
        results = self.db.fetchall(query, (days,))
        
        # Group by device type
        device_stats = {}
        browser_stats = {}
        
        for row in results:
            device_type = row['device_type']
            browser = row['browser']
            
            if device_type not in device_stats:
                device_stats[device_type] = {
                    'user_count': 0,
                    'session_count': 0,
                    'market_share': 0
                }
            
            device_stats[device_type]['user_count'] += row['user_count']
            device_stats[device_type]['session_count'] += row['session_count']
            device_stats[device_type]['market_share'] += row['market_share']
            
            if browser not in browser_stats:
                browser_stats[browser] = {
                    'user_count': 0,
                    'session_count': 0,
                    'avg_duration': row['avg_duration_minutes']
                }
            
            browser_stats[browser]['user_count'] += row['user_count']
            browser_stats[browser]['session_count'] += row['session_count']
        
        return {
            'device_types': device_stats,
            'browsers': browser_stats
        }
    
    def detect_suspicious_devices(self, user_id: str) -> List[Dict]:
        """Detect suspicious device patterns"""
        query = """
        WITH device_patterns AS (
            SELECT 
                d.device_id,
                d.device_type,
                d.browser,
                COUNT(DISTINCT s.ip_address) as ip_count,
                COUNT(s.session_id) as session_count,
                MAX(s.start_time) as last_activity,
                ARRAY_AGG(DISTINCT s.ip_address) as ip_addresses
            FROM user_devices d
            JOIN device_sessions s ON d.device_id = s.device_id
            WHERE d.user_id = %s
            AND s.start_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
            GROUP BY d.device_id, d.device_type, d.browser
        )
        SELECT *
        FROM device_patterns
        WHERE ip_count > 3  -- Multiple IPs from same device
        OR session_count > 100  -- Excessive sessions
        ORDER BY ip_count DESC, session_count DESC
        """
        
        return self.db.fetchall(query, (user_id,))
    
    def calculate_daily_stats(self, date: Optional[datetime] = None) -> None:
        """Calculate daily device statistics"""
        target_date = date or datetime.now().date()
        
        query = """
        INSERT INTO daily_device_stats
        (date, device_type, browser, total_users, total_sessions, avg_session_duration)
        SELECT 
            %s as date,
            d.device_type,
            d.browser,
            COUNT(DISTINCT d.user_id) as total_users,
            COUNT(DISTINCT s.session_id) as total_sessions,
            AVG(EXTRACT(EPOCH FROM (s.end_time - s.start_time)))::INTEGER as avg_duration
        FROM user_devices d
        JOIN device_sessions s ON d.device_id = s.device_id
        WHERE DATE(s.start_time) = %s
        GROUP BY d.device_type, d.browser
        ON CONFLICT (date, device_type, browser)
        DO UPDATE SET
            total_users = EXCLUDED.total_users,
            total_sessions = EXCLUDED.total_sessions,
            avg_session_duration = EXCLUDED.avg_session_duration
        """
        
        self.db.execute(query, (target_date, target_date))
    
    def cleanup_inactive_devices(self, days_inactive: int = 90) -> int:
        """Mark devices as inactive after period of no use"""
        query = """
        UPDATE user_devices
        SET is_active = false
        WHERE last_seen < CURRENT_TIMESTAMP - INTERVAL '%s days'
        AND is_active = true
        """
        
        result = self.db.execute(query, (days_inactive,))
        return result.rowcount if hasattr(result, 'rowcount') else 0
```

## API Endpoints

```python
from fastapi import APIRouter, Query, HTTPException, Header
from typing import List, Optional

router = APIRouter(prefix="/api/devices", tags=["devices"])

@router.post("/track")
async def track_device(
    user_id: str,
    user_agent: str = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    screen_resolution: Optional[str] = None
):
    """Track user device and create session"""
    if not user_agent:
        raise HTTPException(status_code=400, detail="User-Agent header required")
    
    # Get IP address
    ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else "0.0.0.0"
    
    tracker = DeviceTracker(db)
    device_id, session_id = tracker.track_device(
        user_id, user_agent, ip_address, screen_resolution
    )
    
    return {
        "device_id": device_id,
        "session_id": session_id
    }

@router.post("/session/{session_id}/end")
async def end_session(session_id: str):
    """End device session"""
    tracker = DeviceTracker(db)
    tracker.end_session(session_id)
    return {"status": "session_ended"}

@router.post("/session/{session_id}/page-view")
async def track_page_view(session_id: str):
    """Track page view in session"""
    tracker = DeviceTracker(db)
    tracker.track_page_view(session_id)
    return {"status": "page_view_tracked"}

@router.get("/user/{user_id}")
async def get_user_devices(user_id: str):
    """Get all devices for user"""
    tracker = DeviceTracker(db)
    devices = tracker.get_user_devices(user_id)
    
    return {
        "user_id": user_id,
        "devices": devices,
        "count": len(devices)
    }

@router.get("/user/{user_id}/summary")
async def get_user_device_summary(user_id: str):
    """Get user device usage summary"""
    query = """
    SELECT 
        user_id,
        total_devices,
        primary_device_type,
        primary_browser,
        mobile_sessions,
        desktop_sessions,
        tablet_sessions,
        CASE 
            WHEN (mobile_sessions + desktop_sessions + tablet_sessions) > 0
            THEN (mobile_sessions::FLOAT / (mobile_sessions + desktop_sessions + tablet_sessions) * 100)
            ELSE 0 
        END as mobile_usage_percent,
        CASE 
            WHEN (mobile_sessions + desktop_sessions + tablet_sessions) > 0
            THEN (desktop_sessions::FLOAT / (mobile_sessions + desktop_sessions + tablet_sessions) * 100)
            ELSE 0 
        END as desktop_usage_percent
    FROM user_device_summary
    WHERE user_id = %s
    """
    
    result = db.fetchone(query, (user_id,))
    
    if not result:
        raise HTTPException(status_code=404, detail="No device data for user")
    
    return result

@router.get("/statistics")
async def get_device_statistics(
    days: int = Query(30, ge=1, le=90)
):
    """Get overall device statistics"""
    tracker = DeviceTracker(db)
    stats = tracker.get_device_statistics(days)
    return stats

@router.get("/user/{user_id}/suspicious")
async def get_suspicious_devices(user_id: str):
    """Get suspicious device activity for user"""
    tracker = DeviceTracker(db)
    suspicious = tracker.detect_suspicious_devices(user_id)
    
    return {
        "user_id": user_id,
        "suspicious_devices": suspicious,
        "count": len(suspicious)
    }

@router.get("/browser-stats")
async def get_browser_statistics():
    """Get browser usage statistics"""
    query = """
    SELECT 
        browser,
        COUNT(DISTINCT user_id) as user_count,
        COUNT(*) as device_count,
        AVG(session_count) as avg_sessions_per_device,
        MAX(last_seen) as last_activity
    FROM user_devices
    WHERE is_active = true
    GROUP BY browser
    ORDER BY user_count DESC
    LIMIT 20
    """
    
    results = db.fetchall(query)
    
    # Calculate market share
    total_users = sum(r['user_count'] for r in results)
    for r in results:
        r['market_share'] = round(r['user_count'] / total_users * 100, 2)
    
    return {"browsers": results}

@router.get("/os-stats")
async def get_os_statistics():
    """Get operating system statistics"""
    query = """
    SELECT 
        os,
        os_version,
        COUNT(DISTINCT user_id) as user_count,
        COUNT(*) as device_count,
        device_type
    FROM user_devices
    WHERE is_active = true
    GROUP BY os, os_version, device_type
    ORDER BY user_count DESC
    LIMIT 30
    """
    
    results = db.fetchall(query)
    
    # Group by OS
    os_stats = {}
    for r in results:
        os = r['os']
        if os not in os_stats:
            os_stats[os] = {
                'user_count': 0,
                'device_count': 0,
                'versions': [],
                'device_types': {}
            }
        
        os_stats[os]['user_count'] += r['user_count']
        os_stats[os]['device_count'] += r['device_count']
        os_stats[os]['versions'].append(r['os_version'])
        
        if r['device_type'] not in os_stats[os]['device_types']:
            os_stats[os]['device_types'][r['device_type']] = 0
        os_stats[os]['device_types'][r['device_type']] += r['user_count']
    
    return {"operating_systems": os_stats}

@router.post("/cleanup")
async def cleanup_inactive_devices(
    days_inactive: int = Query(90, ge=30, le=365)
):
    """Mark old devices as inactive"""
    tracker = DeviceTracker(db)
    count = tracker.cleanup_inactive_devices(days_inactive)
    
    return {
        "devices_marked_inactive": count,
        "threshold_days": days_inactive
    }
```

## React Dashboard Component

```tsx
import React, { useState, useEffect } from 'react';
import { Monitor, Smartphone, Tablet, Globe, AlertTriangle } from 'lucide-react';
import { PieChart, Pie, BarChart, Bar, Cell, ResponsiveContainer } from 'recharts';

interface Device {
  deviceId: string;
  deviceType: string;
  browser: string;
  browserVersion: string;
  os: string;
  osVersion: string;
  screenResolution: string;
  firstSeen: string;
  lastSeen: string;
  sessionCount: number;
  isActive: boolean;
}

interface DeviceStats {
  deviceTypes: Record<string, any>;
  browsers: Record<string, any>;
}

export const DeviceTrackingDashboard: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [stats, setStats] = useState<DeviceStats | null>(null);
  const [suspicious, setSuspicious] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId] = useState('current-user');

  useEffect(() => {
    fetchDeviceData();
  }, []);

  const fetchDeviceData = async () => {
    try {
      const [devicesRes, statsRes, suspiciousRes] = await Promise.all([
        fetch(`/api/devices/user/${userId}`),
        fetch('/api/devices/statistics?days=30'),
        fetch(`/api/devices/user/${userId}/suspicious`)
      ]);

      const devicesData = await devicesRes.json();
      const statsData = await statsRes.json();
      const suspiciousData = await suspiciousRes.json();

      setDevices(devicesData.devices);
      setStats(statsData);
      setSuspicious(suspiciousData.suspicious_devices);
    } catch (error) {
      console.error('Error fetching device data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getDeviceIcon = (type: string) => {
    switch (type) {
      case 'desktop':
        return <Monitor className="w-5 h-5" />;
      case 'mobile':
        return <Smartphone className="w-5 h-5" />;
      case 'tablet':
        return <Tablet className="w-5 h-5" />;
      default:
        return <Globe className="w-5 h-5" />;
    }
  };

  const formatDate = (date: string) => {
    const d = new Date(date);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return d.toLocaleDateString();
  };

  if (loading) return <div>Loading device data...</div>;

  // Prepare chart data
  const deviceTypeData = stats ? Object.entries(stats.deviceTypes).map(([type, data]) => ({
    name: type,
    value: data.user_count
  })) : [];

  const browserData = stats ? Object.entries(stats.browsers)
    .slice(0, 5)
    .map(([browser, data]) => ({
      name: browser,
      users: data.user_count,
      sessions: data.session_count
    })) : [];

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Device Tracking</h2>

      {/* Device Type Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Device Types</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={deviceTypeData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {deviceTypeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Top Browsers</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={browserData}>
              <Bar dataKey="users" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* User Devices */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Your Devices</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Device
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Browser
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  OS
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Screen
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  First Seen
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Last Seen
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Sessions
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {devices.map((device) => (
                <tr key={device.deviceId} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <div className="flex items-center space-x-2">
                      {getDeviceIcon(device.deviceType)}
                      <span className="text-sm capitalize">{device.deviceType}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {device.browser} {device.browserVersion}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {device.os} {device.osVersion}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {device.screenResolution || '-'}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {formatDate(device.firstSeen)}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {formatDate(device.lastSeen)}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {device.sessionCount}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 text-xs rounded ${
                      device.isActive 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-600'
                    }`}>
                      {device.isActive ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Suspicious Activity */}
      {suspicious.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 p-6 rounded-lg">
          <div className="flex items-center space-x-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            <h3 className="text-lg font-semibold text-yellow-900">
              Suspicious Device Activity
            </h3>
          </div>
          <div className="space-y-2">
            {suspicious.map((item, idx) => (
              <div key={idx} className="p-3 bg-white rounded border border-yellow-200">
                <div className="text-sm">
                  <span className="font-medium">{item.device_type} - {item.browser}</span>
                  <div className="text-xs text-gray-600 mt-1">
                    {item.ip_count} different IPs, {item.session_count} sessions
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    IPs: {item.ip_addresses.slice(0, 3).join(', ')}
                    {item.ip_addresses.length > 3 && '...'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
```

## Implementation Priority
- **Phase 1**: Basic device tracking and identification
- **Phase 2**: Session management
- **Phase 3**: Device analytics and statistics
- **Phase 4**: Suspicious activity detection

## Performance Considerations
- Simple device fingerprinting without complex libraries
- Daily batch processing for statistics
- Session cleanup after 24 hours
- Limited device history (180 days)

## Security Considerations
- No storage of full IP addresses (last octet removed)
- User agent sanitization
- Device ID hashing
- Rate limiting on device registration

## Monitoring and Alerts
- Alert on new device for user
- Alert on suspicious device patterns
- Daily device usage report
- Weekly browser/OS statistics

## Dependencies
- PostgreSQL for data storage
- user-agents Python library for UA parsing
- FastAPI for REST endpoints
- React with Recharts for visualization