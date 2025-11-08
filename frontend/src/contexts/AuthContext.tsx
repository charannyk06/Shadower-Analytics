"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { User, AuthContextType, JWTPayload } from "@/types/auth";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Check for token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem("auth_token");

    if (storedToken) {
      validateAndSetToken(storedToken);
    } else {
      // Check if coming from main app with token
      const urlParams = new URLSearchParams(window.location.search);
      const tokenParam = urlParams.get("token");

      if (tokenParam) {
        validateAndSetToken(tokenParam);
        // Clean URL
        window.history.replaceState({}, "", window.location.pathname);
      } else {
        redirectToMainApp();
      }
    }

    setIsLoading(false);
  }, []);

  const validateAndSetToken = async (jwtToken: string) => {
    try {
      // Decode token (without verification on client)
      const payload: JWTPayload = JSON.parse(atob(jwtToken.split(".")[1]));

      // Check expiration
      if (payload.exp * 1000 < Date.now()) {
        throw new Error("Token expired");
      }

      setToken(jwtToken);
      setUser({
        id: payload.sub,
        email: payload.email,
        workspaceId: payload.workspaceId,
        workspaces: payload.workspaces,
        role: payload.role,
        permissions: payload.permissions,
      });

      // Set default auth header
      axios.defaults.headers.common["Authorization"] = `Bearer ${jwtToken}`;

      localStorage.setItem("auth_token", jwtToken);
    } catch (error) {
      console.error("Invalid token:", error);
      redirectToMainApp();
    }
  };

  const redirectToMainApp = () => {
    const mainAppUrl =
      process.env.NEXT_PUBLIC_MAIN_APP_URL || "http://localhost:3001";
    const returnUrl = encodeURIComponent(window.location.href);
    window.location.href = `${mainAppUrl}/login?return_url=${returnUrl}`;
  };

  const login = (jwtToken: string) => {
    validateAndSetToken(jwtToken);
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem("auth_token");
    delete axios.defaults.headers.common["Authorization"];
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
      console.error("Token refresh failed:", error);
      logout();
    }
  };

  // Auto-refresh before expiration
  useEffect(() => {
    if (!token) return;

    try {
      const payload: JWTPayload = JSON.parse(atob(token.split(".")[1]));
      const expiresIn = payload.exp * 1000 - Date.now();

      // Refresh 5 minutes before expiration
      const refreshTimeout = setTimeout(() => {
        refreshToken();
      }, expiresIn - 5 * 60 * 1000);

      return () => clearTimeout(refreshTimeout);
    } catch (error) {
      console.error("Error setting up token refresh:", error);
    }
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
        refreshToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};
