"use client";

import React, { useEffect, useState } from "react";

import { ApiError, httpClient } from "../../lib/api";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Modal } from "../ui/Modal";
import { Select } from "../ui/Select";

export interface UserToEdit {
  id: string;
  email: string;
  fullName: string;
  role: string;
  isActive: boolean;
}

interface UserResponse {
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
  user: UserToEdit | null;
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
  const [role, setRole] = useState("recruiter");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setFullName(user.fullName || "");
      setRole(user.role || "recruiter");
    }
  }, [user]);

  if (!isOpen || !user) return null;

  function handleClose(): void {
    setErrorMsg(null);
    setIsSubmitting(false);
    onClose();
  }

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setErrorMsg(null);

    if (!fullName.trim()) {
      setErrorMsg("Full name is required.");
      return;
    }

    setIsSubmitting(true);

    try {
      await httpClient.patch<ResponseEnvelope<UserResponse>>(`/api/v1/users/${user!.id}`, {
        fullName: fullName.trim(),
        role,
      });

      handleClose();
      onSuccess();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to update user details. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Edit Team Member"
      actions={
        <>
          <Button type="button" variant="secondary" onClick={handleClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" form="edit-user-form" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save Changes"}
          </Button>
        </>
      }
    >
      {errorMsg && (
        <div
          style={{
            backgroundColor: "#451A03",
            border: "1px solid #78350F",
            color: "#FDE68A",
            padding: "0.75rem 1rem",
            borderRadius: "var(--radius-md)",
            fontSize: "0.875rem",
            marginBottom: "1.25rem",
          }}
        >
          {errorMsg}
        </div>
      )}

      <form id="edit-user-form" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <Input
          id="edit-email"
          type="email"
          label="Email Address (Immutable)"
          value={user.email}
          disabled
          style={{ opacity: 0.6 }}
        />

        <Input
          id="edit-fullname"
          type="text"
          required
          label="Full Name *"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          disabled={isSubmitting}
        />

        <Select
          id="edit-role"
          label="Role *"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          disabled={isSubmitting}
          options={[
            { value: "recruiter", label: "Recruiter" },
            { value: "org_admin", label: "Org Admin" },
            { value: "hiring_manager", label: "Hiring Manager" },
          ]}
        />
      </form>
    </Modal>
  );
}
