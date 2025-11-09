# User Location Tracking Specification

## Overview
Simple location tracking for user analytics without complex geolocation services. Track where users are accessing from for basic geographic insights.

## TypeScript Interfaces

```typescript
// User location data
interface UserLocation {
  location_id: string;
  user_id: string;
  ip_address: string;
  country: string;
  region: string;
  city: string;
  timezone: string;
  latitude?: number;
  longitude?: number;
  timestamp: Date;
}

// Location session
interface LocationSession {
  session_id: string;
  user_id: string;
  location_id: string;
  start_time: Date;
  end_time?: Date;
  page_views: number;
  actions_count: number;
}

// Geographic distribution
interface GeographicDistribution {
  country: string;
  user_count: number;
  session_count: number;
  avg_session_duration: number;
  percentage: number;
}

// User travel pattern
interface UserTravelPattern {
  user_id: string;
  home_country: string;
  countries_visited: string[];
  cities_visited: string[];
  travel_frequency: number;
  is_traveling: boolean;
}
```

## SQL Schema

```sql
-- User locations table
CREATE TABLE user_locations (
    location_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    country VARCHAR(100),
    country_code VARCHAR(2),
    region VARCHAR(100),
    city VARCHAR(100),
    timezone VARCHAR(50),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Location sessions
CREATE TABLE location_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    location_id VARCHAR(255) REFERENCES user_locations(location_id),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    page_views INTEGER DEFAULT 0,
    actions_count INTEGER DEFAULT 0
);

-- User geographic profile
CREATE TABLE user_geographic_profile (
    user_id VARCHAR(255) PRIMARY KEY,
    home_country VARCHAR(100),
    home_city VARCHAR(100),
    current_country VARCHAR(100),
    current_city VARCHAR(100),
    countries_visited TEXT[],
    cities_visited TEXT[],
    total_locations INTEGER DEFAULT 1,
    is_traveling BOOLEAN DEFAULT false,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily location statistics
CREATE TABLE daily_location_stats (
    date DATE NOT NULL,
    country VARCHAR(100) NOT NULL,
    city VARCHAR(100),
    user_count INTEGER DEFAULT 0,
    session_count INTEGER DEFAULT 0,
    new_user_count INTEGER DEFAULT 0,
    avg_session_duration INTEGER DEFAULT 0,
    PRIMARY KEY (date, country, city)
);

-- Country activity summary
CREATE TABLE country_activity_summary (
    country VARCHAR(100) PRIMARY KEY,
    country_code VARCHAR(2),
    total_users INTEGER DEFAULT 0,
    active_users_today INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    avg_session_duration INTEGER DEFAULT 0,
    last_activity TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Basic indexes
CREATE INDEX idx_locations_user ON user_locations(user_id);
CREATE INDEX idx_locations_country ON user_locations(country);
CREATE INDEX idx_locations_timestamp ON user_locations(timestamp DESC);
CREATE INDEX idx_sessions_location ON location_sessions(location_id);
```

## Python Analytics Models

```python
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
from collections import Counter, defaultdict

@dataclass
class LocationInfo:
    """Location information"""
    country: str
    country_code: str
    region: str
    city: str
    timezone: str
    latitude: Optional[float]
    longitude: Optional[float]

class LocationTracker:
    """Simple location tracking based on IP"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_location_from_ip(self, ip_address: str) -> LocationInfo:
        """Get location from IP address (simplified)"""
        # In production, use a service like MaxMind GeoIP2
        # This is a simplified mock implementation
        
        # Hash IP to generate consistent mock data
        ip_hash = hashlib.md5(ip_address.encode()).hexdigest()
        
        # Mock location data based on IP hash
        locations = [
            LocationInfo("United States", "US", "California", "San Francisco", "America/Los_Angeles", 37.7749, -122.4194),
            LocationInfo("United Kingdom", "GB", "England", "London", "Europe/London", 51.5074, -0.1278),
            LocationInfo("Germany", "DE", "Berlin", "Berlin", "Europe/Berlin", 52.5200, 13.4050),
            LocationInfo("Japan", "JP", "Tokyo", "Tokyo", "Asia/Tokyo", 35.6762, 139.6503),
            LocationInfo("Australia", "AU", "New South Wales", "Sydney", "Australia/Sydney", -33.8688, 151.2093),
            LocationInfo("Canada", "CA", "Ontario", "Toronto", "America/Toronto", 43.6532, -79.3832),
            LocationInfo("France", "FR", "Île-de-France", "Paris", "Europe/Paris", 48.8566, 2.3522),
            LocationInfo("India", "IN", "Karnataka", "Bangalore", "Asia/Kolkata", 12.9716, 77.5946)
        ]
        
        # Select location based on IP hash
        index = int(ip_hash[:2], 16) % len(locations)
        return locations[index]
    
    def track_location(
        self,
        user_id: str,
        ip_address: str,
        session_id: Optional[str] = None
    ) -> Tuple[str, LocationInfo]:
        """Track user location"""
        location_info = self.get_location_from_ip(ip_address)
        location_id = self.generate_location_id(user_id, location_info)
        
        # Check if location exists
        existing = self.get_location(location_id)
        
        if not existing:
            # Create new location record
            query = """
            INSERT INTO user_locations
            (location_id, user_id, ip_address, country, country_code, 
             region, city, timezone, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            self.db.execute(query, (
                location_id, user_id, self.anonymize_ip(ip_address),
                location_info.country, location_info.country_code,
                location_info.region, location_info.city,
                location_info.timezone, location_info.latitude,
                location_info.longitude
            ))
        
        # Update user profile
        self.update_user_profile(user_id, location_info)
        
        # Create or update session if provided
        if session_id:
            self.create_location_session(session_id, user_id, location_id)
        
        return location_id, location_info
    
    def generate_location_id(self, user_id: str, location: LocationInfo) -> str:
        """Generate unique location ID"""
        location_string = f"{user_id}:{location.country}:{location.city}"
        return hashlib.md5(location_string.encode()).hexdigest()
    
    def anonymize_ip(self, ip_address: str) -> str:
        """Anonymize IP address for privacy"""
        parts = ip_address.split('.')
        if len(parts) == 4:
            parts[3] = '0'  # Zero out last octet
        return '.'.join(parts)
    
    def get_location(self, location_id: str) -> Optional[Dict]:
        """Get location information"""
        query = """
        SELECT * FROM user_locations
        WHERE location_id = %s
        """
        return self.db.fetchone(query, (location_id,))
    
    def create_location_session(
        self,
        session_id: str,
        user_id: str,
        location_id: str
    ) -> None:
        """Create location session"""
        query = """
        INSERT INTO location_sessions
        (session_id, user_id, location_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (session_id) DO NOTHING
        """
        self.db.execute(query, (session_id, user_id, location_id))
    
    def update_user_profile(self, user_id: str, location: LocationInfo) -> None:
        """Update user geographic profile"""
        # Get current profile
        query = """
        SELECT home_country, home_city, countries_visited, cities_visited
        FROM user_geographic_profile
        WHERE user_id = %s
        """
        
        profile = self.db.fetchone(query, (user_id,))
        
        if not profile:
            # Create new profile
            query = """
            INSERT INTO user_geographic_profile
            (user_id, home_country, home_city, current_country, current_city,
             countries_visited, cities_visited)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            self.db.execute(query, (
                user_id, location.country, location.city,
                location.country, location.city,
                [location.country], [location.city]
            ))
        else:
            # Update profile
            countries = profile['countries_visited'] or []
            cities = profile['cities_visited'] or []
            
            if location.country not in countries:
                countries.append(location.country)
            if location.city not in cities:
                cities.append(location.city)
            
            # Check if traveling
            is_traveling = location.country != profile['home_country']
            
            query = """
            UPDATE user_geographic_profile
            SET 
                current_country = %s,
                current_city = %s,
                countries_visited = %s,
                cities_visited = %s,
                total_locations = ARRAY_LENGTH(%s, 1),
                is_traveling = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            """
            
            self.db.execute(query, (
                location.country, location.city,
                countries, cities, cities,
                is_traveling, user_id
            ))
    
    def get_user_locations(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user's location history"""
        query = """
        SELECT 
            location_id,
            country,
            region,
            city,
            timezone,
            timestamp
        FROM user_locations
        WHERE user_id = %s
        AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '%s days'
        ORDER BY timestamp DESC
        """
        return self.db.fetchall(query, (user_id, days))
    
    def get_geographic_distribution(self) -> List[Dict]:
        """Get geographic distribution of users"""
        query = """
        WITH country_stats AS (
            SELECT 
                country,
                COUNT(DISTINCT user_id) as user_count,
                COUNT(DISTINCT session_id) as session_count,
                AVG(EXTRACT(EPOCH FROM (end_time - start_time))/60)::INTEGER as avg_duration
            FROM user_locations l
            LEFT JOIN location_sessions s ON l.location_id = s.location_id
            WHERE l.timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            GROUP BY country
        )
        SELECT 
            country,
            user_count,
            session_count,
            avg_duration,
            (user_count::FLOAT / SUM(user_count) OVER () * 100) as percentage
        FROM country_stats
        ORDER BY user_count DESC
        """
        return self.db.fetchall(query)
    
    def get_city_distribution(self, country: str) -> List[Dict]:
        """Get city distribution within a country"""
        query = """
        SELECT 
            city,
            COUNT(DISTINCT user_id) as user_count,
            COUNT(DISTINCT l.location_id) as location_count,
            MAX(l.timestamp) as last_activity
        FROM user_locations l
        WHERE country = %s
        AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
        GROUP BY city
        ORDER BY user_count DESC
        LIMIT 20
        """
        return self.db.fetchall(query, (country,))
    
    def detect_vpn_usage(self, user_id: str) -> Dict:
        """Detect possible VPN usage based on location changes"""
        query = """
        WITH location_changes AS (
            SELECT 
                user_id,
                country,
                city,
                timestamp,
                LAG(country) OVER (PARTITION BY user_id ORDER BY timestamp) as prev_country,
                LAG(timestamp) OVER (PARTITION BY user_id ORDER BY timestamp) as prev_timestamp
            FROM user_locations
            WHERE user_id = %s
            AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
        )
        SELECT 
            COUNT(DISTINCT country) as country_count,
            COUNT(DISTINCT city) as city_count,
            COUNT(CASE WHEN country != prev_country 
                  AND EXTRACT(EPOCH FROM (timestamp - prev_timestamp))/3600 < 24 
                  THEN 1 END) as rapid_country_changes,
            ARRAY_AGG(DISTINCT country) as countries
        FROM location_changes
        """
        
        result = self.db.fetchone(query, (user_id,))
        
        # Suspicious if rapid country changes
        is_suspicious = (
            result and 
            result['rapid_country_changes'] > 2 and
            result['country_count'] > 3
        )
        
        return {
            'user_id': user_id,
            'is_suspicious': is_suspicious,
            'country_count': result['country_count'] if result else 0,
            'rapid_changes': result['rapid_country_changes'] if result else 0,
            'countries': result['countries'] if result else []
        }
    
    def get_travel_patterns(self, user_id: str) -> Dict:
        """Get user travel patterns"""
        query = """
        SELECT 
            home_country,
            current_country,
            countries_visited,
            cities_visited,
            is_traveling,
            total_locations
        FROM user_geographic_profile
        WHERE user_id = %s
        """
        
        profile = self.db.fetchone(query, (user_id,))
        
        if not profile:
            return {
                'user_id': user_id,
                'is_traveler': False,
                'countries_visited': 0,
                'cities_visited': 0
            }
        
        return {
            'user_id': user_id,
            'is_traveler': len(profile['countries_visited'] or []) > 2,
            'is_currently_traveling': profile['is_traveling'],
            'home_country': profile['home_country'],
            'current_country': profile['current_country'],
            'countries_visited': len(profile['countries_visited'] or []),
            'cities_visited': len(profile['cities_visited'] or [])
        }
    
    def calculate_daily_stats(self, date: Optional[datetime] = None) -> None:
        """Calculate daily location statistics"""
        target_date = date or datetime.now().date()
        
        query = """
        INSERT INTO daily_location_stats
        (date, country, city, user_count, session_count, new_user_count, avg_session_duration)
        SELECT 
            %s as date,
            l.country,
            l.city,
            COUNT(DISTINCT l.user_id) as user_count,
            COUNT(DISTINCT s.session_id) as session_count,
            COUNT(DISTINCT CASE 
                WHEN DATE(l.timestamp) = %s 
                AND l.user_id NOT IN (
                    SELECT user_id FROM user_locations 
                    WHERE DATE(timestamp) < %s
                ) THEN l.user_id 
            END) as new_user_count,
            AVG(EXTRACT(EPOCH FROM (s.end_time - s.start_time)))::INTEGER as avg_duration
        FROM user_locations l
        LEFT JOIN location_sessions s ON l.location_id = s.location_id
        WHERE DATE(l.timestamp) = %s
        GROUP BY l.country, l.city
        ON CONFLICT (date, country, city)
        DO UPDATE SET
            user_count = EXCLUDED.user_count,
            session_count = EXCLUDED.session_count,
            new_user_count = EXCLUDED.new_user_count,
            avg_session_duration = EXCLUDED.avg_session_duration
        """
        
        self.db.execute(query, (target_date, target_date, target_date, target_date))
        
        # Update country summary
        self.update_country_summary()
    
    def update_country_summary(self) -> None:
        """Update country activity summary"""
        query = """
        INSERT INTO country_activity_summary
        (country, country_code, total_users, active_users_today, total_sessions, 
         avg_session_duration, last_activity)
        SELECT 
            l.country,
            l.country_code,
            COUNT(DISTINCT l.user_id) as total_users,
            COUNT(DISTINCT CASE 
                WHEN DATE(l.timestamp) = CURRENT_DATE 
                THEN l.user_id 
            END) as active_today,
            COUNT(DISTINCT s.session_id) as total_sessions,
            AVG(EXTRACT(EPOCH FROM (s.end_time - s.start_time)))::INTEGER as avg_duration,
            MAX(l.timestamp) as last_activity
        FROM user_locations l
        LEFT JOIN location_sessions s ON l.location_id = s.location_id
        GROUP BY l.country, l.country_code
        ON CONFLICT (country)
        DO UPDATE SET
            total_users = EXCLUDED.total_users,
            active_users_today = EXCLUDED.active_users_today,
            total_sessions = EXCLUDED.total_sessions,
            avg_session_duration = EXCLUDED.avg_session_duration,
            last_activity = EXCLUDED.last_activity,
            updated_at = CURRENT_TIMESTAMP
        """
        
        self.db.execute(query)
```

## API Endpoints

```python
from fastapi import APIRouter, Query, HTTPException, Header
from typing import List, Optional

router = APIRouter(prefix="/api/locations", tags=["locations"])

@router.post("/track")
async def track_location(
    user_id: str,
    x_forwarded_for: Optional[str] = Header(None),
    x_real_ip: Optional[str] = Header(None),
    session_id: Optional[str] = None
):
    """Track user location based on IP"""
    # Get IP address from headers
    ip_address = x_forwarded_for or x_real_ip or "0.0.0.0"
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0].strip()
    
    tracker = LocationTracker(db)
    location_id, location_info = tracker.track_location(user_id, ip_address, session_id)
    
    return {
        "location_id": location_id,
        "country": location_info.country,
        "city": location_info.city,
        "timezone": location_info.timezone
    }

@router.get("/user/{user_id}")
async def get_user_locations(
    user_id: str,
    days: int = Query(30, ge=1, le=90)
):
    """Get user's location history"""
    tracker = LocationTracker(db)
    locations = tracker.get_user_locations(user_id, days)
    
    return {
        "user_id": user_id,
        "locations": locations,
        "count": len(locations)
    }

@router.get("/user/{user_id}/profile")
async def get_user_geographic_profile(user_id: str):
    """Get user's geographic profile"""
    query = """
    SELECT 
        user_id,
        home_country,
        home_city,
        current_country,
        current_city,
        countries_visited,
        cities_visited,
        total_locations,
        is_traveling
    FROM user_geographic_profile
    WHERE user_id = %s
    """
    
    profile = db.fetchone(query, (user_id,))
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile

@router.get("/user/{user_id}/travel-patterns")
async def get_user_travel_patterns(user_id: str):
    """Get user travel patterns"""
    tracker = LocationTracker(db)
    patterns = tracker.get_travel_patterns(user_id)
    return patterns

@router.get("/user/{user_id}/vpn-check")
async def check_vpn_usage(user_id: str):
    """Check for possible VPN usage"""
    tracker = LocationTracker(db)
    vpn_check = tracker.detect_vpn_usage(user_id)
    return vpn_check

@router.get("/distribution/global")
async def get_global_distribution():
    """Get global user distribution"""
    tracker = LocationTracker(db)
    distribution = tracker.get_geographic_distribution()
    
    return {
        "distribution": distribution,
        "total_countries": len(distribution)
    }

@router.get("/distribution/country/{country}")
async def get_country_distribution(country: str):
    """Get city distribution within a country"""
    tracker = LocationTracker(db)
    cities = tracker.get_city_distribution(country)
    
    return {
        "country": country,
        "cities": cities,
        "total_cities": len(cities)
    }

@router.get("/activity/countries")
async def get_country_activity():
    """Get country activity summary"""
    query = """
    SELECT 
        country,
        country_code,
        total_users,
        active_users_today,
        total_sessions,
        avg_session_duration,
        last_activity
    FROM country_activity_summary
    ORDER BY total_users DESC
    LIMIT 50
    """
    
    countries = db.fetchall(query)
    
    return {
        "countries": countries,
        "total": len(countries)
    }

@router.get("/stats/daily")
async def get_daily_location_stats(
    date: Optional[str] = Query(None),
    country: Optional[str] = Query(None)
):
    """Get daily location statistics"""
    target_date = date or datetime.now().date().isoformat()
    
    where_conditions = ["date = %s"]
    params = [target_date]
    
    if country:
        where_conditions.append("country = %s")
        params.append(country)
    
    query = f"""
    SELECT 
        country,
        city,
        user_count,
        session_count,
        new_user_count,
        avg_session_duration
    FROM daily_location_stats
    WHERE {' AND '.join(where_conditions)}
    ORDER BY user_count DESC
    LIMIT 100
    """
    
    stats = db.fetchall(query, tuple(params))
    
    return {
        "date": target_date,
        "stats": stats,
        "count": len(stats)
    }

@router.post("/calculate-daily")
async def calculate_daily_stats(
    date: Optional[str] = None
):
    """Calculate daily location statistics"""
    tracker = LocationTracker(db)
    target_date = datetime.fromisoformat(date) if date else datetime.now()
    tracker.calculate_daily_stats(target_date)
    
    return {"status": "calculated", "date": target_date.isoformat()}
```

## React Dashboard Component

```tsx
import React, { useState, useEffect } from 'react';
import { MapPin, Globe, Plane, AlertTriangle } from 'lucide-react';
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps';

interface LocationData {
  locationId: string;
  country: string;
  city: string;
  region: string;
  timezone: string;
  timestamp: string;
}

interface CountryActivity {
  country: string;
  countryCode: string;
  totalUsers: number;
  activeUsersToday: number;
  avgSessionDuration: number;
}

interface GeographicDistribution {
  country: string;
  userCount: number;
  sessionCount: number;
  percentage: number;
}

export const LocationTrackingDashboard: React.FC = () => {
  const [locations, setLocations] = useState<LocationData[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [distribution, setDistribution] = useState<GeographicDistribution[]>([]);
  const [countryActivity, setCountryActivity] = useState<CountryActivity[]>([]);
  const [vpnCheck, setVpnCheck] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [userId] = useState('current-user');

  useEffect(() => {
    fetchLocationData();
  }, []);

  const fetchLocationData = async () => {
    try {
      const [locationsRes, profileRes, distRes, activityRes, vpnRes] = await Promise.all([
        fetch(`/api/locations/user/${userId}?days=30`),
        fetch(`/api/locations/user/${userId}/profile`),
        fetch('/api/locations/distribution/global'),
        fetch('/api/locations/activity/countries'),
        fetch(`/api/locations/user/${userId}/vpn-check`)
      ]);

      const locationsData = await locationsRes.json();
      const profileData = await profileRes.json();
      const distData = await distRes.json();
      const activityData = await activityRes.json();
      const vpnData = await vpnRes.json();

      setLocations(locationsData.locations);
      setProfile(profileData);
      setDistribution(distData.distribution);
      setCountryActivity(activityData.countries);
      setVpnCheck(vpnData);
    } catch (error) {
      console.error('Error fetching location data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading location data...</div>;

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Location Tracking</h2>

      {/* User Profile Summary */}
      {profile && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Your Geographic Profile</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <MapPin className="w-8 h-8 mx-auto mb-2 text-blue-500" />
              <div className="text-sm text-gray-500">Home</div>
              <div className="font-medium">{profile.home_city}, {profile.home_country}</div>
            </div>
            <div className="text-center">
              <Globe className="w-8 h-8 mx-auto mb-2 text-green-500" />
              <div className="text-sm text-gray-500">Current</div>
              <div className="font-medium">{profile.current_city}, {profile.current_country}</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{profile.countries_visited?.length || 0}</div>
              <div className="text-sm text-gray-500">Countries Visited</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{profile.cities_visited?.length || 0}</div>
              <div className="text-sm text-gray-500">Cities Visited</div>
            </div>
          </div>
          
          {profile.is_traveling && (
            <div className="mt-4 p-3 bg-blue-50 rounded flex items-center">
              <Plane className="w-5 h-5 text-blue-500 mr-2" />
              <span className="text-sm text-blue-800">Currently traveling</span>
            </div>
          )}
        </div>
      )}

      {/* VPN Detection Alert */}
      {vpnCheck && vpnCheck.is_suspicious && (
        <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
          <div className="flex items-center">
            <AlertTriangle className="w-5 h-5 text-yellow-600 mr-2" />
            <div>
              <div className="font-medium text-yellow-900">Unusual Location Activity Detected</div>
              <div className="text-sm text-yellow-700">
                {vpnCheck.rapid_changes} rapid country changes across {vpnCheck.country_count} countries
              </div>
            </div>
          </div>
        </div>
      )}

      {/* World Map */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Global User Distribution</h3>
        <div className="h-96">
          <ComposableMap>
            <Geographies geography="/world-110m.json">
              {({ geographies }) =>
                geographies.map(geo => {
                  const country = distribution.find(d => 
                    d.country === geo.properties.NAME
                  );
                  
                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      fill={country ? `rgba(59, 130, 246, ${country.percentage / 100})` : '#E5E7EB'}
                      stroke="#FFF"
                      strokeWidth={0.5}
                    />
                  );
                })
              }
            </Geographies>
          </ComposableMap>
        </div>
      </div>

      {/* Top Countries */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Top Countries by Users</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Country</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Total Users</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Active Today</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Sessions</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Avg Duration</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">% of Total</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {distribution.slice(0, 10).map((country) => (
                <tr key={country.country} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm font-medium">{country.country}</td>
                  <td className="px-4 py-2 text-sm">{country.userCount}</td>
                  <td className="px-4 py-2 text-sm">
                    {countryActivity.find(c => c.country === country.country)?.activeUsersToday || 0}
                  </td>
                  <td className="px-4 py-2 text-sm">{country.sessionCount}</td>
                  <td className="px-4 py-2 text-sm">
                    {Math.round(country.avgDuration || 0)} min
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <div className="flex items-center">
                      <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{ width: `${country.percentage}%` }}
                        />
                      </div>
                      <span>{country.percentage.toFixed(1)}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Locations */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Your Recent Locations</h3>
        <div className="space-y-2">
          {locations.slice(0, 10).map((location) => (
            <div key={location.locationId} className="flex items-center justify-between py-2 border-b">
              <div className="flex items-center space-x-3">
                <MapPin className="w-4 h-4 text-gray-400" />
                <div>
                  <div className="font-medium">{location.city}, {location.country}</div>
                  <div className="text-sm text-gray-500">{location.region}</div>
                </div>
              </div>
              <div className="text-sm text-gray-500">
                {new Date(location.timestamp).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

## Implementation Priority
- **Phase 1**: Basic IP-based location tracking
- **Phase 2**: User geographic profiles
- **Phase 3**: Travel pattern detection
- **Phase 4**: VPN/anomaly detection

## Performance Considerations
- IP anonymization for privacy
- Cached location lookups
- Daily batch processing for statistics
- Limited location history (90 days)

## Security Considerations
- IP address anonymization
- No exact location tracking
- GDPR compliance for EU users
- Location data encryption

## Monitoring and Alerts
- Alert on suspicious location changes
- Daily geographic distribution report
- Weekly travel pattern summary
- Monitor for VPN usage patterns

## Dependencies
- PostgreSQL for data storage
- GeoIP service for IP location (MaxMind recommended)
- FastAPI for REST endpoints
- React with react-simple-maps for visualization