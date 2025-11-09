# User Search Behavior Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

What are users searching for? Track search queries, what they find, what they don't. Simple search analytics to improve discoverability.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// Search tracking
interface SearchQuery {
  userId: string;
  query: string;
  timestamp: Date;
  results: SearchResults;
  action: SearchAction;
}

interface SearchResults {
  count: number;
  shown: number;
  categories: string[];
  topResult?: string;
}

interface SearchAction {
  clicked: boolean;
  clickedPosition?: number;
  clickedItem?: string;
  refined: boolean;
  abandoned: boolean;
}

interface SearchPattern {
  pattern: 'explorer' | 'targeted' | 'frustrated';
  commonQueries: string[];
  avgRefinements: number;
  successRate: number;
}
```

#### 1.2 SQL Schema

```sql
-- Search queries
CREATE TABLE search_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    query TEXT NOT NULL,
    query_normalized TEXT, -- Lowercase, trimmed
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    result_count INTEGER DEFAULT 0,
    clicked BOOLEAN DEFAULT FALSE,
    clicked_position INTEGER,
    refined BOOLEAN DEFAULT FALSE,
    abandoned BOOLEAN DEFAULT FALSE
);

-- Popular searches
CREATE TABLE popular_searches (
    query_normalized TEXT PRIMARY KEY,
    search_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2),
    last_searched TIMESTAMPTZ
);

-- Failed searches (no results)
CREATE TABLE failed_searches (
    query TEXT PRIMARY KEY,
    fail_count INTEGER DEFAULT 1,
    last_failed TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    users_affected INTEGER DEFAULT 1
);

CREATE INDEX idx_searches_user ON search_queries(user_id, timestamp DESC);
CREATE INDEX idx_searches_query ON search_queries(query_normalized);
```

#### 1.3 Python Analysis Models

```python
@dataclass
class SearchAnalyzer:
    """What are users looking for?"""
    
    def get_user_searches(self, user_id: str) -> List[Dict]:
        """User's recent searches"""
        return self.db.query(
            """
            SELECT 
                query,
                result_count,
                clicked,
                timestamp
            FROM search_queries
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 20
            """,
            (user_id,)
        )
    
    def get_popular_searches(self) -> List[Dict]:
        """What everyone searches for"""
        return self.db.query(
            """
            SELECT 
                query_normalized as query,
                search_count,
                success_rate
            FROM popular_searches
            ORDER BY search_count DESC
            LIMIT 10
            """
        )
    
    def get_failed_searches(self) -> List[Dict]:
        """Searches with no results"""
        return self.db.query(
            """
            SELECT 
                query,
                fail_count,
                users_affected
            FROM failed_searches
            WHERE last_failed > NOW() - INTERVAL '7 days'
            ORDER BY fail_count DESC
            LIMIT 10
            """
        )
    
    def identify_search_pattern(self, user_id: str) -> str:
        """How does user search?"""
        searches = self.get_user_searches(user_id)
        
        if not searches:
            return 'no_searches'
        
        # Check refinements
        refinements = sum(1 for s in searches if s['refined'])
        
        # Check success
        successes = sum(1 for s in searches if s['clicked'])
        
        if refinements > len(searches) * 0.5:
            return 'explorer'  # Tries many variations
        elif successes > len(searches) * 0.8:
            return 'targeted'  # Knows what they want
        else:
            return 'frustrated'  # Can't find things
```

### 2. API Endpoints

```python
@router.post("/search")
async def track_search(
    user_id: str,
    query: str,
    result_count: int
):
    """Track a search query"""
    pass

@router.post("/search/{search_id}/click")
async def track_search_click(
    search_id: str,
    position: int,
    item: str
):
    """Track search result click"""
    pass

@router.get("/popular")
async def get_popular_searches():
    """Most searched terms"""
    pass

@router.get("/failed")
async def get_failed_searches():
    """Searches with no results"""
    pass

@router.get("/user/{user_id}/searches")
async def get_user_searches(user_id: str):
    """User's search history"""
    pass
```

### 3. Dashboard Components

```typescript
export const SearchTracker: React.FC = () => {
  const trackSearch = (query: string, results: any[]) => {
    const searchId = api.post('/search', {
      userId: getCurrentUser().id,
      query,
      resultCount: results.length
    });
    
    // Store for click tracking
    sessionStorage.setItem('lastSearchId', searchId);
  };
  
  const trackClick = (position: number, item: any) => {
    const searchId = sessionStorage.getItem('lastSearchId');
    if (searchId) {
      api.post(`/search/${searchId}/click`, {
        position,
        item: item.id
      });
    }
  };
  
  return null;
};

export const PopularSearches: React.FC = () => {
  const [searches, setSearches] = useState([]);
  
  return (
    <div>
      <h3>Trending Searches</h3>
      <div className="space-y-1">
        {searches.map(s => (
          <button 
            key={s.query}
            onClick={() => performSearch(s.query)}
            className="text-blue-600 text-sm"
          >
            {s.query} ({s.searchCount})
          </button>
        ))}
      </div>
    </div>
  );
};

export const SearchInsights: React.FC = () => {
  const [failed, setFailed] = useState([]);
  
  return (
    <div className="bg-yellow-50 p-3 rounded">
      <h4>Users Can't Find:</h4>
      <ul className="text-sm">
        {failed.map(f => (
          <li key={f.query}>
            "{f.query}" - {f.failCount} times
          </li>
        ))}
      </ul>
    </div>
  );
};
```

## What This Tells Us

- What users are looking for
- What they can't find
- Search effectiveness
- Content gaps

## Cost Optimization

- Store normalized queries
- Daily aggregation for popular
- No full-text indexing
- 30-day retention