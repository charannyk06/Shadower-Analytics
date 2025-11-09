# Agent Logging Analytics Specification

## Overview
Comprehensive log analysis, pattern recognition, anomaly detection, log aggregation, and observability insights for agent operations in the Shadower platform.

## Core Components

### 1. Log Collection and Processing

#### 1.1 Structured Log Model
```typescript
interface StructuredLog {
  log_id: string;
  agent_id: string;
  execution_id?: string;
  timestamp: string;
  log_level: 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';
  
  // Structured fields
  message: string;
  service: string;
  component: string;
  trace_id?: string;
  span_id?: string;
  parent_span_id?: string;
  
  // Contextual data
  context: {
    user_id?: string;
    workspace_id: string;
    environment: string;
    version: string;
    deployment_id?: string;
  };
  
  // Performance metrics
  metrics?: {
    duration_ms?: number;
    memory_mb?: number;
    cpu_percent?: number;
    request_size_bytes?: number;
    response_size_bytes?: number;
  };
  
  // Error details
  error?: {
    type: string;
    message: string;
    stack_trace?: string;
    error_code?: string;
    is_retriable?: boolean;
  };
  
  // Custom fields
  attributes: Record<string, any>;
}
```

#### 1.2 Log Storage and Indexing
```sql
CREATE TABLE agent_logs (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    execution_id UUID,
    timestamp TIMESTAMP NOT NULL,
    log_level VARCHAR(10) NOT NULL,
    
    -- Message and context
    message TEXT NOT NULL,
    service VARCHAR(100),
    component VARCHAR(100),
    
    -- Tracing
    trace_id VARCHAR(64),
    span_id VARCHAR(32),
    parent_span_id VARCHAR(32),
    
    -- Searchable fields
    user_id UUID,
    workspace_id UUID,
    environment VARCHAR(20),
    
    -- Performance data
    duration_ms INTEGER,
    memory_mb FLOAT,
    cpu_percent FLOAT,
    
    -- Error information
    error_type VARCHAR(100),
    error_message TEXT,
    stack_trace TEXT,
    
    -- Full JSON for complex queries
    raw_log JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (timestamp);

-- Create partitions for efficient querying
CREATE TABLE agent_logs_2024_01 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Indexes for common queries
CREATE INDEX idx_logs_agent_time ON agent_logs(agent_id, timestamp DESC);
CREATE INDEX idx_logs_level ON agent_logs(log_level) WHERE log_level IN ('error', 'fatal');
CREATE INDEX idx_logs_trace ON agent_logs(trace_id);
CREATE INDEX idx_logs_search ON agent_logs USING gin(raw_log);

-- Full-text search index
CREATE INDEX idx_logs_message_fts ON agent_logs USING gin(to_tsvector('english', message));
```

### 2. Log Pattern Recognition

#### 2.1 Pattern Mining Engine
```python
class LogPatternMiner:
    def mine_log_patterns(self, agent_id: str, timeframe: str):
        logs = self.get_logs(agent_id, timeframe)
        
        patterns = {
            "message_patterns": self.extract_message_patterns(logs),
            "error_patterns": self.extract_error_patterns(logs),
            "sequence_patterns": self.extract_sequence_patterns(logs),
            "anomaly_patterns": self.detect_anomalies(logs),
            "correlation_patterns": self.find_correlations(logs)
        }
        
        # Advanced pattern analysis
        patterns["temporal_patterns"] = self.analyze_temporal_patterns(logs)
        patterns["causality_chains"] = self.extract_causality_chains(logs)
        patterns["signature_patterns"] = self.generate_log_signatures(logs)
        
        # Pattern scoring and ranking
        scored_patterns = self.score_patterns(patterns)
        
        return {
            "patterns": scored_patterns,
            "insights": self.generate_insights(scored_patterns),
            "alerts": self.generate_pattern_alerts(scored_patterns),
            "visualization_data": self.prepare_visualization_data(scored_patterns)
        }
    
    def extract_message_patterns(self, logs):
        # Use template mining algorithm
        templates = {}
        
        for log in logs:
            # Tokenize and normalize
            tokens = self.tokenize_message(log.message)
            normalized = self.normalize_tokens(tokens)
            
            # Find or create template
            template = self.find_matching_template(normalized, templates)
            if not template:
                template = self.create_template(normalized)
                templates[template.id] = template
            
            template.occurrences.append(log)
            template.count += 1
        
        # Calculate pattern statistics
        for template in templates.values():
            template.frequency = template.count / len(logs)
            template.variables = self.extract_variables(template)
            template.significance = self.calculate_significance(template)
        
        return sorted(templates.values(), key=lambda x: x.significance, reverse=True)
    
    def extract_sequence_patterns(self, logs):
        # Sequential pattern mining using PrefixSpan
        sequences = self.create_log_sequences(logs)
        
        frequent_patterns = []
        min_support = 0.01  # 1% minimum support
        
        # Apply PrefixSpan algorithm
        prefix_span = PrefixSpan(sequences)
        patterns = prefix_span.frequent(min_support)
        
        for pattern in patterns:
            analyzed_pattern = {
                "sequence": pattern.sequence,
                "support": pattern.support,
                "confidence": self.calculate_confidence(pattern, sequences),
                "lift": self.calculate_lift(pattern, sequences),
                "examples": self.get_pattern_examples(pattern, logs)
            }
            
            # Check if pattern indicates an issue
            if self.is_problematic_pattern(analyzed_pattern):
                analyzed_pattern["severity"] = self.assess_pattern_severity(analyzed_pattern)
                analyzed_pattern["recommendation"] = self.generate_recommendation(analyzed_pattern)
            
            frequent_patterns.append(analyzed_pattern)
        
        return frequent_patterns
```

### 3. Log Anomaly Detection

#### 3.1 Anomaly Detection System
```typescript
interface LogAnomalyDetection {
  anomaly_id: string;
  detection_method: 'statistical' | 'ml_based' | 'rule_based' | 'pattern_based';
  anomaly_type: 'volume' | 'pattern' | 'sequence' | 'timing' | 'content';
  
  anomaly_details: {
    description: string;
    confidence_score: number;
    severity: 'low' | 'medium' | 'high' | 'critical';
    affected_logs: string[];
    time_window: {
      start: string;
      end: string;
    };
  };
  
  baseline_comparison: {
    expected_behavior: any;
    actual_behavior: any;
    deviation_percentage: number;
    statistical_significance: number;
  };
  
  impact_analysis: {
    affected_components: string[];
    potential_issues: string[];
    downstream_impact: string[];
    business_impact: string;
  };
  
  recommendations: {
    immediate_actions: string[];
    investigation_steps: string[];
    preventive_measures: string[];
  };
}
```

#### 3.2 Real-time Anomaly Detection
```python
class RealTimeAnomalyDetector:
    def __init__(self):
        self.models = self.load_anomaly_models()
        self.baselines = self.load_baselines()
        self.rules = self.load_detection_rules()
    
    def detect_anomalies(self, log_stream):
        anomalies = []
        
        for log_batch in log_stream:
            # Statistical anomaly detection
            statistical_anomalies = self.detect_statistical_anomalies(log_batch)
            anomalies.extend(statistical_anomalies)
            
            # Machine learning based detection
            ml_anomalies = self.detect_ml_anomalies(log_batch)
            anomalies.extend(ml_anomalies)
            
            # Pattern-based anomaly detection
            pattern_anomalies = self.detect_pattern_anomalies(log_batch)
            anomalies.extend(pattern_anomalies)
            
            # Rule-based detection
            rule_anomalies = self.detect_rule_anomalies(log_batch)
            anomalies.extend(rule_anomalies)
        
        # Correlate and deduplicate anomalies
        correlated_anomalies = self.correlate_anomalies(anomalies)
        
        # Score and prioritize
        scored_anomalies = self.score_anomalies(correlated_anomalies)
        
        return scored_anomalies
    
    def detect_statistical_anomalies(self, logs):
        anomalies = []
        
        # Volume anomalies
        log_count = len(logs)
        expected_count = self.baselines["volume"]["expected"]
        std_dev = self.baselines["volume"]["std_dev"]
        
        if abs(log_count - expected_count) > 3 * std_dev:
            anomalies.append({
                "type": "volume_anomaly",
                "severity": self.calculate_volume_severity(log_count, expected_count, std_dev),
                "description": f"Unusual log volume: {log_count} (expected: {expected_count})",
                "confidence": self.calculate_confidence(log_count, expected_count, std_dev)
            })
        
        # Error rate anomalies
        error_logs = [l for l in logs if l.level in ['error', 'fatal']]
        error_rate = len(error_logs) / len(logs) if logs else 0
        
        if error_rate > self.baselines["error_rate"]["threshold"]:
            anomalies.append({
                "type": "error_rate_anomaly",
                "severity": "high" if error_rate > 0.1 else "medium",
                "description": f"High error rate: {error_rate:.2%}",
                "affected_logs": [l.id for l in error_logs]
            })
        
        return anomalies
```

### 4. Log Aggregation Analytics

#### 4.1 Log Aggregation Pipeline
```sql
CREATE MATERIALIZED VIEW log_aggregation_metrics AS
WITH log_summary AS (
    SELECT 
        agent_id,
        DATE_TRUNC('minute', timestamp) as minute,
        log_level,
        service,
        component,
        COUNT(*) as log_count,
        COUNT(DISTINCT trace_id) as unique_traces,
        COUNT(DISTINCT user_id) as unique_users,
        AVG(duration_ms) as avg_duration,
        MAX(duration_ms) as max_duration,
        COUNT(CASE WHEN error_type IS NOT NULL THEN 1 END) as error_count
    FROM agent_logs
    WHERE timestamp > NOW() - INTERVAL '1 hour'
    GROUP BY agent_id, DATE_TRUNC('minute', timestamp), 
             log_level, service, component
),
level_distribution AS (
    SELECT 
        agent_id,
        minute,
        SUM(CASE WHEN log_level = 'trace' THEN log_count ELSE 0 END) as trace_count,
        SUM(CASE WHEN log_level = 'debug' THEN log_count ELSE 0 END) as debug_count,
        SUM(CASE WHEN log_level = 'info' THEN log_count ELSE 0 END) as info_count,
        SUM(CASE WHEN log_level = 'warn' THEN log_count ELSE 0 END) as warn_count,
        SUM(CASE WHEN log_level = 'error' THEN log_count ELSE 0 END) as error_count,
        SUM(CASE WHEN log_level = 'fatal' THEN log_count ELSE 0 END) as fatal_count
    FROM log_summary
    GROUP BY agent_id, minute
)
SELECT 
    ls.*,
    ld.trace_count,
    ld.debug_count,
    ld.info_count,
    ld.warn_count,
    ld.error_count,
    ld.fatal_count,
    (ld.error_count + ld.fatal_count)::float / NULLIF(ls.log_count, 0) as error_rate,
    ls.avg_duration as avg_operation_duration,
    CASE 
        WHEN ld.error_count > 100 OR ld.fatal_count > 0 THEN 'critical'
        WHEN ld.error_count > 50 THEN 'warning'
        WHEN ld.warn_count > 100 THEN 'attention'
        ELSE 'normal'
    END as health_status
FROM log_summary ls
JOIN level_distribution ld ON ls.agent_id = ld.agent_id AND ls.minute = ld.minute;
```

### 5. Log Correlation and Tracing

#### 5.1 Distributed Tracing Analytics
```typescript
interface TraceAnalytics {
  trace_id: string;
  root_span_id: string;
  trace_summary: {
    total_spans: number;
    total_duration_ms: number;
    service_count: number;
    error_count: number;
    warning_count: number;
  };
  
  span_tree: {
    span_id: string;
    parent_span_id?: string;
    service: string;
    operation: string;
    duration_ms: number;
    logs: StructuredLog[];
    children: SpanNode[];
  };
  
  critical_path: {
    spans: string[];
    total_duration_ms: number;
    percentage_of_trace: number;
  };
  
  bottlenecks: {
    span_id: string;
    operation: string;
    duration_ms: number;
    percentage_of_trace: number;
    improvement_potential: string;
  }[];
  
  error_propagation: {
    origin_span: string;
    affected_spans: string[];
    error_cascade: boolean;
    recovery_point?: string;
  };
}
```

### 6. Log Search and Query Analytics

#### 6.1 Search Performance Optimization
```python
class LogSearchOptimizer:
    def analyze_search_patterns(self, workspace_id: str):
        search_queries = self.get_search_history(workspace_id)
        
        analysis = {
            "common_queries": self.identify_common_queries(search_queries),
            "query_performance": self.analyze_query_performance(search_queries),
            "index_effectiveness": self.evaluate_indexes(search_queries),
            "optimization_opportunities": []
        }
        
        # Analyze query patterns
        for query_pattern in analysis["common_queries"]:
            performance = self.measure_query_performance(query_pattern)
            
            if performance["avg_duration_ms"] > 1000:
                optimization = {
                    "query_pattern": query_pattern,
                    "current_performance": performance,
                    "optimization_type": self.determine_optimization_type(query_pattern),
                    "recommended_index": self.suggest_index(query_pattern),
                    "expected_improvement": self.estimate_improvement(query_pattern)
                }
                analysis["optimization_opportunities"].append(optimization)
        
        # Suggest materialized views for complex queries
        complex_queries = self.identify_complex_queries(search_queries)
        for query in complex_queries:
            if self.would_benefit_from_materialization(query):
                analysis["optimization_opportunities"].append({
                    "type": "materialized_view",
                    "query": query,
                    "refresh_strategy": self.determine_refresh_strategy(query),
                    "storage_overhead": self.estimate_storage_overhead(query),
                    "performance_gain": self.estimate_performance_gain(query)
                })
        
        return analysis
    
    def suggest_index(self, query_pattern):
        # Analyze query structure
        fields_used = self.extract_fields(query_pattern)
        filter_conditions = self.extract_conditions(query_pattern)
        sort_fields = self.extract_sort_fields(query_pattern)
        
        # Determine optimal index
        index_suggestion = {
            "fields": [],
            "type": "btree",  # default
            "partial": False,
            "unique": False
        }
        
        # Add filter fields first (equality conditions)
        equality_fields = [f for f in filter_conditions if f["operator"] == "="]
        index_suggestion["fields"].extend([f["field"] for f in equality_fields])
        
        # Add range fields
        range_fields = [f for f in filter_conditions if f["operator"] in [">", "<", ">=", "<="]]
        index_suggestion["fields"].extend([f["field"] for f in range_fields[:1]])  # Only first range
        
        # Add sort fields if no range fields
        if not range_fields and sort_fields:
            index_suggestion["fields"].extend(sort_fields)
        
        # Check if GIN index would be better for JSON fields
        if any("jsonb" in str(f) for f in fields_used):
            index_suggestion["type"] = "gin"
        
        # Check if partial index would help
        if self.would_benefit_from_partial_index(filter_conditions):
            index_suggestion["partial"] = True
            index_suggestion["condition"] = self.generate_partial_condition(filter_conditions)
        
        return index_suggestion
```

### 7. Log Retention and Archival Analytics

#### 7.1 Retention Policy Optimization
```sql
CREATE VIEW log_retention_analytics AS
WITH log_usage_stats AS (
    SELECT 
        DATE_TRUNC('day', timestamp) as log_date,
        agent_id,
        COUNT(*) as log_count,
        SUM(LENGTH(message) + LENGTH(COALESCE(stack_trace, ''))) as storage_bytes,
        COUNT(DISTINCT user_id) as unique_users,
        MAX(CASE WHEN log_level IN ('error', 'fatal') THEN 1 ELSE 0 END) as has_errors
    FROM agent_logs
    GROUP BY DATE_TRUNC('day', timestamp), agent_id
),
access_patterns AS (
    SELECT 
        log_date,
        agent_id,
        COUNT(*) as access_count,
        MAX(accessed_at) as last_accessed
    FROM log_access_history
    GROUP BY log_date, agent_id
),
retention_value AS (
    SELECT 
        lus.log_date,
        lus.agent_id,
        lus.log_count,
        lus.storage_bytes,
        COALESCE(ap.access_count, 0) as access_count,
        AGE(NOW(), lus.log_date) as age,
        -- Calculate retention value score
        (
            CASE 
                WHEN lus.has_errors = 1 THEN 0.3
                ELSE 0
            END +
            CASE 
                WHEN COALESCE(ap.access_count, 0) > 0 THEN 
                    0.3 * (1 - EXP(-ap.access_count / 10.0))
                ELSE 0
            END +
            CASE 
                WHEN AGE(NOW(), lus.log_date) < INTERVAL '7 days' THEN 0.4
                WHEN AGE(NOW(), lus.log_date) < INTERVAL '30 days' THEN 0.2
                WHEN AGE(NOW(), lus.log_date) < INTERVAL '90 days' THEN 0.1
                ELSE 0
            END
        ) as retention_score
    FROM log_usage_stats lus
    LEFT JOIN access_patterns ap ON lus.log_date = ap.log_date AND lus.agent_id = ap.agent_id
)
SELECT 
    log_date,
    agent_id,
    log_count,
    storage_bytes,
    access_count,
    age,
    retention_score,
    CASE 
        WHEN retention_score > 0.6 THEN 'hot_storage'
        WHEN retention_score > 0.3 THEN 'warm_storage'
        WHEN retention_score > 0.1 THEN 'cold_storage'
        ELSE 'archive'
    END as recommended_tier,
    CASE 
        WHEN age > INTERVAL '365 days' AND retention_score < 0.1 THEN true
        ELSE false
    END as eligible_for_deletion
FROM retention_value;
```

### 8. Log Cost Analytics

#### 8.1 Cost Optimization Engine
```typescript
interface LogCostAnalytics {
  total_monthly_cost: number;
  cost_breakdown: {
    ingestion_cost: number;
    storage_cost: number;
    query_cost: number;
    retention_cost: number;
    transfer_cost: number;
  };
  
  cost_by_agent: {
    agent_id: string;
    log_volume_gb: number;
    monthly_cost: number;
    cost_per_execution: number;
    optimization_potential: number;
  }[];
  
  optimization_opportunities: {
    opportunity: string;
    current_cost: number;
    optimized_cost: number;
    savings: number;
    implementation: string;
    effort: 'low' | 'medium' | 'high';
  }[];
  
  forecasted_costs: {
    next_month: number;
    next_quarter: number;
    growth_rate: number;
    cost_drivers: string[];
  };
}
```

### 9. API Endpoints

#### 9.1 Logging Analytics Endpoints
```python
@router.post("/analytics/logs/search")
async def search_logs(
    query: str,
    agent_id: Optional[str] = None,
    timeframe: str = "1h",
    limit: int = 100
):
    """Search and analyze logs with advanced queries"""
    
@router.get("/analytics/logs/patterns")
async def get_log_patterns(
    agent_id: str,
    pattern_type: str = "all",
    min_frequency: float = 0.01
):
    """Extract and analyze log patterns"""
    
@router.get("/analytics/logs/anomalies")
async def detect_log_anomalies(
    workspace_id: str,
    detection_method: str = "all",
    sensitivity: float = 0.8
):
    """Detect anomalies in log patterns and volumes"""
    
@router.get("/analytics/logs/trace/{trace_id}")
async def analyze_trace(
    trace_id: str,
    include_logs: bool = True
):
    """Analyze distributed trace and associated logs"""
    
@router.post("/analytics/logs/retention-optimization")
async def optimize_log_retention(
    workspace_id: str,
    target_cost_reduction: float = 0.2
):
    """Generate log retention optimization recommendations"""
```

### 10. Logging Analytics Dashboard

#### 10.1 Log Analytics Visualization
```typescript
const LogAnalyticsDashboard: React.FC = () => {
  const [logMetrics, setLogMetrics] = useState<LogMetrics>();
  const [patterns, setPatterns] = useState<LogPattern[]>([]);
  const [anomalies, setAnomalies] = useState<LogAnomaly[]>([]);
  
  useEffect(() => {
    const ws = new WebSocket('/ws/logs/stream');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Real-time anomaly detection
      if (data.type === 'anomaly') {
        handleAnomalyDetection(data);
      }
      
      // Alert on critical errors
      if (data.level === 'fatal' || 
          (data.level === 'error' && data.error?.is_retriable === false)) {
        triggerCriticalAlert(data);
      }
      
      updateLogMetrics(data);
    };
  }, []);
  
  return (
    <div className="log-analytics-dashboard">
      <LogVolumeChart 
        volume={logVolume}
        byLevel={true}
        showAnomalies={true}
      />
      <ErrorRateGauge 
        errorRate={errorRate}
        threshold={errorThreshold}
        trend={errorTrend}
      />
      <LogPatternCloud 
        patterns={patterns}
        interactive={true}
      />
      <AnomalyTimeline 
        anomalies={anomalies}
        severity="all"
      />
      <TraceWaterfall 
        trace={selectedTrace}
        showLogs={true}
        highlightBottlenecks={true}
      />
      <LogSearchPerformance 
        queries={searchQueries}
        performance={queryPerformance}
      />
      <RetentionCostOptimizer 
        currentCost={retentionCost}
        recommendations={costOptimizations}
      />
      <LogLevelDistribution 
        distribution={levelDistribution}
        showTrends={true}
      />
      <ServiceDependencyGraph 
        services={serviceMap}
        errorPropagation={true}
      />
    </div>
  );
};
```

## Implementation Priority
1. Phase 1: Basic log collection and structured logging
2. Phase 2: Pattern recognition and search optimization
3. Phase 3: Anomaly detection and alerting
4. Phase 4: Distributed tracing and correlation
5. Phase 5: Cost optimization and retention management

## Success Metrics
- < 100ms log search response time
- 95% anomaly detection accuracy
- 40% reduction in log storage costs
- 99.9% log ingestion reliability
- < 1 second pattern recognition latency