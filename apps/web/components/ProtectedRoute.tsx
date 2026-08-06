"use client";

import { useRouter } from "next/navigation";
import React, { useEffect } from "react";

import { useAuth } from "../context/AuthContext";

export function ProtectedRoute({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement | null {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          minHeight: "100vh",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#090d16",
          color: "#94a3b8",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              margin: "0 auto 1rem",
              borderRadius: "50%",
              border: "3px solid #1e293b",
              borderTopColor: "#6366f1",
              animation: "spin 1s linear infinite",
            }}
          />
          <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
          <p style={{ margin: 0, fontSize: "0.875rem" }}>Loading session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
