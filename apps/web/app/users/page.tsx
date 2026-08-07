"use client";

import Link from "next/link";
import React, { useCallback, useEffect, useState } from "react";

import { ProtectedRoute } from "../../components/ProtectedRoute";
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
  createdAt: string;
}

interface ResponseEnvelope<T> {
  data: T;
}

function UserManagementContent(): React.ReactElement {
  const { user, logout } = useAuth();
  const isAdmin = user?.role === "org_admin";

  const [users, setUsers] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

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
        `/api/v1/users?${params.toString()}`
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
        setErrorMsg("Failed to load team members. Please check network connection and try again.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [roleFilter, statusFilter, page]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  async function handleToggleStatus(targetUser: UserItem): Promise<void> {
    if (!isAdmin) return;

    const action = targetUser.isActive ? "deactivate" : "reactivate";
    const confirmMessage = targetUser.isActive
      ? `Are you sure you want to deactivate ${targetUser.fullName || targetUser.email}? They will lose access to the platform.`
      : `Reactivate account for ${targetUser.fullName || targetUser.email}?`;

    if (!window.confirm(confirmMessage)) {
      return;
    }

    setActionLoadingId(targetUser.id);
    setErrorMsg(null);

    try {
      await httpClient.post<ResponseEnvelope<UserItem>>(
        `/api/v1/users/${targetUser.id}/${action}`
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

  return (
    <main
      style={{
        minHeight: "100vh",
        backgroundColor: "#090d16",
        color: "#f8fafc",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      {/* Navigation Header */}
      <header
        style={{
          backgroundColor: "#0f172a",
          borderBottom: "1px solid #1e293b",
          padding: "1rem 2rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "2rem" }}>
          <span style={{ fontSize: "1.25rem", fontWeight: 700, color: "#a5b4fc" }}>Hiron</span>
          <nav style={{ display: "flex", gap: "1rem" }}>
            <Link
              href="/"
              style={{
                color: "#94a3b8",
                textDecoration: "none",
                fontSize: "0.875rem",
                fontWeight: 500,
                padding: "0.375rem 0.75rem",
                borderRadius: "6px",
              }}
            >
              Dashboard
            </Link>
            <Link
              href="/users"
              style={{
                color: "#f8fafc",
                backgroundColor: "#1e293b",
                textDecoration: "none",
                fontSize: "0.875rem",
                fontWeight: 600,
                padding: "0.375rem 0.75rem",
                borderRadius: "6px",
              }}
            >
              Team Management
            </Link>
          </nav>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <span style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
            {user?.fullName || user?.email} ({user?.role})
          </span>
          <button
            type="button"
            onClick={() => logout()}
            style={{
              padding: "0.4rem 0.875rem",
              borderRadius: "6px",
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              color: "#cbd5e1",
              fontSize: "0.8125rem",
              cursor: "pointer",
            }}
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Body */}
      <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "2rem 1rem" }}>
        {/* Title & Actions Row */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.75rem", fontWeight: 700 }}>Team Members</h1>
            <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem", color: "#94a3b8" }}>
              Manage user accounts, roles, and administrative permissions.
            </p>
          </div>

          {isAdmin && (
            <button
              type="button"
              onClick={() => setIsInviteModalOpen(true)}
              style={{
                padding: "0.625rem 1.25rem",
                borderRadius: "8px",
                backgroundColor: "#4f46e5",
                border: "none",
                color: "#ffffff",
                fontSize: "0.875rem",
                fontWeight: 600,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                boxShadow: "0 4px 6px -1px rgba(79, 70, 229, 0.25)",
              }}
            >
              + Invite Team Member
            </button>
          )}
        </div>

        {/* Global Error Banner */}
        {errorMsg && (
          <div
            role="alert"
            style={{
              padding: "0.875rem 1.25rem",
              borderRadius: "10px",
              backgroundColor: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.25)",
              color: "#fca5a5",
              fontSize: "0.875rem",
              marginBottom: "1.5rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>{errorMsg}</span>
            <button
              type="button"
              onClick={fetchUsers}
              style={{
                background: "none",
                border: "1px solid #fca5a5",
                color: "#fca5a5",
                padding: "0.25rem 0.75rem",
                borderRadius: "6px",
                fontSize: "0.75rem",
                cursor: "pointer",
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Filter Controls Bar */}
        <div
          style={{
            backgroundColor: "#0f172a",
            borderRadius: "12px",
            border: "1px solid #1e293b",
            padding: "1rem",
            marginBottom: "1.5rem",
            display: "flex",
            flexWrap: "wrap",
            gap: "1rem",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            <div>
              <label
                htmlFor="filter-role"
                style={{ display: "block", fontSize: "0.75rem", color: "#94a3b8", marginBottom: "0.25rem" }}
              >
                Role Filter
              </label>
              <select
                id="filter-role"
                value={roleFilter}
                onChange={(e) => {
                  setRoleFilter(e.target.value);
                  setPage(1);
                }}
                style={{
                  padding: "0.4rem 0.75rem",
                  borderRadius: "6px",
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  color: "#f8fafc",
                  fontSize: "0.875rem",
                  outline: "none",
                }}
              >
                <option value="">All Roles</option>
                <option value="org_admin">Org Admin</option>
                <option value="recruiter">Recruiter</option>
                <option value="hiring_manager">Hiring Manager</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="filter-status"
                style={{ display: "block", fontSize: "0.75rem", color: "#94a3b8", marginBottom: "0.25rem" }}
              >
                Status Filter
              </label>
              <select
                id="filter-status"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                style={{
                  padding: "0.4rem 0.75rem",
                  borderRadius: "6px",
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  color: "#f8fafc",
                  fontSize: "0.875rem",
                  outline: "none",
                }}
              >
                <option value="">All Statuses</option>
                <option value="true">Active Only</option>
                <option value="false">Inactive Only</option>
              </select>
            </div>
          </div>

          <div style={{ fontSize: "0.875rem", color: "#94a3b8" }}>
            Showing {users.length} member{users.length !== 1 ? "s" : ""}
          </div>
        </div>

        {/* Data Table / Content */}
        <div
          style={{
            backgroundColor: "#0f172a",
            borderRadius: "16px",
            border: "1px solid #1e293b",
            overflow: "hidden",
          }}
        >
          {isLoading ? (
            <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  border: "3px solid #334155",
                  borderTopColor: "#6366f1",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                  margin: "0 auto 1rem",
                }}
              />
              Loading team members...
            </div>
          ) : users.length === 0 ? (
            <div style={{ padding: "4rem 2rem", textAlign: "center" }}>
              <p style={{ margin: 0, fontSize: "1.125rem", color: "#e2e8f0", fontWeight: 600 }}>
                No team members found
              </p>
              <p style={{ margin: "0.5rem 0 0", fontSize: "0.875rem", color: "#94a3b8" }}>
                {roleFilter || statusFilter
                  ? "No users match your selected filter criteria."
                  : "Invite your first team member to start collaborating."}
              </p>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  textAlign: "left",
                  fontSize: "0.875rem",
                }}
              >
                <thead>
                  <tr
                    style={{
                      backgroundColor: "#1e293b",
                      borderBottom: "1px solid #334155",
                      color: "#94a3b8",
                      fontWeight: 600,
                    }}
                  >
                    <th style={{ padding: "0.875rem 1.25rem" }}>Name</th>
                    <th style={{ padding: "0.875rem 1.25rem" }}>Email</th>
                    <th style={{ padding: "0.875rem 1.25rem" }}>Role</th>
                    <th style={{ padding: "0.875rem 1.25rem" }}>Status</th>
                    {isAdmin && <th style={{ padding: "0.875rem 1.25rem", textAlign: "right" }}>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr
                      key={u.id}
                      style={{
                        borderBottom: "1px solid #1e293b",
                        transition: "background-color 0.15s ease",
                      }}
                    >
                      <td style={{ padding: "1rem 1.25rem", fontWeight: 600, color: "#f8fafc" }}>
                        {u.fullName || "—"}
                      </td>
                      <td style={{ padding: "1rem 1.25rem", color: "#cbd5e1" }}>{u.email}</td>
                      <td style={{ padding: "1rem 1.25rem" }}>
                        <RoleBadge role={u.role} />
                      </td>
                      <td style={{ padding: "1rem 1.25rem" }}>
                        <UserStatusBadge isActive={u.isActive} />
                      </td>

                      {isAdmin && (
                        <td style={{ padding: "1rem 1.25rem", textAlign: "right" }}>
                          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
                            <button
                              type="button"
                              onClick={() => setEditingUser(u)}
                              disabled={actionLoadingId === u.id}
                              style={{
                                padding: "0.3125rem 0.625rem",
                                borderRadius: "6px",
                                backgroundColor: "#1e293b",
                                border: "1px solid #334155",
                                color: "#38bdf8",
                                fontSize: "0.75rem",
                                fontWeight: 500,
                                cursor: "pointer",
                              }}
                            >
                              Edit Role
                            </button>

                            <button
                              type="button"
                              onClick={() => handleToggleStatus(u)}
                              disabled={actionLoadingId === u.id}
                              style={{
                                padding: "0.3125rem 0.625rem",
                                borderRadius: "6px",
                                backgroundColor: u.isActive
                                  ? "rgba(239, 68, 68, 0.1)"
                                  : "rgba(34, 197, 94, 0.1)",
                                border: `1px solid ${
                                  u.isActive ? "rgba(239, 68, 68, 0.3)" : "rgba(34, 197, 94, 0.3)"
                                }`,
                                color: u.isActive ? "#fca5a5" : "#86efac",
                                fontSize: "0.75rem",
                                fontWeight: 500,
                                cursor: actionLoadingId === u.id ? "not-allowed" : "pointer",
                                opacity: actionLoadingId === u.id ? 0.6 : 1,
                              }}
                            >
                              {actionLoadingId === u.id
                                ? "Processing..."
                                : u.isActive
                                ? "Deactivate"
                                : "Reactivate"}
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          <div
            style={{
              padding: "1rem 1.25rem",
              backgroundColor: "#0f172a",
              borderTop: "1px solid #1e293b",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <button
              type="button"
              disabled={page <= 1 || isLoading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              style={{
                padding: "0.375rem 0.75rem",
                borderRadius: "6px",
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                color: page <= 1 ? "#64748b" : "#f8fafc",
                fontSize: "0.8125rem",
                cursor: page <= 1 || isLoading ? "not-allowed" : "pointer",
              }}
            >
              ← Previous
            </button>

            <span style={{ fontSize: "0.8125rem", color: "#94a3b8" }}>Page {page}</span>

            <button
              type="button"
              disabled={users.length < limit || isLoading}
              onClick={() => setPage((p) => p + 1)}
              style={{
                padding: "0.375rem 0.75rem",
                borderRadius: "6px",
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                color: users.length < limit ? "#64748b" : "#f8fafc",
                fontSize: "0.8125rem",
                cursor: users.length < limit || isLoading ? "not-allowed" : "pointer",
              }}
            >
              Next →
            </button>
          </div>
        </div>
      </div>

      {/* Invite Modal */}
      <InviteUserModal
        isOpen={isInviteModalOpen}
        onClose={() => setIsInviteModalOpen(false)}
        onSuccess={fetchUsers}
      />

      {/* Edit Modal */}
      <EditUserModal
        user={editingUser}
        isOpen={Boolean(editingUser)}
        onClose={() => setEditingUser(null)}
        onSuccess={fetchUsers}
      />
    </main>
  );
}

export default function UserManagementPage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <UserManagementContent />
    </ProtectedRoute>
  );
}
