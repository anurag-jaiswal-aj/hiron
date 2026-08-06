"use client";

import { useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";

import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";

export default function LoginPage(): React.ReactElement | null {
  const { login, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [tenantId, setTenantId] = useState<string>("");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || isAuthenticated) {
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
        <p style={{ fontSize: "0.875rem" }}>Loading...</p>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError("Please enter your email address.");
      return;
    }
    if (!password) {
      setError("Please enter your password.");
      return;
    }
    if (!tenantId.trim()) {
      setError("Please enter your Tenant Organization ID.");
      return;
    }

    setIsSubmitting(true);

    try {
      await login({
        email: email.trim(),
        password,
        tenantId: tenantId.trim(),
      });
      router.replace("/");
    } catch (err) {
      setIsSubmitting(false);
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setError("Invalid email, password, or tenant ID.");
        } else if (err.status === 429) {
          setError("Too many login attempts. Try again in 60 seconds.");
        } else {
          setError(err.message || "Authentication failed. Please try again.");
        }
      } else {
        setError(err instanceof Error ? err.message : "An unexpected error occurred.");
      }
    }
  };

  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        alignItems: "center",
        justifyContent: "center",
        background: "radial-gradient(ellipse at top, #1e1b4b 0%, #090d16 80%)",
        color: "#f8fafc",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        padding: "1.5rem",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "420px",
          backgroundColor: "rgba(15, 23, 42, 0.75)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          borderRadius: "16px",
          padding: "2.5rem 2rem",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
        }}
      >
        {/* Header Branding */}
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <h1
            style={{
              margin: 0,
              fontSize: "2rem",
              fontWeight: 800,
              letterSpacing: "-0.025em",
              background: "linear-gradient(135deg, #a5b4fc 0%, #6366f1 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Hiron
          </h1>
          <p
            style={{
              margin: "0.5rem 0 0",
              fontSize: "0.875rem",
              color: "#94a3b8",
            }}
          >
            Hiring Intelligence Platform
          </p>
        </div>

        {/* Error Alert Box */}
        {error && (
          <div
            role="alert"
            style={{
              marginBottom: "1.5rem",
              padding: "0.75rem 1rem",
              borderRadius: "8px",
              backgroundColor: "rgba(239, 68, 68, 0.15)",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              color: "#fca5a5",
              fontSize: "0.875rem",
              lineHeight: "1.4",
            }}
          >
            {error}
          </div>
        )}

        {/* Login Form */}
        <form aria-label="Sign in" onSubmit={handleSubmit}>
          {/* Email Input */}
          <div style={{ marginBottom: "1.25rem" }}>
            <label
              htmlFor="email"
              style={{
                display: "block",
                marginBottom: "0.5rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "#cbd5e1",
              }}
            >
              Email Address <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <input
              id="email"
              type="email"
              required
              placeholder="jane@acme.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isSubmitting}
              style={{
                width: "100%",
                padding: "0.75rem 1rem",
                borderRadius: "8px",
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                color: "#f8fafc",
                fontSize: "0.875rem",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Tenant ID Input */}
          <div style={{ marginBottom: "1.25rem" }}>
            <label
              htmlFor="tenantId"
              style={{
                display: "block",
                marginBottom: "0.5rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "#cbd5e1",
              }}
            >
              Organization / Tenant ID <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <input
              id="tenantId"
              type="text"
              required
              placeholder="00000000-0000-0000-0000-000000000000"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              disabled={isSubmitting}
              style={{
                width: "100%",
                padding: "0.75rem 1rem",
                borderRadius: "8px",
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                color: "#f8fafc",
                fontSize: "0.875rem",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Password Input */}
          <div style={{ marginBottom: "1.5rem" }}>
            <label
              htmlFor="password"
              style={{
                display: "block",
                marginBottom: "0.5rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "#cbd5e1",
              }}
            >
              Password <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <div style={{ position: "relative" }}>
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                required
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting}
                style={{
                  width: "100%",
                  padding: "0.75rem 2.5rem 0.75rem 1rem",
                  borderRadius: "8px",
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  color: "#f8fafc",
                  fontSize: "0.875rem",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                style={{
                  position: "absolute",
                  right: "0.75rem",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  color: "#94a3b8",
                  cursor: "pointer",
                  fontSize: "1rem",
                  padding: 0,
                }}
              >
                {showPassword ? "🙈" : "👁"}
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              width: "100%",
              padding: "0.875rem 1rem",
              borderRadius: "8px",
              border: "none",
              background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
              color: "#ffffff",
              fontSize: "0.875rem",
              fontWeight: 600,
              cursor: isSubmitting ? "not-allowed" : "pointer",
              opacity: isSubmitting ? 0.7 : 1,
              transition: "all 0.2s ease",
            }}
          >
            {isSubmitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        {/* Footer info */}
        <div style={{ marginTop: "2rem", textAlign: "center", fontSize: "0.8125rem", color: "#64748b" }}>
          Don&apos;t have an account? Contact your administrator.
        </div>
      </div>
    </div>
  );
}
