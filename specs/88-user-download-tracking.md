# User Download Tracking Specification

## Overview
Track file downloads and resource access without complex DRM systems. Monitor what users download, when, and how often.

## TypeScript Interfaces

```typescript
// Download event
interface DownloadEvent {
  download_id: string;
  user_id: string;
  file_id: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  started_at: Date;
  completed_at?: Date;
  status: 'started' | 'completed' | 'failed' | 'cancelled';
  download_speed_kbps?: number;
  resume_count: number;
}

// File metadata
interface FileMetadata {
  file_id: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  mime_type: string;
  category: string;
  upload_date: Date;
  total_downloads: number;
  unique_downloaders: number;
}

// User download summary
interface UserDownloadSummary {
  user_id: string;
  total_downloads: number;
  total_size_mb: number;
  favorite_file_types: string[];
  avg_download_speed_kbps: number;
  failed_downloads: number;
  completion_rate: number;
}

// Download analytics
interface DownloadAnalytics {
  file_id: string;
  download_count: number;
  unique_users: number;
  avg_download_time_seconds: number;
  peak_download_hour: number;
  geographic_distribution: Record<string, number>;
}
```

## SQL Schema

```sql
-- Download events table
CREATE TABLE download_events (
    download_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    file_id VARCHAR(255) NOT NULL,
    file_name VARCHAR(500),
    file_type VARCHAR(50),
    file_size_bytes BIGINT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'started',
    download_speed_kbps INTEGER,
    resume_count INTEGER DEFAULT 0,
    ip_address VARCHAR(45),
    user_agent TEXT,
    referrer VARCHAR(500)
);

-- File metadata
CREATE TABLE file_metadata (
    file_id VARCHAR(255) PRIMARY KEY,
    file_name VARCHAR(500) NOT NULL,
    file_path TEXT,
    file_type VARCHAR(50),
    file_extension VARCHAR(20),
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    category VARCHAR(50),
    tags TEXT[],
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by VARCHAR(255),
    is_public BOOLEAN DEFAULT true,
    access_count INTEGER DEFAULT 0
);

-- User download summary
CREATE TABLE user_download_summary (
    user_id VARCHAR(255) PRIMARY KEY,
    total_downloads INTEGER DEFAULT 0,
    completed_downloads INTEGER DEFAULT 0,
    failed_downloads INTEGER DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    favorite_file_types TEXT[],
    avg_download_speed_kbps INTEGER DEFAULT 0,
    first_download_at TIMESTAMP,
    last_download_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File download statistics
CREATE TABLE file_download_stats (
    file_id VARCHAR(255) PRIMARY KEY,
    total_downloads INTEGER DEFAULT 0,
    unique_downloaders INTEGER DEFAULT 0,
    total_bandwidth_bytes BIGINT DEFAULT 0,
    avg_download_time_seconds INTEGER DEFAULT 0,
    peak_download_hour INTEGER,
    last_downloaded_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily download statistics
CREATE TABLE daily_download_stats (
    date DATE NOT NULL,
    file_type VARCHAR(50),
    total_downloads INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    total_size_mb DECIMAL(10,2) DEFAULT 0,
    avg_speed_kbps INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    PRIMARY KEY (date, file_type)
);

-- Download queue (for tracking partial downloads)
CREATE TABLE download_queue (
    queue_id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    file_id VARCHAR(255) NOT NULL,
    bytes_downloaded BIGINT DEFAULT 0,
    total_bytes BIGINT,
    status VARCHAR(20) DEFAULT 'queued',
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Basic indexes
CREATE INDEX idx_downloads_user ON download_events(user_id);
CREATE INDEX idx_downloads_file ON download_events(file_id);
CREATE INDEX idx_downloads_started ON download_events(started_at DESC);
CREATE INDEX idx_downloads_status ON download_events(status);
CREATE INDEX idx_metadata_category ON file_metadata(category);
CREATE INDEX idx_metadata_type ON file_metadata(file_type);
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import uuid
import mimetypes
import os
from collections import Counter, defaultdict

@dataclass
class DownloadMetrics:
    """Download performance metrics"""
    file_id: str
    total_downloads: number
    completion_rate: float
    avg_speed_kbps: float
    peak_hour: int
    popular_regions: List[str]

class DownloadTracker:
    """Track file downloads and access patterns"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def start_download(
        self,
        user_id: str,
        file_id: str,
        file_name: str,
        file_size_bytes: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> str:
        """Track download start"""
        download_id = str(uuid.uuid4())
        
        # Get file metadata
        file_info = self.get_file_metadata(file_id)
        
        if not file_info:
            # Create metadata entry if doesn't exist
            file_type = self.get_file_type(file_name)
            self.create_file_metadata(file_id, file_name, file_size_bytes, file_type)
        
        query = """
        INSERT INTO download_events
        (download_id, user_id, file_id, file_name, file_type, 
         file_size_bytes, ip_address, user_agent, referrer)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING download_id
        """
        
        file_type = file_info['file_type'] if file_info else self.get_file_type(file_name)
        
        result = self.db.fetchone(query, (
            download_id, user_id, file_id, file_name, file_type,
            file_size_bytes, ip_address, user_agent, referrer
        ))
        
        # Update file access count
        self.increment_access_count(file_id)
        
        # Add to download queue
        self.add_to_queue(user_id, file_id, file_size_bytes)
        
        return result['download_id']
    
    def complete_download(
        self,
        download_id: str,
        download_speed_kbps: Optional[int] = None
    ) -> bool:
        """Mark download as completed"""
        query = """
        UPDATE download_events
        SET 
            completed_at = CURRENT_TIMESTAMP,
            status = 'completed',
            download_speed_kbps = %s
        WHERE download_id = %s
        AND status = 'started'
        """
        
        result = self.db.execute(query, (download_speed_kbps, download_id))
        
        if result.rowcount > 0:
            # Get download info for updates
            download_info = self.get_download_info(download_id)
            
            if download_info:
                # Update user summary
                self.update_user_summary(
                    download_info['user_id'],
                    download_info['file_size_bytes'],
                    download_speed_kbps,
                    'completed'
                )
                
                # Update file statistics
                self.update_file_stats(
                    download_info['file_id'],
                    download_info['file_size_bytes'],
                    download_info['started_at'],
                    datetime.now()
                )
                
                # Remove from queue
                self.remove_from_queue(download_info['user_id'], download_info['file_id'])
            
            return True
        
        return False
    
    def fail_download(
        self,
        download_id: str,
        error_message: Optional[str] = None
    ) -> bool:
        """Mark download as failed"""
        query = """
        UPDATE download_events
        SET 
            status = 'failed',
            completed_at = CURRENT_TIMESTAMP
        WHERE download_id = %s
        """
        
        result = self.db.execute(query, (download_id,))
        
        if result.rowcount > 0:
            download_info = self.get_download_info(download_id)
            if download_info:
                self.update_user_summary(
                    download_info['user_id'],
                    0,
                    0,
                    'failed'
                )
            
            return True
        
        return False
    
    def cancel_download(self, download_id: str) -> bool:
        """Cancel download"""
        query = """
        UPDATE download_events
        SET status = 'cancelled'
        WHERE download_id = %s
        AND status = 'started'
        """
        
        result = self.db.execute(query, (download_id,))
        return result.rowcount > 0
    
    def resume_download(
        self,
        user_id: str,
        file_id: str,
        bytes_downloaded: int
    ) -> str:
        """Resume a partial download"""
        # Check for existing partial download
        query = """
        SELECT download_id, resume_count
        FROM download_events
        WHERE user_id = %s
        AND file_id = %s
        AND status IN ('started', 'cancelled')
        ORDER BY started_at DESC
        LIMIT 1
        """
        
        existing = self.db.fetchone(query, (user_id, file_id))
        
        if existing:
            # Update existing download
            update_query = """
            UPDATE download_events
            SET 
                resume_count = resume_count + 1,
                status = 'started'
            WHERE download_id = %s
            """
            self.db.execute(update_query, (existing['download_id'],))
            
            # Update queue
            self.update_queue_progress(user_id, file_id, bytes_downloaded)
            
            return existing['download_id']
        else:
            # Start new download with resume
            file_info = self.get_file_metadata(file_id)
            if file_info:
                return self.start_download(
                    user_id, file_id, 
                    file_info['file_name'],
                    file_info['file_size_bytes']
                )
            
            return ""
    
    def get_file_type(self, file_name: str) -> str:
        """Determine file type from filename"""
        ext = os.path.splitext(file_name)[1].lower()
        
        type_mapping = {
            '.pdf': 'document',
            '.doc': 'document',
            '.docx': 'document',
            '.xls': 'spreadsheet',
            '.xlsx': 'spreadsheet',
            '.csv': 'data',
            '.zip': 'archive',
            '.rar': 'archive',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.png': 'image',
            '.gif': 'image',
            '.mp4': 'video',
            '.avi': 'video',
            '.mp3': 'audio',
            '.wav': 'audio',
            '.exe': 'executable',
            '.dmg': 'executable',
            '.txt': 'text',
            '.json': 'data',
            '.xml': 'data'
        }
        
        return type_mapping.get(ext, 'other')
    
    def create_file_metadata(
        self,
        file_id: str,
        file_name: str,
        file_size_bytes: int,
        file_type: str
    ) -> None:
        """Create file metadata entry"""
        mime_type, _ = mimetypes.guess_type(file_name)
        extension = os.path.splitext(file_name)[1]
        
        query = """
        INSERT INTO file_metadata
        (file_id, file_name, file_type, file_extension, 
         file_size_bytes, mime_type, category)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (file_id) DO NOTHING
        """
        
        self.db.execute(query, (
            file_id, file_name, file_type, extension,
            file_size_bytes, mime_type or 'application/octet-stream',
            file_type
        ))
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict]:
        """Get file metadata"""
        query = """
        SELECT * FROM file_metadata
        WHERE file_id = %s
        """
        return self.db.fetchone(query, (file_id,))
    
    def increment_access_count(self, file_id: str) -> None:
        """Increment file access count"""
        query = """
        UPDATE file_metadata
        SET access_count = access_count + 1
        WHERE file_id = %s
        """
        self.db.execute(query, (file_id,))
    
    def add_to_queue(
        self,
        user_id: str,
        file_id: str,
        total_bytes: int,
        priority: int = 0
    ) -> None:
        """Add download to queue"""
        query = """
        INSERT INTO download_queue
        (user_id, file_id, total_bytes, priority)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """
        self.db.execute(query, (user_id, file_id, total_bytes, priority))
    
    def update_queue_progress(
        self,
        user_id: str,
        file_id: str,
        bytes_downloaded: int
    ) -> None:
        """Update download progress in queue"""
        query = """
        UPDATE download_queue
        SET 
            bytes_downloaded = %s,
            status = CASE 
                WHEN bytes_downloaded >= total_bytes THEN 'completed'
                ELSE 'downloading'
            END
        WHERE user_id = %s
        AND file_id = %s
        """
        self.db.execute(query, (bytes_downloaded, user_id, file_id))
    
    def remove_from_queue(self, user_id: str, file_id: str) -> None:
        """Remove from download queue"""
        query = """
        DELETE FROM download_queue
        WHERE user_id = %s
        AND file_id = %s
        """
        self.db.execute(query, (user_id, file_id))
    
    def get_download_info(self, download_id: str) -> Optional[Dict]:
        """Get download information"""
        query = """
        SELECT * FROM download_events
        WHERE download_id = %s
        """
        return self.db.fetchone(query, (download_id,))
    
    def update_user_summary(
        self,
        user_id: str,
        file_size_bytes: int,
        speed_kbps: Optional[int],
        status: str
    ) -> None:
        """Update user download summary"""
        query = """
        INSERT INTO user_download_summary
        (user_id, total_downloads, completed_downloads, failed_downloads,
         total_size_bytes, avg_download_speed_kbps, first_download_at)
        VALUES (%s, 1, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id)
        DO UPDATE SET
            total_downloads = user_download_summary.total_downloads + 1,
            completed_downloads = user_download_summary.completed_downloads + %s,
            failed_downloads = user_download_summary.failed_downloads + %s,
            total_size_bytes = user_download_summary.total_size_bytes + %s,
            avg_download_speed_kbps = CASE
                WHEN %s IS NOT NULL AND user_download_summary.completed_downloads > 0
                THEN ((user_download_summary.avg_download_speed_kbps * user_download_summary.completed_downloads + %s) /
                      (user_download_summary.completed_downloads + %s))::INTEGER
                ELSE user_download_summary.avg_download_speed_kbps
            END,
            last_download_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        """
        
        completed = 1 if status == 'completed' else 0
        failed = 1 if status == 'failed' else 0
        
        self.db.execute(query, (
            user_id, completed, failed, file_size_bytes if completed else 0, speed_kbps or 0,
            completed, failed, file_size_bytes if completed else 0,
            speed_kbps, speed_kbps or 0, completed
        ))
        
        # Update favorite file types
        self.update_favorite_types(user_id)
    
    def update_favorite_types(self, user_id: str) -> None:
        """Update user's favorite file types"""
        query = """
        WITH type_counts AS (
            SELECT file_type, COUNT(*) as count
            FROM download_events
            WHERE user_id = %s
            AND status = 'completed'
            GROUP BY file_type
            ORDER BY count DESC
            LIMIT 5
        )
        UPDATE user_download_summary
        SET favorite_file_types = (
            SELECT ARRAY_AGG(file_type)
            FROM type_counts
        )
        WHERE user_id = %s
        """
        self.db.execute(query, (user_id, user_id))
    
    def update_file_stats(
        self,
        file_id: str,
        file_size_bytes: int,
        start_time: datetime,
        end_time: datetime
    ) -> None:
        """Update file download statistics"""
        download_time = (end_time - start_time).total_seconds()
        
        query = """
        INSERT INTO file_download_stats
        (file_id, total_downloads, unique_downloaders, total_bandwidth_bytes,
         avg_download_time_seconds, peak_download_hour, last_downloaded_at)
        VALUES (%s, 1, 1, %s, %s, EXTRACT(HOUR FROM CURRENT_TIMESTAMP), CURRENT_TIMESTAMP)
        ON CONFLICT (file_id)
        DO UPDATE SET
            total_downloads = file_download_stats.total_downloads + 1,
            total_bandwidth_bytes = file_download_stats.total_bandwidth_bytes + %s,
            avg_download_time_seconds = 
                ((file_download_stats.avg_download_time_seconds * file_download_stats.total_downloads + %s) /
                 (file_download_stats.total_downloads + 1))::INTEGER,
            peak_download_hour = EXTRACT(HOUR FROM CURRENT_TIMESTAMP),
            last_downloaded_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        """
        
        self.db.execute(query, (
            file_id, file_size_bytes, int(download_time),
            file_size_bytes, int(download_time)
        ))
        
        # Update unique downloaders
        self.update_unique_downloaders(file_id)
    
    def update_unique_downloaders(self, file_id: str) -> None:
        """Update unique downloader count"""
        query = """
        UPDATE file_download_stats
        SET unique_downloaders = (
            SELECT COUNT(DISTINCT user_id)
            FROM download_events
            WHERE file_id = %s
            AND status = 'completed'
        )
        WHERE file_id = %s
        """
        self.db.execute(query, (file_id, file_id))
    
    def get_user_downloads(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user's download history"""
        query = """
        SELECT 
            download_id,
            file_id,
            file_name,
            file_type,
            file_size_bytes,
            started_at,
            completed_at,
            status,
            download_speed_kbps
        FROM download_events
        WHERE user_id = %s
        AND started_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        ORDER BY started_at DESC
        """
        return self.db.fetchall(query, (user_id, days))
    
    def get_popular_files(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """Get most downloaded files"""
        query = """
        SELECT 
            f.file_id,
            f.file_name,
            f.file_type,
            f.file_size_bytes,
            s.total_downloads,
            s.unique_downloaders,
            s.last_downloaded_at
        FROM file_metadata f
        JOIN file_download_stats s ON f.file_id = s.file_id
        WHERE s.last_downloaded_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        ORDER BY s.total_downloads DESC
        LIMIT %s
        """
        return self.db.fetchall(query, (days, limit))
    
    def get_download_analytics(self, file_id: str) -> Dict:
        """Get download analytics for a file"""
        query = """
        WITH hourly_distribution AS (
            SELECT 
                EXTRACT(HOUR FROM started_at) as hour,
                COUNT(*) as downloads
            FROM download_events
            WHERE file_id = %s
            AND status = 'completed'
            GROUP BY EXTRACT(HOUR FROM started_at)
        ),
        geo_distribution AS (
            SELECT 
                SUBSTRING(ip_address, 1, POSITION('.' IN ip_address) + 3) as region,
                COUNT(*) as downloads
            FROM download_events
            WHERE file_id = %s
            AND status = 'completed'
            AND ip_address IS NOT NULL
            GROUP BY region
            LIMIT 10
        )
        SELECT 
            s.total_downloads,
            s.unique_downloaders,
            s.avg_download_time_seconds,
            s.peak_download_hour,
            (s.total_bandwidth_bytes::FLOAT / 1048576) as total_bandwidth_mb,
            ARRAY_AGG(DISTINCT h.hour ORDER BY h.downloads DESC) as peak_hours,
            json_object_agg(g.region, g.downloads) as geographic_distribution
        FROM file_download_stats s
        CROSS JOIN hourly_distribution h
        CROSS JOIN geo_distribution g
        WHERE s.file_id = %s
        GROUP BY s.total_downloads, s.unique_downloaders, s.avg_download_time_seconds,
                 s.peak_download_hour, s.total_bandwidth_bytes
        """
        
        result = self.db.fetchone(query, (file_id, file_id, file_id))
        
        return result if result else {
            'total_downloads': 0,
            'unique_downloaders': 0,
            'avg_download_time_seconds': 0,
            'total_bandwidth_mb': 0
        }
    
    def calculate_daily_stats(self, date: Optional[datetime] = None) -> None:
        """Calculate daily download statistics"""
        target_date = date or datetime.now().date()
        
        query = """
        INSERT INTO daily_download_stats
        (date, file_type, total_downloads, unique_users, total_size_mb,
         avg_speed_kbps, failed_count)
        SELECT 
            DATE(started_at) as date,
            file_type,
            COUNT(*) as total_downloads,
            COUNT(DISTINCT user_id) as unique_users,
            SUM(CASE WHEN status = 'completed' THEN file_size_bytes ELSE 0 END)::FLOAT / 1048576 as total_mb,
            AVG(CASE WHEN status = 'completed' THEN download_speed_kbps END)::INTEGER as avg_speed,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count
        FROM download_events
        WHERE DATE(started_at) = %s
        GROUP BY DATE(started_at), file_type
        ON CONFLICT (date, file_type)
        DO UPDATE SET
            total_downloads = EXCLUDED.total_downloads,
            unique_users = EXCLUDED.unique_users,
            total_size_mb = EXCLUDED.total_size_mb,
            avg_speed_kbps = EXCLUDED.avg_speed_kbps,
            failed_count = EXCLUDED.failed_count
        """
        
        self.db.execute(query, (target_date,))
```

## API Endpoints

```python
from fastapi import APIRouter, Query, HTTPException, Body, Response
from typing import List, Optional
import os

router = APIRouter(prefix="/api/downloads", tags=["downloads"])

@router.post("/start")
async def start_download(
    user_id: str = Body(...),
    file_id: str = Body(...),
    file_name: str = Body(...),
    file_size_bytes: int = Body(...)
):
    """Start tracking a download"""
    tracker = DownloadTracker(db)
    download_id = tracker.start_download(
        user_id, file_id, file_name, file_size_bytes
    )
    
    return {
        "download_id": download_id,
        "status": "started"
    }

@router.post("/complete/{download_id}")
async def complete_download(
    download_id: str,
    download_speed_kbps: Optional[int] = Body(None)
):
    """Mark download as completed"""
    tracker = DownloadTracker(db)
    success = tracker.complete_download(download_id, download_speed_kbps)
    
    if not success:
        raise HTTPException(status_code=404, detail="Download not found or already completed")
    
    return {"status": "completed", "download_id": download_id}

@router.post("/fail/{download_id}")
async def fail_download(
    download_id: str,
    error_message: Optional[str] = Body(None)
):
    """Mark download as failed"""
    tracker = DownloadTracker(db)
    success = tracker.fail_download(download_id, error_message)
    
    return {"status": "failed" if success else "not_found"}

@router.post("/cancel/{download_id}")
async def cancel_download(download_id: str):
    """Cancel a download"""
    tracker = DownloadTracker(db)
    success = tracker.cancel_download(download_id)
    
    return {"status": "cancelled" if success else "not_found"}

@router.post("/resume")
async def resume_download(
    user_id: str = Body(...),
    file_id: str = Body(...),
    bytes_downloaded: int = Body(0)
):
    """Resume a partial download"""
    tracker = DownloadTracker(db)
    download_id = tracker.resume_download(user_id, file_id, bytes_downloaded)
    
    return {
        "download_id": download_id,
        "status": "resumed" if download_id else "not_found"
    }

@router.get("/user/{user_id}/history")
async def get_user_download_history(
    user_id: str,
    days: int = Query(30, ge=1, le=90)
):
    """Get user's download history"""
    tracker = DownloadTracker(db)
    downloads = tracker.get_user_downloads(user_id, days)
    
    return {
        "user_id": user_id,
        "downloads": downloads,
        "count": len(downloads)
    }

@router.get("/user/{user_id}/summary")
async def get_user_download_summary(user_id: str):
    """Get user's download summary"""
    query = """
    SELECT 
        total_downloads,
        completed_downloads,
        failed_downloads,
        (total_size_bytes::FLOAT / 1048576) as total_size_mb,
        favorite_file_types,
        avg_download_speed_kbps,
        CASE 
            WHEN total_downloads > 0 
            THEN (completed_downloads::FLOAT / total_downloads * 100)
            ELSE 0 
        END as completion_rate
    FROM user_download_summary
    WHERE user_id = %s
    """
    
    result = db.fetchone(query, (user_id,))
    
    if not result:
        return {
            "user_id": user_id,
            "total_downloads": 0,
            "completion_rate": 0
        }
    
    return result

@router.get("/files/popular")
async def get_popular_files(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=50)
):
    """Get most downloaded files"""
    tracker = DownloadTracker(db)
    files = tracker.get_popular_files(days, limit)
    
    return {
        "files": files,
        "period_days": days
    }

@router.get("/files/{file_id}/analytics")
async def get_file_analytics(file_id: str):
    """Get download analytics for a file"""
    tracker = DownloadTracker(db)
    analytics = tracker.get_download_analytics(file_id)
    
    return analytics

@router.get("/queue/{user_id}")
async def get_user_download_queue(user_id: str):
    """Get user's download queue"""
    query = """
    SELECT 
        q.file_id,
        f.file_name,
        q.bytes_downloaded,
        q.total_bytes,
        CASE 
            WHEN q.total_bytes > 0 
            THEN (q.bytes_downloaded::FLOAT / q.total_bytes * 100)
            ELSE 0 
        END as progress_percent,
        q.status,
        q.priority
    FROM download_queue q
    LEFT JOIN file_metadata f ON q.file_id = f.file_id
    WHERE q.user_id = %s
    AND q.status != 'completed'
    ORDER BY q.priority DESC, q.created_at
    """
    
    queue = db.fetchall(query, (user_id,))
    
    return {
        "user_id": user_id,
        "queue": queue,
        "count": len(queue)
    }

@router.get("/stats/daily")
async def get_daily_download_stats(
    date: Optional[str] = Query(None)
):
    """Get daily download statistics"""
    target_date = date or datetime.now().date().isoformat()
    
    query = """
    SELECT 
        file_type,
        total_downloads,
        unique_users,
        total_size_mb,
        avg_speed_kbps,
        failed_count,
        CASE 
            WHEN total_downloads > 0 
            THEN ((total_downloads - failed_count)::FLOAT / total_downloads * 100)
            ELSE 0 
        END as success_rate
    FROM daily_download_stats
    WHERE date = %s
    ORDER BY total_downloads DESC
    """
    
    stats = db.fetchall(query, (target_date,))
    
    # Calculate totals
    totals = {
        'total_downloads': sum(s['total_downloads'] for s in stats),
        'total_size_mb': sum(s['total_size_mb'] for s in stats),
        'total_failed': sum(s['failed_count'] for s in stats)
    }
    
    return {
        "date": target_date,
        "stats_by_type": stats,
        "totals": totals
    }

@router.get("/bandwidth/usage")
async def get_bandwidth_usage(
    days: int = Query(7, ge=1, le=30)
):
    """Get bandwidth usage statistics"""
    query = """
    SELECT 
        DATE(started_at) as date,
        SUM(CASE WHEN status = 'completed' THEN file_size_bytes ELSE 0 END)::FLOAT / 1073741824 as total_gb,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(*) as total_downloads
    FROM download_events
    WHERE started_at >= CURRENT_DATE - INTERVAL '%s days'
    GROUP BY DATE(started_at)
    ORDER BY date DESC
    """
    
    usage = db.fetchall(query, (days,))
    
    return {
        "bandwidth_usage": usage,
        "period_days": days,
        "total_gb": sum(u['total_gb'] for u in usage)
    }
```

## React Dashboard Component

```tsx
import React, { useState, useEffect } from 'react';
import { Download, FileText, TrendingUp, HardDrive, AlertCircle } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DownloadHistory {
  downloadId: string;
  fileName: string;
  fileType: string;
  fileSizeBytes: number;
  startedAt: string;
  completedAt?: string;
  status: string;
  downloadSpeedKbps?: number;
}

interface PopularFile {
  fileId: string;
  fileName: string;
  fileType: string;
  totalDownloads: number;
  uniqueDownloaders: number;
  lastDownloadedAt: string;
}

interface BandwidthUsage {
  date: string;
  totalGb: number;
  uniqueUsers: number;
  totalDownloads: number;
}

export const DownloadTrackingDashboard: React.FC = () => {
  const [downloads, setDownloads] = useState<DownloadHistory[]>([]);
  const [popularFiles, setPopularFiles] = useState<PopularFile[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [bandwidth, setBandwidth] = useState<BandwidthUsage[]>([]);
  const [queue, setQueue] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId] = useState('current-user');

  useEffect(() => {
    fetchDownloadData();
  }, []);

  const fetchDownloadData = async () => {
    try {
      const [historyRes, popularRes, summaryRes, bandwidthRes, queueRes] = await Promise.all([
        fetch(`/api/downloads/user/${userId}/history?days=30`),
        fetch('/api/downloads/files/popular?days=7'),
        fetch(`/api/downloads/user/${userId}/summary`),
        fetch('/api/downloads/bandwidth/usage?days=7'),
        fetch(`/api/downloads/queue/${userId}`)
      ]);

      const historyData = await historyRes.json();
      const popularData = await popularRes.json();
      const summaryData = await summaryRes.json();
      const bandwidthData = await bandwidthRes.json();
      const queueData = await queueRes.json();

      setDownloads(historyData.downloads);
      setPopularFiles(popularData.files);
      setSummary(summaryData);
      setBandwidth(bandwidthData.bandwidth_usage);
      setQueue(queueData.queue);
    } catch (error) {
      console.error('Error fetching download data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
    return `${(bytes / 1073741824).toFixed(2)} GB`;
  };

  const formatSpeed = (kbps: number) => {
    if (kbps < 1024) return `${kbps} KB/s`;
    return `${(kbps / 1024).toFixed(1)} MB/s`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'started': return 'text-blue-600';
      case 'failed': return 'text-red-600';
      case 'cancelled': return 'text-gray-600';
      default: return 'text-gray-500';
    }
  };

  const getFileIcon = (fileType: string) => {
    const iconClass = "w-4 h-4";
    switch (fileType) {
      case 'document': return <FileText className={iconClass} />;
      case 'image': return '🖼️';
      case 'video': return '🎥';
      case 'audio': return '🎵';
      case 'archive': return '📦';
      default: return <FileText className={iconClass} />;
    }
  };

  if (loading) return <div>Loading download data...</div>;

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Download Tracking</h2>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <Download className="w-5 h-5 text-blue-500" />
              <span className="text-sm text-gray-500">Total</span>
            </div>
            <div className="text-2xl font-bold">{summary.total_downloads}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Completed</div>
            <div className="text-2xl font-bold text-green-600">
              {summary.completed_downloads}
            </div>
            <div className="text-xs text-gray-400">
              {summary.completion_rate?.toFixed(1)}% rate
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Failed</div>
            <div className="text-2xl font-bold text-red-600">
              {summary.failed_downloads}
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between mb-2">
              <HardDrive className="w-5 h-5 text-green-500" />
              <span className="text-sm text-gray-500">Total Size</span>
            </div>
            <div className="text-2xl font-bold">
              {summary.total_size_mb?.toFixed(1)} MB
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-500">Avg Speed</div>
            <div className="text-2xl font-bold">
              {summary.avg_download_speed_kbps 
                ? formatSpeed(summary.avg_download_speed_kbps)
                : '-'}
            </div>
          </div>
        </div>
      )}

      {/* Bandwidth Usage Chart */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Bandwidth Usage (7 Days)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={bandwidth}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="totalGb" stroke="#3b82f6" name="GB" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Download Queue */}
      {queue.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Download Queue</h3>
          <div className="space-y-2">
            {queue.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <div className="flex items-center space-x-3">
                  <div className="font-medium">{item.file_name}</div>
                  <span className="text-sm text-gray-500">
                    {formatFileSize(item.bytes_downloaded)} / {formatFileSize(item.total_bytes)}
                  </span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-32 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full"
                      style={{ width: `${item.progress_percent}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">{item.progress_percent.toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Popular Files */}
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Popular Files (7 Days)
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">File</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Type</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Downloads</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Unique Users</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Last Downloaded</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {popularFiles.map((file) => (
                <tr key={file.fileId} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <div className="flex items-center space-x-2">
                      {getFileIcon(file.fileType)}
                      <span className="text-sm font-medium">{file.fileName}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-sm">{file.fileType}</td>
                  <td className="px-4 py-2 text-sm font-semibold">{file.totalDownloads}</td>
                  <td className="px-4 py-2 text-sm">{file.uniqueDownloaders}</td>
                  <td className="px-4 py-2 text-sm">
                    {new Date(file.lastDownloadedAt).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Download History */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Your Recent Downloads</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">File</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Type</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Size</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Speed</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Started</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {downloads.slice(0, 10).map((download) => (
                <tr key={download.downloadId} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <div className="flex items-center space-x-2">
                      {getFileIcon(download.fileType)}
                      <span className="text-sm">{download.fileName}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-sm">{download.fileType}</td>
                  <td className="px-4 py-2 text-sm">{formatFileSize(download.fileSizeBytes)}</td>
                  <td className="px-4 py-2 text-sm">
                    {download.downloadSpeedKbps 
                      ? formatSpeed(download.downloadSpeedKbps)
                      : '-'}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {new Date(download.startedAt).toLocaleString()}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`text-sm capitalize ${getStatusColor(download.status)}`}>
                      {download.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Favorite File Types */}
      {summary && summary.favorite_file_types && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Your Favorite File Types</h3>
          <div className="flex flex-wrap gap-2">
            {summary.favorite_file_types.map((type: string, idx: number) => (
              <span
                key={idx}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
              >
                {type}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
```

## Implementation Priority
- **Phase 1**: Basic download tracking (start, complete, fail)
- **Phase 2**: Resume capability and queue management
- **Phase 3**: File analytics and popular files
- **Phase 4**: Bandwidth monitoring and optimization

## Performance Considerations
- Efficient queue management for partial downloads
- Batch updates for statistics
- Daily aggregation for bandwidth
- Limited download history (90 days)

## Security Considerations
- File access permission checks
- Download token validation
- Rate limiting per user
- Bandwidth throttling options

## Monitoring and Alerts
- Alert on high failure rates
- Alert on excessive bandwidth usage
- Daily download report
- Weekly popular files summary

## Dependencies
- PostgreSQL for data storage
- FastAPI for REST endpoints
- UUID for download IDs
- React with Recharts for visualization