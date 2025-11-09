# Agent Queue Analytics Specification

## Overview
Comprehensive analytics for message queuing, task distribution, backpressure handling, queue optimization, and throughput management in the Shadower platform.

## Core Components

### 1. Queue Performance Monitoring

#### 1.1 Queue Metrics Model
```typescript
interface QueueMetrics {
  queue_id: string;
  agent_id: string;
  queue_type: 'fifo' | 'priority' | 'delayed' | 'dead_letter' | 'circular';
  current_state: {
    depth: number;
    size_bytes: number;
    oldest_message_age_ms: number;
    newest_message_age_ms: number;
    active_consumers: number;
    paused: boolean;
  };
  throughput_metrics: {
    enqueue_rate: number;
    dequeue_rate: number;
    processing_rate: number;
    ack_rate: number;
    reject_rate: number;
    requeue_rate: number;
  };
  latency_metrics: {
    avg_wait_time_ms: number;
    p50_wait_time_ms: number;
    p95_wait_time_ms: number;
    p99_wait_time_ms: number;
    avg_processing_time_ms: number;
    end_to_end_latency_ms: number;
  };
  backpressure_indicators: {
    queue_saturation: number; // 0-1
    consumer_lag: number;
    memory_pressure: number;
    cpu_throttling: boolean;
    flow_control_activated: boolean;
  };
}
```

#### 1.2 Queue Analytics Database
```sql
CREATE TABLE queue_metrics (
    id UUID PRIMARY KEY,
    queue_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- Queue state
    queue_depth INTEGER,
    queue_size_bytes BIGINT,
    consumer_count INTEGER,
    
    -- Throughput metrics
    messages_enqueued INTEGER,
    messages_dequeued INTEGER,
    messages_processed INTEGER,
    messages_failed INTEGER,
    messages_dlq INTEGER,
    
    -- Latency percentiles (in microseconds)
    wait_time_p50_us INTEGER,
    wait_time_p95_us INTEGER,
    wait_time_p99_us INTEGER,
    processing_time_avg_us INTEGER,
    
    -- Resource usage
    memory_usage_mb FLOAT,
    cpu_usage_percent FLOAT,
    io_operations INTEGER,
    
    -- Backpressure
    backpressure_events INTEGER,
    flow_control_activations INTEGER,
    consumer_lag_ms INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_queue_metrics_queue ON queue_metrics(queue_id, timestamp);
CREATE INDEX idx_queue_metrics_depth ON queue_metrics(queue_depth DESC);
CREATE INDEX idx_queue_metrics_backpressure ON queue_metrics(backpressure_events);

-- Time-series hypertable for high-volume data
SELECT create_hypertable('queue_metrics', 'timestamp');
```

### 2. Message Flow Analytics

#### 2.1 Message Lifecycle Tracking
```python
class MessageFlowAnalyzer:
    def analyze_message_flow(self, queue_id: str):
        messages = self.get_message_history(queue_id)
        
        flow_analysis = {
            "message_patterns": self.identify_message_patterns(messages),
            "bottlenecks": self.detect_bottlenecks(messages),
            "routing_efficiency": self.analyze_routing(messages),
            "failure_analysis": self.analyze_failures(messages),
            "retry_patterns": self.analyze_retries(messages)
        }
        
        # Advanced flow analytics
        flow_analysis["burst_detection"] = self.detect_message_bursts(messages)
        flow_analysis["dead_letter_analysis"] = self.analyze_dead_letters(messages)
        flow_analysis["consumer_behavior"] = self.analyze_consumer_patterns(messages)
        flow_analysis["message_correlation"] = self.find_message_correlations(messages)
        
        # Optimization recommendations
        optimizations = self.generate_flow_optimizations(flow_analysis)
        
        return {
            "flow_analysis": flow_analysis,
            "optimizations": optimizations,
            "predicted_improvements": self.predict_optimization_impact(optimizations),
            "implementation_roadmap": self.create_optimization_roadmap(optimizations)
        }
    
    def detect_bottlenecks(self, messages):
        bottlenecks = []
        
        # Analyze processing stages
        stages = self.extract_processing_stages(messages)
        
        for stage in stages:
            stage_metrics = {
                "stage_name": stage.name,
                "avg_duration_ms": np.mean(stage.durations),
                "p95_duration_ms": np.percentile(stage.durations, 95),
                "throughput": len(stage.messages) / stage.time_window,
                "queue_buildup": self.calculate_queue_buildup(stage)
            }
            
            # Identify if this is a bottleneck
            if stage_metrics["queue_buildup"] > 100 or stage_metrics["p95_duration_ms"] > 1000:
                bottlenecks.append({
                    "stage": stage.name,
                    "severity": self.calculate_bottleneck_severity(stage_metrics),
                    "impact": {
                        "delayed_messages": stage_metrics["queue_buildup"],
                        "added_latency_ms": stage_metrics["p95_duration_ms"] - np.mean(stage.durations),
                        "throughput_limitation": stage_metrics["throughput"]
                    },
                    "causes": self.identify_bottleneck_causes(stage),
                    "recommendations": self.generate_bottleneck_solutions(stage_metrics)
                })
        
        return sorted(bottlenecks, key=lambda x: x["severity"], reverse=True)
```

### 3. Priority Queue Analytics

#### 3.1 Priority Distribution Analysis
```sql
CREATE MATERIALIZED VIEW priority_queue_analytics AS
WITH priority_distribution AS (
    SELECT 
        queue_id,
        message_priority,
        COUNT(*) as message_count,
        AVG(wait_time_ms) as avg_wait_time,
        AVG(processing_time_ms) as avg_processing_time,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY wait_time_ms) as p95_wait_time,
        COUNT(CASE WHEN status = 'failed' THEN 1 END)::float / NULLIF(COUNT(*), 0) as failure_rate
    FROM queue_messages
    WHERE created_at > NOW() - INTERVAL '24 hours'
    GROUP BY queue_id, message_priority
),
priority_fairness AS (
    SELECT 
        queue_id,
        STDDEV(avg_wait_time) as wait_time_variance,
        MAX(avg_wait_time) - MIN(avg_wait_time) as wait_time_range,
        -- Calculate Gini coefficient for fairness
        SUM(
            (2 * ROW_NUMBER() OVER (ORDER BY avg_wait_time) - COUNT(*) OVER () - 1) * avg_wait_time
        ) / (COUNT(*) OVER () * SUM(avg_wait_time) OVER ()) as gini_coefficient
    FROM priority_distribution
    GROUP BY queue_id
),
starvation_detection AS (
    SELECT 
        queue_id,
        message_priority,
        CASE 
            WHEN p95_wait_time > 10000 AND message_priority < 5 THEN true
            ELSE false
        END as experiencing_starvation,
        p95_wait_time / NULLIF(
            (SELECT MIN(p95_wait_time) FROM priority_distribution pd2 WHERE pd2.queue_id = pd.queue_id),
            0
        ) as relative_wait_ratio
    FROM priority_distribution pd
)
SELECT 
    pd.*,
    pf.gini_coefficient,
    sd.experiencing_starvation,
    sd.relative_wait_ratio,
    CASE 
        WHEN pf.gini_coefficient > 0.4 THEN 'unfair_scheduling'
        WHEN EXISTS (SELECT 1 FROM starvation_detection WHERE experiencing_starvation) THEN 'starvation_detected'
        WHEN pf.wait_time_variance > 1000 THEN 'high_variance'
        ELSE 'balanced'
    END as priority_health_status
FROM priority_distribution pd
JOIN priority_fairness pf ON pd.queue_id = pf.queue_id
JOIN starvation_detection sd ON pd.queue_id = sd.queue_id 
    AND pd.message_priority = sd.message_priority;
```

### 4. Dead Letter Queue Analytics

#### 4.1 DLQ Management System
```typescript
interface DeadLetterQueueAnalytics {
  dlq_id: string;
  parent_queue_id: string;
  message_analysis: {
    total_messages: number;
    message_age_distribution: {
      last_hour: number;
      last_24h: number;
      last_7d: number;
      older: number;
    };
    failure_reasons: {
      reason: string;
      count: number;
      percentage: number;
      sample_messages: string[];
    }[];
    retry_exhaustion_rate: number;
  };
  recovery_metrics: {
    messages_recovered: number;
    recovery_success_rate: number;
    manual_interventions: number;
    auto_recovery_attempts: number;
  };
  pattern_analysis: {
    recurring_failures: {
      pattern: string;
      frequency: number;
      last_occurrence: string;
      suggested_fix: string;
    }[];
    time_based_patterns: {
      peak_failure_hours: number[];
      failure_trend: 'increasing' | 'stable' | 'decreasing';
    };
  };
  cost_impact: {
    storage_cost: number;
    processing_overhead: number;
    manual_review_hours: number;
    business_impact_score: number;
  };
}
```

### 5. Queue Scaling Analytics

#### 5.1 Dynamic Queue Scaling
```python
class QueueScalingEngine:
    def analyze_scaling_needs(self, queue_id: str):
        queue_metrics = self.get_queue_metrics(queue_id)
        load_patterns = self.analyze_load_patterns(queue_id)
        
        scaling_analysis = {
            "current_capacity": self.get_current_capacity(queue_id),
            "load_forecast": self.forecast_queue_load(load_patterns),
            "scaling_triggers": self.identify_scaling_triggers(queue_metrics),
            "optimal_configuration": self.calculate_optimal_config(queue_metrics, load_patterns)
        }
        
        # Partition strategy analysis
        if scaling_analysis["optimal_configuration"]["partitions"] > 1:
            scaling_analysis["partitioning_strategy"] = {
                "recommended_partitions": scaling_analysis["optimal_configuration"]["partitions"],
                "partition_key": self.determine_partition_key(queue_metrics),
                "load_distribution": self.simulate_partition_distribution(queue_metrics),
                "expected_throughput_gain": self.calculate_partition_throughput_gain(queue_metrics)
            }
        
        # Consumer scaling
        scaling_analysis["consumer_scaling"] = {
            "current_consumers": queue_metrics.active_consumers,
            "optimal_consumers": self.calculate_optimal_consumers(queue_metrics),
            "scaling_strategy": self.determine_consumer_scaling_strategy(queue_metrics),
            "auto_scaling_rules": self.generate_autoscaling_rules(queue_metrics, load_patterns)
        }
        
        # Cost-benefit analysis
        scaling_analysis["cost_benefit"] = {
            "current_cost": self.calculate_current_cost(queue_metrics),
            "scaled_cost": self.calculate_scaled_cost(scaling_analysis["optimal_configuration"]),
            "performance_improvement": self.estimate_performance_gain(scaling_analysis),
            "roi": self.calculate_scaling_roi(scaling_analysis)
        }
        
        return scaling_analysis
    
    def generate_autoscaling_rules(self, metrics, patterns):
        rules = []
        
        # Queue depth based scaling
        if metrics.queue_depth_variance > 1000:
            rules.append({
                "name": "queue_depth_scaling",
                "condition": "queue_depth > 10000",
                "action": "scale_consumers",
                "scale_factor": 1.5,
                "cooldown_seconds": 300
            })
        
        # Latency based scaling
        if metrics.p95_latency > 1000:
            rules.append({
                "name": "latency_scaling",
                "condition": "p95_latency_ms > 500",
                "action": "add_consumers",
                "increment": 2,
                "max_consumers": 20
            })
        
        # Time-based scaling
        if patterns.has_predictable_peaks:
            for peak in patterns.peak_times:
                rules.append({
                    "name": f"scheduled_scaling_{peak.hour}",
                    "schedule": f"0 {peak.hour} * * *",
                    "action": "scale_to",
                    "target_consumers": peak.required_consumers
                })
        
        return rules
```

### 6. Message Ordering Analytics

#### 6.1 Order Guarantee Monitoring
```sql
CREATE TABLE message_ordering_violations (
    id UUID PRIMARY KEY,
    queue_id UUID NOT NULL,
    partition_key VARCHAR(255),
    
    -- Violation details
    expected_sequence BIGINT,
    actual_sequence BIGINT,
    message_id_out_of_order UUID,
    previous_message_id UUID,
    
    -- Impact
    messages_affected INTEGER,
    reordering_required BOOLEAN,
    consumer_id UUID,
    
    -- Resolution
    auto_corrected BOOLEAN,
    correction_method VARCHAR(50),
    correction_latency_ms INTEGER,
    
    detected_at TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX idx_ordering_queue ON message_ordering_violations(queue_id, detected_at);
```

### 7. Backpressure Management Analytics

#### 7.1 Backpressure Detection and Response
```typescript
interface BackpressureAnalytics {
  queue_id: string;
  backpressure_state: {
    current_level: 'none' | 'low' | 'medium' | 'high' | 'critical';
    triggers_active: string[];
    duration_ms: number;
    affected_upstream: string[];
  };
  mitigation_strategies: {
    strategy: 'throttling' | 'buffering' | 'dropping' | 'redirect' | 'scale';
    effectiveness: number;
    messages_affected: number;
    latency_added_ms: number;
  }[];
  flow_control: {
    rate_limiting_active: boolean;
    current_rate_limit: number;
    optimal_rate: number;
    burst_capacity: number;
  };
  impact_metrics: {
    messages_delayed: number;
    messages_dropped: number;
    upstream_backpressure_propagated: boolean;
    sla_violations: number;
  };
}
```

### 8. Queue Reliability Analytics

#### 8.1 Reliability Scoring System
```python
class QueueReliabilityAnalyzer:
    def calculate_reliability_score(self, queue_id: str):
        metrics = self.get_reliability_metrics(queue_id)
        
        reliability_components = {
            "availability": self.calculate_availability(metrics),
            "durability": self.calculate_durability(metrics),
            "consistency": self.calculate_consistency(metrics),
            "performance_stability": self.calculate_stability(metrics),
            "error_recovery": self.calculate_recovery_capability(metrics)
        }
        
        # Weight components
        weights = {
            "availability": 0.25,
            "durability": 0.25,
            "consistency": 0.20,
            "performance_stability": 0.15,
            "error_recovery": 0.15
        }
        
        overall_score = sum(
            reliability_components[component] * weights[component]
            for component in weights
        )
        
        # Identify weak points
        weak_points = [
            component for component, score in reliability_components.items()
            if score < 0.7
        ]
        
        # Generate improvement plan
        improvement_plan = []
        for weak_point in weak_points:
            improvement_plan.append({
                "component": weak_point,
                "current_score": reliability_components[weak_point],
                "target_score": 0.85,
                "actions": self.generate_improvement_actions(weak_point, metrics),
                "estimated_effort": self.estimate_improvement_effort(weak_point),
                "expected_impact": self.predict_improvement_impact(weak_point, metrics)
            })
        
        return {
            "overall_reliability_score": overall_score,
            "component_scores": reliability_components,
            "reliability_grade": self.determine_grade(overall_score),
            "weak_points": weak_points,
            "improvement_plan": improvement_plan,
            "trend": self.calculate_reliability_trend(queue_id)
        }
```

### 9. API Endpoints

#### 9.1 Queue Analytics Endpoints
```python
@router.get("/analytics/queues/{queue_id}/metrics")
async def get_queue_metrics(
    queue_id: str,
    timeframe: str = "1h",
    include_messages: bool = False
):
    """Get comprehensive queue metrics and analytics"""
    
@router.post("/analytics/queues/{queue_id}/optimize")
async def optimize_queue_configuration(
    queue_id: str,
    optimization_goals: List[str] = ["throughput", "latency"],
    constraints: dict = {}
):
    """Generate queue optimization recommendations"""
    
@router.get("/analytics/queues/{queue_id}/bottlenecks")
async def detect_queue_bottlenecks(
    queue_id: str,
    severity_threshold: str = "medium"
):
    """Detect and analyze queue bottlenecks"""
    
@router.post("/analytics/queues/{queue_id}/scaling")
async def analyze_queue_scaling(
    queue_id: str,
    forecast_hours: int = 24,
    auto_apply: bool = False
):
    """Analyze and recommend queue scaling strategies"""
    
@router.get("/analytics/dlq/{dlq_id}/analysis")
async def analyze_dead_letter_queue(
    dlq_id: str,
    include_patterns: bool = True
):
    """Analyze dead letter queue messages and patterns"""
```

### 10. Queue Analytics Dashboard

#### 10.1 Real-time Queue Monitoring
```typescript
const QueueDashboard: React.FC = () => {
  const [queueMetrics, setQueueMetrics] = useState<QueueMetrics[]>([]);
  const [selectedQueue, setSelectedQueue] = useState<string>();
  const [backpressureAlerts, setBackpressureAlerts] = useState<Alert[]>([]);
  
  useEffect(() => {
    const ws = new WebSocket('/ws/queues/monitor');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Check for critical conditions
      if (data.backpressure_level === 'critical') {
        triggerBackpressureAlert(data);
      }
      
      if (data.queue_depth > data.threshold * 1.5) {
        triggerQueueOverflowWarning(data);
      }
      
      if (data.consumer_lag > 5000) {
        triggerConsumerLagAlert(data);
      }
      
      updateQueueMetrics(data);
    };
  }, []);
  
  return (
    <div className="queue-dashboard">
      <QueueDepthChart 
        queues={queueMetrics}
        showThresholds={true}
        alertOnOverflow={true}
      />
      <ThroughputMetrics 
        enqueueRate={throughputData.enqueue}
        dequeueRate={throughputData.dequeue}
        processingRate={throughputData.processing}
      />
      <LatencyHistogram 
        latencyData={latencyDistribution}
        percentiles={[50, 95, 99]}
      />
      <BackpressureIndicator 
        level={backpressureLevel}
        triggers={backpressureTriggers}
        mitigations={activeMitigations}
      />
      <MessageFlowSankey 
        flows={messageFlows}
        showBottlenecks={true}
      />
      <PriorityDistributionPie 
        distribution={priorityDistribution}
        showStarvation={true}
      />
      <DLQAnalytics 
        messages={dlqMessages}
        patterns={failurePatterns}
        recoveryRate={recoveryMetrics}
      />
      <ConsumerScalingChart 
        consumers={consumerCount}
        recommendations={scalingRecommendations}
        autoScaleStatus={autoScaleEnabled}
      />
      <ReliabilityScorecard 
        score={reliabilityScore}
        components={reliabilityComponents}
        trend={reliabilityTrend}
      />
    </div>
  );
};
```

## Implementation Priority
1. Phase 1: Basic queue metrics and monitoring
2. Phase 2: Flow analysis and bottleneck detection
3. Phase 3: Backpressure and scaling analytics
4. Phase 4: DLQ and reliability analysis
5. Phase 5: Advanced optimization and predictions

## Success Metrics
- < 100ms p95 queue wait time
- 99.99% message delivery guarantee
- 30% improvement in queue throughput
- 50% reduction in DLQ messages
- 95% accurate bottleneck detection