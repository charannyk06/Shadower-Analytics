# User Upload Tracking Specification

## Overview
Track and analyze user upload behavior including file uploads, size patterns, content types, and success/failure rates without complex infrastructure.

## Database Schema

### Tables

```sql
-- User upload events
CREATE TABLE user_uploads (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    upload_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_extension VARCHAR(50),
    mime_type VARCHAR(100),
    file_size_bytes BIGINT NOT NULL,
    upload_status VARCHAR(50) NOT NULL, -- initiated, uploading, completed, failed, cancelled
    error_message TEXT,
    upload_duration_ms INTEGER,
    chunk_count INTEGER DEFAULT 1,
    retry_count INTEGER DEFAULT 0,
    source_page VARCHAR(255),
    upload_method VARCHAR(50), -- drag_drop, file_picker, paste, api
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_user_uploads_user (user_id, created_at DESC),
    INDEX idx_user_uploads_status (upload_status, created_at DESC),
    INDEX idx_user_uploads_size (file_size_bytes)
);

-- Daily upload statistics
CREATE TABLE user_upload_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    user_id UUID,
    total_uploads INTEGER DEFAULT 0,
    successful_uploads INTEGER DEFAULT 0,
    failed_uploads INTEGER DEFAULT 0,
    cancelled_uploads INTEGER DEFAULT 0,
    total_bytes_uploaded BIGINT DEFAULT 0,
    avg_upload_duration_ms INTEGER,
    unique_file_types INTEGER DEFAULT 0,
    largest_file_bytes BIGINT,
    retry_attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date, user_id),
    INDEX idx_upload_daily_stats_date (date DESC),
    INDEX idx_upload_daily_stats_user (user_id, date DESC)
);

-- Upload validation rules
CREATE TABLE upload_validation_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) UNIQUE NOT NULL,
    max_file_size_mb INTEGER,
    allowed_extensions TEXT[], -- Array of allowed extensions
    blocked_extensions TEXT[], -- Array of blocked extensions
    allowed_mime_types TEXT[],
    require_virus_scan BOOLEAN DEFAULT false,
    auto_compress BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Upload quota tracking
CREATE TABLE user_upload_quotas (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,
    daily_upload_limit_mb INTEGER DEFAULT 1000,
    monthly_upload_limit_gb INTEGER DEFAULT 10,
    current_day_usage_mb INTEGER DEFAULT 0,
    current_month_usage_gb DECIMAL(10, 2) DEFAULT 0,
    last_reset_date DATE,
    quota_exceeded_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_upload_quotas_user (user_id)
);
```

## TypeScript Interfaces

```typescript
// Upload event interface
interface UserUpload {
  id: string;
  userId: string;
  uploadId: string;
  filename: string;
  fileExtension?: string;
  mimeType?: string;
  fileSizeBytes: number;
  uploadStatus: 'initiated' | 'uploading' | 'completed' | 'failed' | 'cancelled';
  errorMessage?: string;
  uploadDurationMs?: number;
  chunkCount: number;
  retryCount: number;
  sourcePage?: string;
  uploadMethod: 'drag_drop' | 'file_picker' | 'paste' | 'api';
  createdAt: Date;
  completedAt?: Date;
}

// Upload statistics
interface UploadStatistics {
  totalUploads: number;
  successfulUploads: number;
  failedUploads: number;
  cancelledUploads: number;
  totalBytesUploaded: number;
  avgUploadDurationMs: number;
  uniqueFileTypes: number;
  largestFileBytes: number;
  retryAttempts: number;
  successRate: number;
  avgFileSizeMb: number;
}

// Upload validation rule
interface UploadValidationRule {
  id: number;
  ruleName: string;
  maxFileSizeMb?: number;
  allowedExtensions?: string[];
  blockedExtensions?: string[];
  allowedMimeTypes?: string[];
  requireVirusScan: boolean;
  autoCompress: boolean;
  isActive: boolean;
}

// User upload quota
interface UserUploadQuota {
  userId: string;
  dailyUploadLimitMb: number;
  monthlyUploadLimitGb: number;
  currentDayUsageMb: number;
  currentMonthUsageGb: number;
  lastResetDate: Date;
  quotaExceededCount: number;
  remainingDailyMb: number;
  remainingMonthlyGb: number;
}

// File type distribution
interface FileTypeDistribution {
  extension: string;
  mimeType: string;
  uploadCount: number;
  totalSizeBytes: number;
  avgSizeBytes: number;
  percentage: number;
}
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import asyncpg

@dataclass
class UploadAnalytics:
    """Analyze user upload patterns and behaviors"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def track_upload(
        self,
        user_id: str,
        filename: str,
        file_size: int,
        upload_method: str = 'file_picker',
        source_page: Optional[str] = None
    ) -> str:
        """Track a new upload event"""
        query = """
            INSERT INTO user_uploads (
                user_id, filename, file_extension, mime_type,
                file_size_bytes, upload_status, upload_method,
                source_page
            ) VALUES ($1, $2, $3, $4, $5, 'initiated', $6, $7)
            RETURNING upload_id
        """
        
        # Extract file extension
        extension = filename.split('.')[-1] if '.' in filename else None
        mime_type = self._guess_mime_type(extension)
        
        async with self.db.acquire() as conn:
            upload_id = await conn.fetchval(
                query, user_id, filename, extension, mime_type,
                file_size, upload_method, source_page
            )
            
            # Check quotas
            await self._check_upload_quota(conn, user_id, file_size)
            
        return upload_id
    
    async def update_upload_status(
        self,
        upload_id: str,
        status: str,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ):
        """Update upload status"""
        query = """
            UPDATE user_uploads
            SET upload_status = $2,
                error_message = $3,
                upload_duration_ms = COALESCE($4, upload_duration_ms),
                completed_at = CASE 
                    WHEN $2 IN ('completed', 'failed', 'cancelled') 
                    THEN CURRENT_TIMESTAMP 
                    ELSE completed_at 
                END
            WHERE upload_id = $1
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, upload_id, status, error_message, duration_ms)
            
            # Update daily stats if completed
            if status in ['completed', 'failed', 'cancelled']:
                await self._update_daily_stats(conn, upload_id, status)
    
    async def get_user_upload_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get user upload statistics"""
        query = """
            WITH upload_stats AS (
                SELECT 
                    COUNT(*) as total_uploads,
                    COUNT(*) FILTER (WHERE upload_status = 'completed') as successful,
                    COUNT(*) FILTER (WHERE upload_status = 'failed') as failed,
                    COUNT(*) FILTER (WHERE upload_status = 'cancelled') as cancelled,
                    SUM(file_size_bytes) FILTER (WHERE upload_status = 'completed') as total_bytes,
                    AVG(upload_duration_ms) FILTER (WHERE upload_status = 'completed') as avg_duration,
                    COUNT(DISTINCT file_extension) as unique_types,
                    MAX(file_size_bytes) as largest_file,
                    SUM(retry_count) as total_retries
                FROM user_uploads
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            )
            SELECT * FROM upload_stats
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % days, user_id)
            
            return {
                'total_uploads': row['total_uploads'] or 0,
                'successful_uploads': row['successful'] or 0,
                'failed_uploads': row['failed'] or 0,
                'cancelled_uploads': row['cancelled'] or 0,
                'total_bytes_uploaded': row['total_bytes'] or 0,
                'avg_upload_duration_ms': row['avg_duration'] or 0,
                'unique_file_types': row['unique_types'] or 0,
                'largest_file_bytes': row['largest_file'] or 0,
                'total_retry_attempts': row['total_retries'] or 0,
                'success_rate': (
                    (row['successful'] / row['total_uploads'] * 100)
                    if row['total_uploads'] > 0 else 0
                ),
                'avg_file_size_mb': (
                    (row['total_bytes'] / row['successful'] / 1024 / 1024)
                    if row['successful'] > 0 else 0
                )
            }
    
    async def get_file_type_distribution(
        self,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> List[Dict]:
        """Get file type distribution"""
        query = """
            SELECT 
                COALESCE(file_extension, 'unknown') as extension,
                COALESCE(mime_type, 'unknown') as mime_type,
                COUNT(*) as upload_count,
                SUM(file_size_bytes) as total_size,
                AVG(file_size_bytes) as avg_size
            FROM user_uploads
            WHERE upload_status = 'completed'
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                %s
            GROUP BY file_extension, mime_type
            ORDER BY upload_count DESC
            LIMIT 20
        """
        
        user_filter = "AND user_id = $1" if user_id else ""
        
        async with self.db.acquire() as conn:
            if user_id:
                rows = await conn.fetch(query % (days, user_filter), user_id)
            else:
                rows = await conn.fetch(query % (days, user_filter))
            
            total_uploads = sum(row['upload_count'] for row in rows)
            
            return [
                {
                    'extension': row['extension'],
                    'mime_type': row['mime_type'],
                    'upload_count': row['upload_count'],
                    'total_size_bytes': row['total_size'],
                    'avg_size_bytes': row['avg_size'],
                    'percentage': (row['upload_count'] / total_uploads * 100) if total_uploads > 0 else 0
                }
                for row in rows
            ]
    
    async def get_upload_patterns(
        self,
        user_id: str
    ) -> Dict:
        """Analyze upload patterns"""
        query = """
            WITH hourly_uploads AS (
                SELECT 
                    EXTRACT(HOUR FROM created_at) as hour,
                    COUNT(*) as count
                FROM user_uploads
                WHERE user_id = $1
                    AND upload_status = 'completed'
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                GROUP BY EXTRACT(HOUR FROM created_at)
            ),
            daily_uploads AS (
                SELECT 
                    EXTRACT(DOW FROM created_at) as day_of_week,
                    COUNT(*) as count
                FROM user_uploads
                WHERE user_id = $1
                    AND upload_status = 'completed'
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                GROUP BY EXTRACT(DOW FROM created_at)
            ),
            method_stats AS (
                SELECT 
                    upload_method,
                    COUNT(*) as count,
                    AVG(upload_duration_ms) as avg_duration
                FROM user_uploads
                WHERE user_id = $1
                    AND upload_status = 'completed'
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                GROUP BY upload_method
            )
            SELECT 
                (SELECT json_agg(json_build_object('hour', hour, 'count', count) ORDER BY hour) FROM hourly_uploads) as hourly,
                (SELECT json_agg(json_build_object('day', day_of_week, 'count', count) ORDER BY day_of_week) FROM daily_uploads) as daily,
                (SELECT json_agg(json_build_object('method', upload_method, 'count', count, 'avg_duration', avg_duration)) FROM method_stats) as methods
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
            return {
                'hourly_distribution': row['hourly'] or [],
                'daily_distribution': row['daily'] or [],
                'method_preferences': row['methods'] or [],
                'peak_upload_hour': self._find_peak_hour(row['hourly']),
                'peak_upload_day': self._find_peak_day(row['daily']),
                'preferred_method': self._find_preferred_method(row['methods'])
            }
    
    async def check_upload_quota(
        self,
        user_id: str
    ) -> Dict:
        """Check user's upload quota status"""
        query = """
            SELECT 
                daily_upload_limit_mb,
                monthly_upload_limit_gb,
                current_day_usage_mb,
                current_month_usage_gb,
                last_reset_date
            FROM user_upload_quotas
            WHERE user_id = $1
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
            if not row:
                # Create default quota
                await self._create_default_quota(conn, user_id)
                row = await conn.fetchrow(query, user_id)
            
            # Check if reset needed
            if row['last_reset_date'] != datetime.now().date():
                await self._reset_daily_quota(conn, user_id)
                row = await conn.fetchrow(query, user_id)
            
            return {
                'daily_limit_mb': row['daily_upload_limit_mb'],
                'monthly_limit_gb': row['monthly_upload_limit_gb'],
                'current_day_usage_mb': row['current_day_usage_mb'],
                'current_month_usage_gb': float(row['current_month_usage_gb']),
                'remaining_daily_mb': row['daily_upload_limit_mb'] - row['current_day_usage_mb'],
                'remaining_monthly_gb': row['monthly_upload_limit_gb'] - float(row['current_month_usage_gb']),
                'daily_percentage_used': (row['current_day_usage_mb'] / row['daily_upload_limit_mb'] * 100) if row['daily_upload_limit_mb'] > 0 else 0,
                'monthly_percentage_used': (float(row['current_month_usage_gb']) / row['monthly_upload_limit_gb'] * 100) if row['monthly_upload_limit_gb'] > 0 else 0
            }
    
    async def get_failed_uploads(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get recent failed uploads for debugging"""
        query = """
            SELECT 
                upload_id,
                user_id,
                filename,
                file_size_bytes,
                error_message,
                retry_count,
                created_at
            FROM user_uploads
            WHERE upload_status = 'failed'
                %s
            ORDER BY created_at DESC
            LIMIT $1
        """
        
        user_filter = "AND user_id = $2" if user_id else ""
        
        async with self.db.acquire() as conn:
            if user_id:
                rows = await conn.fetch(query % user_filter, limit, user_id)
            else:
                rows = await conn.fetch(query % user_filter, limit)
            
            return [
                {
                    'upload_id': row['upload_id'],
                    'user_id': row['user_id'],
                    'filename': row['filename'],
                    'file_size_bytes': row['file_size_bytes'],
                    'error_message': row['error_message'],
                    'retry_count': row['retry_count'],
                    'created_at': row['created_at'].isoformat()
                }
                for row in rows
            ]
    
    def _guess_mime_type(self, extension: Optional[str]) -> Optional[str]:
        """Simple mime type guessing"""
        if not extension:
            return None
            
        mime_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'zip': 'application/zip',
            'mp4': 'video/mp4',
            'mp3': 'audio/mpeg'
        }
        
        return mime_map.get(extension.lower())
    
    def _find_peak_hour(self, hourly_data):
        """Find peak upload hour"""
        if not hourly_data:
            return None
        return max(hourly_data, key=lambda x: x['count'])['hour']
    
    def _find_peak_day(self, daily_data):
        """Find peak upload day"""
        if not daily_data:
            return None
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        peak = max(daily_data, key=lambda x: x['count'])
        return days[int(peak['day'])]
    
    def _find_preferred_method(self, method_data):
        """Find preferred upload method"""
        if not method_data:
            return None
        return max(method_data, key=lambda x: x['count'])['method']
    
    async def _check_upload_quota(self, conn, user_id: str, file_size: int):
        """Check and update upload quota"""
        # Implementation for quota checking
        pass
    
    async def _update_daily_stats(self, conn, upload_id: str, status: str):
        """Update daily statistics"""
        # Implementation for daily stats update
        pass
    
    async def _create_default_quota(self, conn, user_id: str):
        """Create default quota for user"""
        # Implementation for default quota creation
        pass
    
    async def _reset_daily_quota(self, conn, user_id: str):
        """Reset daily quota"""
        # Implementation for quota reset
        pass
```

## API Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional, List

router = APIRouter(prefix="/api/analytics/uploads", tags=["upload-analytics"])

@router.post("/track")
async def track_upload(
    user_id: str,
    filename: str,
    file_size: int,
    upload_method: str = "file_picker",
    source_page: Optional[str] = None
):
    """Track a new upload event"""
    analytics = UploadAnalytics(db_pool)
    upload_id = await analytics.track_upload(
        user_id, filename, file_size, upload_method, source_page
    )
    return {"upload_id": upload_id}

@router.patch("/status/{upload_id}")
async def update_upload_status(
    upload_id: str,
    status: str,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None
):
    """Update upload status"""
    analytics = UploadAnalytics(db_pool)
    await analytics.update_upload_status(
        upload_id, status, error_message, duration_ms
    )
    return {"status": "updated"}

@router.get("/stats/{user_id}")
async def get_user_upload_stats(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get user upload statistics"""
    analytics = UploadAnalytics(db_pool)
    stats = await analytics.get_user_upload_stats(user_id, days)
    return stats

@router.get("/file-types")
async def get_file_type_distribution(
    user_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Get file type distribution"""
    analytics = UploadAnalytics(db_pool)
    distribution = await analytics.get_file_type_distribution(user_id, days)
    return {"file_types": distribution}

@router.get("/patterns/{user_id}")
async def get_upload_patterns(user_id: str):
    """Get user upload patterns"""
    analytics = UploadAnalytics(db_pool)
    patterns = await analytics.get_upload_patterns(user_id)
    return patterns

@router.get("/quota/{user_id}")
async def check_upload_quota(user_id: str):
    """Check user upload quota"""
    analytics = UploadAnalytics(db_pool)
    quota = await analytics.check_upload_quota(user_id)
    return quota

@router.get("/failed")
async def get_failed_uploads(
    user_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """Get recent failed uploads"""
    analytics = UploadAnalytics(db_pool)
    failed = await analytics.get_failed_uploads(user_id, limit)
    return {"failed_uploads": failed}
```

## React Dashboard Components

```tsx
// User Upload Dashboard Component
import React, { useState, useEffect } from 'react';
import { Card, Grid, Progress, Table, Badge, LineChart, BarChart, PieChart } from '@/components/ui';

interface UploadDashboardProps {
  userId?: string;
}

export const UploadDashboard: React.FC<UploadDashboardProps> = ({ userId }) => {
  const [stats, setStats] = useState<UploadStatistics | null>(null);
  const [fileTypes, setFileTypes] = useState<FileTypeDistribution[]>([]);
  const [patterns, setPatterns] = useState<any>(null);
  const [quota, setQuota] = useState<UserUploadQuota | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUploadData();
  }, [userId]);

  const fetchUploadData = async () => {
    setLoading(true);
    try {
      const [statsRes, typesRes, patternsRes, quotaRes] = await Promise.all([
        fetch(`/api/analytics/uploads/stats/${userId || 'all'}`),
        fetch(`/api/analytics/uploads/file-types${userId ? `?user_id=${userId}` : ''}`),
        userId ? fetch(`/api/analytics/uploads/patterns/${userId}`) : null,
        userId ? fetch(`/api/analytics/uploads/quota/${userId}`) : null
      ]);

      setStats(await statsRes.json());
      setFileTypes((await typesRes.json()).file_types);
      if (patternsRes) setPatterns(await patternsRes.json());
      if (quotaRes) setQuota(await quotaRes.json());
    } catch (error) {
      console.error('Failed to fetch upload data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading upload analytics...</div>;

  return (
    <div className="upload-dashboard">
      <h2>Upload Analytics</h2>
      
      {/* Summary Stats */}
      <Grid cols={4} gap={4}>
        <Card>
          <h3>Total Uploads</h3>
          <div className="stat-value">{stats?.totalUploads || 0}</div>
          <Badge variant={stats?.successRate >= 90 ? 'success' : 'warning'}>
            {stats?.successRate?.toFixed(1)}% Success Rate
          </Badge>
        </Card>
        
        <Card>
          <h3>Data Uploaded</h3>
          <div className="stat-value">
            {formatBytes(stats?.totalBytesUploaded || 0)}
          </div>
          <span className="stat-label">
            Avg: {formatBytes(stats?.avgFileSizeMb * 1024 * 1024 || 0)}
          </span>
        </Card>
        
        <Card>
          <h3>Failed Uploads</h3>
          <div className="stat-value">{stats?.failedUploads || 0}</div>
          <span className="stat-label">
            {stats?.retryAttempts || 0} Retries
          </span>
        </Card>
        
        <Card>
          <h3>File Types</h3>
          <div className="stat-value">{stats?.uniqueFileTypes || 0}</div>
          <span className="stat-label">Unique Types</span>
        </Card>
      </Grid>

      {/* Quota Display */}
      {quota && (
        <Card className="mt-4">
          <h3>Upload Quota</h3>
          <div className="quota-section">
            <div className="quota-item">
              <span>Daily Usage</span>
              <Progress 
                value={quota.dailyPercentageUsed} 
                max={100}
                variant={quota.dailyPercentageUsed > 80 ? 'warning' : 'primary'}
              />
              <span className="quota-label">
                {quota.currentDayUsageMb}MB / {quota.dailyUploadLimitMb}MB
              </span>
            </div>
            
            <div className="quota-item">
              <span>Monthly Usage</span>
              <Progress 
                value={quota.monthlyPercentageUsed} 
                max={100}
                variant={quota.monthlyPercentageUsed > 80 ? 'warning' : 'primary'}
              />
              <span className="quota-label">
                {quota.currentMonthUsageGb}GB / {quota.monthlyUploadLimitGb}GB
              </span>
            </div>
          </div>
        </Card>
      )}

      {/* File Type Distribution */}
      <Card className="mt-4">
        <h3>File Type Distribution</h3>
        <div className="chart-container">
          <PieChart
            data={fileTypes.map(ft => ({
              name: ft.extension,
              value: ft.uploadCount,
              percentage: ft.percentage
            }))}
            height={300}
          />
        </div>
        
        <Table className="mt-4">
          <thead>
            <tr>
              <th>Extension</th>
              <th>Upload Count</th>
              <th>Total Size</th>
              <th>Avg Size</th>
              <th>%</th>
            </tr>
          </thead>
          <tbody>
            {fileTypes.slice(0, 10).map(ft => (
              <tr key={ft.extension}>
                <td>
                  <Badge>{ft.extension}</Badge>
                </td>
                <td>{ft.uploadCount}</td>
                <td>{formatBytes(ft.totalSizeBytes)}</td>
                <td>{formatBytes(ft.avgSizeBytes)}</td>
                <td>{ft.percentage.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {/* Upload Patterns */}
      {patterns && (
        <>
          <Card className="mt-4">
            <h3>Upload Time Patterns</h3>
            <div className="pattern-info">
              <Badge>Peak Hour: {patterns.peakUploadHour}:00</Badge>
              <Badge>Peak Day: {patterns.peakUploadDay}</Badge>
              <Badge>Preferred: {patterns.preferredMethod}</Badge>
            </div>
            
            <div className="chart-grid">
              <div>
                <h4>Hourly Distribution</h4>
                <LineChart
                  data={patterns.hourlyDistribution}
                  xKey="hour"
                  yKey="count"
                  height={200}
                />
              </div>
              
              <div>
                <h4>Daily Distribution</h4>
                <BarChart
                  data={patterns.dailyDistribution}
                  xKey="day"
                  yKey="count"
                  height={200}
                />
              </div>
            </div>
          </Card>

          <Card className="mt-4">
            <h3>Upload Methods</h3>
            <Table>
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Count</th>
                  <th>Avg Duration</th>
                </tr>
              </thead>
              <tbody>
                {patterns.methodPreferences?.map((method: any) => (
                  <tr key={method.method}>
                    <td>{method.method}</td>
                    <td>{method.count}</td>
                    <td>{method.avgDuration?.toFixed(0)}ms</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
        </>
      )}

      {/* Upload Speed Chart */}
      <Card className="mt-4">
        <h3>Average Upload Speed</h3>
        <div className="speed-stat">
          <span className="speed-value">
            {stats?.avgUploadDurationMs 
              ? (stats.avgFileSizeMb * 1024 / stats.avgUploadDurationMs * 1000).toFixed(2)
              : '0'} KB/s
          </span>
          <span className="speed-label">Average Speed</span>
        </div>
      </Card>
    </div>
  );
};

// Helper function
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
};
```

## Implementation Priority
1. Basic upload tracking and status updates
2. File type and size analytics
3. Daily quota management
4. Upload patterns analysis
5. Failed upload monitoring

## Security Considerations
- Validate file types and sizes
- Implement virus scanning hooks
- Track suspicious upload patterns
- Enforce upload quotas
- Monitor for abuse patterns

## Performance Optimizations
- Use chunked uploads for large files
- Implement resumable uploads
- Batch status updates
- Cache file type statistics
- Daily aggregation for reports