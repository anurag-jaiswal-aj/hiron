"use client";

import Link from "next/link";
import React, { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ApiError, httpClient } from "../../lib/api";

export default function ForgotPasswordPage(): React.ReactElement {
  const [email, setEmail] = useState<string>("");
  const [tenantId, setTenantId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError(null);

    const emailTrimmed = email.trim();
    const tenantIdTrimmed = tenantId.trim();

    if (!emailTrimmed) {
      setError("Please enter your email address.");
      return;
    }
    if (!tenantIdTrimmed) {
      setError("Please enter your Organization / Tenant ID.");
      return;
    }

    setIsSubmitting(true);

    try {
      await httpClient.post(
        "/api/v1/auth/forgot-password",
        {
          email: emailTrimmed,
          tenant_id: tenantIdTrimmed,
        },
        { skipAuth: true },
      );

      setIsSuccess(true);
    } catch (err) {
      setIsSubmitting(false);
      if (err instanceof ApiError) {
        if (err.status === 429) {
          setError("Too many requests. Please try again later.");
        } else {
          setError(err.message || "An error occurred. Please try again.");
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
            Forgot Password
          </p>
        </div>

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

        {isSuccess ? (
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
              <p style={{ margin: "0 0 0.5rem", fontWeight: 600 }}>Check your email</p>
              <p style={{ margin: 0, color: "var(--text-secondary)" }}>
                If an account exists for that email, we&apos;ve sent you a password reset link.
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
              Return to Sign In
            </Link>
          </div>
        ) : (
          <form
            aria-label="Forgot Password"
            onSubmit={handleSubmit}
            style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}
          >
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", margin: 0 }}>
              Enter your email address and organization ID. We will send you a link to reset your
              password.
            </p>

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

            <Button
              type="submit"
              disabled={isSubmitting}
              size="lg"
              style={{ width: "100%", marginTop: "0.5rem" }}
            >
              {isSubmitting ? "Sending..." : "Send Reset Link"}
            </Button>

            <div style={{ textAlign: "center", marginTop: "0.5rem" }}>
              <Link
                href="/login"
                style={{
                  color: "var(--text-secondary)",
                  textDecoration: "none",
                  fontSize: "0.875rem",
                }}
              >
                Back to Sign In
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
