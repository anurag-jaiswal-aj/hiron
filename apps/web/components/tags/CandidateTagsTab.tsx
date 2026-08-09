"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { tagsApi, TagData } from "../../lib/tags-api";
import { TagInput } from "./TagInput";

interface CandidateTagsTabProps {
  candidateId: string;
}

export function CandidateTagsTab({ candidateId }: CandidateTagsTabProps): React.ReactElement {
  const { user } = useAuth();
  const canManageTags = user?.role === "org_admin" || user?.role === "recruiter";

  const [tags, setTags] = useState<TagData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [removingTagId, setRemovingTagId] = useState<string | null>(null);

  const fetchTags = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await tagsApi.listCandidateTags(candidateId);
      setTags(data);
    } catch {
      setErrorMsg("Failed to load tags.");
    } finally {
      setIsLoading(false);
    }
  }, [candidateId]);

  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  const handleTagAdded = (newTag: TagData): void => {
    setTags((prev) => [...prev, newTag]);
  };

  const handleRemoveTag = async (tagId: string): Promise<void> => {
    if (removingTagId) return;
    setRemovingTagId(tagId);
    try {
      await tagsApi.removeTag(candidateId, tagId);
      setTags((prev) => prev.filter((t) => t.id !== tagId));
    } catch {
      setErrorMsg("Failed to remove tag.");
    } finally {
      setRemovingTagId(null);
    }
  };

  if (isLoading) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.875rem" }}>
        Loading tags…
      </div>
    );
  }

  if (errorMsg) {
    return (
      <div
        style={{
          backgroundColor: "#451A03",
          border: "1px solid #78350F",
          color: "#FDE68A",
          padding: "0.875rem 1.25rem",
          borderRadius: "var(--radius-md)",
          fontSize: "0.875rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span>{errorMsg}</span>
        <button
          type="button"
          onClick={fetchTags}
          style={{
            background: "transparent",
            border: "1px solid #78350F",
            color: "#FDE68A",
            borderRadius: "var(--radius-sm)",
            padding: "0.25rem 0.75rem",
            cursor: "pointer",
            fontSize: "0.8125rem",
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Add Tag Input — only for authorized roles */}
      {canManageTags && (
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            padding: "1.25rem",
          }}
        >
          <h3
            style={{
              fontSize: "0.875rem",
              fontWeight: 700,
              color: "var(--text-primary)",
              margin: "0 0 0.75rem 0",
            }}
          >
            Add Tag
          </h3>
          <TagInput
            candidateId={candidateId}
            existingTagNames={tags.map((t) => t.tagName)}
            onTagAdded={handleTagAdded}
          />
        </div>
      )}

      {/* Tags Display */}
      <div
        style={{
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          padding: "1.25rem",
        }}
      >
        <h3
          style={{
            fontSize: "0.875rem",
            fontWeight: 700,
            color: "var(--text-primary)",
            margin: "0 0 0.75rem 0",
          }}
        >
          Tags ({tags.length})
        </h3>

        {tags.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.8125rem", margin: 0 }}>
            No tags have been applied to this candidate yet.
          </p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {tags.map((tag) => (
              <span
                key={tag.id}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.375rem",
                  padding: "0.25rem 0.625rem",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.8125rem",
                  fontWeight: 500,
                  backgroundColor: "var(--bg-hover)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-strong)",
                }}
              >
                {tag.tagName}
                {canManageTags && (
                  <button
                    type="button"
                    onClick={() => handleRemoveTag(tag.id)}
                    disabled={removingTagId === tag.id}
                    aria-label={`Remove tag ${tag.tagName}`}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: removingTagId === tag.id ? "wait" : "pointer",
                      padding: "0",
                      fontSize: "0.875rem",
                      lineHeight: 1,
                      display: "inline-flex",
                      alignItems: "center",
                      opacity: removingTagId === tag.id ? 0.5 : 1,
                    }}
                  >
                    ×
                  </button>
                )}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
