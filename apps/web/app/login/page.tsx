"use client";

import { useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
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
      router.replace("/dashboard");
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
          backgroundColor: "var(--bg-app)",
          color: "var(--text-muted)",
        }}
      >
        <p style={{ fontSize: "0.875rem" }}>Loading session...</p>
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
      router.replace("/dashboard");
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
        backgroundColor: "var(--bg-app)",
        color: "var(--text-primary)",
        padding: "1.5rem",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "400px",
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          padding: "2.5rem 2rem",
        }}
      >
        {/* Branding */}
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <h1
            style={{
              margin: 0,
              fontSize: "1.75rem",
              fontWeight: 800,
              letterSpacing: "-0.03em",
              color: "var(--text-primary)",
            }}
          >
            HIRON
          </h1>
          <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem", color: "var(--text-secondary)" }}>
            Minimal Monochrome Recruiting Intelligence
          </p>
        </div>

        {/* Error Alert Box */}
        {error && (
          <div
            role="alert"
            style={{
              marginBottom: "1.5rem",
              padding: "0.75rem 1rem",
              borderRadius: "var(--radius-md)",
              backgroundColor: "#451A03",
              border: "1px solid #78350F",
              color: "#FDE68A",
              fontSize: "0.875rem",
              lineHeight: "1.4",
            }}
          >
            {error}
          </div>
        )}

        {/* Login Form */}
        <form aria-label="Sign in" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Email Input */}
          <Input
            id="email"
            type="email"
            required
            label="Email Address *"
            placeholder="jane@acme.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isSubmitting}
          />

          {/* Tenant ID Input */}
          <Input
            id="tenantId"
            type="text"
            required
            label="Organization / Tenant ID *"
            placeholder="00000000-0000-0000-0000-000000000000"
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            disabled={isSubmitting}
          />

          {/* Password Input */}
          <div>
            <label
              htmlFor="password"
              style={{
                display: "block",
                marginBottom: "0.375rem",
                fontSize: "0.875rem",
                fontWeight: 600,
                color: "var(--text-secondary)",
              }}
            >
              Password *
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
                  padding: "0.625rem 2.5rem 0.625rem 0.75rem",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--bg-surface-secondary)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-primary)",
                  fontSize: "0.875rem",
                  outline: "none",
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
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  fontSize: "0.875rem",
                  padding: "0.25rem 0.5rem",
                  minHeight: "24px",
                }}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <Button type="submit" disabled={isSubmitting} size="lg" style={{ width: "100%", marginTop: "0.5rem" }}>
            {isSubmitting ? "Signing in..." : "Sign In"}
          </Button>
        </form>

        <div style={{ marginTop: "2rem", textAlign: "center", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          Hiron Enterprise Architecture • Securing Multi-Tenant Workflows
        </div>
      </div>
    </div>
  );
}
