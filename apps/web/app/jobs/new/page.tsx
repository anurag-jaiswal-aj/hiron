"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useState } from "react";

import { SkillTagInput } from "../../../components/jobs/SkillTagInput";
import { AppShell } from "../../../components/layout/AppShell";
import { PageHeader } from "../../../components/layout/PageHeader";
import { ProtectedRoute } from "../../../components/ProtectedRoute";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { useAuth } from "../../../context/AuthContext";
import { ApiError, httpClient } from "../../../lib/api";

interface CreateJobPayload {
  title: string;
  description: string;
  department?: string;
  location?: string;
  employmentType?: string;
  experienceYearsMin?: number;
  experienceYearsMax?: number;
  requiredSkills?: string[];
  preferredSkills?: string[];
}

interface ResponseEnvelope<T> {
  data: T;
}

function CreateJobContent(): React.ReactElement {
  const { user } = useAuth();
  const router = useRouter();

  const canCreate = user?.role === "org_admin" || user?.role === "recruiter";

  // Form State
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("Engineering");
  const [customDepartment, setCustomDepartment] = useState("");
  const [location, setLocation] = useState("");
  const [employmentType, setEmploymentType] = useState("full_time");
  const [experienceYearsMin, setExperienceYearsMin] = useState<number | "">("");
  const [experienceYearsMax, setExperienceYearsMax] = useState<number | "">("");
  const [description, setDescription] = useState("");
  const [requiredSkills, setRequiredSkills] = useState<string[]>([]);
  const [preferredSkills, setPreferredSkills] = useState<string[]>([]);

  // UI / Async State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  if (!canCreate) {
    return (
      <AppShell>
        <div style={{ maxWidth: "600px", margin: "4rem auto", textAlign: "center" }}>
          <h2 style={{ color: "var(--text-primary)", fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.5rem" }}>
            Access Denied
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
            Only Organization Admins and Recruiters can create new job descriptions.
          </p>
          <Link href="/jobs" style={{ textDecoration: "none" }}>
            <Button type="button" variant="secondary">
              ← Return to Jobs List
            </Button>
          </Link>
        </div>
      </AppShell>
    );
  }

  const effectiveDepartment =
    department === "Other" ? customDepartment.trim() : department.trim();

  function validateForm(): boolean {
    setValidationError(null);

    if (!title.trim()) {
      setValidationError("Job title is required.");
      return false;
    }
    if (title.trim().length > 200) {
      setValidationError("Job title must be 200 characters or less.");
      return false;
    }
    if (!description.trim()) {
      setValidationError("Job description is required.");
      return false;
    }
    if (description.trim().length > 10000) {
      setValidationError("Job description must be 10,000 characters or less.");
      return false;
    }

    const minYears = experienceYearsMin === "" ? undefined : Number(experienceYearsMin);
    const maxYears = experienceYearsMax === "" ? undefined : Number(experienceYearsMax);

    if (minYears !== undefined && maxYears !== undefined && maxYears < minYears) {
      setValidationError("Maximum experience years must be greater than or equal to minimum experience years.");
      return false;
    }

    return true;
  }

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();

    if (!validateForm()) return;

    setIsSubmitting(true);
    setServerError(null);

    const payload: CreateJobPayload = {
      title: title.trim(),
      description: description.trim(),
      department: effectiveDepartment || undefined,
      location: location.trim() || undefined,
      employmentType: employmentType || undefined,
      experienceYearsMin: experienceYearsMin === "" ? undefined : Number(experienceYearsMin),
      experienceYearsMax: experienceYearsMax === "" ? undefined : Number(experienceYearsMax),
      requiredSkills: requiredSkills.length > 0 ? requiredSkills : undefined,
      preferredSkills: preferredSkills.length > 0 ? preferredSkills : undefined,
    };

    try {
      await httpClient.post<ResponseEnvelope<object>>("/api/v1/jobs", payload);
      router.push("/jobs");
    } catch (err) {
      if (err instanceof ApiError) {
        setServerError(err.message);
      } else {
        setServerError("Failed to create job description. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Create New Job"
        subtitle="Define position parameters, skill requirements, and sourcing attributes."
        backHref="/jobs"
        backLabel="Back to Jobs"
      />

      {/* Validation / Server Error Banner */}
      {(validationError || serverError) && (
        <div
          style={{
            backgroundColor: "#451A03",
            border: "1px solid #78350F",
            color: "#FDE68A",
            padding: "0.875rem 1.25rem",
            borderRadius: "var(--radius-md)",
            marginBottom: "1.5rem",
            fontSize: "0.875rem",
          }}
        >
          {validationError || serverError}
        </div>
      )}

      {/* Grid: Form Left, Preview Right */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: "2rem",
          alignItems: "start",
        }}
      >
        {/* Form Container */}
        <form
          onSubmit={handleSubmit}
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            padding: "1.75rem",
            display: "flex",
            flexDirection: "column",
            gap: "1.25rem",
          }}
        >
          <Input
            id="job-title-input"
            type="text"
            required
            label="Job Title *"
            placeholder="e.g. Senior Backend Engineer"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
          />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <Select
                id="job-department-select"
                label="Department"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                options={[
                  { value: "Engineering", label: "Engineering" },
                  { value: "Product", label: "Product" },
                  { value: "Design", label: "Design" },
                  { value: "Sales", label: "Sales" },
                  { value: "Marketing", label: "Marketing" },
                  { value: "Operations", label: "Operations" },
                  { value: "HR", label: "HR" },
                  { value: "Other", label: "Other..." },
                ]}
              />
              {department === "Other" && (
                <Input
                  placeholder="Enter custom department"
                  value={customDepartment}
                  onChange={(e) => setCustomDepartment(e.target.value)}
                  style={{ marginTop: "0.5rem" }}
                />
              )}
            </div>

            <Select
              id="job-employment-select"
              label="Employment Type"
              value={employmentType}
              onChange={(e) => setEmploymentType(e.target.value)}
              options={[
                { value: "full_time", label: "Full-time" },
                { value: "part_time", label: "Part-time" },
                { value: "contract", label: "Contract" },
                { value: "internship", label: "Internship" },
              ]}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <Input
              id="job-location-input"
              type="text"
              label="Location"
              placeholder="e.g. Remote / San Francisco, CA"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              maxLength={200}
            />

            <div>
              <label htmlFor="job-exp-min-input" style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.375rem" }}>
                Experience (Years)
              </label>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <Input
                  id="job-exp-min-input"
                  type="number"
                  min={0}
                  max={50}
                  placeholder="Min"
                  value={experienceYearsMin}
                  onChange={(e) =>
                    setExperienceYearsMin(e.target.value === "" ? "" : Number(e.target.value))
                  }
                />
                <span style={{ color: "var(--text-muted)" }}>–</span>
                <Input
                  id="job-exp-max-input"
                  type="number"
                  min={0}
                  max={50}
                  placeholder="Max"
                  value={experienceYearsMax}
                  onChange={(e) =>
                    setExperienceYearsMax(e.target.value === "" ? "" : Number(e.target.value))
                  }
                />
              </div>
            </div>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.375rem" }}>
              <label htmlFor="job-description-textarea" style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-secondary)" }}>
                Job Description *
              </label>
              <span style={{ fontSize: "0.75rem", color: description.length > 9500 ? "#FDE68A" : "var(--text-muted)" }}>
                {description.length}/10000
              </span>
            </div>
            <textarea
              id="job-description-textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={10000}
              rows={6}
              required
              style={{
                width: "100%",
                backgroundColor: "var(--bg-surface-secondary)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                color: "var(--text-primary)",
                padding: "0.625rem 0.75rem",
                fontSize: "0.875rem",
                outline: "none",
                resize: "vertical",
              }}
            />
          </div>

          <div>
            <label htmlFor="job-req-skills-input" style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.375rem" }}>
              Required Skills
            </label>
            <SkillTagInput
              id="job-req-skills-input"
              skills={requiredSkills}
              onChange={setRequiredSkills}
              placeholder="Add skill (press Enter)"
            />
          </div>

          <div>
            <label htmlFor="job-pref-skills-input" style={{ display: "block", fontSize: "0.875rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.375rem" }}>
              Preferred Skills
            </label>
            <SkillTagInput
              id="job-pref-skills-input"
              skills={preferredSkills}
              onChange={setPreferredSkills}
              placeholder="Add skill (press Enter)"
            />
          </div>

          <div style={{ display: "flex", gap: "1rem", marginTop: "1rem", justifyContent: "flex-end" }}>
            <Link href="/jobs" style={{ textDecoration: "none" }}>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </Link>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create Job"}
            </Button>
          </div>
        </form>

        {/* Live Preview Container */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            padding: "1.75rem",
            position: "sticky",
            top: "2rem",
          }}
        >
          <div
            style={{
              fontSize: "0.75rem",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--text-muted)",
              fontWeight: 700,
              marginBottom: "1rem",
            }}
          >
            Live Preview
          </div>

          <div
            style={{
              backgroundColor: "var(--bg-surface-secondary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "1.25rem",
            }}
          >
            <h3 style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary)", margin: "0 0 0.5rem 0" }}>
              {title.trim() || "Job Title Preview"}
            </h3>

            <div style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: "1rem", display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              <span>{effectiveDepartment || "Department"}</span>
              <span>•</span>
              <span>{location.trim() || "Location"}</span>
              <span>•</span>
              <span>{employmentType.replace("_", "-")}</span>
              {(experienceYearsMin !== "" || experienceYearsMax !== "") && (
                <>
                  <span>•</span>
                  <span>
                    {experienceYearsMin !== "" ? experienceYearsMin : "0"}–
                    {experienceYearsMax !== "" ? experienceYearsMax : "+"} yrs exp
                  </span>
                </>
              )}
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.25rem" }}>
                Description:
              </div>
              <p
                style={{
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  maxHeight: "120px",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {description.trim() || "Description preview..."}
              </p>
            </div>

            {requiredSkills.length > 0 && (
              <div style={{ marginBottom: "0.75rem" }}>
                <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.375rem" }}>
                  Required Skills:
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                  {requiredSkills.map((skill, idx) => (
                    <span
                      key={idx}
                      style={{
                        backgroundColor: "var(--bg-hover)",
                        color: "var(--text-primary)",
                        border: "1px solid var(--border-subtle)",
                        fontSize: "0.75rem",
                        padding: "0.125rem 0.5rem",
                        borderRadius: "var(--radius-sm)",
                        fontWeight: 500,
                      }}
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {preferredSkills.length > 0 && (
              <div>
                <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.375rem" }}>
                  Preferred Skills:
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                  {preferredSkills.map((skill, idx) => (
                    <span
                      key={idx}
                      style={{
                        backgroundColor: "var(--bg-surface)",
                        border: "1px solid var(--border-subtle)",
                        color: "var(--text-muted)",
                        fontSize: "0.75rem",
                        padding: "0.125rem 0.5rem",
                        borderRadius: "var(--radius-sm)",
                        fontWeight: 500,
                      }}
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default function CreateJobPage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <CreateJobContent />
    </ProtectedRoute>
  );
}
