"use client";

import React, { useState, useEffect } from "react";
import { Button } from "../ui/Button";
import { Select } from "../ui/Select";
import { Input } from "../ui/Input";
import { AuditListParams } from "../../lib/audit-api";

interface AuditFiltersProps {
  initialFilters: AuditListParams;
  onFiltersChange: (filters: AuditListParams) => void;
}

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const ACTION_OPTIONS = [
  { value: "", label: "All Actions" },
  { value: "created", label: "Created" },
  { value: "updated", label: "Updated" },
  { value: "archived", label: "Archived" },
  { value: "deleted", label: "Deleted" },
  { value: "login_success", label: "Login Success" },
  { value: "login_failed", label: "Login Failed" },
  { value: "logout", label: "Logout" },
  { value: "stage_changed", label: "Stage Changed" },
  { value: "scored", label: "Scored" },
  { value: "shortlisted", label: "Shortlisted" },
  { value: "rejected", label: "Rejected" },
];

const ENTITY_TYPE_OPTIONS = [
  { value: "", label: "All Entities" },
  { value: "job", label: "Job" },
  { value: "candidate", label: "Candidate" },
  { value: "job_candidate", label: "Job Candidate" },
  { value: "user", label: "User" },
  { value: "tenant", label: "Tenant" },
  { value: "tenant_settings", label: "Tenant Settings" },
  { value: "resume", label: "Resume" },
  { value: "score", label: "Score" },
  { value: "note", label: "Note" },
];

export function AuditFilters({ initialFilters, onFiltersChange }: AuditFiltersProps): React.ReactElement {
  const [filters, setFilters] = useState<AuditListParams>({ ...initialFilters, cursor: undefined });
  const [debouncedFilters, setDebouncedFilters] = useState<AuditListParams>(filters);
  const [errors, setErrors] = useState<{ entityId?: string; actorId?: string }>({});

  // Debounce typed text fields (actorId, entityId)
  useEffect(() => {
    const handler = setTimeout(() => {
      const newErrors: { entityId?: string; actorId?: string } = {};
      const sanitized: AuditListParams = { ...filters };

      if (filters.entityId) {
        if (!UUID_REGEX.test(filters.entityId)) {
          newErrors.entityId = "Invalid UUID format";
          sanitized.entityId = undefined;
        }
      }

      if (filters.actorId) {
        if (!UUID_REGEX.test(filters.actorId)) {
          newErrors.actorId = "Invalid UUID format";
          sanitized.actorId = undefined;
        }
      }

      setErrors(newErrors);
      setDebouncedFilters(sanitized);
    }, 400);
    return () => clearTimeout(handler);
  }, [filters]);

  // When debounced filters change, notify parent
  useEffect(() => {
    onFiltersChange(debouncedFilters);
  }, [debouncedFilters, onFiltersChange]);

  const handleChange = (key: keyof AuditListParams, value: string): void => {
    setFilters((prev) => ({
      ...prev,
      [key]: value || undefined,
    }));
  };

  const handleClear = (): void => {
    setFilters({});
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: "1rem",
        alignItems: "end",
        backgroundColor: "var(--bg-surface-secondary)",
        padding: "1.25rem",
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--border-subtle)",
        marginBottom: "1.5rem",
      }}
    >
      <Select
        id="audit-filter-action"
        label="Action"
        options={ACTION_OPTIONS}
        value={filters.action || ""}
        onChange={(e) => handleChange("action", e.target.value)}
      />

      <Select
        id="audit-filter-entity-type"
        label="Entity Type"
        options={ENTITY_TYPE_OPTIONS}
        value={filters.entityType || ""}
        onChange={(e) => handleChange("entityType", e.target.value)}
      />

      <Input
        id="audit-filter-entity-id"
        label="Entity ID"
        placeholder="UUID..."
        value={filters.entityId || ""}
        onChange={(e) => handleChange("entityId", e.target.value)}
        error={errors.entityId}
      />

      <Input
        id="audit-filter-actor-id"
        label="Actor ID"
        placeholder="UUID..."
        value={filters.actorId || ""}
        onChange={(e) => handleChange("actorId", e.target.value)}
        error={errors.actorId}
      />

      <Input
        id="audit-filter-start-date"
        type="date"
        label="Start Date"
        value={filters.startDate || ""}
        onChange={(e) => handleChange("startDate", e.target.value)}
      />

      <Input
        id="audit-filter-end-date"
        type="date"
        label="End Date"
        value={filters.endDate || ""}
        onChange={(e) => handleChange("endDate", e.target.value)}
      />

      <div style={{ display: "flex", alignSelf: "end" }}>
        <Button variant="secondary" onClick={handleClear} style={{ width: "100%" }}>
          Clear Filters
        </Button>
      </div>
    </div>
  );
}
