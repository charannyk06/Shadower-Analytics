# User Feedback Tracking Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

Capture what users actually think. Simple feedback tracking without complex surveys. Track ratings, comments, and suggestions.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// Feedback types
interface UserFeedback {
  id: string;
  userId: string;
  type: 'rating' | 'comment' | 'bug' | 'suggestion' | 'praise';
  content: FeedbackContent;
  context: FeedbackContext;
  status: 'new' | 'reviewed' | 'actioned' | 'closed';
}

interface FeedbackContent {
  rating?: number; // 1-5
  message?: string;
  category?: string;
  screenshot?: string;
}

interface FeedbackContext {
  page: string;
  feature?: string;
  timestamp: Date;
  sessionId: string;
  errorId?: string;
}

interface FeedbackSentiment {
  positive: number;
  negative: number;
  neutral: number;
}
```

#### 1.2 SQL Schema

```sql
-- User feedback
CREATE TABLE user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    feedback_type VARCHAR(50) NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    message TEXT,
    category VARCHAR(100),
    page VARCHAR(255),
    feature VARCHAR(100),
    status VARCHAR(20) DEFAULT 'new',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Quick ratings
CREATE TABLE quick_ratings (
    user_id UUID NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    item_id VARCHAR(255) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, item_type, item_id)
);

-- Daily sentiment
CREATE TABLE daily_sentiment (
    date DATE PRIMARY KEY,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    avg_rating DECIMAL(3,2)
);

CREATE INDEX idx_feedback_user ON user_feedback(user_id);
CREATE INDEX idx_feedback_status ON user_feedback(status);
CREATE INDEX idx_ratings_item ON quick_ratings(item_type, item_id);
```

#### 1.3 Python Analysis Models

```python
@dataclass
class FeedbackAnalyzer:
    """What do users think?"""
    
    def get_recent_feedback(self) -> List[Dict]:
        """Latest user feedback"""
        return self.db.query(
            """
            SELECT * FROM user_feedback
            WHERE created_at > NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            """
        )
    
    def get_sentiment_trend(self) -> List[Dict]:
        """How are users feeling?"""
        return self.db.query(
            """
            SELECT 
                date,
                positive_count,
                negative_count,
                avg_rating
            FROM daily_sentiment
            WHERE date > CURRENT_DATE - INTERVAL '7 days'
            ORDER BY date
            """
        )
    
    def get_common_complaints(self) -> List[Dict]:
        """What users complain about"""
        return self.db.query(
            """
            SELECT 
                category,
                COUNT(*) as count
            FROM user_feedback
            WHERE feedback_type IN ('bug', 'complaint')
            AND created_at > NOW() - INTERVAL '30 days'
            GROUP BY category
            ORDER BY count DESC
            LIMIT 5
            """
        )
    
    def get_feature_ratings(self, feature: str) -> Dict:
        """How users rate a feature"""
        stats = self.db.query_one(
            """
            SELECT 
                AVG(rating) as avg_rating,
                COUNT(*) as rating_count,
                COUNT(*) FILTER (WHERE rating >= 4) as positive,
                COUNT(*) FILTER (WHERE rating <= 2) as negative
            FROM quick_ratings
            WHERE item_type = 'feature' AND item_id = ?
            """,
            (feature,)
        )
        
        return {
            'avg_rating': stats['avg_rating'],
            'total_ratings': stats['rating_count'],
            'satisfaction': stats['positive'] / stats['rating_count'] if stats['rating_count'] > 0 else 0
        }
```

### 2. API Endpoints

```python
@router.post("/submit")
async def submit_feedback(feedback: UserFeedback):
    """Submit user feedback"""
    pass

@router.post("/rate")
async def quick_rate(
    user_id: str,
    item_type: str,
    item_id: str,
    rating: int
):
    """Quick rating"""
    pass

@router.get("/recent")
async def get_recent_feedback():
    """Recent feedback"""
    pass

@router.get("/sentiment")
async def get_sentiment():
    """Sentiment trend"""
    pass

@router.get("/complaints")
async def get_complaints():
    """Common complaints"""
    pass
```

### 3. Dashboard Components

```typescript
export const QuickFeedback: React.FC = () => {
  const [rating, setRating] = useState(0);
  const [message, setMessage] = useState('');
  const [showForm, setShowForm] = useState(false);
  
  const submitFeedback = () => {
    api.post('/feedback/submit', {
      userId: getCurrentUser().id,
      type: rating <= 2 ? 'complaint' : 'praise',
      content: { rating, message },
      context: {
        page: window.location.pathname,
        timestamp: new Date()
      }
    });
    
    setShowForm(false);
    setRating(0);
    setMessage('');
  };
  
  return (
    <div className="fixed bottom-4 right-4">
      {!showForm ? (
        <button
          onClick={() => setShowForm(true)}
          className="bg-blue-500 text-white p-2 rounded-full shadow"
        >
          💬
        </button>
      ) : (
        <div className="bg-white p-4 rounded shadow-lg w-64">
          <div className="mb-2">How are we doing?</div>
          <div className="flex space-x-1 mb-2">
            {[1, 2, 3, 4, 5].map(r => (
              <button
                key={r}
                onClick={() => setRating(r)}
                className={`text-2xl ${r <= rating ? 'text-yellow-500' : 'text-gray-300'}`}
              >
                ⭐
              </button>
            ))}
          </div>
          {rating > 0 && (
            <textarea
              className="w-full p-2 border rounded text-sm"
              placeholder="Tell us more (optional)"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
          )}
          <div className="flex space-x-2 mt-2">
            <button
              onClick={submitFeedback}
              className="px-3 py-1 bg-blue-500 text-white rounded text-sm"
            >
              Send
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-1 border rounded text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export const SentimentIndicator: React.FC = () => {
  const [sentiment, setSentiment] = useState(null);
  
  const emoji = sentiment?.avgRating >= 4 ? '😊' :
                sentiment?.avgRating >= 3 ? '😐' : '😟';
  
  return (
    <div className="flex items-center space-x-2">
      <span className="text-2xl">{emoji}</span>
      <div>
        <div className="text-sm font-medium">User Sentiment</div>
        <div className="text-xs text-gray-500">
          {sentiment?.avgRating?.toFixed(1)} / 5.0
        </div>
      </div>
    </div>
  );
};
```

## What This Tells Us

- User satisfaction levels
- Problem areas
- Feature appreciation
- Improvement priorities

## Cost Optimization

- Simple rating system
- Text feedback only
- No image uploads
- 90-day retention