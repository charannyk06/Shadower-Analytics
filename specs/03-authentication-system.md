# Specification: Authentication System

## Feature Overview
Shared JWT authentication between the main Shadower app and the Analytics microservice. Users authenticate once in the main app and seamlessly access analytics.

## Technical Requirements
- JWT token verification using shared secret
- Same token works across both services
- Automatic token refresh handling
- Role-based access control (RBAC)
- Workspace-level permissions

## Implementation Details

### JWT Token Structure
```typescript
interface JWTPayload {
  // Standard claims
  sub: string;           // User ID
  iat: number;           // Issued at
  exp: number;           // Expiration
  
  // Custom claims
  email: string;
  workspaceId: string;   // Current workspace
  workspaces: string[];  // All accessible workspaces
  role: 'owner' | 'admin' | 'member' | 'viewer';
  permissions: string[]; // Granular permissions
}
```

### Backend Authentication

#### Environment Configuration
```python
# backend/src/core/config.py
from pydantic import BaseSettings
from typing import Optional

class AuthSettings(BaseSettings):
    JWT_SECRET_KEY: str  # Shared with main app
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_REFRESH_EXPIRATION_DAYS: int = 30
    
    # Optional: For RS256
    JWT_PUBLIC_KEY: Optional[str] = None
    JWT_PRIVATE_KEY: Optional[str] = None
    
    # Supabase (if using Supabase Auth)
    SUPABASE_JWT_SECRET: Optional[str] = None
    
    class Config:
        env_file = ".env"
```

#### JWT Verification Middleware
```python
# backend/src/api/middleware/auth.py
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional, Dict, Any
import time

security = HTTPBearer()

class JWTAuth:
    def __init__(self, settings: AuthSettings):
        self.secret = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        
    async def verify_token(
        self, 
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> Dict[str, Any]:
        """Verify JWT token and return payload"""
        token = credentials.credentials
        
        try:
            payload = jwt.decode(
                token, 
                self.secret, 
                algorithms=[self.algorithm]
            )
            
            # Check expiration
            if payload.get("exp", 0) < time.time():
                raise HTTPException(
                    status_code=401,
                    detail="Token has expired"
                )
            
            return payload
            
        except JWTError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid authentication credentials: {str(e)}"
            )
    
    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> Dict[str, Any]:
        """Get current user from token"""
        payload = await self.verify_token(credentials)
        
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "workspace_id": payload.get("workspaceId"),
            "workspaces": payload.get("workspaces", []),
            "role": payload.get("role"),
            "permissions": payload.get("permissions", [])
        }

# Initialize
auth_settings = AuthSettings()
jwt_auth = JWTAuth(auth_settings)
```

#### Permission Decorator
```python
# backend/src/api/middleware/permissions.py
from functools import wraps
from fastapi import HTTPException, Depends
from typing import List, Callable

def require_permission(*required_permissions: str):
    """Decorator to check for specific permissions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user from kwargs (injected by FastAPI)
            user = kwargs.get('current_user')
            
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            user_permissions = user.get('permissions', [])
            
            # Check if user has required permissions
            has_permission = any(
                perm in user_permissions 
                for perm in required_permissions
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"Required permissions: {', '.join(required_permissions)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(*allowed_roles: str):
    """Decorator to check for specific roles"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )
            
            user_role = user.get('role')
            
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Required role: {' or '.join(allowed_roles)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

#### Workspace Access Validation
```python
# backend/src/api/middleware/workspace.py
from fastapi import HTTPException
from typing import Dict, Any

class WorkspaceAccess:
    @staticmethod
    async def validate_workspace_access(
        user: Dict[str, Any], 
        workspace_id: str
    ) -> bool:
        """Check if user has access to workspace"""
        user_workspaces = user.get('workspaces', [])
        
        if workspace_id not in user_workspaces:
            raise HTTPException(
                status_code=403,
                detail=f"No access to workspace {workspace_id}"
            )
        
        return True
    
    @staticmethod
    async def get_accessible_workspaces(
        user: Dict[str, Any]
    ) -> List[str]:
        """Get list of workspaces user can access"""
        return user.get('workspaces', [])
```

#### Protected Route Example
```python
# backend/src/api/routes/executive.py
from fastapi import APIRouter, Depends
from typing import Dict, Any

router = APIRouter()

@router.get("/executive/overview")
@require_role("owner", "admin")
async def get_executive_overview(
    current_user: Dict[str, Any] = Depends(jwt_auth.get_current_user),
    workspace_id: str = None
):
    """Get executive dashboard overview"""
    
    # Use current workspace if not specified
    if not workspace_id:
        workspace_id = current_user.get('workspace_id')
    
    # Validate access
    await WorkspaceAccess.validate_workspace_access(
        current_user, 
        workspace_id
    )
    
    # Fetch metrics...
    return {
        "workspace_id": workspace_id,
        "metrics": {...}
    }
```

### Frontend Authentication

#### Auth Context Provider
```typescript
// frontend/src/contexts/AuthContext.tsx
import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (token: string) => void;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Check for token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    
    if (storedToken) {
      validateAndSetToken(storedToken);
    } else {
      // Check if coming from main app with token
      const urlParams = new URLSearchParams(window.location.search);
      const tokenParam = urlParams.get('token');
      
      if (tokenParam) {
        validateAndSetToken(tokenParam);
        // Clean URL
        window.history.replaceState({}, '', window.location.pathname);
      } else {
        redirectToMainApp();
      }
    }
    
    setIsLoading(false);
  }, []);

  const validateAndSetToken = async (jwtToken: string) => {
    try {
      // Decode token (without verification on client)
      const payload = JSON.parse(atob(jwtToken.split('.')[1]));
      
      // Check expiration
      if (payload.exp * 1000 < Date.now()) {
        throw new Error('Token expired');
      }
      
      setToken(jwtToken);
      setUser({
        id: payload.sub,
        email: payload.email,
        workspaceId: payload.workspaceId,
        role: payload.role,
        permissions: payload.permissions
      });
      
      // Set default auth header
      axios.defaults.headers.common['Authorization'] = `Bearer ${jwtToken}`;
      
      localStorage.setItem('auth_token', jwtToken);
      
    } catch (error) {
      console.error('Invalid token:', error);
      redirectToMainApp();
    }
  };

  const redirectToMainApp = () => {
    const mainAppUrl = process.env.NEXT_PUBLIC_MAIN_APP_URL;
    const returnUrl = encodeURIComponent(window.location.href);
    window.location.href = `${mainAppUrl}/login?return_url=${returnUrl}`;
  };

  const login = (jwtToken: string) => {
    validateAndSetToken(jwtToken);
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('auth_token');
    delete axios.defaults.headers.common['Authorization'];
    redirectToMainApp();
  };

  const refreshToken = async () => {
    try {
      // Call main app's refresh endpoint
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_MAIN_APP_URL}/api/auth/refresh`,
        { token }
      );
      
      const newToken = response.data.token;
      validateAndSetToken(newToken);
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
    }
  };

  // Auto-refresh before expiration
  useEffect(() => {
    if (!token) return;

    const payload = JSON.parse(atob(token.split('.')[1]));
    const expiresIn = payload.exp * 1000 - Date.now();
    
    // Refresh 5 minutes before expiration
    const refreshTimeout = setTimeout(() => {
      refreshToken();
    }, expiresIn - 5 * 60 * 1000);

    return () => clearTimeout(refreshTimeout);
  }, [token]);

  return (
    <AuthContext.Provider 
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshToken
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

#### Axios Interceptor
```typescript
// frontend/src/lib/api/client.ts
import axios, { AxiosInstance } from 'axios';
import { toast } from 'react-hot-toast';

const API_BASE_URL = process.env.NEXT_PUBLIC_ANALYTICS_API_URL;

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh token
        const refreshResponse = await axios.post(
          `${process.env.NEXT_PUBLIC_MAIN_APP_URL}/api/auth/refresh`,
          { token: localStorage.getItem('auth_token') }
        );

        const newToken = refreshResponse.data.token;
        localStorage.setItem('auth_token', newToken);
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
        originalRequest.headers.Authorization = `Bearer ${newToken}`;

        return apiClient(originalRequest);
      } catch (refreshError) {
        // Redirect to login
        toast.error('Session expired. Please login again.');
        window.location.href = `${process.env.NEXT_PUBLIC_MAIN_APP_URL}/login`;
        return Promise.reject(refreshError);
      }
    }

    if (error.response?.status === 403) {
      toast.error('You do not have permission to perform this action');
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

#### Protected Route Component
```typescript
// frontend/src/components/auth/ProtectedRoute.tsx
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Spinner } from '@/components/ui/Spinner';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string[];
  requiredPermissions?: string[];
}

export function ProtectedRoute({ 
  children, 
  requiredRole = [], 
  requiredPermissions = [] 
}: ProtectedRouteProps) {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }

    if (user && requiredRole.length > 0) {
      if (!requiredRole.includes(user.role)) {
        router.push('/unauthorized');
      }
    }

    if (user && requiredPermissions.length > 0) {
      const hasPermission = requiredPermissions.some(
        perm => user.permissions.includes(perm)
      );
      
      if (!hasPermission) {
        router.push('/unauthorized');
      }
    }
  }, [isLoading, isAuthenticated, user, requiredRole, requiredPermissions]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
```

### Integration with Main App

#### Main App: Analytics Button
```typescript
// In main Shadower app
// components/navigation/AnalyticsButton.tsx
import { useAuth } from '@/hooks/useAuth';

export function AnalyticsButton() {
  const { token } = useAuth();
  
  const openAnalytics = () => {
    const analyticsUrl = process.env.NEXT_PUBLIC_ANALYTICS_URL;
    
    // Pass token via URL (will be captured by analytics app)
    const url = `${analyticsUrl}?token=${encodeURIComponent(token)}`;
    
    // Open in new tab
    window.open(url, '_blank');
    
    // Alternative: Open in same tab
    // window.location.href = url;
    
    // Alternative: Post message to iframe
    // const iframe = document.getElementById('analytics-iframe');
    // iframe.contentWindow.postMessage({ token }, analyticsUrl);
  };
  
  return (
    <button 
      onClick={openAnalytics}
      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
    >
      <ChartBarIcon className="h-5 w-5" />
      View Analytics
    </button>
  );
}
```

#### Main App: Token Refresh Endpoint
```typescript
// In main Shadower app
// pages/api/auth/refresh.ts
import { NextApiRequest, NextApiResponse } from 'next';
import jwt from 'jsonwebtoken';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { token } = req.body;

  try {
    // Verify old token
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    
    // Generate new token with extended expiration
    const newToken = jwt.sign(
      {
        sub: decoded.sub,
        email: decoded.email,
        workspaceId: decoded.workspaceId,
        workspaces: decoded.workspaces,
        role: decoded.role,
        permissions: decoded.permissions
      },
      process.env.JWT_SECRET,
      { expiresIn: '24h' }
    );
    
    res.status(200).json({ token: newToken });
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
}
```

### Role-Based Access Control

#### Permission Matrix
```typescript
// shared/permissions.ts
export const PERMISSIONS = {
  // Executive
  VIEW_EXECUTIVE_DASHBOARD: 'view_executive_dashboard',
  VIEW_FINANCIAL_METRICS: 'view_financial_metrics',
  
  // Analytics
  VIEW_ANALYTICS: 'view_analytics',
  EXPORT_ANALYTICS: 'export_analytics',
  CREATE_REPORTS: 'create_reports',
  
  // Alerts
  VIEW_ALERTS: 'view_alerts',
  CREATE_ALERTS: 'create_alerts',
  MANAGE_ALERTS: 'manage_alerts',
  
  // Admin
  MANAGE_WORKSPACE: 'manage_workspace',
  VIEW_ALL_WORKSPACES: 'view_all_workspaces',
};

export const ROLE_PERMISSIONS = {
  owner: Object.values(PERMISSIONS),
  admin: [
    PERMISSIONS.VIEW_EXECUTIVE_DASHBOARD,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.EXPORT_ANALYTICS,
    PERMISSIONS.CREATE_REPORTS,
    PERMISSIONS.VIEW_ALERTS,
    PERMISSIONS.CREATE_ALERTS,
    PERMISSIONS.MANAGE_ALERTS,
  ],
  member: [
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.EXPORT_ANALYTICS,
    PERMISSIONS.VIEW_ALERTS,
  ],
  viewer: [
    PERMISSIONS.VIEW_ANALYTICS,
  ],
};
```

## Testing Requirements
- Unit tests for JWT verification
- Integration tests for protected endpoints
- E2E tests for authentication flow
- Token expiration handling tests
- Permission validation tests

## Performance Targets
- Token verification: <10ms
- Permission check: <5ms
- Token refresh: <200ms
- Auth state hydration: <100ms

## Security Considerations
- JWT secret must be strong (256-bit minimum)
- Tokens expire after 24 hours
- Refresh tokens expire after 30 days
- HTTPS only in production
- Implement rate limiting on auth endpoints
- Log all authentication attempts
- Consider implementing JWT revocation list for logout