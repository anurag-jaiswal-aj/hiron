"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import { PageHeader } from "../../components/layout/PageHeader";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { AppShell } from "../../components/layout/AppShell";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { ApiError, httpClient, ResponseEnvelope } from "../../lib/api";

interface TenantResponse {
  id: string;
  name: string;
  slug: string;
  plan: string;
  settings: Record<string, unknown>;
  is_active: boolean;
}

function SettingsContent(): React.ReactElement {
  const { user } = useAuth();
  const [tenant, setTenant] = useState<TenantResponse | null>(null);
  const [orgName, setOrgName] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const fetchTenant = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const response = await httpClient.get<ResponseEnvelope<TenantResponse>>(
        `/api/v1/tenants/${user.tenantId}`,
      );
      setTenant(response.data);
      setOrgName(response.data.name);
    } catch (err: unknown) {
      console.error("Failed to load tenant settings:", err);
      if (err instanceof ApiError) {
        setError(err.message || "Failed to load workspace settings.");
      } else {
        setError("An unexpected error occurred loading workspace settings.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [user?.tenantId]);

  useEffect(() => {
    fetchTenant();
  }, [fetchTenant]);

  if (!user || user.role !== "org_admin") {
    return (
      <AppShell>
        <div style={{ maxWidth: "800px", margin: "0 auto", padding: "2rem" }}>
          <PageHeader
            title="Access Denied"
            subtitle="You do not have permission to view workspace settings."
          />
        </div>
      </AppShell>
    );
  }

  if (isLoading) {
    return (
      <AppShell>
        <div style={{ maxWidth: "800px", margin: "0 auto", padding: "2rem" }}>
          Loading workspace settings...
        </div>
      </AppShell>
    );
  }

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!orgName.trim()) {
      setError("Organization name is required.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await httpClient.patch<ResponseEnvelope<TenantResponse>>(
        `/api/v1/tenants/${user.tenantId}`,
        {
          name: orgName.trim(),
        },
      );
      setTenant(response.data);
      setSuccess(true);
    } catch (err: unknown) {
      console.error("Workspace update failed:", err);
      if (err instanceof ApiError) {
        setError(err.message || "An error occurred while updating settings.");
      } else {
        setError(err instanceof Error ? err.message : "An unexpected error occurred.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div style={{ maxWidth: "800px", margin: "0 auto", padding: "2rem" }}>
        <PageHeader title="Workspace Settings" subtitle="Configure workspace-level settings." />

        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            padding: "2rem",
            marginTop: "2rem",
          }}
        >
          <form
            onSubmit={handleSubmit}
            style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}
          >
            <div>
              <h3
                style={{
                  fontSize: "1.125rem",
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  marginBottom: "0.25rem",
                }}
              >
                General Settings
              </h3>
              <p
                style={{
                  fontSize: "0.875rem",
                  color: "var(--text-secondary)",
                  marginBottom: "1.5rem",
                }}
              >
                Update your organization details.
              </p>
            </div>

            {error && (
              <div
                style={{
                  backgroundColor: "var(--red-50)",
                  color: "var(--red-700)",
                  padding: "1rem",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--red-200)",
                  fontSize: "0.875rem",
                }}
              >
                {error}
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <label
                  htmlFor="orgName"
                  style={{
                    display: "block",
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    color: "var(--text-primary)",
                    marginBottom: "0.5rem",
                  }}
                >
                  Organization Name
                </label>
                <Input
                  id="orgName"
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  placeholder="Acme Corp"
                  disabled={isSubmitting}
                />
              </div>

              <div>
                <label
                  htmlFor="workspaceUrl"
                  style={{
                    display: "block",
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    color: "var(--text-secondary)",
                    marginBottom: "0.5rem",
                  }}
                >
                  Workspace URL
                </label>
                <Input
                  id="workspaceUrl"
                  type="text"
                  value={tenant?.slug ? `${tenant.slug}.hiron.ai` : ""}
                  disabled
                  style={{
                    backgroundColor: "var(--bg-surface-secondary)",
                    color: "var(--text-muted)",
                  }}
                />
              </div>

              <div>
                <label
                  htmlFor="plan"
                  style={{
                    display: "block",
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    color: "var(--text-secondary)",
                    marginBottom: "0.5rem",
                  }}
                >
                  Plan
                </label>
                <Input
                  id="plan"
                  type="text"
                  value={tenant?.plan || ""}
                  disabled
                  style={{
                    backgroundColor: "var(--bg-surface-secondary)",
                    color: "var(--text-muted)",
                    textTransform: "capitalize",
                  }}
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
                  gap: "0.5rem",
                }}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                  <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                Workspace settings updated successfully.
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "1rem" }}>
              <Button
                type="submit"
                variant="primary"
                disabled={isSubmitting || orgName.trim() === tenant?.name}
              >
                {isSubmitting ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </AppShell>
  );
}

export default function SettingsPage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <SettingsContent />
    </ProtectedRoute>
  );
}
