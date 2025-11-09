# User Collaboration Patterns Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

Track how users work together. Who collaborates with whom, on what, and how successfully. Simple collaboration analytics without complex social graphs.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// Collaboration tracking
interface UserCollaboration {
  userId: string;
  collaborators: Collaborator[];
  sharedItems: SharedItem[];
  teamActivity: TeamActivity;
}

interface Collaborator {
  userId: string;
  username: string;
  interactionCount: number;
  lastInteraction: Date;
  collaborationType: 'frequent' | 'occasional' | 'new';
}

interface SharedItem {
  itemId: string;
  itemType: 'workflow' | 'agent' | 'data' | 'dashboard';
  sharedWith: string[];
  sharedAt: Date;
  accessLevel: 'view' | 'edit' | 'admin';
  activity: number;
}

interface TeamActivity {
  teamSize: number;
  activeMembers: number;
  sharedWorkflows: number;
  collaborationScore: number;
}
```

#### 1.2 SQL Schema

```sql
-- Collaboration events
CREATE TABLE collaboration_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    collaborator_id UUID NOT NULL,
    event_type VARCHAR(50), -- 'share', 'edit', 'comment', 'mention'
    item_id VARCHAR(255),
    item_type VARCHAR(50),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Shared items
CREATE TABLE shared_items (
    item_id VARCHAR(255) NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    owner_id UUID NOT NULL,
    shared_with UUID[],
    access_level VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item_id, item_type)
);

-- Team activity
CREATE TABLE team_activity (
    team_id UUID PRIMARY KEY,
    date DATE NOT NULL,
    active_users INTEGER DEFAULT 0,
    collaborations INTEGER DEFAULT 0,
    items_shared INTEGER DEFAULT 0
);

CREATE INDEX idx_collab_users ON collaboration_events(user_id, collaborator_id);
CREATE INDEX idx_shared_owner ON shared_items(owner_id);
```

#### 1.3 Python Analysis Models

```python
@dataclass
class CollaborationAnalyzer:
    """Who works with whom?"""
    
    def get_user_collaborators(self, user_id: str) -> List[Dict]:
        """User's collaboration network"""
        return self.db.query(
            """
            SELECT 
                collaborator_id,
                COUNT(*) as interactions,
                MAX(timestamp) as last_interaction
            FROM collaboration_events
            WHERE user_id = ?
            GROUP BY collaborator_id
            ORDER BY interactions DESC
            """,
            (user_id,)
        )
    
    def get_shared_items(self, user_id: str) -> List[Dict]:
        """What user shares"""
        return self.db.query(
            """
            SELECT 
                item_id,
                item_type,
                array_length(shared_with, 1) as share_count,
                created_at
            FROM shared_items
            WHERE owner_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        )
    
    def identify_collaboration_pattern(self, user_id: str) -> str:
        """How does user collaborate?"""
        collabs = self.get_user_collaborators(user_id)
        
        if not collabs:
            return 'solo_worker'
        elif len(collabs) > 10:
            return 'hub_connector'
        elif len(collabs) <= 3:
            return 'small_team'
        else:
            return 'regular_collaborator'
```

### 2. API Endpoints

```python
@router.post("/share")
async def share_item(
    user_id: str,
    item_id: str,
    share_with: List[str]
):
    """Share an item"""
    pass

@router.get("/collaborators/{user_id}")
async def get_collaborators(user_id: str):
    """Get user's collaborators"""
    pass

@router.get("/shared/{user_id}")
async def get_shared_items(user_id: str):
    """Get shared items"""
    pass
```

### 3. Dashboard Components

```typescript
export const CollaborationTracker: React.FC = () => {
  const trackShare = (itemId: string, sharedWith: string[]) => {
    api.post('/collaboration/share', {
      userId: getCurrentUser().id,
      itemId,
      sharedWith
    });
  };
  
  return null;
};

export const MyCollaborators: React.FC = () => {
  const [collaborators, setCollaborators] = useState([]);
  
  return (
    <div>
      <h3>Your Team</h3>
      <div className="space-y-2">
        {collaborators.map(c => (
          <div key={c.userId} className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gray-300 rounded-full" />
            <div>
              <div className="font-medium">{c.username}</div>
              <div className="text-xs text-gray-500">
                {c.interactionCount} collaborations
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

## What This Tells Us

- Team dynamics
- Popular shared resources
- Collaboration effectiveness
- Isolated users who need help

## Cost Optimization

- Track shares, not views
- Daily aggregation
- No real-time presence
- Simple collaboration metrics