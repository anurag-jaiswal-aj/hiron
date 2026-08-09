"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { tagsApi, TagData } from "../../lib/tags-api";

interface TagInputProps {
  candidateId: string;
  existingTagNames: string[];
  onTagAdded: (tag: TagData) => void;
}

export function TagInput({ candidateId, existingTagNames, onTagAdded }: TagInputProps): React.ReactElement {
  const [inputValue, setInputValue] = useState("");
  const [tenantTags, setTenantTags] = useState<string[]>([]);
  const [tenantTagsLoaded, setTenantTagsLoaded] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [highlightIndex, setHighlightIndex] = useState(-1);

  const wrapperRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load tenant tags once on focus
  const loadTenantTags = useCallback(async () => {
    if (tenantTagsLoaded) return;
    try {
      const tags = await tagsApi.listTenantTags();
      setTenantTags(tags);
      setTenantTagsLoaded(true);
    } catch {
      // Silently fail — autocomplete just won't show suggestions
    }
  }, [tenantTagsLoaded]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent): void => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Filter suggestions: match input, exclude tags already on candidate
  const normalizedInput = inputValue.trim().toLowerCase();
  const suggestions = tenantTags.filter(
    (tag) =>
      tag.toLowerCase().includes(normalizedInput) &&
      !existingTagNames.includes(tag)
  );
  const filteredSuggestions = normalizedInput.length > 0 ? suggestions : [];

  const handleSubmit = async (tagName: string): Promise<void> => {
    const normalized = tagName.trim().toLowerCase();
    if (!normalized) return;

    // Check for duplicates client-side
    if (existingTagNames.includes(normalized)) {
      setErrorMsg("This tag is already applied to this candidate.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const newTag = await tagsApi.addTag(candidateId, { tagName: normalized });
      onTagAdded(newTag);
      setInputValue("");
      setShowDropdown(false);
      setHighlightIndex(-1);

      // Refresh tenant tags to include the new tag
      if (!tenantTags.includes(normalized)) {
        setTenantTags((prev) => [...prev, normalized]);
      }
    } catch (err: unknown) {
      const apiErr = err as { status?: number; message?: string };
      if (apiErr.status === 409) {
        setErrorMsg("This tag is already applied to this candidate.");
      } else {
        setErrorMsg(apiErr.message || "Failed to add tag.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIndex((prev) =>
        prev < filteredSuggestions.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIndex((prev) => (prev > 0 ? prev - 1 : -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (highlightIndex >= 0 && highlightIndex < filteredSuggestions.length) {
        handleSubmit(filteredSuggestions[highlightIndex]);
      } else if (normalizedInput) {
        handleSubmit(normalizedInput);
      }
    } else if (e.key === "Escape") {
      setShowDropdown(false);
      setHighlightIndex(-1);
    }
  };

  return (
    <div ref={wrapperRef} style={{ position: "relative" }}>
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
        <div style={{ flex: 1, position: "relative" }}>
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            placeholder="Type a tag name…"
            aria-label="Tag name input"
            disabled={isSubmitting}
            onChange={(e) => {
              setInputValue(e.target.value);
              setShowDropdown(true);
              setHighlightIndex(-1);
              setErrorMsg(null);
            }}
            onFocus={() => {
              loadTenantTags();
              if (normalizedInput.length > 0) {
                setShowDropdown(true);
              }
            }}
            onKeyDown={handleKeyDown}
            style={{
              width: "100%",
              backgroundColor: "var(--bg-surface-secondary)",
              border: errorMsg ? "1px solid #7F1D1D" : "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              color: "var(--text-primary)",
              padding: "0.625rem 0.75rem",
              fontSize: "0.875rem",
              outline: "none",
              transition: "border-color 0.15s ease",
              boxSizing: "border-box",
            }}
          />

          {/* Autocomplete dropdown */}
          {showDropdown && filteredSuggestions.length > 0 && (
            <div
              role="listbox"
              style={{
                position: "absolute",
                top: "100%",
                left: 0,
                right: 0,
                marginTop: "0.25rem",
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                maxHeight: "200px",
                overflowY: "auto",
                zIndex: 100,
              }}
            >
              {filteredSuggestions.map((suggestion, idx) => (
                <div
                  key={suggestion}
                  role="option"
                  tabIndex={-1}
                  aria-selected={idx === highlightIndex}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    handleSubmit(suggestion);
                  }}
                  onMouseEnter={() => setHighlightIndex(idx)}
                  style={{
                    padding: "0.5rem 0.75rem",
                    fontSize: "0.8125rem",
                    color: "var(--text-primary)",
                    cursor: "pointer",
                    backgroundColor:
                      idx === highlightIndex
                        ? "var(--bg-hover)"
                        : "transparent",
                    transition: "background-color 0.1s ease",
                  }}
                >
                  {suggestion}
                </div>
              ))}
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={() => handleSubmit(inputValue)}
          disabled={isSubmitting || !normalizedInput}
          style={{
            padding: "0.625rem 1rem",
            fontSize: "0.875rem",
            fontWeight: 600,
            borderRadius: "var(--radius-md)",
            border: "none",
            backgroundColor:
              isSubmitting || !normalizedInput
                ? "var(--bg-surface-secondary)"
                : "var(--text-primary)",
            color:
              isSubmitting || !normalizedInput
                ? "var(--text-muted)"
                : "var(--bg-app)",
            cursor: isSubmitting || !normalizedInput ? "not-allowed" : "pointer",
            whiteSpace: "nowrap",
            transition: "background-color 0.15s ease, color 0.15s ease",
            flexShrink: 0,
          }}
        >
          {isSubmitting ? "Adding…" : "Add"}
        </button>
      </div>

      {errorMsg && (
        <div
          style={{
            fontSize: "0.8125rem",
            color: "#F87171",
            marginTop: "0.375rem",
          }}
        >
          {errorMsg}
        </div>
      )}
    </div>
  );
}
