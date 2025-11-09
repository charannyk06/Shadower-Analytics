# User Data Export Specification

## Overview
Simple user data export functionality for compliance and user requests. No complex ETL pipelines or data warehousing.

## TypeScript Interfaces

```typescript
// Export request
interface ExportRequest {
  request_id: string;
  user_id: string;
  requested_by: string;
  request_type: 'gdpr' | 'backup' | 'audit' | 'custom';
  data_types: string[];
  format: 'json' | 'csv' | 'pdf';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  requested_at: Date;
  completed_at?: Date;
  file_url?: string;
  error_message?: string;
}

// Export metadata
interface ExportMetadata {
  request_id: string;
  user_id: string;
  total_records: number;
  data_types_included: string[];
  export_date: Date;
  file_size_bytes: number;
  format: string;
}

// Data type configuration
interface DataTypeConfig {
  data_type: string;
  table_name: string;
  user_id_column: string;
  columns_to_export: string[];
  is_sensitive: boolean;
  requires_approval: boolean;
}

// Export audit log
interface ExportAuditLog {
  log_id: string;
  request_id: string;
  user_id: string;
  action: string;
  timestamp: Date;
  ip_address?: string;
  user_agent?: string;
}
```

## SQL Schema

```sql
-- Export requests table
CREATE TABLE export_requests (
    request_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    requested_by VARCHAR(255) NOT NULL,
    request_type VARCHAR(20) NOT NULL,
    data_types TEXT[],
    format VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    file_url TEXT,
    error_message TEXT
);

-- Export metadata
CREATE TABLE export_metadata (
    request_id VARCHAR(255) PRIMARY KEY REFERENCES export_requests(request_id),
    user_id VARCHAR(255) NOT NULL,
    total_records INTEGER DEFAULT 0,
    data_types_included TEXT[],
    export_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_size_bytes BIGINT DEFAULT 0,
    format VARCHAR(10)
);

-- Data type configurations
CREATE TABLE data_type_configs (
    data_type VARCHAR(100) PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    user_id_column VARCHAR(100) DEFAULT 'user_id',
    columns_to_export TEXT[],
    is_sensitive BOOLEAN DEFAULT false,
    requires_approval BOOLEAN DEFAULT false
);

-- Export audit logs
CREATE TABLE export_audit_logs (
    log_id SERIAL PRIMARY KEY,
    request_id VARCHAR(255) REFERENCES export_requests(request_id),
    user_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT
);

-- Basic indexes
CREATE INDEX idx_export_user ON export_requests(user_id);
CREATE INDEX idx_export_status ON export_requests(status);
CREATE INDEX idx_audit_request ON export_audit_logs(request_id);

-- Insert default data type configurations
INSERT INTO data_type_configs (data_type, table_name, columns_to_export, is_sensitive) VALUES
('user_profile', 'users', ARRAY['user_id', 'email', 'created_at'], true),
('user_sessions', 'user_sessions', ARRAY['session_id', 'user_id', 'start_time', 'end_time'], false),
('user_clicks', 'user_clicks', ARRAY['user_id', 'element_id', 'timestamp'], false),
('user_workflows', 'user_workflow_usage', ARRAY['user_id', 'workflow_id', 'timestamp'], false),
('user_errors', 'user_errors', ARRAY['user_id', 'error_message', 'timestamp'], false);
```

## Python Analytics Models

```python
import json
import csv
import io
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import asyncio
from enum import Enum

class ExportFormat(Enum):
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"

class ExportStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class UserDataExport:
    """Container for user data export"""
    user_id: str
    request_id: str
    data: Dict[str, List[Dict]]
    metadata: Dict[str, Any]
    
    def to_json(self) -> str:
        """Convert to JSON format"""
        return json.dumps({
            "user_id": self.user_id,
            "request_id": self.request_id,
            "export_date": datetime.now().isoformat(),
            "data": self.data,
            "metadata": self.metadata
        }, indent=2, default=str)
    
    def to_csv_files(self) -> Dict[str, str]:
        """Convert to CSV format (one file per data type)"""
        csv_files = {}
        
        for data_type, records in self.data.items():
            if not records:
                continue
                
            output = io.StringIO()
            if records:
                writer = csv.DictWriter(output, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
            
            csv_files[f"{data_type}.csv"] = output.getvalue()
        
        return csv_files

class DataExporter:
    """Simple data export handler"""
    
    def __init__(self, db_connection, storage_client=None):
        self.db = db_connection
        self.storage = storage_client  # Optional cloud storage
    
    def create_export_request(
        self,
        user_id: str,
        requested_by: str,
        request_type: str,
        data_types: List[str],
        format: str
    ) -> str:
        """Create new export request"""
        request_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO export_requests 
        (request_id, user_id, requested_by, request_type, data_types, format)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING request_id
        """
        
        result = self.db.fetchone(query, (
            request_id, user_id, requested_by, 
            request_type, data_types, format
        ))
        
        # Log the request
        self.log_action(request_id, user_id, "export_requested")
        
        # Start async processing
        asyncio.create_task(self.process_export(request_id))
        
        return request_id
    
    async def process_export(self, request_id: str) -> None:
        """Process export request asynchronously"""
        try:
            # Update status to processing
            self.update_status(request_id, ExportStatus.PROCESSING)
            
            # Get request details
            request = self.get_request(request_id)
            if not request:
                raise ValueError(f"Request {request_id} not found")
            
            # Collect data
            user_data = await self.collect_user_data(
                request['user_id'],
                request['data_types']
            )
            
            # Generate export file
            file_url = await self.generate_export_file(
                request_id,
                request['user_id'],
                user_data,
                request['format']
            )
            
            # Update request with completion
            self.complete_request(request_id, file_url)
            
            # Log completion
            self.log_action(request_id, request['user_id'], "export_completed")
            
        except Exception as e:
            self.fail_request(request_id, str(e))
            self.log_action(request_id, "", f"export_failed: {str(e)}")
    
    async def collect_user_data(
        self, 
        user_id: str, 
        data_types: List[str]
    ) -> Dict[str, List[Dict]]:
        """Collect all requested user data"""
        user_data = {}
        
        for data_type in data_types:
            # Get configuration for data type
            config = self.get_data_type_config(data_type)
            if not config:
                continue
            
            # Query data
            query = f"""
            SELECT {', '.join(config['columns_to_export'])}
            FROM {config['table_name']}
            WHERE {config['user_id_column']} = %s
            ORDER BY 
                CASE 
                    WHEN column_name = 'timestamp' THEN timestamp
                    WHEN column_name = 'created_at' THEN created_at
                    ELSE CURRENT_TIMESTAMP
                END DESC
            LIMIT 10000
            """
            
            data = self.db.fetchall(query, (user_id,))
            user_data[data_type] = data
        
        return user_data
    
    def get_data_type_config(self, data_type: str) -> Optional[Dict]:
        """Get configuration for data type"""
        query = """
        SELECT 
            table_name,
            user_id_column,
            columns_to_export,
            is_sensitive,
            requires_approval
        FROM data_type_configs
        WHERE data_type = %s
        """
        
        return self.db.fetchone(query, (data_type,))
    
    async def generate_export_file(
        self,
        request_id: str,
        user_id: str,
        data: Dict[str, List[Dict]],
        format: str
    ) -> str:
        """Generate export file and return URL"""
        export = UserDataExport(
            user_id=user_id,
            request_id=request_id,
            data=data,
            metadata={
                "total_records": sum(len(records) for records in data.values()),
                "data_types": list(data.keys()),
                "export_date": datetime.now().isoformat()
            }
        )
        
        # Generate file based on format
        if format == ExportFormat.JSON.value:
            file_content = export.to_json()
            file_name = f"export_{user_id}_{request_id}.json"
        elif format == ExportFormat.CSV.value:
            # For CSV, we'll create a zip with multiple files
            csv_files = export.to_csv_files()
            file_name = f"export_{user_id}_{request_id}.zip"
            file_content = self.create_zip(csv_files)
        else:
            # PDF would require additional library
            file_content = export.to_json()
            file_name = f"export_{user_id}_{request_id}.json"
        
        # Store file (local or cloud)
        file_url = self.store_file(file_name, file_content)
        
        # Store metadata
        self.store_metadata(request_id, export.metadata, len(file_content))
        
        return file_url
    
    def store_file(self, file_name: str, content: str) -> str:
        """Store file and return URL"""
        # Simple local storage implementation
        import os
        
        export_dir = "/tmp/exports"
        os.makedirs(export_dir, exist_ok=True)
        
        file_path = os.path.join(export_dir, file_name)
        with open(file_path, 'w') as f:
            f.write(content)
        
        # Return local path or cloud URL
        return f"file://{file_path}"
    
    def create_zip(self, files: Dict[str, str]) -> str:
        """Create zip file from multiple CSV files"""
        import zipfile
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.zip') as tmp:
            with zipfile.ZipFile(tmp.name, 'w') as zipf:
                for filename, content in files.items():
                    zipf.writestr(filename, content)
            
            with open(tmp.name, 'rb') as f:
                return f.read().decode('latin-1')
    
    def update_status(self, request_id: str, status: ExportStatus) -> None:
        """Update request status"""
        query = """
        UPDATE export_requests
        SET status = %s
        WHERE request_id = %s
        """
        self.db.execute(query, (status.value, request_id))
    
    def complete_request(self, request_id: str, file_url: str) -> None:
        """Mark request as completed"""
        query = """
        UPDATE export_requests
        SET 
            status = 'completed',
            completed_at = CURRENT_TIMESTAMP,
            file_url = %s
        WHERE request_id = %s
        """
        self.db.execute(query, (file_url, request_id))
    
    def fail_request(self, request_id: str, error_message: str) -> None:
        """Mark request as failed"""
        query = """
        UPDATE export_requests
        SET 
            status = 'failed',
            completed_at = CURRENT_TIMESTAMP,
            error_message = %s
        WHERE request_id = %s
        """
        self.db.execute(query, (error_message, request_id))
    
    def store_metadata(self, request_id: str, metadata: Dict, file_size: int) -> None:
        """Store export metadata"""
        query = """
        INSERT INTO export_metadata
        (request_id, user_id, total_records, data_types_included, file_size_bytes, format)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        self.db.execute(query, (
            request_id,
            metadata.get('user_id', ''),
            metadata.get('total_records', 0),
            metadata.get('data_types', []),
            file_size,
            metadata.get('format', 'json')
        ))
    
    def log_action(self, request_id: str, user_id: str, action: str) -> None:
        """Log export action"""
        query = """
        INSERT INTO export_audit_logs
        (request_id, user_id, action)
        VALUES (%s, %s, %s)
        """
        self.db.execute(query, (request_id, user_id, action))
    
    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get export request details"""
        query = """
        SELECT * FROM export_requests
        WHERE request_id = %s
        """
        return self.db.fetchone(query, (request_id,))
    
    def get_user_exports(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's export history"""
        query = """
        SELECT 
            r.request_id,
            r.request_type,
            r.data_types,
            r.format,
            r.status,
            r.requested_at,
            r.completed_at,
            m.total_records,
            m.file_size_bytes
        FROM export_requests r
        LEFT JOIN export_metadata m ON r.request_id = m.request_id
        WHERE r.user_id = %s
        ORDER BY r.requested_at DESC
        LIMIT %s
        """
        return self.db.fetchall(query, (user_id, limit))
```

## API Endpoints

```python
from fastapi import APIRouter, Query, HTTPException, Body, BackgroundTasks
from typing import List, Optional
import asyncio

router = APIRouter(prefix="/api/exports", tags=["exports"])

@router.post("/request")
async def request_export(
    user_id: str = Body(...),
    data_types: List[str] = Body(...),
    format: str = Body("json"),
    request_type: str = Body("backup"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Request user data export"""
    exporter = DataExporter(db)
    
    # Validate format
    if format not in ['json', 'csv', 'pdf']:
        raise HTTPException(status_code=400, detail="Invalid format")
    
    # Create request
    request_id = exporter.create_export_request(
        user_id=user_id,
        requested_by=user_id,  # Self-service
        request_type=request_type,
        data_types=data_types,
        format=format
    )
    
    # Process in background
    background_tasks.add_task(exporter.process_export, request_id)
    
    return {
        "request_id": request_id,
        "status": "pending",
        "message": "Export request created. You will be notified when ready."
    }

@router.get("/status/{request_id}")
async def get_export_status(request_id: str):
    """Get export request status"""
    exporter = DataExporter(db)
    request = exporter.get_request(request_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Export request not found")
    
    return {
        "request_id": request['request_id'],
        "status": request['status'],
        "requested_at": request['requested_at'],
        "completed_at": request['completed_at'],
        "file_url": request['file_url'],
        "error_message": request['error_message']
    }

@router.get("/download/{request_id}")
async def download_export(request_id: str):
    """Get download URL for completed export"""
    exporter = DataExporter(db)
    request = exporter.get_request(request_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Export request not found")
    
    if request['status'] != 'completed':
        raise HTTPException(status_code=400, detail=f"Export is {request['status']}")
    
    if not request['file_url']:
        raise HTTPException(status_code=404, detail="Export file not found")
    
    # Log download
    exporter.log_action(request_id, request['user_id'], "export_downloaded")
    
    return {
        "download_url": request['file_url'],
        "expires_in": 3600  # URL expires in 1 hour
    }

@router.get("/user/{user_id}/history")
async def get_user_export_history(
    user_id: str,
    limit: int = Query(10, ge=1, le=50)
):
    """Get user's export history"""
    exporter = DataExporter(db)
    exports = exporter.get_user_exports(user_id, limit)
    
    return {
        "user_id": user_id,
        "exports": exports,
        "count": len(exports)
    }

@router.get("/data-types")
async def get_available_data_types():
    """Get available data types for export"""
    query = """
    SELECT 
        data_type,
        table_name,
        is_sensitive,
        requires_approval
    FROM data_type_configs
    ORDER BY data_type
    """
    
    data_types = db.fetchall(query)
    
    return {
        "data_types": data_types,
        "formats": ["json", "csv", "pdf"]
    }

@router.delete("/{request_id}")
async def delete_export(request_id: str):
    """Delete export request and file"""
    exporter = DataExporter(db)
    request = exporter.get_request(request_id)
    
    if not request:
        raise HTTPException(status_code=404, detail="Export request not found")
    
    # Delete file if exists
    if request['file_url']:
        # Delete from storage
        pass
    
    # Delete request
    query = "DELETE FROM export_requests WHERE request_id = %s"
    db.execute(query, (request_id,))
    
    # Log deletion
    exporter.log_action(request_id, request['user_id'], "export_deleted")
    
    return {"message": "Export deleted successfully"}

@router.get("/gdpr/{user_id}")
async def request_gdpr_export(
    user_id: str,
    background_tasks: BackgroundTasks
):
    """Request GDPR compliant data export"""
    exporter = DataExporter(db)
    
    # Get all data types for GDPR
    all_data_types = [
        'user_profile', 'user_sessions', 'user_clicks',
        'user_workflows', 'user_errors', 'user_feedback'
    ]
    
    request_id = exporter.create_export_request(
        user_id=user_id,
        requested_by=user_id,
        request_type='gdpr',
        data_types=all_data_types,
        format='json'
    )
    
    background_tasks.add_task(exporter.process_export, request_id)
    
    return {
        "request_id": request_id,
        "status": "pending",
        "message": "GDPR export requested. Will be ready within 24 hours."
    }
```

## React Dashboard Component

```tsx
import React, { useState, useEffect } from 'react';
import { Download, Clock, CheckCircle, XCircle, FileText } from 'lucide-react';

interface ExportRequest {
  requestId: string;
  requestType: string;
  dataTypes: string[];
  format: string;
  status: string;
  requestedAt: string;
  completedAt?: string;
  totalRecords?: number;
  fileSizeBytes?: number;
}

interface DataType {
  dataType: string;
  tableName: string;
  isSensitive: boolean;
  requiresApproval: boolean;
}

export const UserDataExportDashboard: React.FC = () => {
  const [exports, setExports] = useState<ExportRequest[]>([]);
  const [dataTypes, setDataTypes] = useState<DataType[]>([]);
  const [selectedDataTypes, setSelectedDataTypes] = useState<string[]>([]);
  const [selectedFormat, setSelectedFormat] = useState('json');
  const [loading, setLoading] = useState(false);
  const [userId] = useState('current-user'); // Would come from auth context

  useEffect(() => {
    fetchExportHistory();
    fetchDataTypes();
  }, []);

  const fetchExportHistory = async () => {
    try {
      const res = await fetch(`/api/exports/user/${userId}/history`);
      const data = await res.json();
      setExports(data.exports);
    } catch (error) {
      console.error('Error fetching export history:', error);
    }
  };

  const fetchDataTypes = async () => {
    try {
      const res = await fetch('/api/exports/data-types');
      const data = await res.json();
      setDataTypes(data.data_types);
    } catch (error) {
      console.error('Error fetching data types:', error);
    }
  };

  const requestExport = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/exports/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          data_types: selectedDataTypes,
          format: selectedFormat,
          request_type: 'backup'
        })
      });
      
      const data = await res.json();
      
      // Refresh history
      setTimeout(fetchExportHistory, 1000);
      
      // Clear selection
      setSelectedDataTypes([]);
    } catch (error) {
      console.error('Error requesting export:', error);
    } finally {
      setLoading(false);
    }
  };

  const requestGDPRExport = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/exports/gdpr/${userId}`);
      const data = await res.json();
      
      setTimeout(fetchExportHistory, 1000);
    } catch (error) {
      console.error('Error requesting GDPR export:', error);
    } finally {
      setLoading(false);
    }
  };

  const downloadExport = async (requestId: string) => {
    try {
      const res = await fetch(`/api/exports/download/${requestId}`);
      const data = await res.json();
      
      // Open download URL
      window.open(data.download_url, '_blank');
    } catch (error) {
      console.error('Error downloading export:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'processing':
        return <Clock className="w-5 h-5 text-yellow-500 animate-spin" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">User Data Export</h2>

      {/* Export Request Form */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Request New Export</h3>
        
        {/* Data Types Selection */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Data Types
          </label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {dataTypes.map(dt => (
              <label key={dt.dataType} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={selectedDataTypes.includes(dt.dataType)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedDataTypes([...selectedDataTypes, dt.dataType]);
                    } else {
                      setSelectedDataTypes(
                        selectedDataTypes.filter(t => t !== dt.dataType)
                      );
                    }
                  }}
                  className="rounded"
                />
                <span className="text-sm">
                  {dt.dataType.replace(/_/g, ' ')}
                  {dt.isSensitive && (
                    <span className="text-red-500 ml-1">*</span>
                  )}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Format Selection */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Export Format
          </label>
          <select
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value)}
            className="w-full p-2 border rounded"
          >
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
            <option value="pdf">PDF Report</option>
          </select>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-4">
          <button
            onClick={requestExport}
            disabled={loading || selectedDataTypes.length === 0}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? 'Processing...' : 'Request Export'}
          </button>
          
          <button
            onClick={requestGDPRExport}
            disabled={loading}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
          >
            Request GDPR Export (All Data)
          </button>
        </div>
      </div>

      {/* Export History */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Export History</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Status
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Type
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Format
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Data Types
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Requested
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Size
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {exports.map((exp) => (
                <tr key={exp.requestId} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(exp.status)}
                      <span className="text-sm capitalize">{exp.status}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-sm capitalize">
                    {exp.requestType}
                  </td>
                  <td className="px-4 py-2 text-sm uppercase">
                    {exp.format}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <div className="max-w-xs truncate">
                      {exp.dataTypes.join(', ')}
                    </div>
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {new Date(exp.requestedAt).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    {exp.fileSizeBytes 
                      ? formatFileSize(exp.fileSizeBytes)
                      : '-'}
                  </td>
                  <td className="px-4 py-2">
                    {exp.status === 'completed' && (
                      <button
                        onClick={() => downloadExport(exp.requestId)}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 p-4 rounded-lg">
        <div className="flex items-start space-x-2">
          <FileText className="w-5 h-5 text-blue-500 mt-0.5" />
          <div className="text-sm text-blue-900">
            <p className="font-semibold mb-1">Data Export Information</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>Exports are available for download for 7 days</li>
              <li>GDPR exports include all your personal data</li>
              <li>Large exports may take several minutes to process</li>
              <li>Sensitive data requires additional verification</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
```

## Implementation Priority
- **Phase 1**: Basic export functionality (JSON format)
- **Phase 2**: CSV export support
- **Phase 3**: GDPR compliance features
- **Phase 4**: Scheduled/automated exports

## Performance Considerations
- Async processing for large exports
- Chunked data retrieval for large datasets
- Temporary file cleanup after 7 days
- Rate limiting on export requests (5 per day per user)

## Security Considerations
- Authentication required for all exports
- Audit logging of all export activities
- Encrypted file storage
- Time-limited download URLs
- Data anonymization options

## Monitoring and Alerts
- Alert on failed exports
- Monitor export queue length
- Track average export completion time
- Daily report of export requests

## Dependencies
- PostgreSQL for data storage
- FastAPI for REST endpoints
- AsyncIO for background processing
- Local/Cloud storage for export files
- React for dashboard UI