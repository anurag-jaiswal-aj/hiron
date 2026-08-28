"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React, { Suspense, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ApiError, httpClient } from "../../lib/api";

function ResetPasswordForm(): React.ReactElement {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError(null);

    if (!token) {
      setError("This password reset link is invalid or has expired.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);

    try {
      await httpClient.post(
        "/api/v1/auth/reset-password",
        {
          token,
          new_password: password,
        },
        { skipAuth: true },
      );

      setIsSuccess(true);
    } catch (err) {
      setIsSubmitting(false);
      if (err instanceof ApiError) {
        if (err.status === 400 || err.status === 404) {
          setError("This password reset link is invalid or has expired.");
        } else if (err.status === 429) {
          setError("Too many requests. Please try again later.");
        } else {
          // Do not leak internal details. Fallback generic message.
          setError("An error occurred while resetting your password. Please try again.");
        }
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    }
  };

  if (!token && !isSuccess) {
    return (
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            marginBottom: "1.5rem",
            padding: "1rem",
            borderRadius: "var(--radius-md)",
            backgroundColor: "#451A03",
            border: "1px solid #78350F",
            color: "#FDE68A",
            fontSize: "0.875rem",
            lineHeight: "1.5",
          }}
        >
          <p style={{ margin: "0 0 0.5rem", fontWeight: 600 }}>Invalid Link</p>
          <p style={{ margin: 0, color: "#FDE68A" }}>
            This password reset link is invalid or has expired.
          </p>
        </div>
        <Link
          href="/forgot-password"
          style={{
            color: "var(--text-primary)",
            textDecoration: "underline",
            fontSize: "0.875rem",
          }}
        >
          Request a new link
        </Link>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            marginBottom: "1.5rem",
            padding: "1rem",
            borderRadius: "var(--radius-md)",
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            border: "1px solid rgba(16, 185, 129, 0.2)",
            color: "var(--text-primary)",
            fontSize: "0.875rem",
            lineHeight: "1.5",
          }}
        >
          <p style={{ margin: "0 0 0.5rem", fontWeight: 600 }}>Password Reset Complete</p>
          <p style={{ margin: 0, color: "var(--text-secondary)" }}>
            Your password has been successfully reset. You can now log in with your new password.
          </p>
        </div>
        <Link
          href="/login"
          style={{
            color: "var(--text-primary)",
            textDecoration: "underline",
            fontSize: "0.875rem",
          }}
        >
          Proceed to Sign In
        </Link>
      </div>
    );
  }

  return (
    <form
      aria-label="Reset Password"
      onSubmit={handleSubmit}
      style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}
    >
      <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", margin: 0 }}>
        Please enter your new password below.
      </p>

      {error && (
        <div
          role="alert"
          style={{
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
          New Password *
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
        <p style={{ margin: "0.25rem 0 0", fontSize: "0.75rem", color: "var(--text-muted)" }}>
          Minimum 8 characters
        </p>
      </div>

      <Input
        id="confirmPassword"
        type="password"
        required
        label="Confirm New Password *"
        placeholder="••••••••••••"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        disabled={isSubmitting}
      />

      <Button
        type="submit"
        disabled={isSubmitting}
        size="lg"
        style={{ width: "100%", marginTop: "0.5rem" }}
      >
        {isSubmitting ? "Resetting..." : "Reset Password"}
      </Button>
    </form>
  );
}

export default function ResetPasswordPage(): React.ReactElement {
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
          <p
            style={{ margin: "0.25rem 0 0", fontSize: "0.875rem", color: "var(--text-secondary)" }}
          >
            Reset Password
          </p>
        </div>

        <Suspense
          fallback={
            <div style={{ textAlign: "center", color: "var(--text-muted)" }}>Loading...</div>
          }
        >
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}
