# Specification: Leaderboards

## Feature Overview
Competitive rankings and leaderboards for agents, users, and workspaces based on various performance metrics.

## Technical Requirements
- Real-time ranking updates
- Multiple ranking criteria
- Historical ranking tracking
- Percentile calculations
- Achievement badges

## Implementation Details

### Data Structure
```typescript
interface Leaderboards {
  timeframe: TimeFrame;
  
  // Agent Leaderboard
  agentLeaderboard: {
    criteria: 'runs' | 'success_rate' | 'speed' | 'efficiency' | 'popularity';
    
    rankings: Array<{
      rank: number;
      previousRank: number | null;
      change: 'up' | 'down' | 'same' | 'new';
      
      agent: {
        id: string;
        name: string;
        type: string;
        workspace: string;
      };
      
      metrics: {
        totalRuns: number;
        successRate: number;
        avgRuntime: number;
        creditsPerRun: number;
        uniqueUsers: number;
      };
      
      score: number;
      percentile: number;
      badge?: 'gold' | 'silver' | 'bronze';
    }>;
  };
  
  // User Leaderboard
  userLeaderboard: {
    criteria: 'activity' | 'efficiency' | 'contribution' | 'savings';
    
    rankings: Array<{
      rank: number;
      previousRank: number | null;
      change: 'up' | 'down' | 'same' | 'new';
      
      user: {
        id: string;
        name: string;
        avatar: string;
        workspace: string;
      };
      
      metrics: {
        totalActions: number;
        successRate: number;
        creditsUsed: number;
        creditsSaved: number;
        agentsUsed: number;
      };
      
      score: number;
      percentile: number;
      achievements: string[];
    }>;
  };
  
  // Workspace Leaderboard  
  workspaceLeaderboard: {
    criteria: 'activity' | 'efficiency' | 'growth' | 'innovation';
    
    rankings: Array<{
      rank: number;
      previousRank: number | null;
      
      workspace: {
        id: string;
        name: string;
        plan: string;
        memberCount: number;
      };
      
      metrics: {
        totalActivity: number;
        activeUsers: number;
        agentCount: number;
        successRate: number;
        healthScore: number;
      };
      
      score: number;
      tier: 'platinum' | 'gold' | 'silver' | 'bronze';
    }>;
  };
}
```

### Frontend Components

```typescript
// frontend/src/components/leaderboards/LeaderboardTable.tsx
export function LeaderboardTable({ 
  leaderboard, 
  type,
  currentUserId 
}: LeaderboardProps) {
  return (
    <div className="bg-white rounded-lg shadow">
      {/* Leaderboard implementation */}
    </div>
  );
}
```

## Testing Requirements
- Ranking algorithm tests
- Real-time update tests
- Performance with large datasets

## Performance Targets
- Leaderboard load: <1 second
- Ranking update: <500ms
- Percentile calculation: <200ms

## Security Considerations
- Privacy settings for rankings
- Workspace data isolation