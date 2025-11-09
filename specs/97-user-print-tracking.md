# User Print Tracking Specification

## Overview
Track user printing behavior including document types, print frequency, and resource usage patterns to optimize printing costs and identify opportunities for digital alternatives.

## Database Schema

### Tables

```sql
-- Print job tracking
CREATE TABLE print_jobs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    job_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    document_name VARCHAR(500),
    document_type VARCHAR(50), -- pdf, doc, spreadsheet, image, webpage
    page_count INTEGER NOT NULL,
    color_pages INTEGER DEFAULT 0,
    bw_pages INTEGER DEFAULT 0,
    paper_size VARCHAR(20), -- A4, Letter, Legal, etc.
    duplex_printing BOOLEAN DEFAULT false,
    quality_setting VARCHAR(20), -- draft, normal, high
    printer_name VARCHAR(200),
    print_status VARCHAR(50), -- queued, printing, completed, cancelled, failed
    estimated_cost DECIMAL(10, 2),
    ink_usage_ml DECIMAL(10, 3),
    paper_saved INTEGER DEFAULT 0, -- Pages saved through duplex/n-up
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_print_jobs_user (user_id, created_at DESC),
    INDEX idx_print_jobs_status (print_status, created_at DESC),
    INDEX idx_print_jobs_type (document_type)
);

-- Print cost tracking
CREATE TABLE print_costs (
    id SERIAL PRIMARY KEY,
    cost_type VARCHAR(50) NOT NULL, -- paper, ink_color, ink_bw, maintenance
    unit_cost DECIMAL(10, 4) NOT NULL,
    unit_measure VARCHAR(20), -- page, ml, job
    effective_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_print_costs_type (cost_type, effective_date DESC)
);

-- Daily print statistics
CREATE TABLE print_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    user_id UUID,
    department VARCHAR(100),
    total_pages_printed INTEGER DEFAULT 0,
    color_pages INTEGER DEFAULT 0,
    bw_pages INTEGER DEFAULT 0,
    duplex_jobs INTEGER DEFAULT 0,
    cancelled_jobs INTEGER DEFAULT 0,
    failed_jobs INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 2),
    pages_saved INTEGER DEFAULT 0,
    most_printed_type VARCHAR(50),
    peak_print_hour INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date, user_id),
    INDEX idx_print_daily_stats_date (date DESC),
    INDEX idx_print_daily_stats_user (user_id, date DESC),
    INDEX idx_print_daily_stats_dept (department, date DESC)
);

-- Print reduction opportunities
CREATE TABLE print_reduction_opportunities (
    id SERIAL PRIMARY KEY,
    user_id UUID,
    opportunity_type VARCHAR(100), -- digital_alternative, duplex_usage, draft_mode, batch_printing
    potential_savings_pages INTEGER,
    potential_cost_savings DECIMAL(10, 2),
    recommendation TEXT,
    identified_date DATE DEFAULT CURRENT_DATE,
    implemented BOOLEAN DEFAULT false,
    
    INDEX idx_reduction_opportunities_user (user_id),
    INDEX idx_reduction_opportunities_type (opportunity_type)
);
```

## TypeScript Interfaces

```typescript
// Print job interface
interface PrintJob {
  id: string;
  userId: string;
  jobId: string;
  documentName?: string;
  documentType?: 'pdf' | 'doc' | 'spreadsheet' | 'image' | 'webpage';
  pageCount: number;
  colorPages: number;
  bwPages: number;
  paperSize: string;
  duplexPrinting: boolean;
  qualitySetting: 'draft' | 'normal' | 'high';
  printerName?: string;
  printStatus: 'queued' | 'printing' | 'completed' | 'cancelled' | 'failed';
  estimatedCost: number;
  inkUsageMl?: number;
  paperSaved: number;
  createdAt: Date;
  completedAt?: Date;
}

// Print statistics
interface PrintStatistics {
  totalPagesPrinted: number;
  colorVsBwRatio: number;
  averageJobSize: number;
  duplexUsageRate: number;
  cancellationRate: number;
  totalCost: number;
  paperSaved: number;
  printPattern: PrintPattern;
  topDocumentTypes: DocumentTypeStats[];
}

// Print pattern
interface PrintPattern {
  patternType: 'heavy_user' | 'moderate_user' | 'light_user' | 'digital_first';
  confidence: number;
  characteristics: {
    avgPagesPerDay: number;
    colorUsageRate: number;
    duplexRate: number;
    peakPrintTime: number[];
  };
}

// Cost analysis
interface CostAnalysis {
  totalCost: number;
  costBreakdown: {
    paper: number;
    inkColor: number;
    inkBw: number;
    maintenance: number;
  };
  costPerPage: number;
  projectedMonthlyCost: number;
  savingsOpportunities: SavingsOpportunity[];
}
```

## Python Analytics Models

```python
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from decimal import Decimal
import asyncpg

@dataclass
class PrintAnalytics:
    """Analyze printing patterns and costs"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.default_costs = {
            'paper': 0.02,  # per page
            'ink_color': 0.10,  # per page
            'ink_bw': 0.03,  # per page
        }
    
    async def track_print_job(
        self,
        user_id: str,
        document_name: Optional[str],
        document_type: Optional[str],
        page_count: int,
        color_pages: int = 0,
        paper_size: str = 'A4',
        duplex: bool = False,
        quality: str = 'normal',
        printer_name: Optional[str] = None
    ) -> str:
        """Track a new print job"""
        # Calculate costs
        bw_pages = page_count - color_pages
        estimated_cost = await self._calculate_print_cost(
            color_pages, bw_pages, duplex
        )
        
        # Calculate paper saved
        paper_saved = page_count // 2 if duplex else 0
        
        query = """
            INSERT INTO print_jobs (
                user_id, document_name, document_type, page_count,
                color_pages, bw_pages, paper_size, duplex_printing,
                quality_setting, printer_name, print_status,
                estimated_cost, paper_saved
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'queued', $11, $12)
            RETURNING job_id
        """
        
        async with self.db.acquire() as conn:
            job_id = await conn.fetchval(
                query, user_id, document_name, document_type, page_count,
                color_pages, bw_pages, paper_size, duplex,
                quality, printer_name, estimated_cost, paper_saved
            )
        
        return job_id
    
    async def update_print_status(
        self,
        job_id: str,
        status: str,
        ink_usage: Optional[float] = None
    ):
        """Update print job status"""
        query = """
            UPDATE print_jobs
            SET print_status = $2,
                ink_usage_ml = COALESCE($3, ink_usage_ml),
                completed_at = CASE 
                    WHEN $2 IN ('completed', 'cancelled', 'failed')
                    THEN CURRENT_TIMESTAMP
                    ELSE completed_at
                END
            WHERE job_id = $1
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(query, job_id, status, ink_usage)
            
            # Update daily stats if completed
            if status == 'completed':
                await self._update_daily_stats(conn, job_id)
    
    async def get_print_statistics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get user print statistics"""
        query = """
            WITH print_stats AS (
                SELECT 
                    SUM(page_count) as total_pages,
                    SUM(color_pages) as color_pages,
                    SUM(bw_pages) as bw_pages,
                    COUNT(*) as total_jobs,
                    COUNT(*) FILTER (WHERE duplex_printing) as duplex_jobs,
                    COUNT(*) FILTER (WHERE print_status = 'cancelled') as cancelled,
                    COUNT(*) FILTER (WHERE print_status = 'failed') as failed,
                    AVG(page_count) as avg_job_size,
                    SUM(estimated_cost) as total_cost,
                    SUM(paper_saved) as paper_saved
                FROM print_jobs
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ),
            doc_types AS (
                SELECT 
                    document_type,
                    COUNT(*) as count,
                    SUM(page_count) as pages
                FROM print_jobs
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND document_type IS NOT NULL
                GROUP BY document_type
                ORDER BY count DESC
                LIMIT 5
            )
            SELECT 
                s.*,
                (SELECT json_agg(json_build_object(
                    'type', document_type,
                    'count', count,
                    'pages', pages
                )) FROM doc_types) as top_types
            FROM print_stats s
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % (days, days), user_id)
            
            if not row or not row['total_jobs']:
                return self._empty_statistics()
            
            # Detect print pattern
            pattern = await self._detect_print_pattern(conn, user_id, days)
            
            return {
                'total_pages_printed': row['total_pages'] or 0,
                'color_vs_bw_ratio': (
                    row['color_pages'] / row['bw_pages'] 
                    if row['bw_pages'] > 0 else 0
                ),
                'average_job_size': float(row['avg_job_size'] or 0),
                'duplex_usage_rate': (
                    row['duplex_jobs'] / row['total_jobs'] * 100
                    if row['total_jobs'] > 0 else 0
                ),
                'cancellation_rate': (
                    row['cancelled'] / row['total_jobs'] * 100
                    if row['total_jobs'] > 0 else 0
                ),
                'total_cost': float(row['total_cost'] or 0),
                'paper_saved': row['paper_saved'] or 0,
                'print_pattern': pattern,
                'top_document_types': row['top_types'] or []
            }
    
    async def get_cost_analysis(
        self,
        user_id: Optional[str] = None,
        department: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """Analyze printing costs"""
        query = """
            WITH cost_data AS (
                SELECT 
                    SUM(estimated_cost) as total_cost,
                    SUM(color_pages) as color_pages,
                    SUM(bw_pages) as bw_pages,
                    SUM(page_count) as total_pages,
                    COUNT(*) as job_count,
                    DATE(created_at) as print_date
                FROM print_jobs
                WHERE print_status = 'completed'
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    %s
                GROUP BY DATE(created_at)
            ),
            cost_breakdown AS (
                SELECT 
                    SUM(color_pages) * $1 as color_ink_cost,
                    SUM(bw_pages) * $2 as bw_ink_cost,
                    SUM(total_pages) * $3 as paper_cost,
                    SUM(total_cost) as total,
                    AVG(total_cost) as daily_avg
                FROM cost_data
            )
            SELECT * FROM cost_breakdown
        """
        
        user_filter = "AND user_id = $4" if user_id else ""
        
        # Get current costs
        costs = await self._get_current_costs()
        
        async with self.db.acquire() as conn:
            params = [
                costs['ink_color'],
                costs['ink_bw'],
                costs['paper']
            ]
            if user_id:
                params.append(user_id)
            
            row = await conn.fetchrow(query % (days, user_filter), *params)
            
            if not row:
                return self._empty_cost_analysis()
            
            # Get savings opportunities
            opportunities = await self._identify_savings_opportunities(
                conn, user_id, days
            )
            
            total_cost = float(row['total'] or 0)
            daily_avg = float(row['daily_avg'] or 0)
            
            return {
                'total_cost': total_cost,
                'cost_breakdown': {
                    'paper': float(row['paper_cost'] or 0),
                    'ink_color': float(row['color_ink_cost'] or 0),
                    'ink_bw': float(row['bw_ink_cost'] or 0),
                    'maintenance': 0  # Would be calculated separately
                },
                'cost_per_page': total_cost / days if days > 0 else 0,
                'projected_monthly_cost': daily_avg * 30,
                'savings_opportunities': opportunities
            }
    
    async def detect_print_pattern(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Detect user print pattern"""
        query = """
            SELECT 
                AVG(pages_per_day) as avg_pages_per_day,
                AVG(color_ratio) as avg_color_ratio,
                AVG(duplex_ratio) as avg_duplex_ratio,
                array_agg(DISTINCT peak_hour) as peak_hours
            FROM (
                SELECT 
                    DATE(created_at) as print_date,
                    SUM(page_count) as pages_per_day,
                    SUM(color_pages)::float / NULLIF(SUM(page_count), 0) as color_ratio,
                    SUM(CASE WHEN duplex_printing THEN 1 ELSE 0 END)::float / COUNT(*) as duplex_ratio,
                    EXTRACT(HOUR FROM created_at) as peak_hour
                FROM print_jobs
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                GROUP BY DATE(created_at), EXTRACT(HOUR FROM created_at)
            ) daily_stats
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query % days, user_id)
            
            if not row or not row['avg_pages_per_day']:
                return {'pattern_type': 'unknown', 'confidence': 0}
            
            pattern = self._determine_print_pattern(
                row['avg_pages_per_day'] or 0,
                row['avg_color_ratio'] or 0,
                row['avg_duplex_ratio'] or 0
            )
            
            pattern['characteristics']['peak_print_time'] = row['peak_hours'][:3] if row['peak_hours'] else []
            
            return pattern
    
    async def get_environmental_impact(
        self,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """Calculate environmental impact of printing"""
        query = """
            WITH print_data AS (
                SELECT 
                    SUM(page_count) as total_pages,
                    SUM(paper_saved) as pages_saved,
                    SUM(CASE WHEN duplex_printing THEN page_count ELSE 0 END) as duplex_pages,
                    COUNT(*) FILTER (WHERE print_status = 'cancelled') as cancelled_jobs,
                    SUM(CASE WHEN print_status = 'cancelled' THEN page_count ELSE 0 END) as cancelled_pages
                FROM print_jobs
                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    %s
            )
            SELECT * FROM print_data
        """
        
        user_filter = "AND user_id = $1" if user_id else ""
        
        async with self.db.acquire() as conn:
            if user_id:
                row = await conn.fetchrow(query % (days, user_filter), user_id)
            else:
                row = await conn.fetchrow(query % (days, user_filter))
            
            if not row:
                return self._empty_environmental_impact()
            
            total_pages = row['total_pages'] or 0
            pages_saved = row['pages_saved'] or 0
            
            # Environmental calculations (rough estimates)
            trees_consumed = total_pages / 8333  # 1 tree = ~8,333 pages
            trees_saved = pages_saved / 8333
            co2_produced = total_pages * 0.01  # kg CO2 per page
            co2_saved = pages_saved * 0.01
            water_used = total_pages * 10  # liters per page
            water_saved = pages_saved * 10
            
            return {
                'total_pages_printed': total_pages,
                'pages_saved': pages_saved,
                'trees_consumed': round(trees_consumed, 2),
                'trees_saved': round(trees_saved, 2),
                'co2_produced_kg': round(co2_produced, 2),
                'co2_saved_kg': round(co2_saved, 2),
                'water_used_liters': round(water_used, 2),
                'water_saved_liters': round(water_saved, 2),
                'environmental_score': self._calculate_environmental_score(
                    total_pages, pages_saved
                )
            }
    
    async def get_printer_usage(
        self,
        days: int = 30
    ) -> List[Dict]:
        """Get printer usage statistics"""
        query = """
            SELECT 
                printer_name,
                COUNT(*) as job_count,
                SUM(page_count) as total_pages,
                SUM(color_pages) as color_pages,
                AVG(page_count) as avg_job_size,
                COUNT(*) FILTER (WHERE print_status = 'failed') as failures,
                COUNT(DISTINCT user_id) as unique_users
            FROM print_jobs
            WHERE printer_name IS NOT NULL
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            GROUP BY printer_name
            ORDER BY job_count DESC
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query % days)
            
            return [
                {
                    'printer_name': row['printer_name'],
                    'job_count': row['job_count'],
                    'total_pages': row['total_pages'],
                    'color_pages': row['color_pages'],
                    'avg_job_size': float(row['avg_job_size']),
                    'failure_rate': (
                        row['failures'] / row['job_count'] * 100
                        if row['job_count'] > 0 else 0
                    ),
                    'unique_users': row['unique_users'],
                    'utilization': self._calculate_utilization(row['job_count'], days)
                }
                for row in rows
            ]
    
    async def identify_reduction_opportunities(
        self,
        user_id: str
    ) -> List[Dict]:
        """Identify print reduction opportunities"""
        query = """
            WITH user_patterns AS (
                SELECT 
                    COUNT(*) FILTER (WHERE NOT duplex_printing AND page_count > 1) as single_sided,
                    COUNT(*) FILTER (WHERE quality_setting = 'high') as high_quality,
                    COUNT(*) FILTER (WHERE document_type = 'webpage') as web_prints,
                    COUNT(*) FILTER (WHERE page_count = 1) as single_page,
                    AVG(page_count) as avg_pages
                FROM print_jobs
                WHERE user_id = $1
                    AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            )
            SELECT * FROM user_patterns
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
            opportunities = []
            
            if row:
                # Check for duplex opportunity
                if row['single_sided'] > 10:
                    opportunities.append({
                        'type': 'duplex_usage',
                        'potential_pages_saved': row['single_sided'] * 0.4,  # Estimate 40% savings
                        'recommendation': 'Enable duplex printing by default',
                        'priority': 'high'
                    })
                
                # Check for quality settings
                if row['high_quality'] > 5:
                    opportunities.append({
                        'type': 'draft_mode',
                        'potential_ink_saved': row['high_quality'] * 0.3,  # 30% ink savings
                        'recommendation': 'Use draft mode for internal documents',
                        'priority': 'medium'
                    })
                
                # Check for digital alternatives
                if row['web_prints'] > 10:
                    opportunities.append({
                        'type': 'digital_alternative',
                        'potential_pages_saved': row['web_prints'] * 5,  # Estimate pages
                        'recommendation': 'Use digital bookmarks instead of printing webpages',
                        'priority': 'high'
                    })
            
            return opportunities
    
    def _empty_statistics(self) -> Dict:
        """Return empty statistics structure"""
        return {
            'total_pages_printed': 0,
            'color_vs_bw_ratio': 0,
            'average_job_size': 0,
            'duplex_usage_rate': 0,
            'cancellation_rate': 0,
            'total_cost': 0,
            'paper_saved': 0,
            'print_pattern': {'pattern_type': 'unknown', 'confidence': 0},
            'top_document_types': []
        }
    
    def _empty_cost_analysis(self) -> Dict:
        """Return empty cost analysis"""
        return {
            'total_cost': 0,
            'cost_breakdown': {
                'paper': 0,
                'ink_color': 0,
                'ink_bw': 0,
                'maintenance': 0
            },
            'cost_per_page': 0,
            'projected_monthly_cost': 0,
            'savings_opportunities': []
        }
    
    def _empty_environmental_impact(self) -> Dict:
        """Return empty environmental impact"""
        return {
            'total_pages_printed': 0,
            'pages_saved': 0,
            'trees_consumed': 0,
            'trees_saved': 0,
            'co2_produced_kg': 0,
            'co2_saved_kg': 0,
            'water_used_liters': 0,
            'water_saved_liters': 0,
            'environmental_score': 0
        }
    
    def _determine_print_pattern(
        self,
        avg_pages: float,
        color_ratio: float,
        duplex_ratio: float
    ) -> Dict:
        """Determine print pattern type"""
        
        # Heavy user
        if avg_pages > 50:
            pattern_type = 'heavy_user'
            confidence = 0.8
        # Moderate user
        elif 10 < avg_pages <= 50:
            pattern_type = 'moderate_user'
            confidence = 0.75
        # Light user
        elif avg_pages <= 10 and duplex_ratio > 0.5:
            pattern_type = 'light_user'
            confidence = 0.7
        # Digital first
        elif avg_pages < 5:
            pattern_type = 'digital_first'
            confidence = 0.8
        else:
            pattern_type = 'moderate_user'
            confidence = 0.6
        
        return {
            'pattern_type': pattern_type,
            'confidence': confidence,
            'characteristics': {
                'avg_pages_per_day': avg_pages,
                'color_usage_rate': color_ratio * 100,
                'duplex_rate': duplex_ratio * 100,
                'peak_print_time': []  # Will be set by caller
            }
        }
    
    def _calculate_environmental_score(
        self,
        total_pages: int,
        pages_saved: int
    ) -> int:
        """Calculate environmental score (0-100)"""
        if total_pages == 0:
            return 100
        
        save_ratio = pages_saved / (total_pages + pages_saved)
        
        # Score based on savings ratio
        score = min(save_ratio * 200, 100)  # Double weight for good behavior
        
        return int(score)
    
    def _calculate_utilization(self, job_count: int, days: int) -> str:
        """Calculate printer utilization level"""
        daily_jobs = job_count / days if days > 0 else 0
        
        if daily_jobs > 50:
            return 'high'
        elif daily_jobs > 20:
            return 'medium'
        elif daily_jobs > 5:
            return 'low'
        else:
            return 'very_low'
    
    async def _calculate_print_cost(
        self,
        color_pages: int,
        bw_pages: int,
        duplex: bool
    ) -> Decimal:
        """Calculate estimated print cost"""
        costs = await self._get_current_costs()
        
        paper_pages = (color_pages + bw_pages) / (2 if duplex else 1)
        
        total = (
            Decimal(str(color_pages)) * Decimal(str(costs['ink_color'])) +
            Decimal(str(bw_pages)) * Decimal(str(costs['ink_bw'])) +
            Decimal(str(paper_pages)) * Decimal(str(costs['paper']))
        )
        
        return total
    
    async def _get_current_costs(self) -> Dict:
        """Get current print costs"""
        # In production, would fetch from database
        return self.default_costs
    
    async def _update_daily_stats(self, conn, job_id: str):
        """Update daily print statistics"""
        # Implementation
        pass
    
    async def _detect_print_pattern(
        self,
        conn,
        user_id: str,
        days: int
    ) -> Dict:
        """Detect print pattern from database"""
        return await self.detect_print_pattern(user_id, days)
    
    async def _identify_savings_opportunities(
        self,
        conn,
        user_id: Optional[str],
        days: int
    ) -> List[Dict]:
        """Identify cost savings opportunities"""
        if user_id:
            return await self.identify_reduction_opportunities(user_id)
        return []
```

## API Endpoints

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from decimal import Decimal

router = APIRouter(prefix="/api/analytics/print", tags=["print-analytics"])

@router.post("/job")
async def track_print_job(
    user_id: str,
    page_count: int,
    color_pages: int = 0,
    document_name: Optional[str] = None,
    document_type: Optional[str] = None,
    paper_size: str = "A4",
    duplex: bool = False,
    quality: str = "normal",
    printer_name: Optional[str] = None
):
    """Track print job"""
    analytics = PrintAnalytics(db_pool)
    job_id = await analytics.track_print_job(
        user_id, document_name, document_type, page_count,
        color_pages, paper_size, duplex, quality, printer_name
    )
    return {"job_id": job_id}

@router.patch("/job/{job_id}/status")
async def update_print_status(
    job_id: str,
    status: str,
    ink_usage: Optional[float] = None
):
    """Update print job status"""
    analytics = PrintAnalytics(db_pool)
    await analytics.update_print_status(job_id, status, ink_usage)
    return {"status": "updated"}

@router.get("/statistics/{user_id}")
async def get_print_statistics(
    user_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """Get print statistics"""
    analytics = PrintAnalytics(db_pool)
    stats = await analytics.get_print_statistics(user_id, days)
    return stats

@router.get("/cost-analysis")
async def get_cost_analysis(
    user_id: Optional[str] = None,
    department: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Get cost analysis"""
    analytics = PrintAnalytics(db_pool)
    analysis = await analytics.get_cost_analysis(user_id, department, days)
    return analysis

@router.get("/environmental-impact")
async def get_environmental_impact(
    user_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Get environmental impact"""
    analytics = PrintAnalytics(db_pool)
    impact = await analytics.get_environmental_impact(user_id, days)
    return impact

@router.get("/printer-usage")
async def get_printer_usage(
    days: int = Query(30, ge=1, le=365)
):
    """Get printer usage statistics"""
    analytics = PrintAnalytics(db_pool)
    usage = await analytics.get_printer_usage(days)
    return {"printers": usage}

@router.get("/reduction-opportunities/{user_id}")
async def get_reduction_opportunities(user_id: str):
    """Get print reduction opportunities"""
    analytics = PrintAnalytics(db_pool)
    opportunities = await analytics.identify_reduction_opportunities(user_id)
    return {"opportunities": opportunities}
```

## React Dashboard Components

```tsx
// Print Analytics Dashboard Component
import React, { useState, useEffect } from 'react';
import { Card, Grid, Progress, Badge, PieChart, BarChart } from '@/components/ui';

interface PrintDashboardProps {
  userId?: string;
}

export const PrintDashboard: React.FC<PrintDashboardProps> = ({ userId }) => {
  const [stats, setStats] = useState<PrintStatistics | null>(null);
  const [cost, setCost] = useState<CostAnalysis | null>(null);
  const [impact, setImpact] = useState<any>(null);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPrintData();
  }, [userId]);

  const fetchPrintData = async () => {
    setLoading(true);
    try {
      const endpoints = [
        userId && `/api/analytics/print/statistics/${userId}`,
        `/api/analytics/print/cost-analysis${userId ? `?user_id=${userId}` : ''}`,
        `/api/analytics/print/environmental-impact${userId ? `?user_id=${userId}` : ''}`,
        userId && `/api/analytics/print/reduction-opportunities/${userId}`
      ].filter(Boolean);

      const responses = await Promise.all(
        endpoints.map(endpoint => fetch(endpoint!))
      );

      const data = await Promise.all(
        responses.map(res => res.json())
      );

      let idx = 0;
      if (userId) {
        setStats(data[idx++]);
      }
      setCost(data[idx++]);
      setImpact(data[idx++]);
      if (userId) {
        setOpportunities(data[idx].opportunities);
      }
    } catch (error) {
      console.error('Failed to fetch print data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading print analytics...</div>;

  return (
    <div className="print-dashboard">
      <h2>Print Analytics</h2>
      
      {stats && (
        <>
          {/* Summary Stats */}
          <Grid cols={4} gap={4}>
            <Card>
              <h3>Pages Printed</h3>
              <div className="stat-value">{stats.totalPagesPrinted}</div>
              <span className="stat-label">
                {stats.paperSaved} pages saved
              </span>
            </Card>
            
            <Card>
              <h3>Total Cost</h3>
              <div className="stat-value">${stats.totalCost.toFixed(2)}</div>
              <Badge variant={stats.printPattern.patternType === 'digital_first' ? 'success' : 'warning'}>
                {stats.printPattern.patternType.replace('_', ' ')}
              </Badge>
            </Card>
            
            <Card>
              <h3>Duplex Usage</h3>
              <Progress value={stats.duplexUsageRate} max={100} />
              <span>{stats.duplexUsageRate.toFixed(1)}% of jobs</span>
            </Card>
            
            <Card>
              <h3>Avg Job Size</h3>
              <div className="stat-value">{stats.averageJobSize.toFixed(0)} pages</div>
              <span className="stat-label">
                {stats.cancellationRate.toFixed(1)}% cancelled
              </span>
            </Card>
          </Grid>
        </>
      )}

      {/* Cost Analysis */}
      {cost && (
        <Card className="mt-4">
          <h3>Cost Analysis</h3>
          <div className="cost-breakdown">
            <PieChart
              data={[
                { name: 'Paper', value: cost.costBreakdown.paper },
                { name: 'Color Ink', value: cost.costBreakdown.inkColor },
                { name: 'B/W Ink', value: cost.costBreakdown.inkBw }
              ]}
              height={200}
            />
            <div className="cost-details">
              <div>Projected Monthly: ${cost.projectedMonthlyCost.toFixed(2)}</div>
              <div>Cost per Page: ${cost.costPerPage.toFixed(3)}</div>
            </div>
          </div>
        </Card>
      )}

      {/* Environmental Impact */}
      {impact && (
        <Card className="mt-4">
          <h3>Environmental Impact</h3>
          <Grid cols={4} gap={2}>
            <div className="impact-item">
              <span>Trees Used</span>
              <strong>{impact.treesConsumed}</strong>
              <Badge variant="info">Saved: {impact.treesSaved}</Badge>
            </div>
            <div className="impact-item">
              <span>CO2 Produced</span>
              <strong>{impact.co2ProducedKg} kg</strong>
              <Badge variant="info">Saved: {impact.co2SavedKg} kg</Badge>
            </div>
            <div className="impact-item">
              <span>Water Used</span>
              <strong>{impact.waterUsedLiters} L</strong>
              <Badge variant="info">Saved: {impact.waterSavedLiters} L</Badge>
            </div>
            <div className="impact-item">
              <span>Eco Score</span>
              <Progress value={impact.environmentalScore} max={100} />
            </div>
          </Grid>
        </Card>
      )}

      {/* Savings Opportunities */}
      {opportunities.length > 0 && (
        <Card className="mt-4">
          <h3>Savings Opportunities</h3>
          <div className="opportunities-list">
            {opportunities.map((opp, idx) => (
              <div key={idx} className="opportunity-item">
                <Badge variant={opp.priority === 'high' ? 'danger' : 'warning'}>
                  {opp.priority}
                </Badge>
                <span className="opportunity-type">{opp.type.replace('_', ' ')}</span>
                <p>{opp.recommendation}</p>
                {opp.potential_pages_saved && (
                  <span className="savings">
                    Could save {opp.potential_pages_saved.toFixed(0)} pages
                  </span>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};
```

## Implementation Priority
1. Basic print job tracking
2. Cost calculation
3. Environmental impact metrics
4. Savings opportunity detection
5. Printer usage analytics

## Security Considerations
- Anonymize document names
- Secure printer access logs
- Respect privacy settings
- Department-level permissions
- Audit trail for print jobs

## Performance Optimizations
- Batch job status updates
- Daily cost aggregation
- Cache environmental calculations
- Efficient opportunity queries
- Async printer communication