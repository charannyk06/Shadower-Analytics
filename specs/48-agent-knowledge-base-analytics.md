# Agent Knowledge Base Analytics Specification

## Overview
Analytics for agent knowledge management, including knowledge acquisition, retention, retrieval efficiency, and knowledge graph optimization in the Shadower platform.

## Core Components

### 1. Knowledge Base Structure Analysis

#### 1.1 Knowledge Graph Model
```typescript
interface AgentKnowledgeGraph {
  agent_id: string;
  knowledge_base_id: string;
  graph_metrics: {
    total_nodes: number;
    total_edges: number;
    graph_density: number;
    average_degree: number;
    clustering_coefficient: number;
    connected_components: number;
    max_path_length: number;
  };
  node_types: {
    concepts: number;
    facts: number;
    procedures: number;
    examples: number;
    rules: number;
    relationships: number;
  };
  knowledge_domains: {
    domain: string;
    coverage: number;
    depth: number;
    quality_score: number;
    last_updated: string;
  }[];
  evolution_metrics: {
    growth_rate: number;
    update_frequency: number;
    deprecation_rate: number;
    quality_trend: 'improving' | 'stable' | 'degrading';
  };
}
```

#### 1.2 Knowledge Storage Schema
```sql
CREATE TABLE agent_knowledge_items (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    
    -- Knowledge metadata
    knowledge_type VARCHAR(50), -- 'fact', 'rule', 'procedure', 'concept', 'example'
    domain VARCHAR(100),
    subdomain VARCHAR(100),
    
    -- Content
    content TEXT NOT NULL,
    embedding VECTOR(1536), -- For semantic search
    
    -- Quality metrics
    confidence_score FLOAT,
    verification_status VARCHAR(20),
    source_reliability FLOAT,
    
    -- Usage metrics
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    usefulness_score FLOAT,
    
    -- Relationships
    related_items UUID[],
    prerequisite_items UUID[],
    derived_from UUID[],
    
    -- Temporal aspects
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    deprecation_date TIMESTAMP
);

CREATE INDEX idx_knowledge_agent ON agent_knowledge_items(agent_id);
CREATE INDEX idx_knowledge_embedding ON agent_knowledge_items USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_knowledge_domain ON agent_knowledge_items(domain, subdomain);
```

### 2. Knowledge Acquisition Analytics

#### 2.1 Learning Pattern Analysis
```python
class KnowledgeAcquisitionAnalyzer:
    def analyze_learning_patterns(self, agent_id: str):
        patterns = {
            "acquisition_rate": self.calculate_acquisition_rate(),
            "learning_sources": self.analyze_learning_sources(),
            "knowledge_quality": self.assess_knowledge_quality(),
            "integration_efficiency": self.measure_integration_efficiency(),
            "retention_analysis": self.analyze_retention_patterns()
        }
        
        # Advanced learning analytics
        patterns["learning_curve"] = self.plot_learning_curve(agent_id)
        patterns["knowledge_gaps"] = self.identify_knowledge_gaps(agent_id)
        patterns["optimal_learning_paths"] = self.suggest_learning_paths(agent_id)
        
        return patterns
    
    def plot_learning_curve(self, agent_id: str):
        timeline_data = self.get_knowledge_timeline(agent_id)
        
        curve_analysis = {
            "phases": [],
            "current_phase": None,
            "saturation_point": None,
            "efficiency_trend": []
        }
        
        # Identify learning phases
        phases = [
            {"name": "initial", "start": 0, "end": 0, "rate": 0},
            {"name": "rapid_growth", "start": 0, "end": 0, "rate": 0},
            {"name": "consolidation", "start": 0, "end": 0, "rate": 0},
            {"name": "mastery", "start": 0, "end": 0, "rate": 0}
        ]
        
        for phase in phases:
            phase_data = self.extract_phase_data(timeline_data, phase["name"])
            if phase_data:
                phase.update(phase_data)
                curve_analysis["phases"].append(phase)
        
        # Determine current phase
        curve_analysis["current_phase"] = self.identify_current_phase(timeline_data)
        
        # Predict saturation point
        if curve_analysis["current_phase"] != "mastery":
            curve_analysis["saturation_point"] = self.predict_saturation(timeline_data)
        
        return curve_analysis
```

#### 2.2 Source Quality Assessment
```sql
CREATE MATERIALIZED VIEW knowledge_source_quality AS
WITH source_metrics AS (
    SELECT 
        aki.agent_id,
        aki.source_id,
        s.source_type,
        s.source_name,
        COUNT(aki.id) as items_from_source,
        AVG(aki.confidence_score) as avg_confidence,
        AVG(aki.usefulness_score) as avg_usefulness,
        SUM(aki.access_count) as total_accesses,
        COUNT(CASE WHEN aki.verification_status = 'verified' THEN 1 END)::float / 
            NULLIF(COUNT(*), 0) as verification_rate
    FROM agent_knowledge_items aki
    JOIN knowledge_sources s ON aki.source_id = s.id
    GROUP BY aki.agent_id, aki.source_id, s.source_type, s.source_name
),
source_reliability AS (
    SELECT 
        source_id,
        agent_id,
        -- Calculate reliability score based on multiple factors
        (avg_confidence * 0.3 + 
         avg_usefulness * 0.3 + 
         verification_rate * 0.2 +
         LEAST(items_from_source / 100.0, 1) * 0.2) as reliability_score,
        CASE 
            WHEN avg_confidence > 0.8 AND verification_rate > 0.7 THEN 'highly_reliable'
            WHEN avg_confidence > 0.6 AND verification_rate > 0.5 THEN 'reliable'
            WHEN avg_confidence > 0.4 THEN 'moderately_reliable'
            ELSE 'unreliable'
        END as reliability_category
    FROM source_metrics
)
SELECT 
    sm.*,
    sr.reliability_score,
    sr.reliability_category,
    RANK() OVER (PARTITION BY sm.agent_id ORDER BY sr.reliability_score DESC) as source_rank
FROM source_metrics sm
JOIN source_reliability sr ON sm.source_id = sr.source_id AND sm.agent_id = sr.agent_id;
```

### 3. Knowledge Retrieval Efficiency

#### 3.1 Retrieval Performance Metrics
```typescript
interface RetrievalMetrics {
  agent_id: string;
  retrieval_performance: {
    avg_retrieval_time_ms: number;
    p95_retrieval_time_ms: number;
    cache_hit_rate: number;
    index_efficiency: number;
    query_success_rate: number;
  };
  retrieval_patterns: {
    most_accessed_knowledge: {
      item_id: string;
      access_count: number;
      avg_retrieval_time: number;
    }[];
    access_distribution: {
      hot_items_percentage: number; // Top 10% items
      cold_items_percentage: number; // Never accessed
      access_inequality: number; // Gini coefficient
    };
    temporal_patterns: {
      peak_hours: number[];
      weekly_pattern: number[];
      seasonal_trends: any;
    };
  };
  search_effectiveness: {
    precision: number;
    recall: number;
    f1_score: number;
    avg_results_examined: number;
    user_satisfaction: number;
  };
}
```

#### 3.2 Semantic Search Analytics
```python
class SemanticSearchAnalyzer:
    def analyze_search_performance(self, agent_id: str):
        search_logs = self.get_search_logs(agent_id)
        
        analysis = {
            "embedding_quality": self.assess_embedding_quality(agent_id),
            "semantic_accuracy": self.measure_semantic_accuracy(search_logs),
            "query_understanding": self.analyze_query_understanding(search_logs),
            "result_relevance": self.calculate_result_relevance(search_logs),
            "optimization_opportunities": []
        }
        
        # Identify optimization opportunities
        if analysis["embedding_quality"]["outdated_embeddings"] > 0.2:
            analysis["optimization_opportunities"].append({
                "type": "reindex",
                "reason": "High percentage of outdated embeddings",
                "impact": "30% improvement in search relevance"
            })
        
        if analysis["semantic_accuracy"]["false_positive_rate"] > 0.15:
            analysis["optimization_opportunities"].append({
                "type": "fine_tune_embeddings",
                "reason": "High false positive rate in semantic matches",
                "impact": "25% reduction in irrelevant results"
            })
        
        return analysis
    
    def assess_embedding_quality(self, agent_id: str):
        embeddings = self.get_knowledge_embeddings(agent_id)
        
        quality_metrics = {
            "embedding_coverage": len(embeddings) / self.total_knowledge_items(agent_id),
            "embedding_freshness": self.calculate_embedding_freshness(embeddings),
            "clustering_quality": self.evaluate_clustering(embeddings),
            "semantic_coherence": self.measure_semantic_coherence(embeddings),
            "outdated_embeddings": self.count_outdated_embeddings(embeddings) / len(embeddings)
        }
        
        return quality_metrics
```

### 4. Knowledge Validation and Verification

#### 4.1 Knowledge Accuracy Tracking
```sql
CREATE TABLE knowledge_validation_events (
    id UUID PRIMARY KEY,
    knowledge_item_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    
    -- Validation details
    validation_type VARCHAR(50), -- 'manual', 'automated', 'crowd_sourced', 'cross_reference'
    validator_id VARCHAR(100),
    validation_method TEXT,
    
    -- Results
    is_valid BOOLEAN,
    confidence_level FLOAT,
    error_details JSONB,
    corrections_applied JSONB,
    
    -- Impact
    affected_decisions INTEGER,
    affected_users INTEGER,
    business_impact VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_validation_knowledge ON knowledge_validation_events(knowledge_item_id);
CREATE INDEX idx_validation_agent ON knowledge_validation_events(agent_id);
```

#### 4.2 Knowledge Drift Detection
```python
class KnowledgeDriftDetector:
    def detect_knowledge_drift(self, agent_id: str):
        knowledge_base = self.get_knowledge_base(agent_id)
        
        drift_analysis = {
            "concept_drift": self.detect_concept_drift(knowledge_base),
            "fact_staleness": self.identify_stale_facts(knowledge_base),
            "rule_conflicts": self.find_rule_conflicts(knowledge_base),
            "accuracy_degradation": self.measure_accuracy_degradation(knowledge_base)
        }
        
        # Temporal drift analysis
        for time_window in ['daily', 'weekly', 'monthly']:
            drift_rate = self.calculate_drift_rate(knowledge_base, time_window)
            drift_analysis[f"{time_window}_drift_rate"] = drift_rate
        
        # Generate remediation plan
        if self.requires_intervention(drift_analysis):
            drift_analysis["remediation_plan"] = self.create_remediation_plan(drift_analysis)
        
        return drift_analysis
    
    def detect_concept_drift(self, knowledge_base):
        # Use statistical methods to detect changes in concept distributions
        current_distribution = self.get_current_concept_distribution(knowledge_base)
        baseline_distribution = self.get_baseline_distribution(knowledge_base)
        
        drift_score = self.calculate_kl_divergence(current_distribution, baseline_distribution)
        
        return {
            "drift_score": drift_score,
            "drift_detected": drift_score > 0.3,
            "affected_concepts": self.identify_drifted_concepts(
                current_distribution, 
                baseline_distribution
            )
        }
```

### 5. Knowledge Utilization Analytics

#### 5.1 Usage Pattern Analysis
```typescript
interface KnowledgeUsageAnalytics {
  agent_id: string;
  utilization_metrics: {
    overall_usage_rate: number;
    knowledge_coverage: number; // Percentage of knowledge base actually used
    redundancy_ratio: number;
    knowledge_roi: number;
  };
  usage_patterns: {
    by_type: Record<string, number>;
    by_domain: Record<string, number>;
    by_time_of_day: number[];
    by_user_segment: Record<string, number>;
  };
  effectiveness_analysis: {
    decision_impact: {
      decisions_influenced: number;
      decision_quality_improvement: number;
      error_reduction: number;
    };
    performance_correlation: {
      accuracy_correlation: number;
      speed_correlation: number;
      user_satisfaction_correlation: number;
    };
  };
  optimization_recommendations: {
    unused_knowledge: string[];
    high_value_knowledge: string[];
    knowledge_to_deprecate: string[];
    knowledge_to_expand: string[];
  };
}
```

### 6. Knowledge Graph Optimization

#### 6.1 Graph Structure Optimizer
```python
class KnowledgeGraphOptimizer:
    def optimize_graph_structure(self, agent_id: str):
        graph = self.load_knowledge_graph(agent_id)
        
        optimizations = {
            "redundancy_removal": self.remove_redundant_nodes(graph),
            "edge_optimization": self.optimize_edges(graph),
            "cluster_reorganization": self.reorganize_clusters(graph),
            "path_optimization": self.optimize_paths(graph)
        }
        
        # Calculate improvement metrics
        original_metrics = self.calculate_graph_metrics(graph)
        optimized_graph = self.apply_optimizations(graph, optimizations)
        new_metrics = self.calculate_graph_metrics(optimized_graph)
        
        improvement = {
            "query_speed_improvement": (
                (original_metrics["avg_query_time"] - new_metrics["avg_query_time"]) / 
                original_metrics["avg_query_time"] * 100
            ),
            "storage_reduction": (
                (original_metrics["storage_size"] - new_metrics["storage_size"]) / 
                original_metrics["storage_size"] * 100
            ),
            "traversal_efficiency": new_metrics["traversal_efficiency"] / original_metrics["traversal_efficiency"]
        }
        
        return {
            "optimizations": optimizations,
            "improvement_metrics": improvement,
            "new_graph_metrics": new_metrics
        }
    
    def optimize_edges(self, graph):
        optimizations = []
        
        # Remove weak relationships
        weak_edges = [e for e in graph.edges if e.weight < 0.1]
        optimizations.append({
            "action": "remove_weak_edges",
            "count": len(weak_edges),
            "impact": "Reduced noise in relationship traversal"
        })
        
        # Add missing transitive relationships
        transitive_edges = self.find_transitive_relationships(graph)
        optimizations.append({
            "action": "add_transitive_edges",
            "count": len(transitive_edges),
            "impact": "Faster multi-hop queries"
        })
        
        return optimizations
```

### 7. Knowledge Transfer Analytics

#### 7.1 Cross-Agent Knowledge Sharing
```sql
CREATE VIEW knowledge_transfer_analytics AS
WITH transfer_events AS (
    SELECT 
        source_agent_id,
        target_agent_id,
        COUNT(*) as transfer_count,
        AVG(knowledge_quality_score) as avg_quality,
        SUM(CASE WHEN transfer_successful THEN 1 ELSE 0 END)::float / COUNT(*) as success_rate,
        AVG(adaptation_time_hours) as avg_adaptation_time
    FROM knowledge_transfers
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY source_agent_id, target_agent_id
),
transfer_effectiveness AS (
    SELECT 
        target_agent_id,
        COUNT(DISTINCT source_agent_id) as knowledge_sources,
        AVG(performance_improvement) as avg_performance_gain,
        SUM(transfer_count) as total_transfers_received
    FROM transfer_events te
    JOIN agent_performance_metrics apm ON te.target_agent_id = apm.agent_id
    GROUP BY target_agent_id
)
SELECT 
    te.*,
    tef.avg_performance_gain,
    CASE 
        WHEN success_rate > 0.8 AND avg_performance_gain > 0.1 THEN 'highly_effective'
        WHEN success_rate > 0.6 AND avg_performance_gain > 0.05 THEN 'effective'
        WHEN success_rate > 0.4 THEN 'moderately_effective'
        ELSE 'ineffective'
    END as transfer_effectiveness
FROM transfer_events te
LEFT JOIN transfer_effectiveness tef ON te.target_agent_id = tef.target_agent_id;
```

### 8. Knowledge Lifecycle Management

#### 8.1 Lifecycle Stage Tracking
```typescript
interface KnowledgeLifecycle {
  knowledge_item_id: string;
  current_stage: 'acquisition' | 'validation' | 'active_use' | 'maintenance' | 'deprecation' | 'archived';
  stage_history: {
    stage: string;
    entered_at: string;
    duration_days: number;
    trigger_event: string;
  }[];
  health_metrics: {
    accuracy_score: number;
    relevance_score: number;
    usage_frequency: number;
    last_validation: string;
    update_needed: boolean;
  };
  lifecycle_predictions: {
    expected_deprecation_date: string;
    maintenance_priority: 'high' | 'medium' | 'low';
    refresh_recommendation: string;
  };
}
```

### 9. API Endpoints

#### 9.1 Knowledge Analytics Endpoints
```python
@router.get("/analytics/agents/{agent_id}/knowledge-base")
async def get_knowledge_base_analytics(
    agent_id: str,
    include_graph_metrics: bool = True,
    include_usage_patterns: bool = True
):
    """Get comprehensive knowledge base analytics for an agent"""
    
@router.post("/analytics/agents/{agent_id}/knowledge/optimize")
async def optimize_knowledge_base(
    agent_id: str,
    optimization_type: str = "comprehensive",
    dry_run: bool = True
):
    """Optimize agent's knowledge base structure"""
    
@router.get("/analytics/knowledge/drift-detection")
async def detect_knowledge_drift(
    workspace_id: str,
    time_window: str = "30d",
    drift_threshold: float = 0.3
):
    """Detect knowledge drift across agents"""
    
@router.post("/analytics/knowledge/transfer")
async def analyze_knowledge_transfer(
    source_agent_id: str,
    target_agent_id: str,
    knowledge_domain: Optional[str] = None
):
    """Analyze knowledge transfer effectiveness between agents"""
```

### 10. Knowledge Dashboard

#### 10.1 Knowledge Analytics Visualization
```typescript
const KnowledgeDashboard: React.FC = () => {
  return (
    <div className="knowledge-dashboard">
      <KnowledgeGraphVisualization 
        graph={knowledgeGraph}
        layout="force-directed"
        showClusters={true}
      />
      <KnowledgeGrowthChart 
        data={growthData}
        showLearningCurve={true}
      />
      <KnowledgeUtilizationHeatmap 
        usage={usageData}
        groupBy="domain"
      />
      <DriftDetectionTimeline 
        driftEvents={driftData}
        severity="all"
      />
      <SourceQualityMatrix 
        sources={sourceData}
        metric="reliability"
      />
      <RetrievalPerformanceGauge 
        metrics={retrievalMetrics}
      />
      <KnowledgeLifecycleFlow 
        items={lifecycleData}
        stage="all"
      />
    </div>
  );
};
```

## Implementation Priority
1. Phase 1: Knowledge base structure and storage
2. Phase 2: Acquisition and retrieval analytics
3. Phase 3: Validation and drift detection
4. Phase 4: Graph optimization and utilization
5. Phase 5: Transfer and lifecycle management

## Success Metrics
- 40% improvement in knowledge retrieval speed
- 30% reduction in knowledge redundancy
- 95% accuracy in drift detection
- 25% improvement in knowledge utilization rate