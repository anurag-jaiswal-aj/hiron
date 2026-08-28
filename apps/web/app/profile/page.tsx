"use client";

import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { PageHeader } from "../../components/layout/PageHeader";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { httpClient, ResponseEnvelope } from "../../lib/api";
import type { UserResponse } from "../../lib/users-api";

export default function ProfilePage(): React.ReactElement {
  const { user, refreshSession } = useAuth();

  const [fullName, setFullName] = useState(user?.fullName || "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // If unauthenticated, redirecting is handled by ProtectedRoute typically,
  // but we can add a fallback here just in case.
  if (!user) {
    return <div>Loading...</div>;
  }

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!fullName.trim()) {
      setError("Full name is required.");
      return;
    }

    setIsSubmitting(true);
    try {
      await httpClient.patch<ResponseEnvelope<UserResponse>>(
        `/api/v1/users/${user.id}`,
        { fullName: fullName.trim() }
      );
      
      setSuccess(true);
      
      // Refresh session to update context and sidebar
      await refreshSession();
    } catch (err: unknown) {
      console.error("Profile update failed:", err);
      // Fallback for axios-like error object
      const errorObj = err as { response?: { data?: { error?: { message?: string } } } };
      setError(
        errorObj.response?.data?.error?.message ||
        "An error occurred while updating your profile."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "2rem" }}>
      <PageHeader
        title="Profile"
        subtitle="Manage your personal profile information."
      />

      <div
        style={{
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          padding: "2rem",
          marginTop: "2rem",
        }}
      >
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <div>
            <h3 style={{ fontSize: "1.125rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "0.25rem" }}>
              Personal Information
            </h3>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
              Update your display name. Email address changes are not currently supported.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div>
              <label
                htmlFor="email"
                style={{
                  display: "block",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  color: "var(--text-secondary)",
                  marginBottom: "0.5rem",
                }}
              >
                Email Address
              </label>
              <Input
                id="email"
                type="email"
                value={user.email}
                disabled
                style={{ backgroundColor: "var(--bg-surface-secondary)", color: "var(--text-muted)" }}
              />
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
                Contact an administrator to change your email address.
              </p>
            </div>

            <div>
              <label
                htmlFor="role"
                style={{
                  display: "block",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  color: "var(--text-secondary)",
                  marginBottom: "0.5rem",
                }}
              >
                Role
              </label>
              <Input
                id="role"
                type="text"
                value={user.role.replace("_", " ")}
                disabled
                style={{ backgroundColor: "var(--bg-surface-secondary)", color: "var(--text-muted)", textTransform: "capitalize" }}
              />
            </div>

            <div>
              <label
                htmlFor="fullName"
                style={{
                  display: "block",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  color: "var(--text-primary)",
                  marginBottom: "0.5rem",
                }}
              >
                Full Name
              </label>
              <Input
                id="fullName"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Jane Doe"
                required
                disabled={isSubmitting}
                error={error || undefined}
              />
            </div>
          </div>

          {success && (
            <div
              style={{
                backgroundColor: "var(--green-50)",
                color: "var(--green-700)",
                padding: "1rem",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--green-200)",
                fontSize: "0.875rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem"
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
              Profile updated successfully.
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "1rem" }}>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting || fullName.trim() === user.fullName}
            >
              {isSubmitting ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
