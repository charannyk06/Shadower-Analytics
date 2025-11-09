# User API Usage Specification

## Overview
Track API usage patterns without complex API management platforms. Monitor endpoint usage, response times, and error rates per user.

## TypeScript Interfaces

```typescript
// API request
interface APIRequest {
  request_id: string;
  user_id: string;
  endpoint: string;
  method: string;
  status_code: number;
  response_time_ms: number;
  request_size_bytes: number;
  response_size_bytes: number;
  timestamp: Date;
  error_message?: string;
}

// API usage summary
interface APIUsageSummary {
  user_id: string;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  avg_response_time_ms: number;
  total_data_transferred_mb: number;
  most_used_endpoints: string[];
}

// Endpoint metrics
interface EndpointMetrics {
  endpoint: string;
  method: string;
  total_calls: number;
  success_rate: number;
  avg_response_time_ms: number;
  p95_response_time_ms: number;
  error_rate: number;
}

// Rate limit status
interface RateLimitStatus {
  user_id: string;
  endpoint: string;
  requests_made: number;
  limit: number;
  remaining: number;
  reset_at: Date;
}
```

## SQL Schema

```sql
-- API requests table
CREATE TABLE api_requests (
    request_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    request_size_bytes INTEGER DEFAULT 0,
    response_size_bytes INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT
);

-- User API usage summary
CREATE TABLE user_api_summary (
    user_id VARCHAR(255) PRIMARY KEY,
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    total_response_time_ms BIGINT DEFAULT 0,
    total_data_transferred_bytes BIGINT DEFAULT 0,
    most_used_endpoints TEXT[],
    first_request_at TIMESTAMP,
    last_request_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Endpoint metrics
CREATE TABLE endpoint_metrics (
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    total_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    total_response_time_ms BIGINT DEFAULT 0,
    min_response_time_ms INTEGER,
    max_response_time_ms INTEGER,
    last_called_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (endpoint, method)
);

-- Daily API statistics
CREATE TABLE daily_api_stats (
    date DATE NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    avg_response_time_ms INTEGER DEFAULT 0,
    p95_response_time_ms INTEGER DEFAULT 0,
    total_data_mb DECIMAL(10,2) DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    PRIMARY KEY (date, endpoint, method)
);

-- Rate limiting
CREATE TABLE rate_limits (
    user_id VARCHAR(255) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    window_start TIMESTAMP NOT NULL,
    request_count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, endpoint, window_start)
);

-- API keys (simple implementation)
CREATE TABLE api_keys (
    api_key VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    request_count INTEGER DEFAULT 0
);

-- Basic indexes
CREATE INDEX idx_requests_user ON api_requests(user_id);
CREATE INDEX idx_requests_endpoint ON api_requests(endpoint);
CREATE INDEX idx_requests_timestamp ON api_requests(timestamp DESC);
CREATE INDEX idx_requests_status ON api_requests(status_code);
CREATE INDEX idx_rate_limits_user ON rate_limits(user_id);
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import uuid
import hashlib
import secrets
from collections import defaultdict, Counter

@dataclass
class APIMetrics:
    """API performance metrics"""
    endpoint: str
    method: str
    success_rate: float
    avg_response_time: float
    p95_response_time: float
    requests_per_minute: float
    error_types: Dict[int, int]

class APIUsageTracker:
    """Track API usage and performance"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.rate_limits = {
            'default': 100,  # requests per hour
            'premium': 1000,
            'enterprise': 10000
        }
    
    def track_request(
        self,
        user_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        request_size: int = 0,
        response_size: int = 0,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Track API request"""
        request_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO api_requests
        (request_id, user_id, endpoint, method, status_code, response_time_ms,
         request_size_bytes, response_size_bytes, error_message, ip_address, user_agent)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        self.db.execute(query, (
            request_id, user_id, endpoint, method, status_code,
            response_time_ms, request_size, response_size,
            error_message, ip_address, user_agent
        ))
        
        # Update user summary
        self.update_user_summary(user_id, status_code, response_time_ms, 
                                request_size + response_size)
        
        # Update endpoint metrics
        self.update_endpoint_metrics(endpoint, method, status_code, response_time_ms)
        
        # Update rate limit
        self.update_rate_limit(user_id, endpoint)
        
        return request_id
    
    def update_user_summary(
        self,
        user_id: str,
        status_code: int,
        response_time_ms: int,
        data_bytes: int
    ) -> None:
        """Update user API usage summary"""
        is_success = 200 <= status_code < 400
        
        query = """
        INSERT INTO user_api_summary
        (user_id, total_requests, successful_requests, failed_requests,
         total_response_time_ms, total_data_transferred_bytes, first_request_at)
        VALUES (%s, 1, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id)
        DO UPDATE SET
            total_requests = user_api_summary.total_requests + 1,
            successful_requests = user_api_summary.successful_requests + %s,
            failed_requests = user_api_summary.failed_requests + %s,
            total_response_time_ms = user_api_summary.total_response_time_ms + %s,
            total_data_transferred_bytes = user_api_summary.total_data_transferred_bytes + %s,
            last_request_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        """
        
        self.db.execute(query, (
            user_id, 
            1 if is_success else 0,
            0 if is_success else 1,
            response_time_ms,
            data_bytes,
            1 if is_success else 0,
            0 if is_success else 1,
            response_time_ms,
            data_bytes
        ))
        
        # Update most used endpoints
        self.update_most_used_endpoints(user_id)
    
    def update_most_used_endpoints(self, user_id: str, limit: int = 5) -> None:
        """Update user's most used endpoints"""
        query = """
        WITH endpoint_usage AS (
            SELECT endpoint, COUNT(*) as usage_count
            FROM api_requests
            WHERE user_id = %s
            AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            GROUP BY endpoint
            ORDER BY usage_count DESC
            LIMIT %s
        )
        UPDATE user_api_summary
        SET most_used_endpoints = (
            SELECT ARRAY_AGG(endpoint)
            FROM endpoint_usage
        )
        WHERE user_id = %s
        """
        
        self.db.execute(query, (user_id, limit, user_id))
    
    def update_endpoint_metrics(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int
    ) -> None:
        """Update endpoint metrics"""
        is_success = 200 <= status_code < 400
        
        query = """
        INSERT INTO endpoint_metrics
        (endpoint, method, total_calls, successful_calls, failed_calls,
         total_response_time_ms, min_response_time_ms, max_response_time_ms, last_called_at)
        VALUES (%s, %s, 1, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (endpoint, method)
        DO UPDATE SET
            total_calls = endpoint_metrics.total_calls + 1,
            successful_calls = endpoint_metrics.successful_calls + %s,
            failed_calls = endpoint_metrics.failed_calls + %s,
            total_response_time_ms = endpoint_metrics.total_response_time_ms + %s,
            min_response_time_ms = LEAST(endpoint_metrics.min_response_time_ms, %s),
            max_response_time_ms = GREATEST(endpoint_metrics.max_response_time_ms, %s),
            last_called_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        """
        
        self.db.execute(query, (
            endpoint, method,
            1 if is_success else 0,
            0 if is_success else 1,
            response_time_ms,
            response_time_ms,
            response_time_ms,
            1 if is_success else 0,
            0 if is_success else 1,
            response_time_ms,
            response_time_ms,
            response_time_ms
        ))
    
    def check_rate_limit(self, user_id: str, endpoint: str) -> Tuple[bool, Dict]:
        """Check if user has exceeded rate limit"""
        # Get user tier (simplified)
        tier = self.get_user_tier(user_id)
        limit = self.rate_limits.get(tier, 100)
        
        # Check requests in current hour window
        window_start = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        query = """
        SELECT request_count
        FROM rate_limits
        WHERE user_id = %s
        AND endpoint = %s
        AND window_start = %s
        """
        
        result = self.db.fetchone(query, (user_id, endpoint, window_start))
        
        current_count = result['request_count'] if result else 0
        remaining = limit - current_count
        
        return remaining > 0, {
            'limit': limit,
            'remaining': max(0, remaining),
            'reset_at': (window_start + timedelta(hours=1)).isoformat(),
            'current_count': current_count
        }
    
    def update_rate_limit(self, user_id: str, endpoint: str) -> None:
        """Update rate limit counter"""
        window_start = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        query = """
        INSERT INTO rate_limits
        (user_id, endpoint, window_start, request_count)
        VALUES (%s, %s, %s, 1)
        ON CONFLICT (user_id, endpoint, window_start)
        DO UPDATE SET request_count = rate_limits.request_count + 1
        """
        
        self.db.execute(query, (user_id, endpoint, window_start))
    
    def get_user_tier(self, user_id: str) -> str:
        """Get user tier (simplified implementation)"""
        # In production, fetch from user subscription table
        return 'default'
    
    def generate_api_key(self, user_id: str, name: str) -> str:
        """Generate new API key for user"""
        api_key = f"sk_{secrets.token_urlsafe(32)}"
        
        query = """
        INSERT INTO api_keys
        (api_key, user_id, name)
        VALUES (%s, %s, %s)
        """
        
        self.db.execute(query, (api_key, user_id, name))
        
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[str]:
        """Validate API key and return user_id"""
        query = """
        UPDATE api_keys
        SET 
            last_used_at = CURRENT_TIMESTAMP,
            request_count = request_count + 1
        WHERE api_key = %s
        AND is_active = true
        RETURNING user_id
        """
        
        result = self.db.fetchone(query, (api_key,))
        return result['user_id'] if result else None
    
    def get_endpoint_metrics(self, endpoint: str, method: str) -> APIMetrics:
        """Get metrics for specific endpoint"""
        query = """
        WITH recent_requests AS (
            SELECT 
                status_code,
                response_time_ms,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_time
            FROM api_requests
            WHERE endpoint = %s
            AND method = %s
            AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )
        SELECT 
            COUNT(*) as total_requests,
            COUNT(CASE WHEN status_code >= 200 AND status_code < 400 THEN 1 END) as success_count,
            AVG(response_time_ms) as avg_time,
            MAX(p95_time) as p95_time,
            COUNT(*) / (EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60) as rpm
        FROM recent_requests, api_requests
        WHERE api_requests.endpoint = %s
        AND api_requests.method = %s
        AND api_requests.timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
        """
        
        result = self.db.fetchone(query, (endpoint, method, endpoint, method))
        
        if not result or result['total_requests'] == 0:
            return APIMetrics(
                endpoint=endpoint,
                method=method,
                success_rate=0,
                avg_response_time=0,
                p95_response_time=0,
                requests_per_minute=0,
                error_types={}
            )
        
        # Get error distribution
        error_query = """
        SELECT status_code, COUNT(*) as count
        FROM api_requests
        WHERE endpoint = %s
        AND method = %s
        AND status_code >= 400
        AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
        GROUP BY status_code
        """
        
        error_results = self.db.fetchall(error_query, (endpoint, method))
        error_types = {row['status_code']: row['count'] for row in error_results}
        
        return APIMetrics(
            endpoint=endpoint,
            method=method,
            success_rate=(result['success_count'] / result['total_requests'] * 100),
            avg_response_time=result['avg_time'] or 0,
            p95_response_time=result['p95_time'] or 0,
            requests_per_minute=result['rpm'] or 0,
            error_types=error_types
        )
    
    def get_user_usage(self, user_id: str) -> Dict:
        """Get user's API usage statistics"""
        query = """
        SELECT 
            total_requests,
            successful_requests,
            failed_requests,
            CASE 
                WHEN total_requests > 0 
                THEN (total_response_time_ms::FLOAT / total_requests)
                ELSE 0 
            END as avg_response_time,
            (total_data_transferred_bytes::FLOAT / 1048576) as total_data_mb,
            most_used_endpoints,
            first_request_at,
            last_request_at
        FROM user_api_summary
        WHERE user_id = %s
        """
        
        result = self.db.fetchone(query, (user_id,))
        
        if not result:
            return {
                'user_id': user_id,
                'total_requests': 0,
                'success_rate': 0,
                'avg_response_time': 0,
                'total_data_mb': 0
            }
        
        return {
            'user_id': user_id,
            'total_requests': result['total_requests'],
            'success_rate': (result['successful_requests'] / result['total_requests'] * 100) 
                          if result['total_requests'] > 0 else 0,
            'avg_response_time': result['avg_response_time'],
            'total_data_mb': result['total_data_mb'],
            'most_used_endpoints': result['most_used_endpoints'] or [],
            'first_request': result['first_request_at'],
            'last_request': result['last_request_at']
        }
    
    def get_slow_endpoints(self, threshold_ms: int = 1000) -> List[Dict]:
        """Identify slow endpoints"""
        query = """
        SELECT 
            endpoint,
            method,
            total_calls,
            (total_response_time_ms::FLOAT / total_calls) as avg_response_time,
            max_response_time_ms
        FROM endpoint_metrics
        WHERE total_calls > 10
        AND (total_response_time_ms::FLOAT / total_calls) > %s
        ORDER BY avg_response_time DESC
        LIMIT 20
        """
        
        return self.db.fetchall(query, (threshold_ms,))
    
    def calculate_daily_stats(self, date: Optional[datetime] = None) -> None:
        """Calculate daily API statistics"""
        target_date = date or datetime.now().date()
        
        query = """
        INSERT INTO daily_api_stats
        (date, endpoint, method, total_requests, successful_requests, failed_requests,
         avg_response_time_ms, p95_response_time_ms, total_data_mb, unique_users)
        SELECT 
            DATE(timestamp) as date,
            endpoint,
            method,
            COUNT(*) as total_requests,
            COUNT(CASE WHEN status_code >= 200 AND status_code < 400 THEN 1 END) as successful,
            COUNT(CASE WHEN status_code >= 400 THEN 1 END) as failed,
            AVG(response_time_ms)::INTEGER as avg_time,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms)::INTEGER as p95_time,
            SUM(request_size_bytes + response_size_bytes)::FLOAT / 1048576 as total_mb,
            COUNT(DISTINCT user_id) as unique_users
        FROM api_requests
        WHERE DATE(timestamp) = %s
        GROUP BY DATE(timestamp), endpoint, method
        ON CONFLICT (date, endpoint, method)
        DO UPDATE SET
            total_requests = EXCLUDED.total_requests,
            successful_requests = EXCLUDED.successful_requests,
            failed_requests = EXCLUDED.failed_requests,
            avg_response_time_ms = EXCLUDED.avg_response_time_ms,
            p95_response_time_ms = EXCLUDED.p95_response_time_ms,
            total_data_mb = EXCLUDED.total_data_mb,
            unique_users = EXCLUDED.unique_users
        """
        
        self.db.execute(query, (target_date,))
```

## API Endpoints

```python
from fastapi import APIRouter, Query, HTTPException, Header, Depends
from typing import List, Optional

router = APIRouter(prefix="/api/usage", tags=["api-usage"])

async def get_current_user(api_key: str = Header(None, alias="X-API-Key")) -> str:
    """Get current user from API key"""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    tracker = APIUsageTracker(db)
    user_id = tracker.validate_api_key(api_key)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return user_id

@router.post("/track")
async def track_api_request(
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int,
    request_size: int = 0,
    response_size: int = 0,
    error_message: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Track API request"""
    tracker = APIUsageTracker(db)
    
    # Check rate limit
    allowed, limit_info = tracker.check_rate_limit(user_id, endpoint)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limit_info['limit']),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": limit_info['reset_at']
            }
        )
    
    request_id = tracker.track_request(
        user_id, endpoint, method, status_code,
        response_time_ms, request_size, response_size,
        error_message
    )
    
    return {
        "request_id": request_id,
        "tracked": True,
        "rate_limit": limit_info
    }

@router.get("/user/{user_id}/summary")
async def get_user_api_summary(user_id: str):
    """Get user's API usage summary"""
    tracker = APIUsageTracker(db)
    usage = tracker.get_user_usage(user_id)
    
    return usage

@router.get("/user/{user_id}/recent")
async def get_recent_requests(
    user_id: str,
    hours: int = Query(24, ge=1, le=168)
):
    """Get user's recent API requests"""
    query = """
    SELECT 
        request_id,
        endpoint,
        method,
        status_code,
        response_time_ms,
        timestamp,
        error_message
    FROM api_requests
    WHERE user_id = %s
    AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s hours'
    ORDER BY timestamp DESC
    LIMIT 100
    """
    
    requests = db.fetchall(query, (user_id, hours))
    
    return {
        "user_id": user_id,
        "requests": requests,
        "count": len(requests)
    }

@router.get("/endpoints/metrics")
async def get_all_endpoints_metrics():
    """Get metrics for all endpoints"""
    query = """
    SELECT 
        endpoint,
        method,
        total_calls,
        CASE 
            WHEN total_calls > 0 
            THEN (successful_calls::FLOAT / total_calls * 100)
            ELSE 0 
        END as success_rate,
        CASE 
            WHEN total_calls > 0 
            THEN (total_response_time_ms::FLOAT / total_calls)
            ELSE 0 
        END as avg_response_time,
        min_response_time_ms,
        max_response_time_ms,
        last_called_at
    FROM endpoint_metrics
    ORDER BY total_calls DESC
    LIMIT 50
    """
    
    endpoints = db.fetchall(query)
    
    return {"endpoints": endpoints}

@router.get("/endpoints/{endpoint}/metrics")
async def get_endpoint_metrics(
    endpoint: str,
    method: str = Query("GET")
):
    """Get metrics for specific endpoint"""
    tracker = APIUsageTracker(db)
    metrics = tracker.get_endpoint_metrics(endpoint, method)
    
    return {
        "endpoint": endpoint,
        "method": method,
        "success_rate": metrics.success_rate,
        "avg_response_time": metrics.avg_response_time,
        "p95_response_time": metrics.p95_response_time,
        "requests_per_minute": metrics.requests_per_minute,
        "error_types": metrics.error_types
    }

@router.get("/endpoints/slow")
async def get_slow_endpoints(
    threshold_ms: int = Query(1000, ge=100, le=10000)
):
    """Get slow endpoints"""
    tracker = APIUsageTracker(db)
    slow_endpoints = tracker.get_slow_endpoints(threshold_ms)
    
    return {
        "threshold_ms": threshold_ms,
        "slow_endpoints": slow_endpoints
    }

@router.post("/keys/generate")
async def generate_api_key(
    name: str,
    user_id: str = Depends(get_current_user)
):
    """Generate new API key"""
    tracker = APIUsageTracker(db)
    api_key = tracker.generate_api_key(user_id, name)
    
    return {
        "api_key": api_key,
        "name": name,
        "message": "Store this key securely. It won't be shown again."
    }

@router.get("/keys/{user_id}")
async def get_user_api_keys(user_id: str):
    """Get user's API keys (without revealing the actual keys)"""
    query = """
    SELECT 
        SUBSTRING(api_key, 1, 8) || '...' as key_prefix,
        name,
        created_at,
        last_used_at,
        is_active,
        request_count
    FROM api_keys
    WHERE user_id = %s
    ORDER BY created_at DESC
    """
    
    keys = db.fetchall(query, (user_id,))
    
    return {
        "user_id": user_id,
        "api_keys": keys
    }

@router.get("/rate-limit/{user_id}")
async def check_rate_limit(
    user_id: str,
    endpoint: str = Query("/api/default")
):
    """Check rate limit status"""
    tracker = APIUsageTracker(db)
    allowed, limit_info = tracker.check_rate_limit(user_id, endpoint)
    
    return {
        "user_id": user_id,
        "endpoint": endpoint,
        "allowed": allowed,
        **limit_info
    }
```

## React Dashboard Component

```tsx
import React, { useState, useEffect } from 'react';
import { Activity, AlertTriangle, Key, TrendingUp, Clock } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface APIUsageSummary {
  totalRequests: number;
  successRate: number;
  avgResponseTime: number;
  totalDataMb: number;
  mostUsedEndpoints: string[];
}

interface EndpointMetric {
  endpoint: string;
  method: string;
  totalCalls: number;
  successRate: number;
  avgResponseTime: number;
  lastCalledAt: string;
}

interface APIKey {
  keyPrefix: string;
  name: string;
  createdAt: string;
  lastUsedAt?: string;
  isActive: boolean;
  requestCount: number;
}

export const APIUsageDashboard: React.FC = () => {
  const [summary, setSummary] = useState<APIUsageSummary | null>(null);
  const [endpoints, setEndpoints] = useState<EndpointMetric[]>([]);
  const [slowEndpoints, setSlowEndpoints] = useState<any[]>([]);
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [recentRequests, setRecentRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId] = useState('current-user');

  useEffect(() => {
    fetchAPIData();
  }, []);

  const fetchAPIData = async () => {
    try {
      const [summaryRes, endpointsRes, slowRes, keysRes, recentRes] = await Promise.all([
        fetch(`/api/usage/user/${userId}/summary`),
        fetch('/api/usage/endpoints/metrics'),
        fetch('/api/usage/endpoints/slow?threshold_ms=1000'),
        fetch(`/api/usage/keys/${userId}`),
        fetch(`/api/usage/user/${userId}/recent?hours=24`)
      ]);

      const summaryData = await summaryRes.json();
      const endpointsData = await endpointsRes.json();
      const slowData = await slowRes.json();
      const keysData = await keysRes.json();
      const recentData = await recentRes.json();

      setSummary(summaryData);
      setEndpoints(endpointsData.endpoints);
      setSlowEndpoints(slowData.slow_endpoints);
      setApiKeys(keysData.api_keys);
      setRecentRequests(recentData.requests);
    } catch (error) {
      console.error('Error fetching API data:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateNewKey = async () => {
    const name = prompt('Enter a name for the API key:');
    if (!name) return;

    try {
      const res = await fetch('/api/usage/keys/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'current-user-key'
        },
        body: JSON.stringify({ name })
      });

      const data = await res.json();
      alert(`New API Key: ${data.api_key}\n\nStore this securely!`);
      fetchAPIData();
    } catch (error) {
      console.error('Error generating API key:', error);
    }
  };

  const getStatusColor = (code: number) => {
    if (code >= 200 && code < 300) return 'text-green-600';
    if (code >= 300 && code < 400) return 'text-blue-600';
    if (code >= 400 && code < 500) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (loading) return <div>Loading API usage data...</div>;

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">API Usage Analytics</h2>

      {/* Usage Summary */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <Activity className="w-5 h-5 text-blue-500" />
              <span className="text-sm text-gray-500">Total Requests</span>
            </div>
            <div className="text-2xl font-bold">{summary.totalRequests.toLocaleString()}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="w-5 h-5 text-green-500" />
              <span className="text-sm text-gray-500">Success Rate</span>
            </div>
            <div className="text-2xl font-bold">{summary.successRate.toFixed(1)}%</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <Clock className="w-5 h-5 text-yellow-500" />
              <span className="text-sm text-gray-500">Avg Response</span>
            </div>
            <div className="text-2xl font-bold">{Math.round(summary.avgResponseTime)}ms</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Data Transfer</div>
            <div className="text-2xl font-bold">{summary.totalDataMb.toFixed(2)} MB</div>
          </div>
        </div>
      )}

      {/* Most Used Endpoints */}
      {summary && summary.mostUsedEndpoints.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Most Used Endpoints</h3>
          <div className="flex flex-wrap gap-2">
            {summary.mostUsedEndpoints.map((endpoint, idx) => (
              <span
                key={idx}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
              >
                {endpoint}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Endpoint Performance */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Endpoint Performance</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Endpoint</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Method</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Calls</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Success Rate</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Avg Time</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Last Called</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {endpoints.slice(0, 10).map((endpoint, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm font-medium">{endpoint.endpoint}</td>
                  <td className="px-4 py-2 text-sm">
                    <span className={`px-2 py-1 text-xs rounded ${
                      endpoint.method === 'GET' ? 'bg-green-100 text-green-800' :
                      endpoint.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                      endpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                      endpoint.method === 'DELETE' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {endpoint.method}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm">{endpoint.totalCalls.toLocaleString()}</td>
                  <td className="px-4 py-2 text-sm">
                    <span className={endpoint.successRate > 95 ? 'text-green-600' : 'text-yellow-600'}>
                      {endpoint.successRate.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm">{Math.round(endpoint.avgResponseTime)}ms</td>
                  <td className="px-4 py-2 text-sm">
                    {new Date(endpoint.lastCalledAt).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Slow Endpoints Alert */}
      {slowEndpoints.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 p-6 rounded-lg">
          <div className="flex items-center mb-4">
            <AlertTriangle className="w-5 h-5 text-yellow-600 mr-2" />
            <h3 className="text-lg font-semibold text-yellow-900">Slow Endpoints</h3>
          </div>
          <div className="space-y-2">
            {slowEndpoints.slice(0, 5).map((endpoint, idx) => (
              <div key={idx} className="flex justify-between items-center p-2 bg-white rounded">
                <span className="text-sm font-medium">{endpoint.endpoint}</span>
                <span className="text-sm text-red-600">
                  {Math.round(endpoint.avg_response_time)}ms avg
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* API Keys */}
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Key className="w-5 h-5" />
            API Keys
          </h3>
          <button
            onClick={generateNewKey}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Generate New Key
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Name</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Key</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Created</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Last Used</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Requests</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {apiKeys.map((key, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm font-medium">{key.name}</td>
                  <td className="px-4 py-2 text-sm font-mono">{key.keyPrefix}</td>
                  <td className="px-4 py-2 text-sm">
                    {new Date(key.createdAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {key.lastUsedAt ? new Date(key.lastUsedAt).toLocaleDateString() : 'Never'}
                  </td>
                  <td className="px-4 py-2 text-sm">{key.requestCount.toLocaleString()}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 text-xs rounded ${
                      key.isActive ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {key.isActive ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Requests */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Recent Requests (24h)</h3>
        <div className="space-y-2">
          {recentRequests.slice(0, 10).map((request, idx) => (
            <div key={idx} className="flex items-center justify-between py-2 border-b">
              <div className="flex items-center space-x-3">
                <span className={`text-sm font-bold ${getStatusColor(request.status_code)}`}>
                  {request.status_code}
                </span>
                <span className="text-sm font-medium">{request.method}</span>
                <span className="text-sm">{request.endpoint}</span>
              </div>
              <div className="flex items-center space-x-3">
                <span className="text-sm text-gray-500">{request.response_time_ms}ms</span>
                <span className="text-sm text-gray-400">
                  {new Date(request.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

## Implementation Priority
- **Phase 1**: Basic request tracking
- **Phase 2**: Rate limiting
- **Phase 3**: API key management
- **Phase 4**: Performance analytics

## Performance Considerations
- Efficient rate limit checking
- Batch updates for metrics
- Daily aggregation for statistics
- Limited request history (30 days)

## Security Considerations
- Secure API key generation
- Rate limiting per user/endpoint
- No sensitive data in logs
- IP address tracking for security

## Monitoring and Alerts
- Alert on high error rates (>10%)
- Alert on slow endpoints (>2s)
- Alert on rate limit violations
- Daily API usage report

## Dependencies
- PostgreSQL for data storage
- FastAPI with authentication
- Secrets library for key generation
- React with Recharts for visualization