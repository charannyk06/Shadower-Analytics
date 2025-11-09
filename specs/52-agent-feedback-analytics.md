# Agent Feedback Analytics Specification

## Overview
Comprehensive analytics for user feedback, satisfaction metrics, improvement tracking, and sentiment analysis for agent interactions in the Shadower platform.

## Core Components

### 1. Feedback Collection System

#### 1.1 Feedback Data Model
```typescript
interface AgentFeedback {
  feedback_id: string;
  agent_id: string;
  execution_id: string;
  user_id: string;
  workspace_id: string;
  feedback_data: {
    type: 'rating' | 'comment' | 'survey' | 'implicit' | 'behavioral';
    rating?: number; // 1-5 scale
    comment?: string;
    survey_responses?: {
      question_id: string;
      question_text: string;
      response: any;
    }[];
    behavioral_signals?: {
      task_completed: boolean;
      retry_attempted: boolean;
      session_abandoned: boolean;
      time_to_complete: number;
    };
  };
  sentiment_analysis: {
    sentiment_score: number; // -1 to 1
    emotion: string; // 'satisfied', 'frustrated', 'neutral', 'delighted', 'disappointed'
    confidence: number;
    key_phrases: string[];
  };
  categorization: {
    category: string; // 'performance', 'accuracy', 'usability', 'feature_request', 'bug'
    subcategory?: string;
    priority: 'low' | 'medium' | 'high' | 'critical';
    actionable: boolean;
  };
  metadata: {
    session_duration: number;
    interaction_count: number;
    context: any;
  };
  timestamp: string;
}
```

#### 1.2 Feedback Storage Schema
```sql
CREATE TABLE agent_feedback (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    execution_id UUID,
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    
    -- Feedback content
    feedback_type VARCHAR(20) NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    survey_data JSONB,
    
    -- Sentiment analysis
    sentiment_score FLOAT,
    emotion VARCHAR(50),
    sentiment_confidence FLOAT,
    key_phrases TEXT[],
    
    -- Categorization
    category VARCHAR(50),
    subcategory VARCHAR(50),
    priority VARCHAR(20),
    is_actionable BOOLEAN DEFAULT FALSE,
    
    -- Response tracking
    response_provided BOOLEAN DEFAULT FALSE,
    response_time_hours FLOAT,
    resolution_status VARCHAR(20),
    
    -- Metadata
    session_duration_seconds INTEGER,
    interaction_count INTEGER,
    device_type VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedback_agent ON agent_feedback(agent_id, created_at);
CREATE INDEX idx_feedback_sentiment ON agent_feedback(sentiment_score);
CREATE INDEX idx_feedback_priority ON agent_feedback(priority, is_actionable);
```

### 2. Sentiment Analysis Engine

#### 2.1 Advanced Sentiment Processing
```python
class SentimentAnalysisEngine:
    def analyze_feedback_sentiment(self, feedback_text: str):
        # Basic sentiment analysis
        base_sentiment = self.calculate_base_sentiment(feedback_text)
        
        # Advanced analysis
        analysis = {
            "sentiment_score": base_sentiment["score"],
            "emotion_detection": self.detect_emotions(feedback_text),
            "aspect_sentiment": self.analyze_aspect_sentiment(feedback_text),
            "intensity_analysis": self.analyze_intensity(feedback_text),
            "sarcasm_detection": self.detect_sarcasm(feedback_text)
        }
        
        # Context-aware adjustment
        analysis = self.apply_context_adjustment(analysis, feedback_text)
        
        # Extract actionable insights
        analysis["key_issues"] = self.extract_key_issues(feedback_text)
        analysis["improvement_suggestions"] = self.extract_suggestions(feedback_text)
        
        return analysis
    
    def analyze_aspect_sentiment(self, text):
        aspects = {
            "performance": [],
            "accuracy": [],
            "usability": [],
            "features": [],
            "reliability": []
        }
        
        sentences = self.split_sentences(text)
        for sentence in sentences:
            # Identify aspect
            aspect = self.identify_aspect(sentence)
            if aspect:
                sentiment = self.calculate_sentiment(sentence)
                aspects[aspect].append({
                    "text": sentence,
                    "sentiment": sentiment,
                    "confidence": self.calculate_confidence(sentence)
                })
        
        # Aggregate aspect sentiments
        for aspect in aspects:
            if aspects[aspect]:
                aspects[aspect] = {
                    "sentences": aspects[aspect],
                    "average_sentiment": np.mean([s["sentiment"] for s in aspects[aspect]]),
                    "mentions": len(aspects[aspect])
                }
        
        return aspects
```

### 3. Satisfaction Metrics Analysis

#### 3.1 Satisfaction Score Calculation
```sql
CREATE MATERIALIZED VIEW satisfaction_metrics AS
WITH feedback_aggregation AS (
    SELECT 
        agent_id,
        DATE_TRUNC('day', created_at) as feedback_date,
        COUNT(*) as feedback_count,
        AVG(rating) as avg_rating,
        STDDEV(rating) as rating_stddev,
        AVG(sentiment_score) as avg_sentiment,
        COUNT(CASE WHEN rating >= 4 THEN 1 END)::float / NULLIF(COUNT(*), 0) as satisfaction_rate,
        COUNT(CASE WHEN rating <= 2 THEN 1 END)::float / NULLIF(COUNT(*), 0) as dissatisfaction_rate
    FROM agent_feedback
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY agent_id, DATE_TRUNC('day', created_at)
),
nps_calculation AS (
    SELECT 
        agent_id,
        COUNT(CASE WHEN rating >= 9 THEN 1 END)::float / NULLIF(COUNT(*), 0) * 100 as promoters,
        COUNT(CASE WHEN rating >= 7 AND rating <= 8 THEN 1 END)::float / NULLIF(COUNT(*), 0) * 100 as passives,
        COUNT(CASE WHEN rating <= 6 THEN 1 END)::float / NULLIF(COUNT(*), 0) * 100 as detractors
    FROM agent_feedback
    WHERE feedback_type = 'survey'
    GROUP BY agent_id
)
SELECT 
    fa.agent_id,
    fa.feedback_date,
    fa.avg_rating,
    fa.avg_sentiment,
    fa.satisfaction_rate,
    (nps.promoters - nps.detractors) as nps_score,
    CASE 
        WHEN fa.avg_rating >= 4.5 THEN 'excellent'
        WHEN fa.avg_rating >= 4.0 THEN 'good'
        WHEN fa.avg_rating >= 3.5 THEN 'acceptable'
        WHEN fa.avg_rating >= 3.0 THEN 'needs_improvement'
        ELSE 'poor'
    END as satisfaction_level,
    fa.rating_stddev as rating_consistency
FROM feedback_aggregation fa
LEFT JOIN nps_calculation nps ON fa.agent_id = nps.agent_id;
```

### 4. Feedback Pattern Recognition

#### 4.1 Pattern Detection System
```typescript
interface FeedbackPattern {
  pattern_id: string;
  pattern_type: 'recurring' | 'trending' | 'anomaly' | 'seasonal';
  description: string;
  occurrence_count: number;
  affected_agents: string[];
  pattern_details: {
    keywords: string[];
    sentiment_range: [number, number];
    time_pattern?: {
      recurring_interval?: string;
      peak_times?: string[];
    };
    user_segments: string[];
  };
  impact_assessment: {
    urgency: 'low' | 'medium' | 'high' | 'critical';
    affected_users: number;
    business_impact: string;
  };
  recommended_actions: {
    action: string;
    priority: number;
    estimated_effort: string;
    expected_outcome: string;
  }[];
}
```

#### 4.2 Pattern Mining Engine
```python
class FeedbackPatternMiner:
    def mine_feedback_patterns(self, workspace_id: str):
        feedback_data = self.get_feedback_data(workspace_id)
        
        patterns = {
            "recurring_issues": self.find_recurring_patterns(feedback_data),
            "trending_topics": self.identify_trends(feedback_data),
            "sentiment_patterns": self.analyze_sentiment_patterns(feedback_data),
            "user_segment_patterns": self.analyze_by_segment(feedback_data)
        }
        
        # Advanced pattern analysis
        patterns["correlation_patterns"] = self.find_correlations(feedback_data)
        patterns["predictive_patterns"] = self.identify_predictive_patterns(feedback_data)
        
        # Generate insights
        insights = self.generate_pattern_insights(patterns)
        
        return {
            "patterns": patterns,
            "insights": insights,
            "action_items": self.prioritize_actions(patterns),
            "trend_forecast": self.forecast_trends(patterns)
        }
    
    def find_recurring_patterns(self, feedback_data):
        # Use frequent pattern mining
        patterns = []
        
        # Extract text features
        text_features = self.extract_text_features(feedback_data)
        
        # Apply FP-Growth algorithm
        fp_tree = self.build_fp_tree(text_features)
        frequent_patterns = self.mine_fp_tree(fp_tree, min_support=0.05)
        
        for pattern in frequent_patterns:
            if pattern.support > 0.1:  # Significant pattern
                patterns.append({
                    "pattern": pattern.items,
                    "frequency": pattern.support,
                    "examples": self.get_pattern_examples(pattern, feedback_data),
                    "impact": self.assess_pattern_impact(pattern, feedback_data)
                })
        
        return patterns
```

### 5. Response and Resolution Tracking

#### 5.1 Response Effectiveness Metrics
```sql
CREATE VIEW feedback_response_analytics AS
WITH response_metrics AS (
    SELECT 
        fr.agent_id,
        fr.response_id,
        fr.feedback_id,
        f.priority,
        fr.response_time_hours,
        fr.resolution_time_hours,
        f.sentiment_score as initial_sentiment,
        f2.sentiment_score as post_response_sentiment,
        (f2.sentiment_score - f.sentiment_score) as sentiment_improvement
    FROM feedback_responses fr
    JOIN agent_feedback f ON fr.feedback_id = f.id
    LEFT JOIN agent_feedback f2 ON f.user_id = f2.user_id 
        AND f2.created_at > fr.responded_at
        AND f2.created_at < fr.responded_at + INTERVAL '7 days'
),
response_effectiveness AS (
    SELECT 
        agent_id,
        AVG(response_time_hours) as avg_response_time,
        AVG(resolution_time_hours) as avg_resolution_time,
        COUNT(CASE WHEN sentiment_improvement > 0 THEN 1 END)::float / 
            NULLIF(COUNT(*), 0) as positive_impact_rate,
        AVG(sentiment_improvement) as avg_sentiment_improvement,
        COUNT(CASE WHEN priority = 'critical' AND response_time_hours < 1 THEN 1 END)::float /
            NULLIF(COUNT(CASE WHEN priority = 'critical' THEN 1 END), 0) as critical_response_rate
    FROM response_metrics
    GROUP BY agent_id
)
SELECT 
    *,
    CASE 
        WHEN avg_response_time < 2 AND positive_impact_rate > 0.7 THEN 'excellent'
        WHEN avg_response_time < 8 AND positive_impact_rate > 0.5 THEN 'good'
        WHEN avg_response_time < 24 AND positive_impact_rate > 0.3 THEN 'acceptable'
        ELSE 'needs_improvement'
    END as response_quality
FROM response_effectiveness;
```

### 6. Improvement Tracking

#### 6.1 Feedback-Driven Improvements
```typescript
interface ImprovementTracker {
  improvement_id: string;
  source_feedback_ids: string[];
  agent_id: string;
  improvement_details: {
    type: 'bug_fix' | 'feature_addition' | 'performance_optimization' | 'ui_improvement';
    description: string;
    implementation_date: string;
    version_deployed: string;
  };
  impact_metrics: {
    feedback_addressed: number;
    users_impacted: number;
    satisfaction_before: number;
    satisfaction_after: number;
    satisfaction_improvement: number;
  };
  validation: {
    success_criteria: string[];
    metrics_achieved: boolean[];
    overall_success: boolean;
  };
  roi_analysis: {
    implementation_cost: number;
    value_generated: number;
    payback_period_days: number;
  };
}
```

### 7. Comparative Feedback Analysis

#### 7.1 Cross-Agent Comparison
```python
class ComparativeFeedbackAnalyzer:
    def compare_agent_feedback(self, workspace_id: str):
        agents = self.get_workspace_agents(workspace_id)
        
        comparison_matrix = {}
        for agent in agents:
            feedback_metrics = self.calculate_feedback_metrics(agent.id)
            comparison_matrix[agent.id] = feedback_metrics
        
        # Calculate relative performance
        rankings = {
            "satisfaction": self.rank_by_metric(comparison_matrix, "avg_rating"),
            "sentiment": self.rank_by_metric(comparison_matrix, "avg_sentiment"),
            "response_quality": self.rank_by_metric(comparison_matrix, "response_effectiveness"),
            "improvement_rate": self.rank_by_metric(comparison_matrix, "improvement_velocity")
        }
        
        # Identify best practices
        best_practices = self.identify_best_practices(comparison_matrix)
        
        # Generate recommendations
        recommendations = {}
        for agent_id in comparison_matrix:
            recommendations[agent_id] = self.generate_improvement_recommendations(
                comparison_matrix[agent_id],
                best_practices
            )
        
        return {
            "comparison_matrix": comparison_matrix,
            "rankings": rankings,
            "best_practices": best_practices,
            "recommendations": recommendations
        }
```

### 8. Predictive Feedback Analytics

#### 8.1 Satisfaction Prediction Model
```python
class SatisfactionPredictor:
    def predict_future_satisfaction(self, agent_id: str):
        historical_data = self.get_historical_feedback(agent_id)
        
        # Feature engineering
        features = self.engineer_features(historical_data)
        
        # Time series prediction
        satisfaction_forecast = self.forecast_satisfaction(features)
        
        # Risk detection
        risk_indicators = {
            "declining_satisfaction_risk": self.detect_decline_risk(satisfaction_forecast),
            "churn_risk": self.predict_churn_risk(features),
            "escalation_risk": self.predict_escalation_risk(features)
        }
        
        # Preventive actions
        if any(risk_indicators.values()):
            preventive_actions = self.generate_preventive_actions(risk_indicators)
        else:
            preventive_actions = []
        
        return {
            "satisfaction_forecast": satisfaction_forecast,
            "confidence_interval": self.calculate_confidence_interval(satisfaction_forecast),
            "risk_indicators": risk_indicators,
            "preventive_actions": preventive_actions,
            "key_drivers": self.identify_satisfaction_drivers(features)
        }
```

### 9. API Endpoints

#### 9.1 Feedback Analytics Endpoints
```python
@router.post("/analytics/feedback/submit")
async def submit_feedback(
    agent_id: str,
    feedback: AgentFeedback
):
    """Submit and analyze agent feedback"""
    
@router.get("/analytics/agents/{agent_id}/satisfaction")
async def get_satisfaction_metrics(
    agent_id: str,
    timeframe: str = "30d",
    include_predictions: bool = True
):
    """Get satisfaction metrics and trends"""
    
@router.get("/analytics/feedback/patterns")
async def get_feedback_patterns(
    workspace_id: str,
    pattern_type: str = "all",
    min_frequency: float = 0.05
):
    """Identify feedback patterns across agents"""
    
@router.get("/analytics/feedback/improvements")
async def track_improvements(
    agent_id: str,
    source: str = "feedback_driven"
):
    """Track improvements made based on feedback"""
```

### 10. Feedback Dashboard

#### 10.1 Feedback Analytics Visualization
```typescript
const FeedbackDashboard: React.FC = () => {
  const [feedbackData, setFeedbackData] = useState<AgentFeedback[]>([]);
  const [patterns, setPatterns] = useState<FeedbackPattern[]>([]);
  
  return (
    <div className="feedback-dashboard">
      <SatisfactionGauge 
        score={satisfactionScore}
        trend={satisfactionTrend}
      />
      <SentimentTimeline 
        data={sentimentData}
        showEvents={true}
      />
      <FeedbackWordCloud 
        feedback={feedbackData}
        sentiment="all"
      />
      <NPSTracker 
        score={npsScore}
        breakdown={npsBreakdown}
      />
      <IssueHeatmap 
        issues={issueData}
        priority="all"
      />
      <ResponseEffectivenessChart 
        metrics={responseMetrics}
      />
      <ImprovementTimeline 
        improvements={improvementData}
        showImpact={true}
      />
      <PatternDetectionMatrix 
        patterns={patterns}
        actionable={true}
      />
    </div>
  );
};
```

## Implementation Priority
1. Phase 1: Basic feedback collection and storage
2. Phase 2: Sentiment analysis and satisfaction metrics
3. Phase 3: Pattern recognition and mining
4. Phase 4: Response tracking and improvement monitoring
5. Phase 5: Predictive analytics and recommendations

## Success Metrics
- 95% feedback capture rate for agent interactions
- < 2 hour average response time for critical feedback
- 30% improvement in satisfaction scores through feedback-driven changes
- 80% accuracy in sentiment classification