# User Onboarding Flow Specification

## Document Version
- Version: 1.0.0
- Last Updated: 2024-01-20
- Status: Draft

## Overview

Track how new users learn the system. Where they succeed, where they drop off. Simple onboarding analytics to improve first-time user experience.

## Core Components

### 1. Data Models

#### 1.1 TypeScript Interfaces

```typescript
// Onboarding tracking
interface OnboardingProgress {
  userId: string;
  startedAt: Date;
  completedAt?: Date;
  steps: OnboardingStep[];
  status: 'in_progress' | 'completed' | 'abandoned';
  completionRate: number;
}

interface OnboardingStep {
  id: string;
  name: string;
  required: boolean;
  startedAt?: Date;
  completedAt?: Date;
  skipped: boolean;
  attempts: number;
  timeSpent: number;
}

interface OnboardingDropoff {
  stepId: string;
  dropoffRate: number;
  avgTimeToDropoff: number;
  commonIssues: string[];
}
```

#### 1.2 SQL Schema

```sql
-- Onboarding progress
CREATE TABLE onboarding_progress (
    user_id UUID PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    current_step VARCHAR(100),
    steps_completed INTEGER DEFAULT 0,
    steps_total INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'in_progress',
    completion_rate DECIMAL(5,2) DEFAULT 0
);

-- Individual steps
CREATE TABLE onboarding_steps (
    user_id UUID NOT NULL,
    step_id VARCHAR(100) NOT NULL,
    step_name VARCHAR(255),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    skipped BOOLEAN DEFAULT FALSE,
    attempts INTEGER DEFAULT 0,
    time_spent_seconds INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, step_id)
);

-- Dropoff analysis
CREATE TABLE onboarding_dropoffs (
    step_id VARCHAR(100) PRIMARY KEY,
    users_started INTEGER DEFAULT 0,
    users_completed INTEGER DEFAULT 0,
    users_dropped INTEGER DEFAULT 0,
    avg_time_to_dropoff INTEGER,
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_onboarding_status ON onboarding_progress(status);
CREATE INDEX idx_steps_user ON onboarding_steps(user_id);
```

#### 1.3 Python Analysis Models

```python
@dataclass
class OnboardingAnalyzer:
    """Track new user success"""
    
    def get_user_progress(self, user_id: str) -> Dict:
        """Where is user in onboarding?"""
        progress = self.db.query_one(
            "SELECT * FROM onboarding_progress WHERE user_id = ?",
            (user_id,)
        )
        
        steps = self.db.query(
            "SELECT * FROM onboarding_steps WHERE user_id = ? ORDER BY started_at",
            (user_id,)
        )
        
        return {
            'progress': progress,
            'steps': steps,
            'next_step': self._get_next_step(progress, steps)
        }
    
    def get_dropoff_points(self) -> List[Dict]:
        """Where do users quit?"""
        return self.db.query(
            """
            SELECT 
                step_id,
                users_dropped,
                users_started,
                CAST(users_dropped AS FLOAT) / NULLIF(users_started, 0) as dropoff_rate
            FROM onboarding_dropoffs
            WHERE users_started > 10
            ORDER BY dropoff_rate DESC
            """
        )
    
    def get_completion_rate(self) -> float:
        """How many finish onboarding?"""
        stats = self.db.query_one(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as completed
            FROM onboarding_progress
            WHERE started_at > NOW() - INTERVAL '30 days'
            """
        )
        
        return stats['completed'] / stats['total'] if stats['total'] > 0 else 0
    
    def identify_struggling_users(self) -> List[Dict]:
        """Users stuck in onboarding"""
        return self.db.query(
            """
            SELECT 
                user_id,
                current_step,
                EXTRACT(EPOCH FROM NOW() - started_at) / 3600 as hours_stuck
            FROM onboarding_progress
            WHERE status = 'in_progress'
            AND started_at < NOW() - INTERVAL '24 hours'
            """
        )
```

### 2. API Endpoints

```python
@router.post("/start")
async def start_onboarding(user_id: str):
    """Start onboarding for new user"""
    pass

@router.post("/step/start")
async def start_step(
    user_id: str,
    step_id: str
):
    """Start an onboarding step"""
    pass

@router.post("/step/complete")
async def complete_step(
    user_id: str,
    step_id: str
):
    """Complete an onboarding step"""
    pass

@router.post("/step/skip")
async def skip_step(
    user_id: str,
    step_id: str
):
    """Skip an optional step"""
    pass

@router.get("/progress/{user_id}")
async def get_progress(user_id: str):
    """Get user's onboarding progress"""
    pass

@router.get("/dropoffs")
async def get_dropoff_points():
    """Where users abandon onboarding"""
    pass
```

### 3. Dashboard Components

```typescript
export const OnboardingTracker: React.FC = () => {
  const [currentStep, setCurrentStep] = useState('');
  const [stepStartTime, setStepStartTime] = useState(Date.now());
  
  const startStep = (stepId: string) => {
    api.post('/onboarding/step/start', {
      userId: getCurrentUser().id,
      stepId
    });
    setCurrentStep(stepId);
    setStepStartTime(Date.now());
  };
  
  const completeStep = () => {
    api.post('/onboarding/step/complete', {
      userId: getCurrentUser().id,
      stepId: currentStep,
      timeSpent: Date.now() - stepStartTime
    });
  };
  
  return null;
};

export const OnboardingProgress: React.FC = () => {
  const [progress, setProgress] = useState(null);
  
  return (
    <div className="bg-blue-50 p-4 rounded">
      <h3>Getting Started</h3>
      <div className="mt-2">
        <div className="bg-gray-200 rounded h-2">
          <div 
            className="bg-blue-500 h-2 rounded"
            style={{ width: `${progress?.completionRate || 0}%` }}
          />
        </div>
      </div>
      <div className="mt-2 text-sm">
        {progress?.stepsCompleted} of {progress?.stepsTotal} complete
      </div>
    </div>
  );
};

export const OnboardingHelper: React.FC = () => {
  const [stuck, setStuck] = useState(false);
  
  // Check if user is stuck
  useEffect(() => {
    const timer = setTimeout(() => {
      setStuck(true);
    }, 30000); // 30 seconds on same step
    
    return () => clearTimeout(timer);
  }, []);
  
  if (!stuck) return null;
  
  return (
    <div className="fixed bottom-4 right-4 bg-yellow-100 p-3 rounded shadow">
      <div>Need help with this step?</div>
      <button className="text-blue-600 text-sm">
        Show me how
      </button>
    </div>
  );
};
```

## What This Tells Us

- Where new users struggle
- Which steps to simplify
- Onboarding effectiveness
- Time to first value

## Cost Optimization

- Track steps, not every action
- Daily dropoff calculations
- 30-day retention for completed
- No video tutorials tracking