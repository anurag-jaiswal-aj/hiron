"use client";

import { useRouter } from "next/navigation";
import React, { useState } from "react";

import { SkillTagInput } from "../../../components/jobs/SkillTagInput";
import { AppShell } from "../../../components/layout/AppShell";
import { PageHeader } from "../../../components/layout/PageHeader";
import { ProtectedRoute } from "../../../components/ProtectedRoute";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { useAuth } from "../../../context/AuthContext";
import { ApiError, httpClient } from "../../../lib/api";

interface CreateCandidatePayload {
  fullName: string;
  email?: string;
  phone?: string;
  location?: string;
  linkedinUrl?: string;
  summary?: string;
  currentTitle?: string;
  currentCompany?: string;
  skills: string[];
  totalExperienceYears?: number;
  source: string;
}

interface ResponseEnvelope<T> {
  data: T;
}

function CreateCandidateContent(): React.ReactElement {
  const { user } = useAuth();
  const router = useRouter();

  const canCreate = user?.role === "org_admin" || user?.role === "recruiter";

  // Form State
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [location, setLocation] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [currentTitle, setCurrentTitle] = useState("");
  const [currentCompany, setCurrentCompany] = useState("");
  const [totalExperienceYears, setTotalExperienceYears] = useState<number | "">("");
  const [skills, setSkills] = useState<string[]>([]);
  const [summary, setSummary] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!canCreate) return;

    if (!fullName.trim()) {
      setErrorMsg("Candidate name is required.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const payload: CreateCandidatePayload = {
        fullName: fullName.trim(),
        source: "upload",
        skills,
      };

      if (email.trim()) payload.email = email.trim();
      if (phone.trim()) payload.phone = phone.trim();
      if (location.trim()) payload.location = location.trim();
      if (linkedinUrl.trim()) payload.linkedinUrl = linkedinUrl.trim();
      if (currentTitle.trim()) payload.currentTitle = currentTitle.trim();
      if (currentCompany.trim()) payload.currentCompany = currentCompany.trim();
      if (summary.trim()) payload.summary = summary.trim();
      if (typeof totalExperienceYears === "number") {
        payload.totalExperienceYears = totalExperienceYears;
      }

      const res = await httpClient.post<ResponseEnvelope<{ id: string }>>("/api/v1/candidates", payload);

      if (res && res.data && res.data.id) {
        router.push(`/candidates/${res.data.id}`);
      } else {
        setErrorMsg("Failed to create candidate (missing ID in response).");
        setIsSubmitting(false);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setErrorMsg("A candidate with this email already exists in your organization.");
        } else {
          setErrorMsg(err.message);
        }
      } else {
        setErrorMsg("An unexpected error occurred. Please try again.");
      }
      setIsSubmitting(false);
    }
  };

  if (!canCreate) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
        <h2 style={{ color: "var(--text-primary)" }}>Access Denied</h2>
        <p>You do not have permission to create candidates.</p>
        <Button variant="secondary" onClick={() => router.push("/candidates")} style={{ marginTop: "1rem" }}>
          Return to Candidates List
        </Button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", paddingBottom: "4rem" }}>
      <PageHeader
        title="Add New Candidate"
        subtitle="Manually create a candidate profile"
        backHref="/candidates"
        backLabel="Back to Candidates"
      />

      {errorMsg && (
        <div
          style={{
            padding: "1rem",
            backgroundColor: "var(--bg-error-subtle, #ffebee)",
            color: "var(--text-error, #c62828)",
            borderRadius: "var(--radius-md)",
            marginBottom: "1.5rem",
            fontSize: "0.875rem",
            border: "1px solid var(--border-error, #ffcdd2)",
          }}
        >
          {errorMsg}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        style={{
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          padding: "2rem",
          display: "flex",
          flexDirection: "column",
          gap: "1.5rem",
        }}
      >
        {/* Basic Info */}
        <div>
          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem", color: "var(--text-primary)" }}>
            Basic Information
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <label htmlFor="fullName" style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                Full Name *
              </label>
              <Input
                id="fullName"
                placeholder="e.g. Jane Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <label htmlFor="email" style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                Email Address
              </label>
              <Input
                id="email"
                type="email"
                placeholder="jane@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <label htmlFor="phone" style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                Phone Number
              </label>
              <Input
                id="phone"
                placeholder="+1 (555) 000-0000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <label htmlFor="location" style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                Location
              </label>
              <Input
                id="location"
                placeholder="e.g. San Francisco, CA"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", gridColumn: "1 / -1" }}>
              <label htmlFor="linkedinUrl" style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                LinkedIn URL
              </label>
              <Input
                id="linkedinUrl"
                placeholder="https://linkedin.com/in/janedoe"
                value={linkedinUrl}
                onChange={(e) => setLinkedinUrl(e.target.value)}
              />
            </div>
          </div>
        </div>

        <hr style={{ border: 0, borderTop: "1px solid var(--border-subtle)", margin: "0.5rem 0" }} />

        {/* Experience & Skills */}
        <div>
          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem", color: "var(--text-primary)" }}>
            Professional Background
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <label htmlFor="currentTitle" style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                Current Title
              </label>
              <Input
                id="currentTitle"
                placeholder="e.g. Senior Software Engineer"
                value={currentTitle}
                onChange={(e) => setCurrentTitle(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <label htmlFor="currentCompany" style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                Current Company
              </label>
              <Input
                id="currentCompany"
                placeholder="e.g. Acme Corp"
                value={currentCompany}
                onChange={(e) => setCurrentCompany(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <label htmlFor="totalExperience" style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                Total Years of Experience
              </label>
              <Input
                id="totalExperience"
                type="number"
                min="0"
                max="70"
                placeholder="e.g. 5"
                value={totalExperienceYears}
                onChange={(e) => {
                  const val = e.target.value;
                  setTotalExperienceYears(val === "" ? "" : parseInt(val, 10));
                }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", gridColumn: "1 / -1" }}>
              <label htmlFor="skills" style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                Skills
              </label>
              <div id="skills">
                <SkillTagInput
                  skills={skills}
                  onChange={setSkills}
                  placeholder="Type a skill and press Enter..."
                />
              </div>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", gridColumn: "1 / -1" }}>
              <label htmlFor="summary" style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                Summary / Bio
              </label>
              <textarea
                id="summary"
                placeholder="Brief professional summary..."
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                rows={4}
                style={{
                  width: "100%",
                  padding: "0.75rem 1rem",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-input)",
                  backgroundColor: "var(--bg-surface)",
                  color: "var(--text-primary)",
                  fontSize: "0.875rem",
                  fontFamily: "inherit",
                  resize: "vertical",
                  outline: "none",
                }}
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem", marginTop: "1rem" }}>
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push("/candidates")}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting || !fullName.trim()}>
            {isSubmitting ? "Creating..." : "Create Candidate"}
          </Button>
        </div>
      </form>
    </div>
  );
}

export default function CreateCandidatePage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <AppShell>
        <CreateCandidateContent />
      </AppShell>
    </ProtectedRoute>
  );
}
