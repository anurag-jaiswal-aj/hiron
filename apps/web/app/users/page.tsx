"use client";

import React, { useCallback, useEffect, useState } from "react";

import { AppShell } from "../../components/layout/AppShell";
import { PageHeader } from "../../components/layout/PageHeader";
import { ProtectedRoute } from "../../components/ProtectedRoute";

import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { EditUserModal } from "../../components/users/EditUserModal";
import { InviteUserModal } from "../../components/users/InviteUserModal";
import { RoleBadge } from "../../components/users/RoleBadge";
import { UserStatusBadge } from "../../components/users/UserStatusBadge";
import { useAuth } from "../../context/AuthContext";
import { ApiError, httpClient } from "../../lib/api";

interface UserItem {
  id: string;
  tenantId: string;
  email: string;
  fullName: string;
  role: string;
  isActive: boolean;
  isEmailVerified: boolean;
  createdAt: string;
}

interface ResponseEnvelope<T> {
  data: T;
}

function UserManagementContent(): React.ReactElement {
  const { user } = useAuth();
  const isAdmin = user?.role === "org_admin";

  const [users, setUsers] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters & Pagination
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState<number>(1);
  const limit = 20;

  // Modals & Action loading
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);

    try {
      const params = new URLSearchParams();
      if (roleFilter) params.append("role", roleFilter);
      if (statusFilter !== "") params.append("isActive", statusFilter);
      params.append("limit", String(limit));
      params.append("offset", String((page - 1) * limit));

      const response = await httpClient.get<ResponseEnvelope<UserItem[]>>(
        `/api/v1/users?${params.toString()}`,
      );
      if (response && response.data) {
        setUsers(response.data);
      } else {
        setUsers([]);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to load user roster.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [roleFilter, statusFilter, page]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  async function handleToggleStatus(targetUser: UserItem): Promise<void> {
    setActionLoadingId(targetUser.id);
    setErrorMsg(null);
    setSuccessMsg(null);

    const action = targetUser.isActive ? "deactivate" : "reactivate";

    try {
      await httpClient.post<ResponseEnvelope<UserItem>>(
        `/api/v1/users/${targetUser.id}/${action}`,
        {},
      );
      await fetchUsers();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg(`Failed to ${action} user. Please try again.`);
      }
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleResendInvite(targetUser: UserItem): Promise<void> {
    setActionLoadingId(targetUser.id);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await httpClient.post<ResponseEnvelope<{ status: string }>>(
        `/api/v1/users/${targetUser.id}/invite/resend`,
        {},
      );
      setSuccessMsg(`Invitation resent successfully to ${targetUser.email}.`);
      await fetchUsers(); // Optional, but keeps UI state fresh if needed
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setErrorMsg("Cannot resend invitation. The user may be already verified or inactive.");
        } else {
          setErrorMsg(err.message);
        }
      } else {
        setErrorMsg(`Failed to resend invitation. Please try again.`);
      }
    } finally {
      setActionLoadingId(null);
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Team Management"
        subtitle="Manage user accounts, roles, and administrative permissions."
        actions={
          isAdmin ? (
            <Button type="button" onClick={() => setIsInviteModalOpen(true)}>
              + Invite User
            </Button>
          ) : undefined
        }
      />

      {/* Global Error Notice */}
      {errorMsg && (
        <div
          style={{
            marginBottom: "1.5rem",
            padding: "0.875rem 1.25rem",
            borderRadius: "var(--radius-md)",
            backgroundColor: "#451A03",
            border: "1px solid #78350F",
            color: "#FDE68A",
            fontSize: "0.875rem",
          }}
        >
          {errorMsg}
        </div>
      )}

      {/* Global Success Notice */}
      {successMsg && (
        <div
          style={{
            marginBottom: "1.5rem",
            padding: "0.875rem 1.25rem",
            borderRadius: "var(--radius-md)",
            backgroundColor: "#064E3B",
            border: "1px solid #065F46",
            color: "#A7F3D0",
            fontSize: "0.875rem",
          }}
        >
          {successMsg}
        </div>
      )}

      {/* Filter Bar */}
      <div
        style={{
          display: "flex",
          gap: "1rem",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <div style={{ width: "180px" }}>
          <Select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(1);
            }}
            options={[
              { value: "", label: "All Roles" },
              { value: "org_admin", label: "Org Admin" },
              { value: "recruiter", label: "Recruiter" },
              { value: "hiring_manager", label: "Hiring Manager" },
            ]}
          />
        </div>

        <div style={{ width: "180px" }}>
          <Select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            options={[
              { value: "", label: "All Statuses" },
              { value: "true", label: "Active Only" },
              { value: "false", label: "Inactive Only" },
            ]}
          />
        </div>
      </div>

      {/* Users Data Table */}
      <div
        style={{
          backgroundColor: "var(--bg-surface)",
          borderRadius: "var(--radius-lg)",
          border: "1px solid var(--border-subtle)",
          overflow: "hidden",
        }}
      >
        {isLoading ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
            <p style={{ margin: 0, fontSize: "0.875rem" }}>Loading team roster...</p>
          </div>
        ) : users.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-secondary)" }}>
            <p style={{ margin: 0, fontSize: "0.875rem" }}>
              No team members match the selected filter criteria.
            </p>
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
            <thead>
              <tr
                style={{
                  borderBottom: "1px solid var(--border-subtle)",
                  color: "var(--text-muted)",
                  fontSize: "0.75rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>User</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Role</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Status</th>
                <th style={{ padding: "1rem 1.25rem", fontWeight: 600 }}>Joined Date</th>
                {isAdmin && (
                  <th style={{ padding: "1rem 1.25rem", fontWeight: 600, textAlign: "right" }}>
                    Actions
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isActioning = actionLoadingId === u.id;
                const isSelf = user?.email === u.email;

                return (
                  <tr
                    key={u.id}
                    style={{
                      borderBottom: "1px solid var(--border-subtle)",
                      transition: "background-color 0.15s ease",
                    }}
                  >
                    {/* User info */}
                    <td style={{ padding: "1rem 1.25rem" }}>
                      <div
                        style={{
                          fontWeight: 600,
                          color: "var(--text-primary)",
                          fontSize: "0.875rem",
                        }}
                      >
                        {u.fullName || "Unnamed User"}
                      </div>
                      <div
                        style={{
                          fontSize: "0.8125rem",
                          color: "var(--text-secondary)",
                          marginTop: "0.125rem",
                        }}
                      >
                        {u.email}
                      </div>
                    </td>

                    {/* Role Badge */}
                    <td style={{ padding: "1rem 1.25rem" }}>
                      <RoleBadge role={u.role} />
                    </td>

                    {/* Status Badge */}
                    <td style={{ padding: "1rem 1.25rem" }}>
                      <UserStatusBadge isActive={u.isActive} isEmailVerified={u.isEmailVerified} />
                    </td>

                    {/* Created Date */}
                    <td
                      style={{
                        padding: "1rem 1.25rem",
                        color: "var(--text-secondary)",
                        fontSize: "0.875rem",
                      }}
                    >
                      {new Date(u.createdAt).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </td>

                    {/* Admin Actions */}
                    {isAdmin && (
                      <td style={{ padding: "1rem 1.25rem", textAlign: "right" }}>
                        <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
                          {u.isActive && !u.isEmailVerified && (
                            <Button
                              type="button"
                              variant="secondary"
                              size="sm"
                              onClick={() => handleResendInvite(u)}
                              disabled={isActioning}
                            >
                              Resend Invite
                            </Button>
                          )}
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            onClick={() => setEditingUser(u)}
                            disabled={isActioning}
                          >
                            Edit
                          </Button>

                          <Button
                            type="button"
                            variant={u.isActive ? "destructive" : "secondary"}
                            size="sm"
                            onClick={() => handleToggleStatus(u)}
                            disabled={isActioning || isSelf}
                            title={isSelf ? "You cannot deactivate your own account" : undefined}
                          >
                            {isActioning ? "Updating..." : u.isActive ? "Deactivate" : "Reactivate"}
                          </Button>
                        </div>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {/* Footer / Pagination summary */}
        <div
          style={{
            padding: "0.875rem 1.25rem",
            backgroundColor: "var(--bg-surface-secondary)",
            borderTop: "1px solid var(--border-subtle)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: "0.8125rem",
            color: "var(--text-secondary)",
          }}
        >
          <span>Showing {users.length} team member(s)</span>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || isLoading}
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={users.length < limit || isLoading}
            >
              Next
            </Button>
          </div>
        </div>
      </div>

      {/* Invite Modal */}
      <InviteUserModal
        isOpen={isInviteModalOpen}
        onClose={() => setIsInviteModalOpen(false)}
        onSuccess={() => fetchUsers()}
      />

      {/* Edit Modal */}
      <EditUserModal
        user={editingUser}
        isOpen={Boolean(editingUser)}
        onClose={() => setEditingUser(null)}
        onSuccess={() => fetchUsers()}
      />
    </AppShell>
  );
}

export default function UserManagementPage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <UserManagementContent />
    </ProtectedRoute>
  );
}
