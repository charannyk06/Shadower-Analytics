# Agent Database Analytics Specification

## Overview
Comprehensive database performance monitoring, query optimization, connection pooling analytics, transaction analysis, and database health metrics for agent operations in the Shadower platform.

## Core Components

### 1. Database Performance Monitoring

#### 1.1 Database Metrics Model
```typescript
interface DatabaseMetrics {
  database_id: string;
  agent_id: string;
  connection_info: {
    host: string;
    port: number;
    database_name: string;
    engine: 'postgresql' | 'mysql' | 'mongodb' | 'redis' | 'dynamodb';
    version: string;
    cluster_mode: boolean;
  };
  
  performance_metrics: {
    queries_per_second: number;
    transactions_per_second: number;
    active_connections: number;
    idle_connections: number;
    connection_pool_size: number;
    avg_query_time_ms: number;
    p95_query_time_ms: number;
    p99_query_time_ms: number;
    slow_query_count: number;
    deadlock_count: number;
    rollback_count: number;
  };
  
  resource_metrics: {
    cpu_usage_percent: number;
    memory_usage_gb: number;
    disk_io_read_mbps: number;
    disk_io_write_mbps: number;
    storage_used_gb: number;
    storage_total_gb: number;
    buffer_cache_hit_ratio: number;
    index_cache_hit_ratio: number;
  };
  
  replication_metrics?: {
    replication_lag_ms: number;
    replica_count: number;
    sync_status: 'in_sync' | 'lagging' | 'error';
    last_sync_timestamp: string;
  };
}
```

#### 1.2 Database Performance Schema
```sql
CREATE TABLE database_performance_metrics (
    id UUID PRIMARY KEY,
    database_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- Query metrics
    total_queries BIGINT,
    select_queries BIGINT,
    insert_queries BIGINT,
    update_queries BIGINT,
    delete_queries BIGINT,
    
    -- Performance metrics
    avg_query_time_us BIGINT,
    p50_query_time_us BIGINT,
    p95_query_time_us BIGINT,
    p99_query_time_us BIGINT,
    max_query_time_us BIGINT,
    
    -- Connection metrics
    active_connections INTEGER,
    idle_connections INTEGER,
    waiting_connections INTEGER,
    connection_errors INTEGER,
    
    -- Transaction metrics
    transactions_committed BIGINT,
    transactions_rolled_back BIGINT,
    deadlocks_detected INTEGER,
    lock_waits BIGINT,
    
    -- Resource metrics
    cpu_usage_percent FLOAT,
    memory_usage_mb INTEGER,
    disk_read_ops BIGINT,
    disk_write_ops BIGINT,
    network_bytes_sent BIGINT,
    network_bytes_received BIGINT,
    
    -- Cache metrics
    buffer_cache_hits BIGINT,
    buffer_cache_misses BIGINT,
    index_cache_hits BIGINT,
    index_cache_misses BIGINT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE database_performance_metrics_2024_01 
    PARTITION OF database_performance_metrics
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE INDEX idx_db_perf_agent ON database_performance_metrics(agent_id, timestamp);
CREATE INDEX idx_db_perf_slow ON database_performance_metrics(p99_query_time_us DESC);
```

### 2. Query Optimization Analytics

#### 2.1 Query Analysis Engine
```python
class QueryOptimizationEngine:
    def analyze_query_performance(self, database_id: str):
        queries = self.get_query_log(database_id)
        
        analysis = {
            "slow_queries": self.identify_slow_queries(queries),
            "frequent_queries": self.identify_frequent_queries(queries),
            "expensive_queries": self.identify_expensive_queries(queries),
            "optimization_opportunities": [],
            "index_recommendations": [],
            "query_rewrites": []
        }
        
        # Analyze each problematic query
        for query in analysis["slow_queries"]:
            optimization = self.analyze_single_query(query)
            
            # Check for missing indexes
            if optimization["missing_indexes"]:
                analysis["index_recommendations"].extend(
                    self.generate_index_recommendations(query, optimization["missing_indexes"])
                )
            
            # Check for query structure issues
            if optimization["structural_issues"]:
                analysis["query_rewrites"].append({
                    "original_query": query.sql,
                    "optimized_query": self.rewrite_query(query),
                    "expected_improvement": optimization["expected_improvement"],
                    "explanation": optimization["explanation"]
                })
            
            # Check for N+1 problems
            if self.detect_n_plus_one(query):
                analysis["optimization_opportunities"].append({
                    "type": "n_plus_one",
                    "query": query.sql,
                    "solution": "Use JOIN or batch loading",
                    "impact": "High"
                })
        
        # Analyze query patterns
        patterns = self.analyze_query_patterns(queries)
        if patterns["cacheable_queries"]:
            analysis["optimization_opportunities"].append({
                "type": "caching_opportunity",
                "queries": patterns["cacheable_queries"],
                "cache_hit_rate_potential": patterns["cache_potential"],
                "implementation": self.suggest_caching_strategy(patterns)
            })
        
        return analysis
    
    def analyze_single_query(self, query):
        # Get query execution plan
        explain_plan = self.get_execution_plan(query)
        
        optimization = {
            "execution_plan": explain_plan,
            "cost": explain_plan.total_cost,
            "missing_indexes": [],
            "structural_issues": [],
            "expected_improvement": 0
        }
        
        # Analyze plan nodes
        for node in explain_plan.nodes:
            # Check for full table scans
            if node.operation == "Sequential Scan" and node.rows > 1000:
                optimization["missing_indexes"].append({
                    "table": node.table,
                    "columns": node.filter_columns,
                    "estimated_improvement": node.cost * 0.7
                })
            
            # Check for expensive sorts
            if node.operation == "Sort" and node.cost > 1000:
                optimization["structural_issues"].append({
                    "issue": "expensive_sort",
                    "description": f"Sorting {node.rows} rows",
                    "solution": "Add index on sort columns or limit result set"
                })
            
            # Check for nested loops on large tables
            if node.operation == "Nested Loop" and node.inner_rows * node.outer_rows > 100000:
                optimization["structural_issues"].append({
                    "issue": "inefficient_join",
                    "description": "Nested loop join on large dataset",
                    "solution": "Consider hash join or merge join"
                })
        
        optimization["expected_improvement"] = sum(
            idx["estimated_improvement"] for idx in optimization["missing_indexes"]
        )
        
        return optimization
```

### 3. Connection Pool Analytics

#### 3.1 Connection Pool Monitoring
```sql
CREATE MATERIALIZED VIEW connection_pool_analytics AS
WITH pool_metrics AS (
    SELECT 
        agent_id,
        database_id,
        DATE_TRUNC('minute', timestamp) as minute,
        AVG(active_connections) as avg_active,
        MAX(active_connections) as max_active,
        AVG(idle_connections) as avg_idle,
        AVG(waiting_connections) as avg_waiting,
        SUM(connection_errors) as total_errors,
        AVG(active_connections::float / NULLIF(active_connections + idle_connections, 0)) as utilization
    FROM database_performance_metrics
    WHERE timestamp > NOW() - INTERVAL '1 hour'
    GROUP BY agent_id, database_id, DATE_TRUNC('minute', timestamp)
),
pool_efficiency AS (
    SELECT 
        agent_id,
        database_id,
        minute,
        avg_active,
        max_active,
        avg_idle,
        utilization,
        CASE 
            WHEN avg_waiting > 0 THEN 'undersized'
            WHEN utilization < 0.3 AND avg_idle > 10 THEN 'oversized'
            WHEN utilization > 0.8 THEN 'high_utilization'
            ELSE 'optimal'
        END as pool_status,
        CASE 
            WHEN avg_waiting > 0 THEN 
                CEIL(max_active * 1.2) -- Add 20% buffer
            WHEN utilization < 0.3 THEN 
                CEIL(max_active * 1.1) -- Reduce but keep buffer
            ELSE 
                max_active
        END as recommended_pool_size
    FROM pool_metrics
)
SELECT 
    pe.*,
    pm.total_errors,
    CASE 
        WHEN pm.total_errors > 10 THEN 'connection_issues'
        WHEN pe.pool_status = 'undersized' THEN 'increase_pool_size'
        WHEN pe.pool_status = 'oversized' THEN 'decrease_pool_size'
        ELSE 'no_action_needed'
    END as recommendation
FROM pool_efficiency pe
JOIN pool_metrics pm ON pe.agent_id = pm.agent_id 
    AND pe.database_id = pm.database_id 
    AND pe.minute = pm.minute;
```

### 4. Transaction Analysis

#### 4.1 Transaction Performance Tracking
```typescript
interface TransactionAnalytics {
  transaction_id: string;
  agent_id: string;
  database_id: string;
  
  transaction_details: {
    start_time: string;
    end_time: string;
    duration_ms: number;
    isolation_level: string;
    read_only: boolean;
    auto_commit: boolean;
  };
  
  operations: {
    operation_type: 'select' | 'insert' | 'update' | 'delete';
    table_name: string;
    row_count: number;
    duration_ms: number;
    lock_wait_ms: number;
  }[];
  
  lock_analysis: {
    locks_acquired: {
      lock_type: string;
      lock_mode: string;
      table_name: string;
      duration_ms: number;
    }[];
    lock_waits: number;
    deadlock_victim: boolean;
    blocking_transactions: string[];
  };
  
  resource_usage: {
    cpu_time_ms: number;
    memory_mb: number;
    disk_io_operations: number;
    network_bytes: number;
  };
  
  outcome: {
    status: 'committed' | 'rolled_back' | 'aborted';
    error?: string;
    retry_count: number;
  };
}
```

#### 4.2 Transaction Optimization Engine
```python
class TransactionOptimizer:
    def analyze_transaction_patterns(self, database_id: str):
        transactions = self.get_transaction_history(database_id)
        
        analysis = {
            "long_running_transactions": self.identify_long_running(transactions),
            "high_contention_patterns": self.analyze_lock_contention(transactions),
            "rollback_analysis": self.analyze_rollbacks(transactions),
            "optimization_strategies": []
        }
        
        # Analyze transaction batching opportunities
        batching_opportunities = self.identify_batching_opportunities(transactions)
        if batching_opportunities:
            analysis["optimization_strategies"].append({
                "type": "transaction_batching",
                "patterns": batching_opportunities,
                "expected_benefit": "Reduce round trips by 50%",
                "implementation": self.generate_batching_code(batching_opportunities)
            })
        
        # Analyze lock contention
        contention_points = self.identify_contention_points(transactions)
        for point in contention_points:
            analysis["optimization_strategies"].append({
                "type": "reduce_contention",
                "table": point["table"],
                "pattern": point["pattern"],
                "solution": self.suggest_contention_solution(point),
                "expected_benefit": f"Reduce lock waits by {point['reduction_potential']}%"
            })
        
        # Analyze transaction isolation
        isolation_issues = self.analyze_isolation_levels(transactions)
        if isolation_issues:
            analysis["optimization_strategies"].append({
                "type": "isolation_optimization",
                "current_issues": isolation_issues,
                "recommendations": self.recommend_isolation_levels(isolation_issues)
            })
        
        return analysis
    
    def analyze_lock_contention(self, transactions):
        contention_patterns = []
        
        # Group transactions by time windows
        time_windows = self.create_time_windows(transactions, window_size_ms=1000)
        
        for window in time_windows:
            # Find transactions waiting for locks
            waiting_txns = [t for t in window if t.lock_waits > 0]
            
            if len(waiting_txns) > 2:  # Multiple transactions waiting
                pattern = {
                    "timestamp": window.start_time,
                    "waiting_transactions": len(waiting_txns),
                    "total_wait_time_ms": sum(t.total_lock_wait_ms for t in waiting_txns),
                    "hotspot_tables": self.identify_hotspot_tables(waiting_txns),
                    "blocking_pattern": self.analyze_blocking_pattern(waiting_txns)
                }
                
                # Determine severity
                pattern["severity"] = self.calculate_contention_severity(pattern)
                
                contention_patterns.append(pattern)
        
        return contention_patterns
```

### 5. Index Usage Analytics

#### 5.1 Index Performance Monitoring
```sql
CREATE TABLE index_usage_stats (
    id UUID PRIMARY KEY,
    database_id UUID NOT NULL,
    schema_name VARCHAR(100),
    table_name VARCHAR(100),
    index_name VARCHAR(100),
    
    -- Usage statistics
    index_scans BIGINT,
    index_tuple_reads BIGINT,
    index_tuple_fetches BIGINT,
    
    -- Performance metrics
    avg_scan_time_ms FLOAT,
    total_scan_time_ms BIGINT,
    
    -- Size metrics
    index_size_bytes BIGINT,
    table_size_bytes BIGINT,
    
    -- Maintenance metrics
    last_vacuum TIMESTAMP,
    last_analyze TIMESTAMP,
    bloat_ratio FLOAT,
    
    -- Effectiveness
    selectivity FLOAT,
    cardinality INTEGER,
    
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_index_usage_db ON index_usage_stats(database_id, collected_at);

-- Index effectiveness view
CREATE VIEW index_effectiveness AS
WITH index_metrics AS (
    SELECT 
        database_id,
        schema_name,
        table_name,
        index_name,
        index_scans,
        index_size_bytes,
        table_size_bytes,
        selectivity,
        index_scans::float / NULLIF(
            EXTRACT(EPOCH FROM (MAX(collected_at) - MIN(collected_at))), 0
        ) as scans_per_second,
        index_size_bytes::float / NULLIF(table_size_bytes, 0) as size_ratio
    FROM index_usage_stats
    WHERE collected_at > NOW() - INTERVAL '7 days'
    GROUP BY database_id, schema_name, table_name, index_name, 
             index_scans, index_size_bytes, table_size_bytes, selectivity
)
SELECT 
    *,
    CASE 
        WHEN index_scans = 0 THEN 'unused'
        WHEN scans_per_second < 0.001 THEN 'rarely_used'
        WHEN size_ratio > 0.5 AND scans_per_second < 0.01 THEN 'oversized'
        WHEN selectivity < 0.01 THEN 'low_selectivity'
        ELSE 'effective'
    END as index_status,
    CASE 
        WHEN index_scans = 0 THEN 'DROP INDEX ' || index_name
        WHEN scans_per_second < 0.001 AND size_ratio > 0.1 THEN 'Consider dropping'
        WHEN selectivity < 0.01 THEN 'Review selectivity'
        ELSE 'No action needed'
    END as recommendation
FROM index_metrics;
```

### 6. Database Health Scoring

#### 6.1 Health Score Calculation
```typescript
interface DatabaseHealthScore {
  database_id: string;
  overall_score: number; // 0-100
  
  component_scores: {
    performance: number;
    reliability: number;
    efficiency: number;
    security: number;
    maintenance: number;
  };
  
  health_indicators: {
    slow_query_ratio: number;
    deadlock_frequency: number;
    connection_pool_efficiency: number;
    cache_hit_ratio: number;
    replication_lag?: number;
    backup_recency: number;
    index_bloat: number;
  };
  
  risk_factors: {
    factor: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    impact: string;
    mitigation: string;
  }[];
  
  recommendations: {
    priority: 'immediate' | 'short_term' | 'long_term';
    action: string;
    expected_improvement: string;
    effort: 'low' | 'medium' | 'high';
  }[];
}
```

### 7. Replication and Clustering Analytics

#### 7.1 Replication Performance Monitoring
```python
class ReplicationAnalyzer:
    def analyze_replication_health(self, cluster_id: str):
        replication_metrics = self.get_replication_metrics(cluster_id)
        
        analysis = {
            "lag_analysis": self.analyze_replication_lag(replication_metrics),
            "consistency_check": self.check_data_consistency(cluster_id),
            "failover_readiness": self.assess_failover_readiness(cluster_id),
            "optimization_opportunities": []
        }
        
        # Analyze replication lag patterns
        lag_patterns = analysis["lag_analysis"]
        if lag_patterns["avg_lag_ms"] > 1000:
            analysis["optimization_opportunities"].append({
                "type": "reduce_replication_lag",
                "current_lag": lag_patterns["avg_lag_ms"],
                "causes": self.identify_lag_causes(lag_patterns),
                "solutions": [
                    "Increase wal_sender processes",
                    "Optimize network bandwidth",
                    "Reduce transaction size",
                    "Implement parallel replication"
                ]
            })
        
        # Check for replication slots issues
        slot_issues = self.analyze_replication_slots(cluster_id)
        if slot_issues:
            analysis["optimization_opportunities"].append({
                "type": "replication_slot_optimization",
                "issues": slot_issues,
                "recommendations": self.generate_slot_recommendations(slot_issues)
            })
        
        # Analyze failover scenarios
        failover_analysis = self.simulate_failover(cluster_id)
        analysis["failover_analysis"] = {
            "estimated_failover_time": failover_analysis["time_seconds"],
            "data_loss_risk": failover_analysis["potential_data_loss"],
            "readiness_score": failover_analysis["readiness_score"],
            "improvements": failover_analysis["suggested_improvements"]
        }
        
        return analysis
```

### 8. Query Cache Analytics

#### 8.1 Cache Effectiveness Analysis
```sql
CREATE MATERIALIZED VIEW query_cache_analytics AS
WITH cache_stats AS (
    SELECT 
        database_id,
        DATE_TRUNC('hour', timestamp) as hour,
        SUM(query_cache_hits) as total_hits,
        SUM(query_cache_misses) as total_misses,
        SUM(query_cache_inserts) as total_inserts,
        SUM(query_cache_evictions) as total_evictions,
        AVG(query_cache_size_mb) as avg_cache_size,
        MAX(query_cache_size_mb) as max_cache_size
    FROM database_cache_metrics
    WHERE timestamp > NOW() - INTERVAL '24 hours'
    GROUP BY database_id, DATE_TRUNC('hour', timestamp)
),
cache_effectiveness AS (
    SELECT 
        database_id,
        hour,
        total_hits,
        total_misses,
        total_hits::float / NULLIF(total_hits + total_misses, 0) as hit_ratio,
        total_evictions::float / NULLIF(total_inserts, 0) as eviction_ratio,
        avg_cache_size,
        max_cache_size
    FROM cache_stats
)
SELECT 
    *,
    CASE 
        WHEN hit_ratio < 0.5 THEN 'poor'
        WHEN hit_ratio < 0.7 THEN 'fair'
        WHEN hit_ratio < 0.85 THEN 'good'
        ELSE 'excellent'
    END as cache_performance,
    CASE 
        WHEN eviction_ratio > 0.5 THEN 'cache_too_small'
        WHEN hit_ratio < 0.5 THEN 'review_query_patterns'
        WHEN avg_cache_size < max_cache_size * 0.5 THEN 'cache_oversized'
        ELSE 'optimal'
    END as cache_recommendation
FROM cache_effectiveness;
```

### 9. API Endpoints

#### 9.1 Database Analytics Endpoints
```python
@router.get("/analytics/databases/{database_id}/performance")
async def get_database_performance(
    database_id: str,
    timeframe: str = "1h",
    metrics: List[str] = Query(default=["queries", "connections", "resources"])
):
    """Get comprehensive database performance metrics"""
    
@router.post("/analytics/databases/{database_id}/optimize-queries")
async def optimize_database_queries(
    database_id: str,
    query_count: int = 10,
    optimization_level: str = "aggressive"
):
    """Analyze and optimize slow/expensive queries"""
    
@router.get("/analytics/databases/{database_id}/health-score")
async def get_database_health_score(
    database_id: str,
    include_recommendations: bool = True
):
    """Calculate database health score and get recommendations"""
    
@router.post("/analytics/databases/{database_id}/index-analysis")
async def analyze_database_indexes(
    database_id: str,
    include_unused: bool = True,
    suggest_new: bool = True
):
    """Analyze index usage and generate recommendations"""
    
@router.get("/analytics/databases/{cluster_id}/replication")
async def get_replication_analytics(
    cluster_id: str,
    include_lag_analysis: bool = True
):
    """Get replication and clustering analytics"""
```

### 10. Database Analytics Dashboard

#### 10.1 Database Performance Visualization
```typescript
const DatabaseDashboard: React.FC = () => {
  const [dbMetrics, setDbMetrics] = useState<DatabaseMetrics>();
  const [slowQueries, setSlowQueries] = useState<Query[]>([]);
  const [healthScore, setHealthScore] = useState<number>();
  
  useEffect(() => {
    const ws = new WebSocket('/ws/databases/monitor');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Alert on performance issues
      if (data.slow_query_count > 10) {
        showSlowQueryAlert(data);
      }
      
      if (data.deadlock_detected) {
        showDeadlockAlert(data);
      }
      
      if (data.replication_lag > 5000) {
        showReplicationLagAlert(data);
      }
      
      updateMetrics(data);
    };
  }, []);
  
  return (
    <div className="database-dashboard">
      <QueryPerformanceChart 
        queries={queryMetrics}
        showPercentiles={true}
      />
      <ConnectionPoolGauge 
        active={connectionPool.active}
        idle={connectionPool.idle}
        maximum={connectionPool.max}
      />
      <SlowQueryList 
        queries={slowQueries}
        showExecutionPlan={true}
        showOptimizations={true}
      />
      <TransactionTimeline 
        transactions={transactionData}
        showLockContention={true}
      />
      <IndexEffectivenessMatrix 
        indexes={indexUsage}
        showRecommendations={true}
      />
      <CacheHitRatioChart 
        bufferCache={cacheMetrics.buffer}
        queryCache={cacheMetrics.query}
      />
      <ReplicationLagMonitor 
        primary={replicationData.primary}
        replicas={replicationData.replicas}
      />
      <DatabaseHealthScore 
        score={healthScore}
        components={healthComponents}
        risks={riskFactors}
      />
      <ResourceUtilizationHeatmap 
        cpu={resourceMetrics.cpu}
        memory={resourceMetrics.memory}
        io={resourceMetrics.io}
      />
    </div>
  );
};
```

## Implementation Priority
1. Phase 1: Basic performance monitoring and query tracking
2. Phase 2: Query optimization and index analysis
3. Phase 3: Connection pool and transaction analytics
4. Phase 4: Replication and health scoring
5. Phase 5: Advanced optimization and predictive analytics

## Success Metrics
- < 50ms average query response time
- 95% cache hit ratio
- 99.99% database availability
- 40% reduction in slow queries
- < 100ms replication lag