"use client";

import React, { useEffect, useState } from "react";

import { ApiError, httpClient } from "../../lib/api";

export interface UserItem {
  id: string;
  email: string;
  fullName: string;
  role: string;
  isActive: boolean;
}

interface ResponseEnvelope<T> {
  data: T;
}

interface EditUserModalProps {
  user: UserItem | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function EditUserModal({
  user,
  isOpen,
  onClose,
  onSuccess,
}: EditUserModalProps): React.ReactElement | null {
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<"org_admin" | "recruiter" | "hiring_manager">("recruiter");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setFullName(user.fullName);
      const r = user.role.toLowerCase();
      if (r === "org_admin" || r === "recruiter" || r === "hiring_manager") {
        setRole(r);
      } else {
        setRole("recruiter");
      }
    }
  }, [user]);

  if (!isOpen || !user) {
    return null;
  }

  function handleClose(): void {
    setErrorMsg(null);
    setIsSubmitting(false);
    onClose();
  }

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setErrorMsg(null);

    const trimmedFullName = fullName.trim();
    if (!trimmedFullName) {
      setErrorMsg("Full name cannot be empty.");
      return;
    }

    setIsSubmitting(true);

    try {
      await httpClient.patch<ResponseEnvelope<UserItem>>(`/api/v1/users/${user?.id}`, {
        fullName: trimmedFullName,
        role,
      });

      handleClose();
      onSuccess();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to update user profile. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-modal-title"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
        padding: "1rem",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "480px",
          backgroundColor: "#0f172a",
          borderRadius: "16px",
          border: "1px solid #1e293b",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5)",
          padding: "1.75rem",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
          <div>
            <h2 id="edit-modal-title" style={{ margin: 0, fontSize: "1.25rem", fontWeight: 700, color: "#f8fafc" }}>
              Edit Team Member
            </h2>
            <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem", color: "#94a3b8" }}>
              Update profile details or role for {user.email}
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            style={{
              background: "none",
              border: "none",
              color: "#94a3b8",
              fontSize: "1.25rem",
              cursor: "pointer",
              padding: "0.25rem 0.5rem",
              borderRadius: "6px",
            }}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {errorMsg && (
          <div
            role="alert"
            style={{
              padding: "0.75rem 1rem",
              borderRadius: "8px",
              backgroundColor: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              color: "#fca5a5",
              fontSize: "0.875rem",
              marginBottom: "1.25rem",
            }}
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1.25rem" }}>
            <label
              htmlFor="edit-fullName"
              style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, color: "#cbd5e1", marginBottom: "0.375rem" }}
            >
              Full Name *
            </label>
            <input
              id="edit-fullName"
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={isSubmitting}
              style={{
                width: "100%",
                padding: "0.625rem 0.875rem",
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

          <div style={{ marginBottom: "1.75rem" }}>
            <label
              htmlFor="edit-role"
              style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, color: "#cbd5e1", marginBottom: "0.375rem" }}
            >
              Role *
            </label>
            <select
              id="edit-role"
              value={role}
              onChange={(e) => setRole(e.target.value as "org_admin" | "recruiter" | "hiring_manager")}
              disabled={isSubmitting}
              style={{
                width: "100%",
                padding: "0.625rem 0.875rem",
                borderRadius: "8px",
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                color: "#f8fafc",
                fontSize: "0.875rem",
                outline: "none",
                boxSizing: "border-box",
                cursor: "pointer",
              }}
            >
              <option value="recruiter">Recruiter</option>
              <option value="hiring_manager">Hiring Manager</option>
              <option value="org_admin">Org Admin</option>
            </select>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              style={{
                padding: "0.625rem 1.25rem",
                borderRadius: "8px",
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                color: "#f8fafc",
                fontSize: "0.875rem",
                fontWeight: 500,
                cursor: isSubmitting ? "not-allowed" : "pointer",
              }}
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                padding: "0.625rem 1.25rem",
                borderRadius: "8px",
                backgroundColor: "#4f46e5",
                border: "none",
                color: "#ffffff",
                fontSize: "0.875rem",
                fontWeight: 600,
                cursor: isSubmitting ? "not-allowed" : "pointer",
                opacity: isSubmitting ? 0.7 : 1,
              }}
            >
              {isSubmitting ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
