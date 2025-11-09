# User Preference Tracking Specification

## Overview
Track user preferences and settings without complex personalization engines. Focus on what users choose and how they customize their experience.

## TypeScript Interfaces

```typescript
// User preference
interface UserPreference {
  user_id: string;
  preference_key: string;
  preference_value: any;
  category: string;
  updated_at: Date;
  updated_via: 'ui' | 'api' | 'default';
}

// Preference change event
interface PreferenceChange {
  user_id: string;
  preference_key: string;
  old_value: any;
  new_value: any;
  changed_at: Date;
  change_source: string;
}

// Preference category
interface PreferenceCategory {
  category: string;
  preferences: PreferenceDefinition[];
  user_count: number;
  most_common_values: Record<string, any>;
}

// Preference definition
interface PreferenceDefinition {
  key: string;
  category: string;
  data_type: string;
  default_value: any;
  possible_values?: any[];
  description: string;
}
```

## SQL Schema

```sql
-- User preferences table
CREATE TABLE user_preferences (
    user_id VARCHAR(255) NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    preference_value TEXT,
    category VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_via VARCHAR(20) DEFAULT 'ui',
    PRIMARY KEY (user_id, preference_key)
);

-- Preference changes history
CREATE TABLE preference_changes (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_source VARCHAR(50)
);

-- Preference definitions
CREATE TABLE preference_definitions (
    preference_key VARCHAR(100) PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    data_type VARCHAR(20) NOT NULL,
    default_value TEXT,
    possible_values TEXT[],
    description TEXT
);

-- Daily preference statistics
CREATE TABLE daily_preference_stats (
    date DATE NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    total_users INTEGER DEFAULT 0,
    changes_count INTEGER DEFAULT 0,
    most_common_value TEXT,
    PRIMARY KEY (date, preference_key)
);

-- Basic indexes
CREATE INDEX idx_preferences_user ON user_preferences(user_id);
CREATE INDEX idx_preferences_category ON user_preferences(category);
CREATE INDEX idx_changes_user_date ON preference_changes(user_id, changed_at DESC);

-- Insert default preference definitions
INSERT INTO preference_definitions (preference_key, category, data_type, default_value, description) VALUES
('theme', 'display', 'string', 'light', 'Color theme preference'),
('language', 'locale', 'string', 'en', 'Preferred language'),
('timezone', 'locale', 'string', 'UTC', 'User timezone'),
('notifications_email', 'notifications', 'boolean', 'true', 'Email notifications enabled'),
('notifications_push', 'notifications', 'boolean', 'false', 'Push notifications enabled'),
('dashboard_layout', 'display', 'string', 'grid', 'Dashboard layout style'),
('items_per_page', 'display', 'integer', '25', 'Items shown per page'),
('auto_save', 'behavior', 'boolean', 'true', 'Auto-save enabled'),
('keyboard_shortcuts', 'behavior', 'boolean', 'true', 'Keyboard shortcuts enabled');
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
from collections import Counter

@dataclass
class PreferenceMetrics:
    """Simple preference metrics"""
    preference_key: str
    total_users: int
    adoption_rate: float
    most_common_value: Any
    change_frequency: float

class PreferenceTracker:
    """Simple preference tracking"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def set_preference(
        self, 
        user_id: str, 
        key: str, 
        value: Any,
        source: str = 'ui'
    ) -> bool:
        """Set or update user preference"""
        # Get current value for change tracking
        current = self.get_preference(user_id, key)
        
        # Convert value to JSON string for storage
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        # Get category from definition
        category = self.get_preference_category(key)
        
        # Update preference
        query = """
        INSERT INTO user_preferences 
        (user_id, preference_key, preference_value, category, updated_via)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, preference_key)
        DO UPDATE SET 
            preference_value = EXCLUDED.preference_value,
            updated_at = CURRENT_TIMESTAMP,
            updated_via = EXCLUDED.updated_via
        """
        
        try:
            self.db.execute(query, (user_id, key, value_str, category, source))
            
            # Track change if value changed
            if current is not None and current != value:
                self.track_change(user_id, key, current, value, source)
            
            return True
        except Exception as e:
            print(f"Error setting preference: {e}")
            return False
    
    def get_preference(self, user_id: str, key: str) -> Any:
        """Get user preference value"""
        query = """
        SELECT preference_value 
        FROM user_preferences
        WHERE user_id = %s AND preference_key = %s
        """
        
        result = self.db.fetchone(query, (user_id, key))
        
        if result:
            try:
                return json.loads(result['preference_value'])
            except:
                return result['preference_value']
        
        # Return default if not set
        return self.get_default_value(key)
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get all preferences for a user"""
        query = """
        SELECT 
            preference_key,
            preference_value,
            category,
            updated_at
        FROM user_preferences
        WHERE user_id = %s
        ORDER BY category, preference_key
        """
        
        results = self.db.fetchall(query, (user_id,))
        
        preferences = {}
        for row in results:
            try:
                value = json.loads(row['preference_value'])
            except:
                value = row['preference_value']
            
            if row['category'] not in preferences:
                preferences[row['category']] = {}
            
            preferences[row['category']][row['preference_key']] = {
                'value': value,
                'updated_at': row['updated_at']
            }
        
        return preferences
    
    def track_change(
        self, 
        user_id: str, 
        key: str, 
        old_value: Any, 
        new_value: Any,
        source: str
    ) -> None:
        """Track preference change"""
        query = """
        INSERT INTO preference_changes
        (user_id, preference_key, old_value, new_value, change_source)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        old_str = json.dumps(old_value) if old_value is not None else None
        new_str = json.dumps(new_value) if new_value is not None else None
        
        self.db.execute(query, (user_id, key, old_str, new_str, source))
    
    def get_preference_category(self, key: str) -> Optional[str]:
        """Get category for preference key"""
        query = """
        SELECT category 
        FROM preference_definitions
        WHERE preference_key = %s
        """
        
        result = self.db.fetchone(query, (key,))
        return result['category'] if result else 'custom'
    
    def get_default_value(self, key: str) -> Any:
        """Get default value for preference"""
        query = """
        SELECT default_value, data_type
        FROM preference_definitions
        WHERE preference_key = %s
        """
        
        result = self.db.fetchone(query, (key,))
        
        if result:
            value = result['default_value']
            data_type = result['data_type']
            
            # Convert to appropriate type
            if data_type == 'boolean':
                return value.lower() == 'true'
            elif data_type == 'integer':
                return int(value)
            elif data_type == 'float':
                return float(value)
            else:
                return value
        
        return None
    
    def reset_to_defaults(self, user_id: str, category: Optional[str] = None) -> int:
        """Reset user preferences to defaults"""
        if category:
            query = """
            DELETE FROM user_preferences
            WHERE user_id = %s AND category = %s
            """
            result = self.db.execute(query, (user_id, category))
        else:
            query = """
            DELETE FROM user_preferences
            WHERE user_id = %s
            """
            result = self.db.execute(query, (user_id,))
        
        # Track reset
        self.track_change(user_id, 'reset', None, category or 'all', 'system')
        
        return result.rowcount if hasattr(result, 'rowcount') else 0
    
    def get_preference_statistics(self, key: str) -> Dict:
        """Get statistics for a preference"""
        query = """
        WITH stats AS (
            SELECT 
                COUNT(DISTINCT user_id) as total_users,
                COUNT(*) as total_changes,
                preference_value,
                COUNT(*) as value_count
            FROM user_preferences
            WHERE preference_key = %s
            GROUP BY preference_value
        )
        SELECT 
            MAX(total_users) as total_users,
            SUM(value_count) as total_values,
            ARRAY_AGG(
                json_build_object(
                    'value', preference_value, 
                    'count', value_count
                ) ORDER BY value_count DESC
            ) as value_distribution
        FROM stats
        """
        
        result = self.db.fetchone(query, (key,))
        
        if result:
            return {
                'preference_key': key,
                'total_users': result['total_users'] or 0,
                'value_distribution': result['value_distribution'] or []
            }
        
        return {'preference_key': key, 'total_users': 0, 'value_distribution': []}
    
    def get_popular_preferences(self, category: Optional[str] = None) -> List[Dict]:
        """Get most popular preference values"""
        where_clause = "WHERE category = %s" if category else ""
        params = (category,) if category else ()
        
        query = f"""
        WITH preference_stats AS (
            SELECT 
                preference_key,
                preference_value,
                COUNT(*) as user_count,
                ROW_NUMBER() OVER (
                    PARTITION BY preference_key 
                    ORDER BY COUNT(*) DESC
                ) as rn
            FROM user_preferences
            {where_clause}
            GROUP BY preference_key, preference_value
        )
        SELECT 
            preference_key,
            preference_value as most_common_value,
            user_count
        FROM preference_stats
        WHERE rn = 1
        ORDER BY user_count DESC
        """
        
        return self.db.fetchall(query, params)
    
    def get_change_history(
        self, 
        user_id: str, 
        key: Optional[str] = None,
        days: int = 30
    ) -> List[Dict]:
        """Get preference change history"""
        where_conditions = ["user_id = %s"]
        params = [user_id]
        
        if key:
            where_conditions.append("preference_key = %s")
            params.append(key)
        
        where_conditions.append("changed_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'")
        params.append(days)
        
        query = f"""
        SELECT 
            preference_key,
            old_value,
            new_value,
            changed_at,
            change_source
        FROM preference_changes
        WHERE {' AND '.join(where_conditions)}
        ORDER BY changed_at DESC
        LIMIT 100
        """
        
        return self.db.fetchall(query, tuple(params))
    
    def calculate_daily_stats(self, date: Optional[datetime] = None) -> None:
        """Calculate daily preference statistics"""
        target_date = date or datetime.now().date()
        
        query = """
        INSERT INTO daily_preference_stats 
        (date, preference_key, total_users, changes_count, most_common_value)
        SELECT 
            %s as date,
            p.preference_key,
            COUNT(DISTINCT p.user_id) as total_users,
            COUNT(DISTINCT c.id) as changes_count,
            MODE() WITHIN GROUP (ORDER BY p.preference_value) as most_common_value
        FROM user_preferences p
        LEFT JOIN preference_changes c 
            ON p.preference_key = c.preference_key 
            AND DATE(c.changed_at) = %s
        GROUP BY p.preference_key
        ON CONFLICT (date, preference_key)
        DO UPDATE SET
            total_users = EXCLUDED.total_users,
            changes_count = EXCLUDED.changes_count,
            most_common_value = EXCLUDED.most_common_value
        """
        
        self.db.execute(query, (target_date, target_date))
    
    def get_preference_adoption(self, key: str) -> Dict:
        """Get adoption metrics for a preference"""
        query = """
        WITH adoption AS (
            SELECT 
                COUNT(DISTINCT p.user_id) as users_set,
                (SELECT COUNT(DISTINCT user_id) FROM user_sessions 
                 WHERE DATE(start_time) >= CURRENT_DATE - INTERVAL '30 days') as total_active_users,
                COUNT(DISTINCT c.id) as total_changes,
                AVG(EXTRACT(EPOCH FROM (c.changed_at - LAG(c.changed_at) 
                    OVER (PARTITION BY c.user_id ORDER BY c.changed_at)))/86400)::FLOAT as avg_days_between_changes
            FROM user_preferences p
            LEFT JOIN preference_changes c ON p.preference_key = c.preference_key
            WHERE p.preference_key = %s
        )
        SELECT 
            users_set,
            total_active_users,
            CASE 
                WHEN total_active_users > 0 
                THEN (users_set::FLOAT / total_active_users * 100)
                ELSE 0 
            END as adoption_rate,
            total_changes,
            COALESCE(avg_days_between_changes, 0) as avg_days_between_changes
        FROM adoption
        """
        
        return self.db.fetchone(query, (key,))
```

## API Endpoints

```python
from fastapi import APIRouter, Query, HTTPException, Body
from typing import Dict, List, Optional, Any

router = APIRouter(prefix="/api/preferences", tags=["preferences"])

@router.get("/user/{user_id}")
async def get_user_preferences(user_id: str):
    """Get all preferences for a user"""
    tracker = PreferenceTracker(db)
    preferences = tracker.get_user_preferences(user_id)
    return {
        "user_id": user_id,
        "preferences": preferences
    }

@router.get("/user/{user_id}/{key}")
async def get_preference(user_id: str, key: str):
    """Get specific preference value"""
    tracker = PreferenceTracker(db)
    value = tracker.get_preference(user_id, key)
    return {
        "user_id": user_id,
        "key": key,
        "value": value
    }

@router.post("/user/{user_id}")
async def set_preference(
    user_id: str,
    key: str = Body(...),
    value: Any = Body(...),
    source: str = Body("ui")
):
    """Set user preference"""
    tracker = PreferenceTracker(db)
    success = tracker.set_preference(user_id, key, value, source)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to set preference")
    
    return {
        "success": success,
        "user_id": user_id,
        "key": key,
        "value": value
    }

@router.post("/user/{user_id}/bulk")
async def set_bulk_preferences(
    user_id: str,
    preferences: Dict[str, Any] = Body(...)
):
    """Set multiple preferences at once"""
    tracker = PreferenceTracker(db)
    results = {}
    
    for key, value in preferences.items():
        success = tracker.set_preference(user_id, key, value, 'bulk')
        results[key] = success
    
    return {
        "user_id": user_id,
        "results": results,
        "success": all(results.values())
    }

@router.delete("/user/{user_id}/reset")
async def reset_preferences(
    user_id: str,
    category: Optional[str] = Query(None)
):
    """Reset user preferences to defaults"""
    tracker = PreferenceTracker(db)
    count = tracker.reset_to_defaults(user_id, category)
    
    return {
        "user_id": user_id,
        "category": category or "all",
        "reset_count": count
    }

@router.get("/statistics/{key}")
async def get_preference_statistics(key: str):
    """Get statistics for a preference"""
    tracker = PreferenceTracker(db)
    stats = tracker.get_preference_statistics(key)
    return stats

@router.get("/popular")
async def get_popular_preferences(
    category: Optional[str] = Query(None)
):
    """Get most popular preference values"""
    tracker = PreferenceTracker(db)
    popular = tracker.get_popular_preferences(category)
    return {
        "category": category,
        "popular_preferences": popular
    }

@router.get("/history/{user_id}")
async def get_preference_history(
    user_id: str,
    key: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=90)
):
    """Get preference change history"""
    tracker = PreferenceTracker(db)
    history = tracker.get_change_history(user_id, key, days)
    return {
        "user_id": user_id,
        "key": key,
        "history": history,
        "days": days
    }

@router.get("/adoption/{key}")
async def get_preference_adoption(key: str):
    """Get adoption metrics for preference"""
    tracker = PreferenceTracker(db)
    adoption = tracker.get_preference_adoption(key)
    return adoption

@router.get("/definitions")
async def get_preference_definitions(
    category: Optional[str] = Query(None)
):
    """Get available preference definitions"""
    where_clause = "WHERE category = %s" if category else ""
    params = (category,) if category else ()
    
    query = f"""
    SELECT 
        preference_key,
        category,
        data_type,
        default_value,
        possible_values,
        description
    FROM preference_definitions
    {where_clause}
    ORDER BY category, preference_key
    """
    
    definitions = db.fetchall(query, params)
    
    return {
        "definitions": definitions,
        "count": len(definitions)
    }
```

## React Dashboard Component

```tsx
import React, { useState, useEffect } from 'react';
import { Settings, Save, RotateCcw, TrendingUp } from 'lucide-react';

interface Preference {
  key: string;
  value: any;
  updatedAt: string;
}

interface PreferenceCategory {
  [key: string]: {
    [prefKey: string]: {
      value: any;
      updated_at: string;
    };
  };
}

interface PreferenceDefinition {
  preferenceKey: string;
  category: string;
  dataType: string;
  defaultValue: any;
  possibleValues?: any[];
  description: string;
}

export const UserPreferencesDashboard: React.FC = () => {
  const [preferences, setPreferences] = useState<PreferenceCategory>({});
  const [definitions, setDefinitions] = useState<PreferenceDefinition[]>([]);
  const [editedPrefs, setEditedPrefs] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [userId] = useState('current-user');

  useEffect(() => {
    fetchPreferences();
    fetchDefinitions();
  }, []);

  const fetchPreferences = async () => {
    try {
      const res = await fetch(`/api/preferences/user/${userId}`);
      const data = await res.json();
      setPreferences(data.preferences);
    } catch (error) {
      console.error('Error fetching preferences:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDefinitions = async () => {
    try {
      const res = await fetch('/api/preferences/definitions');
      const data = await res.json();
      setDefinitions(data.definitions);
    } catch (error) {
      console.error('Error fetching definitions:', error);
    }
  };

  const handlePreferenceChange = (key: string, value: any) => {
    setEditedPrefs(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const savePreferences = async () => {
    try {
      const res = await fetch(`/api/preferences/user/${userId}/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferences: editedPrefs })
      });
      
      if (res.ok) {
        fetchPreferences();
        setEditedPrefs({});
      }
    } catch (error) {
      console.error('Error saving preferences:', error);
    }
  };

  const resetCategory = async (category: string) => {
    if (!confirm(`Reset all ${category} preferences to defaults?`)) return;
    
    try {
      await fetch(`/api/preferences/user/${userId}/reset?category=${category}`, {
        method: 'DELETE'
      });
      fetchPreferences();
    } catch (error) {
      console.error('Error resetting preferences:', error);
    }
  };

  const renderPreferenceControl = (def: PreferenceDefinition) => {
    const currentValue = preferences[def.category]?.[def.preferenceKey]?.value 
      ?? def.defaultValue;
    const editedValue = editedPrefs[def.preferenceKey] ?? currentValue;

    switch (def.dataType) {
      case 'boolean':
        return (
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={editedValue === true || editedValue === 'true'}
              onChange={(e) => handlePreferenceChange(def.preferenceKey, e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">{def.description}</span>
          </label>
        );
      
      case 'string':
        if (def.possibleValues && def.possibleValues.length > 0) {
          return (
            <div>
              <label className="block text-sm text-gray-700 mb-1">
                {def.description}
              </label>
              <select
                value={editedValue}
                onChange={(e) => handlePreferenceChange(def.preferenceKey, e.target.value)}
                className="w-full p-2 border rounded"
              >
                {def.possibleValues.map(val => (
                  <option key={val} value={val}>{val}</option>
                ))}
              </select>
            </div>
          );
        }
        return (
          <div>
            <label className="block text-sm text-gray-700 mb-1">
              {def.description}
            </label>
            <input
              type="text"
              value={editedValue}
              onChange={(e) => handlePreferenceChange(def.preferenceKey, e.target.value)}
              className="w-full p-2 border rounded"
            />
          </div>
        );
      
      case 'integer':
        return (
          <div>
            <label className="block text-sm text-gray-700 mb-1">
              {def.description}
            </label>
            <input
              type="number"
              value={editedValue}
              onChange={(e) => handlePreferenceChange(def.preferenceKey, parseInt(e.target.value))}
              className="w-full p-2 border rounded"
            />
          </div>
        );
      
      default:
        return null;
    }
  };

  if (loading) return <div>Loading preferences...</div>;

  // Group definitions by category
  const groupedDefinitions = definitions.reduce((acc, def) => {
    if (!acc[def.category]) acc[def.category] = [];
    acc[def.category].push(def);
    return acc;
  }, {} as Record<string, PreferenceDefinition[]>);

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="w-6 h-6" />
          User Preferences
        </h2>
        
        {Object.keys(editedPrefs).length > 0 && (
          <button
            onClick={savePreferences}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            Save Changes ({Object.keys(editedPrefs).length})
          </button>
        )}
      </div>

      {/* Preference Categories */}
      {Object.entries(groupedDefinitions).map(([category, defs]) => (
        <div key={category} className="bg-white p-6 rounded-lg shadow">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold capitalize">
              {category.replace(/_/g, ' ')}
            </h3>
            <button
              onClick={() => resetCategory(category)}
              className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" />
              Reset to Defaults
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {defs.map(def => (
              <div key={def.preferenceKey} className="p-3 border rounded">
                {renderPreferenceControl(def)}
                {editedPrefs[def.preferenceKey] !== undefined && (
                  <div className="mt-1 text-xs text-blue-600">Modified</div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Preference Statistics */}
      <PreferenceStats />

      {/* Change History */}
      <ChangeHistory userId={userId} />
    </div>
  );
};

const PreferenceStats: React.FC = () => {
  const [popularPrefs, setPopularPrefs] = useState<any[]>([]);

  useEffect(() => {
    fetch('/api/preferences/popular')
      .then(res => res.json())
      .then(data => setPopularPrefs(data.popular_preferences))
      .catch(console.error);
  }, []);

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <TrendingUp className="w-5 h-5" />
        Popular Preferences
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {popularPrefs.slice(0, 6).map(pref => (
          <div key={pref.preference_key} className="p-3 bg-gray-50 rounded">
            <div className="text-sm font-medium">{pref.preference_key}</div>
            <div className="text-xs text-gray-600">
              Most common: {pref.most_common_value}
            </div>
            <div className="text-xs text-gray-500">
              {pref.user_count} users
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const ChangeHistory: React.FC<{ userId: string }> = ({ userId }) => {
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    fetch(`/api/preferences/history/${userId}?days=7`)
      .then(res => res.json())
      .then(data => setHistory(data.history))
      .catch(console.error);
  }, [userId]);

  if (history.length === 0) return null;

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Recent Changes</h3>
      <div className="space-y-2">
        {history.slice(0, 5).map((change, idx) => (
          <div key={idx} className="flex justify-between text-sm py-2 border-b">
            <div>
              <span className="font-medium">{change.preference_key}</span>
              <span className="mx-2 text-gray-400">→</span>
              <span>{change.new_value}</span>
            </div>
            <div className="text-gray-500">
              {new Date(change.changed_at).toLocaleDateString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

## Implementation Priority
- **Phase 1**: Basic preference storage and retrieval
- **Phase 2**: Change tracking and history
- **Phase 3**: Statistics and popular preferences
- **Phase 4**: Bulk operations and exports

## Performance Considerations
- JSON storage for flexible preference values
- Daily batch processing for statistics
- Cached preference lookups
- Limited change history (90 days)

## Security Considerations
- User can only modify own preferences
- Validation against defined preference types
- No sensitive data in preferences
- Audit trail for all changes

## Monitoring and Alerts
- Alert on unusual preference change patterns
- Daily summary of preference changes
- Weekly report of popular preferences
- Monitor for preference drift from defaults

## Dependencies
- PostgreSQL with JSON support
- FastAPI for REST endpoints
- React for preferences UI
- Daily cron job for statistics