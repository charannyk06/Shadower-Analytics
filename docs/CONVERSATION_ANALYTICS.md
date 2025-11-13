# Conversation Analytics - Implementation Documentation

## Overview

The Conversation Analytics feature provides comprehensive tracking and analysis of agent conversations, including sentiment analysis, engagement metrics, context management, and conversation outcomes.

## Features Implemented

### 1. Database Schema

**Migration File**: `database/migrations/028_create_conversation_analytics_tables.sql`

#### Core Tables

- **conversation_analytics**: Aggregated conversation metrics
  - Session timing and duration
  - Message counts and velocity
  - Token usage and costs
  - Quality scores (sentiment, clarity, relevance, satisfaction)
  - Conversation status and goals

- **conversation_messages**: Individual message tracking
  - Message content and metadata
  - Sentiment and emotion analysis
  - Intent classification
  - Quality metrics per message
  - Error tracking

- **conversation_context_metrics**: Context management analytics
  - Context window usage
  - Topic tracking
  - Memory and recall metrics

- **conversation_engagement_metrics**: User engagement scoring
  - Interaction depth
  - User investment
  - Conversation momentum
  - Question quality

- **conversation_outcomes**: Outcome tracking
  - Goal achievement
  - Tasks completed
  - User satisfaction
  - Business value metrics

#### Supporting Tables

- **conversation_turn_metrics**: Turn-taking patterns
- **conversation_emotion_timeline**: Emotional progression
- **conversation_sentiment_progression**: Sentiment tracking
- **response_quality_metrics**: Response quality analysis
- **intent_analytics**: Intent recognition performance
- **entity_extraction_metrics**: Entity extraction tracking
- **conversation_patterns_cache**: Pattern analysis cache

#### Materialized Views

- **mv_agent_conversation_performance**: Agent performance aggregates
- **mv_conversation_quality_trends**: Quality trends over time
- **mv_intent_recognition_performance**: Intent recognition metrics

### 2. Data Models (Pydantic Schemas)

**File**: `backend/src/models/schemas/conversation_analytics.py`

Key models:
- `ConversationAnalytics`: Complete conversation data
- `ConversationMessage`: Individual messages with analysis
- `EmotionAnalytics`: Emotion tracking and progression
- `EngagementMetrics`: User engagement scores
- `ConversationOutcome`: Outcome tracking
- `TurnTakingMetrics`: Conversation dynamics

### 3. Services

#### ConversationAnalyticsService

**File**: `backend/src/services/analytics/conversation_analytics_service.py`

Core functionality:
- Create and track conversations
- Record messages with analytics
- End conversations and calculate final metrics
- Retrieve comprehensive analytics
- Agent performance metrics
- Quality trends over time

**Methods**:
```python
async def create_conversation(conversation_id, agent_id, workspace_id, user_id)
async def record_message(conversation_id, role, content, tokens_used, ...)
async def end_conversation(conversation_id, status, goal_achieved)
async def get_conversation_analytics(conversation_id, include_messages)
async def get_agent_performance(agent_id, workspace_id, timeframe_days)
async def get_quality_trends(workspace_id, agent_id, hours)
```

#### SentimentEmotionService

**File**: `backend/src/services/analytics/sentiment_emotion_service.py`

Features:
- Sentiment analysis using keyword-based approach
- Emotion detection (happy, frustrated, confused, satisfied, neutral)
- Emotion timeline tracking
- Sentiment progression analysis
- Emotion transition detection

**Methods**:
```python
def analyze_sentiment(text) -> float
def detect_emotion(text) -> Tuple[str, float, float]
async def analyze_message_sentiment(message_id, conversation_id, content)
async def get_emotion_analytics(conversation_id)
async def analyze_sentiment_progression(conversation_id)
```

#### EngagementScoringService

**File**: `backend/src/services/analytics/engagement_scoring_service.py`

Engagement components:
- Interaction depth (20% weight)
- User investment (25% weight)
- Conversation momentum (15% weight)
- Topic exploration (15% weight)
- Question quality (15% weight)
- Feedback indicators (10% weight)

**Methods**:
```python
async def calculate_engagement(conversation_id, agent_id, user_id)
async def get_workspace_engagement_trends(workspace_id, days)
```

### 4. API Endpoints

**File**: `backend/src/api/routes/conversation_analytics.py`

Base URL: `/api/v1/analytics/conversations`

#### Conversation Retrieval

**GET** `/api/v1/analytics/conversations/{conversation_id}`
- Get comprehensive analytics for a conversation
- Query parameters:
  - `include_messages`: bool (default: false)
  - `include_sentiment`: bool (default: true)
  - `include_engagement`: bool (default: true)

**GET** `/api/v1/analytics/conversations/agents/{agent_id}/performance`
- Get agent performance metrics from conversations
- Query parameters:
  - `workspace_id`: required
  - `timeframe_days`: int (1-90, default: 7)

**GET** `/api/v1/analytics/conversations/workspace/{workspace_id}/quality-trends`
- Get quality trends over time
- Query parameters:
  - `agent_id`: optional filter
  - `hours`: int (1-168, default: 24)

**GET** `/api/v1/analytics/conversations/workspace/{workspace_id}/engagement-trends`
- Get engagement trends for workspace
- Query parameters:
  - `period`: hourly|daily|weekly (default: daily)
  - `days`: int (1-90, default: 7)
  - `metric_types`: array

#### Conversation Analysis

**POST** `/api/v1/analytics/conversations/analyze-quality`
- Analyze quality across multiple conversations
- Body: `ConversationQualityAnalysisRequest`
  - `conversation_ids`: array (max 100)
  - `quality_dimensions`: array

**GET** `/api/v1/analytics/conversations/agents/{agent_id}/conversation-patterns`
- Analyze conversation patterns for agent
- Query parameters:
  - `timeframe`: 24h|7d|30d|90d (default: 7d)
  - `pattern_type`: flow|topic|user_behavior|failure

#### Conversation Management

**POST** `/api/v1/analytics/conversations`
- Create new conversation analytics record
- Body:
  - `conversation_id`: string
  - `agent_id`: string
  - `workspace_id`: string
  - `user_id`: string
  - `metadata`: optional object

**POST** `/api/v1/analytics/conversations/{conversation_id}/messages`
- Record a conversation message
- Body:
  - `message_index`: int
  - `role`: user|agent|system
  - `content`: string
  - `tokens_used`: optional int
  - `response_time_ms`: optional int
  - `metadata`: optional object

**POST** `/api/v1/analytics/conversations/{conversation_id}/end`
- End conversation and finalize metrics
- Body:
  - `status`: active|completed|abandoned|timeout
  - `goal_achieved`: optional bool

## Usage Examples

### 1. Start Tracking a Conversation

```python
import requests

# Create conversation
response = requests.post(
    "http://api.example.com/api/v1/analytics/conversations",
    json={
        "conversation_id": "conv-123",
        "agent_id": "agent-456",
        "workspace_id": "workspace-789",
        "user_id": "user-101",
        "metadata": {"source": "web_chat"}
    },
    headers={"Authorization": "Bearer <token>"}
)
```

### 2. Record Messages

```python
# Record user message
requests.post(
    "http://api.example.com/api/v1/analytics/conversations/conv-123/messages",
    json={
        "message_index": 0,
        "role": "user",
        "content": "I need help with my account",
        "metadata": {}
    },
    headers={"Authorization": "Bearer <token>"}
)

# Record agent response
requests.post(
    "http://api.example.com/api/v1/analytics/conversations/conv-123/messages",
    json={
        "message_index": 1,
        "role": "agent",
        "content": "I'd be happy to help you with your account. What specific issue are you experiencing?",
        "tokens_used": 25,
        "response_time_ms": 1200,
        "metadata": {}
    },
    headers={"Authorization": "Bearer <token>"}
)
```

### 3. End Conversation

```python
# End conversation
requests.post(
    "http://api.example.com/api/v1/analytics/conversations/conv-123/end",
    json={
        "status": "completed",
        "goal_achieved": True
    },
    headers={"Authorization": "Bearer <token>"}
)
```

### 4. Get Analytics

```python
# Get conversation analytics
response = requests.get(
    "http://api.example.com/api/v1/analytics/conversations/conv-123",
    params={
        "include_messages": True,
        "include_sentiment": True,
        "include_engagement": True
    },
    headers={"Authorization": "Bearer <token>"}
)

analytics = response.json()
print(f"Sentiment Score: {analytics['conversation']['interaction_quality']['sentiment_score']}")
print(f"Engagement Level: {analytics['engagement']['engagement_level']}")
```

### 5. Get Agent Performance

```python
# Get agent performance metrics
response = requests.get(
    "http://api.example.com/api/v1/analytics/conversations/agents/agent-456/performance",
    params={
        "workspace_id": "workspace-789",
        "timeframe_days": 7
    },
    headers={"Authorization": "Bearer <token>"}
)

performance = response.json()
print(f"Total Conversations: {performance['total_conversations']}")
print(f"Avg Satisfaction: {performance['avg_satisfaction']}")
print(f"Completion Rate: {performance['completion_rate']}")
```

## Analytics Metrics

### Conversation Quality Scores

All scores are on a 0-1 scale:

- **Sentiment Score**: Overall sentiment (-1 to 1, normalized to 0-1)
- **Clarity Score**: How clear and understandable the conversation is
- **Relevance Score**: How relevant responses are to user queries
- **Completion Rate**: Percentage of conversations completed successfully
- **User Satisfaction**: Overall user satisfaction score

### Engagement Components

- **Interaction Depth** (20%): Message count and complexity
- **User Investment** (25%): Time spent and effort
- **Conversation Momentum** (15%): Response times and flow
- **Topic Exploration** (15%): Unique topics discussed
- **Question Quality** (15%): Quality of user questions
- **Feedback Indicators** (10%): Explicit and implicit feedback

### Engagement Levels

- **Very High**: Score >= 0.8
- **High**: Score >= 0.6
- **Medium**: Score >= 0.4
- **Low**: Score >= 0.2
- **Very Low**: Score < 0.2

## Performance Considerations

### Database Indexes

The implementation includes comprehensive indexes for:
- Conversation lookups by ID, agent, workspace, user
- Time-based queries for trend analysis
- Sentiment and quality score filtering
- Message-level queries

### Materialized Views

Materialized views are created for expensive aggregations:
- Agent performance metrics
- Quality trends
- Intent recognition performance

Refresh views periodically:
```sql
SELECT analytics.refresh_conversation_materialized_views();
```

### Rate Limiting

All endpoints are rate-limited to:
- 30 requests per minute
- 500 requests per hour

## Future Enhancements

### Phase 2: Advanced Pattern Recognition
- Conversation flow pattern mining
- Topic modeling with LDA/NMF
- User behavior clustering
- Failure pattern detection

### Phase 3: Real-time Monitoring
- WebSocket endpoints for live updates
- Real-time alerts for quality issues
- Live conversation dashboard
- Proactive intervention suggestions

### Phase 4: Machine Learning Integration
- Advanced sentiment analysis with ML models
- Intent classification with transformers
- Engagement prediction models
- Response quality scoring with AI

### Phase 5: Advanced Analytics
- Conversation outcome prediction
- User churn prediction from conversations
- Personalized agent recommendations
- A/B testing for conversation strategies

## Testing

### Unit Tests

Run unit tests for services:
```bash
pytest backend/tests/services/analytics/test_conversation_analytics.py
pytest backend/tests/services/analytics/test_sentiment_emotion.py
pytest backend/tests/services/analytics/test_engagement_scoring.py
```

### Integration Tests

Run integration tests for API endpoints:
```bash
pytest backend/tests/api/test_conversation_analytics.py
```

## Monitoring

### Key Metrics to Monitor

1. **Conversation Volume**: Track conversations created/completed
2. **Analytics Coverage**: Percentage of conversations with full analytics
3. **Quality Distribution**: Distribution of quality scores
4. **Engagement Trends**: Engagement scores over time
5. **Performance**: API response times and database query performance

### Alerts

Set up alerts for:
- Low average sentiment (< 0.3)
- High conversation abandonment rate (> 30%)
- Slow response times (> 5s)
- Low engagement scores (< 0.4)

## Support

For questions or issues:
- Check the API documentation: `/docs` endpoint
- Review the code in `backend/src/services/analytics/`
- Consult the database schema: `database/migrations/028_create_conversation_analytics_tables.sql`

## Changelog

### Version 1.0.0 (2025-11-13)
- Initial implementation
- Core conversation tracking
- Sentiment and emotion analysis
- Engagement scoring
- API endpoints for analytics retrieval
- Database schema and migrations
- Comprehensive documentation
