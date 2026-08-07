"use client";

import React, { useState } from "react";

import { ApiError, httpClient } from "../../lib/api";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Modal } from "../ui/Modal";
import { Select } from "../ui/Select";

interface UserResponse {
  id: string;
  email: string;
  fullName: string;
  role: string;
}

interface ResponseEnvelope<T> {
  data: T;
}

interface InviteUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function InviteUserModal({
  isOpen,
  onClose,
  onSuccess,
}: InviteUserModalProps): React.ReactElement | null {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<"org_admin" | "recruiter" | "hiring_manager">("recruiter");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  function handleClose(): void {
    setEmail("");
    setFullName("");
    setRole("recruiter");
    setErrorMsg(null);
    setIsSubmitting(false);
    onClose();
  }

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setErrorMsg(null);

    if (!email.trim()) {
      setErrorMsg("Email is required.");
      return;
    }
    if (!fullName.trim()) {
      setErrorMsg("Full name is required.");
      return;
    }

    setIsSubmitting(true);

    try {
      await httpClient.post<ResponseEnvelope<UserResponse>>("/api/v1/users/invite", {
        email: email.trim(),
        fullName: fullName.trim(),
        role,
      });

      handleClose();
      onSuccess();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setErrorMsg("A user with this email address already exists in your organization.");
        } else {
          setErrorMsg(err.message);
        }
      } else {
        setErrorMsg("Failed to send invitation. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Invite Team Member"
      actions={
        <>
          <Button type="button" variant="secondary" onClick={handleClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" form="invite-user-form" disabled={isSubmitting}>
            {isSubmitting ? "Inviting..." : "Send Invitation"}
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

      <form id="invite-user-form" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <Input
          id="invite-email"
          type="email"
          required
          label="Email Address *"
          placeholder="colleague@acme.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isSubmitting}
        />

        <Input
          id="invite-fullname"
          type="text"
          required
          label="Full Name *"
          placeholder="Jane Doe"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          disabled={isSubmitting}
        />

        <Select
          id="invite-role"
          label="Role *"
          value={role}
          onChange={(e) => setRole(e.target.value as "org_admin" | "recruiter" | "hiring_manager")}
          disabled={isSubmitting}
          options={[
            { value: "recruiter", label: "Recruiter (Full Job & Candidate Access)" },
            { value: "org_admin", label: "Org Admin (Full Access & Team Management)" },
            { value: "hiring_manager", label: "Hiring Manager (Read-Only Access)" },
          ]}
        />
      </form>
    </Modal>
  );
}
