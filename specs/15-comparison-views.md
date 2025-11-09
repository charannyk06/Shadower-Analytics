# Specification: Comparison Views

## Feature Overview
Side-by-side comparison views for agents, periods, workspaces, and metrics to identify differences and improvements.

## Technical Requirements
- Multi-entity comparison
- Period-over-period analysis
- Visual diff highlighting
- Export comparison reports

## Implementation Details

### Data Structure
```typescript
interface ComparisonViews {
  type: 'agents' | 'periods' | 'workspaces' | 'metrics';
  
  // Agent Comparison
  agentComparison?: {
    agents: Array<{
      id: string;
      name: string;
      metrics: AgentMetrics;
    }>;
    
    differences: {
      successRate: { best: string; worst: string; delta: number };
      runtime: { fastest: string; slowest: string; delta: number };
      cost: { cheapest: string; mostExpensive: string; delta: number };
    };
    
    winner: string;
    recommendations: string[];
  };
  
  // Period Comparison
  periodComparison?: {
    current: PeriodMetrics;
    previous: PeriodMetrics;
    change: ChangeMetrics;
    
    improvements: string[];
    regressions: string[];
  };
  
  // Workspace Comparison
  workspaceComparison?: {
    workspaces: WorkspaceMetrics[];
    benchmarks: BenchmarkMetrics;
    rankings: RankingMetrics;
  };
}
```

## Testing Requirements
- Comparison accuracy tests
- Visual diff validation
- Performance with multiple entities

## Performance Targets
- Comparison load: <1.5 seconds
- Diff calculation: <500ms

## Security Considerations
- Cross-workspace data access control
- Comparison data privacy