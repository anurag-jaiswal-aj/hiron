"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";

import { AppShell } from "../../../components/layout/AppShell";
import { PageHeader } from "../../../components/layout/PageHeader";
import { ProtectedRoute } from "../../../components/ProtectedRoute";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { useAuth } from "../../../context/AuthContext";
import { httpClient, ResponseEnvelope } from "../../../lib/api";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

interface JobListItem {
  id: string;
  title: string;
}

interface PaginatedData<T> {
  data: T[];
}

interface FileUploadState {
  id: string;
  file: File;
  status: "pending" | "uploading" | "parsing" | "parsed" | "failed";
  error?: string;
  progress?: number;
  resumeId?: string;
  candidateId?: string;
}

function UploadContent(): React.ReactElement {
  const router = useRouter();
  const { user } = useAuth();
  
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [filesState, setFilesState] = useState<FileUploadState[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    // Redirect if hiring manager
    if (user?.role === "hiring_manager") {
      router.replace("/candidates");
    }
  }, [user, router]);

  useEffect(() => {
    async function fetchJobs(): Promise<void> {
      try {
        const res = await httpClient.get<ResponseEnvelope<PaginatedData<JobListItem>>>(
          "/api/v1/jobs?limit=100&status=open"
        );
        if (res?.data?.data) {
          setJobs(res.data.data);
        }
      } catch (err) {
        // ignore for now
      }
    }
    fetchJobs();
  }, []);

  const onDrop = useCallback((acceptedFiles: File[], fileRejections: import("react-dropzone").FileRejection[]) => {
    const newFiles: FileUploadState[] = acceptedFiles.map((file) => ({
      id: Math.random().toString(36).substring(7),
      file,
      status: "pending",
    }));

    const rejectedFiles: FileUploadState[] = fileRejections.map((rejection) => {
      let error = "Unsupported file type";
      if (rejection.errors.some((e) => e.code === "file-too-large")) {
        error = "File exceeds 10 MB limit";
      }
      return {
        id: Math.random().toString(36).substring(7),
        file: rejection.file,
        status: "failed",
        error,
      };
    });

    setFilesState((prev) => [...prev, ...newFiles, ...rejectedFiles].slice(0, 500));
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    maxSize: MAX_FILE_SIZE,
    maxFiles: 500,
  });

  const uploadSingle = async (fileState: FileUploadState): Promise<void> => {
    try {
      const formData = new FormData();
      formData.append("file", fileState.file);
      if (selectedJobId) {
        formData.append("jobId", selectedJobId);
      }

      setFilesState((prev) =>
        prev.map((f) => (f.id === fileState.id ? { ...f, status: "uploading" } : f))
      );

      const res = await httpClient.post<ResponseEnvelope<{ resumeId: string; candidateId: string }>>("/api/v1/resumes/upload", formData);
      
      const resumeId = res.data?.resumeId;
      const candidateId = res.data?.candidateId;

      setFilesState((prev) =>
        prev.map((f) =>
          f.id === fileState.id ? { ...f, status: "parsing", resumeId, candidateId } : f
        )
      );
    } catch (err: unknown) {
      console.error("API error:", err);
      const errorMsg = err instanceof Error ? err.message : "Upload failed";
      setFilesState((prev) =>
        prev.map((f) =>
          f.id === fileState.id
            ? { ...f, status: "failed", error: errorMsg }
            : f
        )
      );
    }
  };

  const uploadBulk = async (pendingFiles: FileUploadState[]): Promise<void> => {
    try {
      const formData = new FormData();
      pendingFiles.forEach((fileState) => {
        formData.append("files", fileState.file);
      });
      if (selectedJobId) {
        formData.append("jobId", selectedJobId);
      }

      setFilesState((prev) =>
        prev.map((f) => (pendingFiles.some((p) => p.id === f.id) ? { ...f, status: "uploading" } : f))
      );

      await httpClient.post<ResponseEnvelope<{ resumeIds: string[] }>>("/api/v1/resumes/bulk-upload", formData);
      
      // Bulk polling is more complex, just mark them as parsing for now
      setFilesState((prev) =>
        prev.map((f) => (pendingFiles.some((p) => p.id === f.id) ? { ...f, status: "parsing" } : f))
      );
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Bulk upload failed";
      setFilesState((prev) =>
        prev.map((f) => (pendingFiles.some((p) => p.id === f.id) ? { ...f, status: "failed", error: errorMsg } : f))
      );
    }
  };

  const handleUpload = async (): Promise<void> => {
    const pendingFiles = filesState.filter((f) => f.status === "pending");
    if (pendingFiles.length === 0) return;

    setIsUploading(true);

    if (pendingFiles.length === 1) {
      await uploadSingle(pendingFiles[0]);
    } else {
      await uploadBulk(pendingFiles);
    }

    setIsUploading(false);
  };

  const filesStateRef = React.useRef(filesState);
  useEffect(() => {
    filesStateRef.current = filesState;
  }, [filesState]);

  useEffect(() => {
    const intervalId = setInterval(async () => {
      const currentFiles = filesStateRef.current;
      const parsingFiles = currentFiles.filter((f) => f.status === "parsing" && f.resumeId);
      
      if (parsingFiles.length === 0) return;

      // Poll each parsing file
      await Promise.allSettled(
        parsingFiles.map(async (file) => {
          try {
            const res = await httpClient.get<
              ResponseEnvelope<{ status: string; parseError?: string; parseConfidence?: number }>
            >(`/api/v1/resumes/${file.resumeId}/status`);
            const status = res.data?.status;
            
            if (status === "parsed" || status === "failed") {
              setFilesState((prev) =>
                prev.map((f) =>
                  f.id === file.id
                    ? { ...f, status: status as FileUploadState["status"], error: res.data?.parseError }
                    : f
                )
              );
            }
          } catch (err) {
            // Transient error - keep polling next time
          }
        })
      );
    }, 2000);

    return () => clearInterval(intervalId);
  }, []);

  const retryParse = async (fileState: FileUploadState): Promise<void> => {
    if (!fileState.resumeId) return;
    try {
      setFilesState((prev) =>
        prev.map((f) => (f.id === fileState.id ? { ...f, status: "parsing", error: undefined } : f))
      );
      await httpClient.post(`/api/v1/resumes/${fileState.resumeId}/retry`, {});
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Retry failed";
      setFilesState((prev) =>
        prev.map((f) => (f.id === fileState.id ? { ...f, status: "failed", error: errorMsg } : f))
      );
    }
  };

  const removeFile = (id: string): void => {
    setFilesState((prev) => prev.filter((f) => f.id !== id));
  };

  if (!user || user.role === "hiring_manager") {
    return null;
  }

  const jobOptions = [
    { value: "", label: "None (Global pool)" },
    ...jobs.map((j) => ({ value: j.id, label: j.title })),
  ];

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", paddingBottom: "4rem" }}>
      <PageHeader
        title="Upload Resumes"
        subtitle="Upload single or bulk resumes. Optionally associate with a job."
        backHref="/candidates"
        backLabel="Candidates"
      />

      <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
        <div style={{ maxWidth: "400px" }}>
          <Select
            label="Associate with job (optional)"
            id="jobSelect"
            options={jobOptions}
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
          />
        </div>

        <div
          {...getRootProps()}
          style={{
            border: `2px dashed ${isDragActive ? "var(--text-primary)" : "var(--border-subtle)"}`,
            borderRadius: "var(--radius-lg)",
            padding: "4rem 2rem",
            textAlign: "center",
            cursor: "pointer",
            backgroundColor: isDragActive ? "var(--bg-surface-secondary)" : "transparent",
            transition: "all 0.2s ease",
          }}
        >
          <input {...getInputProps()} data-testid="resume-upload-input" />
          <p style={{ margin: "0 0 0.5rem 0", fontSize: "1.125rem", fontWeight: 500, color: "var(--text-primary)" }}>
            Drag & drop resumes here
          </p>
          <p style={{ margin: "0 0 1rem 0", fontSize: "0.875rem", color: "var(--text-secondary)" }}>
            or click to browse
          </p>
          <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
            PDF, DOCX, TXT • Max 10 MB per file
          </p>
          <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
            Up to 500 files for bulk upload
          </p>
        </div>

        {filesState.length > 0 && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h3 style={{ margin: 0, fontSize: "1.125rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Uploaded Files
              </h3>
              <Button
                type="button"
                variant="primary"
                onClick={handleUpload}
                disabled={isUploading || filesState.every((f) => f.status !== "pending")}
              >
                {isUploading ? "Uploading..." : "Start Upload"}
              </Button>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {filesState.map((f) => (
                <div
                  key={f.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "0.75rem 1rem",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--bg-surface-secondary)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                    {f.status === "parsed" && <span style={{ color: "var(--color-success)" }}>✓</span>}
                    {f.status === "failed" && <span style={{ color: "var(--color-danger)" }}>✕</span>}
                    {(f.status === "uploading" || f.status === "parsing") && <span>⟳</span>}
                    {f.status === "pending" && <span>•</span>}
                    
                    <div>
                      <div style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--text-primary)" }}>
                        {f.file.name}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                        {f.status === "pending" && "Ready to upload"}
                        {f.status === "uploading" && "Uploading..."}
                        {f.status === "parsing" && "Parsing..."}
                        {f.status === "parsed" && "Parsed"}
                        {f.status === "failed" && <span style={{ color: "var(--color-danger)" }}>{f.error}</span>}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
                    {f.status === "parsed" && f.candidateId && (
                      <Link
                        href={`/candidates/${f.candidateId}`}
                        style={{ fontSize: "0.875rem", color: "var(--text-primary)", textDecoration: "underline" }}
                      >
                        View candidate
                      </Link>
                    )}

                    {f.status === "failed" && f.resumeId && (
                      <button
                        onClick={() => retryParse(f)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--color-primary)",
                          cursor: "pointer",
                          fontSize: "0.875rem",
                          textDecoration: "underline"
                        }}
                      >
                        Retry
                      </button>
                    )}

                    {(f.status === "pending" || f.status === "failed") && (
                      <button
                        onClick={() => removeFile(f.id)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--text-secondary)",
                          cursor: "pointer",
                          fontSize: "0.875rem",
                        }}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ResumeUploadPage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <AppShell>
        <UploadContent />
      </AppShell>
    </ProtectedRoute>
  );
}

