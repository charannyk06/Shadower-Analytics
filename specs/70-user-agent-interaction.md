# User Agent Interaction Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

Track how users interact with agents. Which agents they use, how they communicate, what works, what confuses them. Simple agent usage analytics focused on improving the user-agent experience.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// User-agent interaction
interface UserAgentInteraction {
  id: string;
  userId: string;
  agentId: string;
  agentName: string;
  interaction: InteractionDetails;
  outcome: InteractionOutcome;
  satisfaction: UserSatisfaction;
}

interface InteractionDetails {
  startTime: Date;
  endTime?: Date;
  duration?: number;
  messageCount: number;
  userMessages: number;
  agentResponses: number;
  interactionType: 'chat' | 'command' | 'workflow' | 'help';
  context?: string;
}

interface InteractionOutcome {
  completed: boolean;
  successful: boolean;
  taskAchieved: boolean;
  errorOccurred: boolean;
  userAbandoned: boolean;
  reason?: string;
}

interface UserSatisfaction {
  rating?: number; // 1-5
  feedback?: string;
  wouldUseAgain: boolean;
  reportedIssue: boolean;
}

// Agent usage patterns
interface AgentUsagePattern {
  userId: string;
  preferredAgents: string[];
  avoidedAgents: string[];
  usageFrequency: Record<string, number>;
  successRates: Record<string, number>;
}

// Communication patterns
interface CommunicationPattern {
  pattern: 'question' | 'command' | 'clarification' | 'correction' | 'frustration';
  frequency: number;
  examples: string[];
  agentHandling: 'good' | 'poor' | 'failed';
}
```

#### 1.2 SQL Schema

```sql
-- Simple agent interaction tracking
CREATE TABLE user_agent_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    agent_name VARCHAR(255),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration_seconds INTEGER,
    message_count INTEGER DEFAULT 0,
    user_messages INTEGER DEFAULT 0,
    agent_responses INTEGER DEFAULT 0,
    interaction_type VARCHAR(50),
    completed BOOLEAN DEFAULT FALSE,
    successful BOOLEAN,
    error_occurred BOOLEAN DEFAULT FALSE,
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Daily agent usage summary
CREATE TABLE daily_agent_usage (
    date DATE NOT NULL,
    user_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    interaction_count INTEGER DEFAULT 0,
    total_duration_seconds INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    avg_rating DECIMAL(3,2),
    PRIMARY KEY (date, user_id, agent_id)
);

-- User agent preferences
CREATE TABLE user_agent_preferences (
    user_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    is_favorite BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,
    custom_name VARCHAR(255),
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMPTZ,
    avg_satisfaction DECIMAL(3,2),
    notes TEXT,
    PRIMARY KEY (user_id, agent_id)
);

-- Common user phrases
CREATE TABLE user_agent_phrases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phrase_text TEXT NOT NULL,
    phrase_type VARCHAR(50),
    agent_id UUID,
    frequency INTEGER DEFAULT 1,
    successful_handling BOOLEAN,
    last_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Simple indexes
CREATE INDEX idx_interactions_user ON user_agent_interactions(user_id, start_time DESC);
CREATE INDEX idx_interactions_agent ON user_agent_interactions(agent_id);
CREATE INDEX idx_daily_usage_date ON daily_agent_usage(date DESC);
```

#### 1.3 Python Analysis Models

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict

@dataclass
class AgentInteractionAnalyzer:
    """Simple agent interaction analysis"""
    
    def get_user_agents(self, user_id: str) -> List[Dict]:
        """Which agents does user interact with?"""
        return self.db.query(
            """
            SELECT 
                agent_id,
                agent_name,
                COUNT(*) as interactions,
                AVG(duration_seconds) as avg_duration,
                AVG(CASE WHEN successful THEN 1 ELSE 0 END) as success_rate,
                AVG(user_rating) as avg_rating,
                MAX(start_time) as last_used
            FROM user_agent_interactions
            WHERE user_id = ?
            GROUP BY agent_id, agent_name
            ORDER BY interactions DESC
            """,
            (user_id,)
        )
    
    def get_agent_effectiveness(self, agent_id: str) -> Dict:
        """How effective is this agent?"""
        stats = self.db.query_one(
            """
            SELECT 
                COUNT(*) as total_interactions,
                AVG(CASE WHEN successful THEN 1 ELSE 0 END) as success_rate,
                AVG(CASE WHEN completed THEN 1 ELSE 0 END) as completion_rate,
                AVG(user_rating) as avg_rating,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(message_count) as avg_messages
            FROM user_agent_interactions
            WHERE agent_id = ? AND start_time > NOW() - INTERVAL '30 days'
            """,
            (agent_id,)
        )
        
        return {
            'effectiveness_score': (
                stats['success_rate'] * 0.4 + 
                stats['completion_rate'] * 0.3 + 
                (stats['avg_rating'] or 3) / 5 * 0.3
            ),
            **stats
        }
    
    def find_confused_interactions(self) -> List[Dict]:
        """Find interactions where user seems confused"""
        return self.db.query(
            """
            SELECT 
                id,
                user_id,
                agent_id,
                message_count,
                duration_seconds
            FROM user_agent_interactions
            WHERE (
                message_count > 10 AND NOT successful
                OR duration_seconds > 600 AND NOT completed
                OR user_messages > agent_responses * 2
            )
            AND start_time > NOW() - INTERVAL '24 hours'
            """
        )
    
    def get_communication_patterns(self, user_id: str) -> List[Dict]:
        """How does user communicate with agents?"""
        # This would analyze actual message content in production
        # For now, return patterns based on interaction metrics
        interactions = self.db.query(
            """
            SELECT 
                message_count,
                user_messages,
                agent_responses,
                successful,
                duration_seconds
            FROM user_agent_interactions
            WHERE user_id = ?
            ORDER BY start_time DESC
            LIMIT 20
            """,
            (user_id,)
        )
        
        patterns = []
        
        # Quick interactions
        quick = [i for i in interactions if i['message_count'] <= 3]
        if len(quick) > 5:
            patterns.append({
                'type': 'quick_commander',
                'description': 'Prefers quick, direct commands',
                'frequency': len(quick) / len(interactions)
            })
        
        # Long conversations
        long_convs = [i for i in interactions if i['message_count'] > 10]
        if len(long_convs) > 3:
            patterns.append({
                'type': 'conversationalist',
                'description': 'Has detailed conversations with agents',
                'frequency': len(long_convs) / len(interactions)
            })
        
        # High failure rate
        failures = [i for i in interactions if not i['successful']]
        if len(failures) > len(interactions) * 0.3:
            patterns.append({
                'type': 'struggling',
                'description': 'Having difficulty with agents',
                'frequency': len(failures) / len(interactions)
            })
        
        return patterns
    
    def recommend_agents(self, user_id: str) -> List[Dict]:
        """Recommend agents based on user's needs"""
        # Get user's successful interactions
        successful = self.db.query(
            """
            SELECT agent_id, agent_name, COUNT(*) as count
            FROM user_agent_interactions
            WHERE user_id = ? AND successful = TRUE
            GROUP BY agent_id, agent_name
            ORDER BY count DESC
            LIMIT 5
            """,
            (user_id,)
        )
        
        # Get similar users' favorite agents
        # (simplified - would use better similarity in production)
        similar_users_agents = self.db.query(
            """
            SELECT agent_id, agent_name, COUNT(DISTINCT user_id) as users
            FROM user_agent_interactions
            WHERE successful = TRUE
            AND agent_id NOT IN (
                SELECT agent_id FROM user_agent_interactions WHERE user_id = ?
            )
            GROUP BY agent_id, agent_name
            ORDER BY users DESC
            LIMIT 3
            """,
            (user_id,)
        )
        
        return similar_users_agents
```

### 2. API Endpoints

```python
from fastapi import APIRouter, Query
from typing import List, Optional

router = APIRouter(prefix="/api/v1/agent-interactions")

@router.post("/start")
async def start_interaction(
    user_id: str,
    agent_id: str,
    interaction_type: str
):
    """Start tracking an agent interaction"""
    pass

@router.post("/{interaction_id}/end")
async def end_interaction(
    interaction_id: str,
    outcome: InteractionOutcome
):
    """End an agent interaction"""
    pass

@router.post("/{interaction_id}/message")
async def track_message(
    interaction_id: str,
    sender: str  # 'user' or 'agent'
):
    """Track a message in the interaction"""
    pass

@router.post("/{interaction_id}/rate")
async def rate_interaction(
    interaction_id: str,
    rating: int,
    feedback: Optional[str] = None
):
    """Rate an agent interaction"""
    pass

@router.get("/user/{user_id}/agents")
async def get_user_agents(user_id: str):
    """Get agents user interacts with"""
    pass

@router.get("/user/{user_id}/patterns")
async def get_user_patterns(user_id: str):
    """Get user's communication patterns"""
    pass

@router.get("/agent/{agent_id}/effectiveness")
async def get_agent_effectiveness(agent_id: str):
    """Get agent effectiveness metrics"""
    pass

@router.get("/confused")
async def get_confused_interactions():
    """Find confused user interactions"""
    pass

@router.get("/recommendations/{user_id}")
async def get_agent_recommendations(user_id: str):
    """Recommend agents for user"""
    pass
```

### 3. Dashboard Components

```typescript
export const AgentInteractionTracker: React.FC = () => {
  const [interactionId, setInteractionId] = useState<string | null>(null);
  
  const startInteraction = (agentId: string) => {
    api.post('/agent-interactions/start', {
      userId: getCurrentUser().id,
      agentId,
      interactionType: 'chat'
    }).then(res => setInteractionId(res.id));
  };
  
  const endInteraction = (outcome: any) => {
    if (!interactionId) return;
    
    api.post(`/agent-interactions/${interactionId}/end`, {
      outcome
    });
    setInteractionId(null);
  };
  
  // Track messages
  useEffect(() => {
    if (!interactionId) return;
    
    const trackMessage = (sender: string) => {
      api.post(`/agent-interactions/${interactionId}/message`, { sender });
    };
    
    // Hook into message system
    messageEmitter.on('message', trackMessage);
    
    return () => {
      messageEmitter.off('message', trackMessage);
    };
  }, [interactionId]);
  
  return null;
};

export const MyAgents: React.FC = () => {
  const [agents, setAgents] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-bold mb-2">Your Agents</h3>
        <div className="grid grid-cols-2 gap-2">
          {agents.map(agent => (
            <div key={agent.agentId} className="p-3 border rounded">
              <div className="font-medium">{agent.agentName}</div>
              <div className="text-sm text-gray-600">
                Used {agent.interactions} times
              </div>
              <div className="text-xs">
                {agent.successRate > 0.8 ? '✅' : '⚠️'} 
                {(agent.successRate * 100).toFixed(0)}% success
              </div>
              {agent.avgRating && (
                <div className="text-xs">
                  {'⭐'.repeat(Math.round(agent.avgRating))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      
      {recommendations.length > 0 && (
        <div>
          <h3 className="font-bold mb-2">Try These Agents</h3>
          <div className="space-y-1">
            {recommendations.map(agent => (
              <button
                key={agent.agentId}
                className="w-full text-left p-2 hover:bg-gray-50 rounded"
                onClick={() => startChat(agent.agentId)}
              >
                <div className="font-medium">{agent.agentName}</div>
                <div className="text-xs text-gray-500">
                  Popular with similar users
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export const AgentRating: React.FC<{ interactionId: string }> = ({ interactionId }) => {
  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState('');
  
  const submitRating = () => {
    api.post(`/agent-interactions/${interactionId}/rate`, {
      rating,
      feedback
    });
  };
  
  return (
    <div className="p-3 bg-gray-50 rounded">
      <div className="text-sm mb-2">How was this interaction?</div>
      <div className="flex space-x-1 mb-2">
        {[1, 2, 3, 4, 5].map(star => (
          <button
            key={star}
            onClick={() => setRating(star)}
            className={`text-2xl ${star <= rating ? 'text-yellow-500' : 'text-gray-300'}`}
          >
            ⭐
          </button>
        ))}
      </div>
      {rating > 0 && rating < 4 && (
        <textarea
          className="w-full p-2 text-sm border rounded"
          placeholder="What went wrong?"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
        />
      )}
      {rating > 0 && (
        <button
          onClick={submitRating}
          className="mt-2 px-3 py-1 bg-blue-500 text-white rounded text-sm"
        >
          Submit
        </button>
      )}
    </div>
  );
};

export const AgentEffectivenessIndicator: React.FC<{ agentId: string }> = ({ agentId }) => {
  const [effectiveness, setEffectiveness] = useState(null);
  
  useEffect(() => {
    api.get(`/agent-interactions/agent/${agentId}/effectiveness`)
      .then(setEffectiveness);
  }, [agentId]);
  
  if (!effectiveness) return null;
  
  const score = effectiveness.effectiveness_score;
  const color = score > 0.8 ? 'green' : score > 0.6 ? 'yellow' : 'red';
  
  return (
    <div className={`text-${color}-600 text-sm`}>
      {score > 0.8 ? '🎯 Highly Effective' :
       score > 0.6 ? '📊 Moderately Effective' :
       '⚠️ Needs Improvement'}
    </div>
  );
};
```

### 4. Interaction Insights

```typescript
// Generate insights from interactions
export const generateInteractionInsights = (interactions: UserAgentInteraction[]) => {
  const insights = [];
  
  // Most helpful agent
  const bySuccess = interactions.sort((a, b) => 
    (b.outcome.successful ? 1 : 0) - (a.outcome.successful ? 1 : 0)
  );
  
  if (bySuccess[0]?.outcome.successful) {
    insights.push({
      type: 'helpful_agent',
      message: `${bySuccess[0].agentName} solves your problems best`,
      agentId: bySuccess[0].agentId
    });
  }
  
  // Struggling with an agent
  const struggles = interactions.filter(i => 
    i.interaction.messageCount > 10 && !i.outcome.successful
  );
  
  if (struggles.length > 0) {
    insights.push({
      type: 'struggling',
      message: `You might need help with ${struggles[0].agentName}`,
      action: 'View tutorial'
    });
  }
  
  // Underused highly-rated agents
  const highRated = interactions.filter(i => i.satisfaction.rating >= 4);
  const underused = highRated.filter(i => {
    const uses = interactions.filter(int => int.agentId === i.agentId).length;
    return uses < 3;
  });
  
  if (underused.length > 0) {
    insights.push({
      type: 'underused',
      message: `You liked ${underused[0].agentName} - use it more!`,
      agentId: underused[0].agentId
    });
  }
  
  return insights;
};
```

## Implementation Priority

### Phase 1 (Day 1)
- Track interaction start/end
- Message counting
- Basic outcome tracking

### Phase 2 (Days 2-3)
- User ratings
- Agent effectiveness
- Daily summaries

### Phase 3 (Days 4-5)
- Pattern detection
- Confused interaction detection
- Agent recommendations

## Cost Optimization

- Track interactions, not individual messages
- Daily aggregations
- Keep detailed data for 7 days only
- Simple rating system (1-5)
- No message content storage

## What This Tells Us

- Which agents users prefer
- Where users get confused
- Agent effectiveness
- Communication patterns
- User satisfaction levels

## What We DON'T Track

- Full conversation transcripts
- Message content analysis
- Real-time sentiment analysis
- Complex NLP processing
- Agent internal state