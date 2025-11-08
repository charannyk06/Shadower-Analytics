/**
 * Authentication types and interfaces
 */

export interface User {
  id: string;
  email: string;
  workspaceId: string;
  workspaces: string[];
  role: UserRole;
  permissions: string[];
}

export type UserRole = "owner" | "admin" | "member" | "viewer";

export interface JWTPayload {
  // Standard claims
  sub: string; // User ID
  iat: number; // Issued at
  exp: number; // Expiration

  // Custom claims
  email: string;
  workspaceId: string; // Current workspace
  workspaces: string[]; // All accessible workspaces
  role: UserRole;
  permissions: string[]; // Granular permissions
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (token: string) => void;
  logout: () => void;
  refreshToken: () => Promise<void>;
}
