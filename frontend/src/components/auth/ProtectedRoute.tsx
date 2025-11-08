"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Permission, Role } from "@/types/permissions";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: Role[];
  requiredPermissions?: Permission[];
}

export function ProtectedRoute({
  children,
  requiredRole = [],
  requiredPermissions = [],
}: ProtectedRouteProps) {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }

    if (user && requiredRole.length > 0) {
      if (!requiredRole.includes(user.role)) {
        router.push("/unauthorized");
      }
    }

    if (user && requiredPermissions.length > 0) {
      const hasPermission = requiredPermissions.some((perm) =>
        user.permissions.includes(perm)
      );

      if (!hasPermission) {
        router.push("/unauthorized");
      }
    }
  }, [isLoading, isAuthenticated, user, requiredRole, requiredPermissions]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
