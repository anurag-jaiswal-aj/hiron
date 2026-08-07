"use client";

import React, { useState } from "react";

interface SkillTagInputProps {
  id?: string;
  skills: string[];
  onChange: (skills: string[]) => void;
  placeholder?: string;
  maxSkills?: number;
}

export function SkillTagInput({
  id,
  skills,
  onChange,
  placeholder = "Add a skill (press Enter or comma)",
  maxSkills = 50,
}: SkillTagInputProps): React.ReactElement {
  const [inputValue, setInputValue] = useState("");

  function addSkill(value: string): void {
    const trimmed = value.trim();
    if (!trimmed) return;

    if (skills.length >= maxSkills) return;

    // Avoid duplicates (case-insensitive check)
    const exists = skills.some((s) => s.toLowerCase() === trimmed.toLowerCase());
    if (!exists) {
      onChange([...skills, trimmed]);
    }
    setInputValue("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>): void {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addSkill(inputValue);
    } else if (e.key === "Backspace" && !inputValue && skills.length > 0) {
      // Remove last tag on backspace if input is empty
      e.preventDefault();
      onChange(skills.slice(0, -1));
    }
  }

  function handleRemove(indexToRemove: number): void {
    onChange(skills.filter((_, idx) => idx !== indexToRemove));
  }

  return (
    <div
      style={{
        backgroundColor: "var(--bg-surface-secondary)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: "0.5rem 0.75rem",
        display: "flex",
        flexWrap: "wrap",
        gap: "0.5rem",
        alignItems: "center",
        minHeight: "44px",
      }}
    >
      {/* Skill Tag Chips */}
      {skills.map((skill, index) => (
        <span
          key={`${skill}-${index}`}
          style={{
            backgroundColor: "var(--bg-hover)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-subtle)",
            fontSize: "0.8125rem",
            fontWeight: 500,
            padding: "0.25rem 0.625rem",
            borderRadius: "var(--radius-sm)",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.375rem",
          }}
        >
          {skill}
          <button
            type="button"
            onClick={() => handleRemove(index)}
            aria-label={`Remove ${skill}`}
            style={{
              backgroundColor: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: 0,
              fontSize: "0.875rem",
              lineHeight: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            ×
          </button>
        </span>
      ))}

      {/* Text Input */}
      {skills.length < maxSkills && (
        <input
          id={id}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => {
            if (inputValue.trim()) addSkill(inputValue);
          }}
          placeholder={skills.length === 0 ? placeholder : "+ Add skill"}
          style={{
            flex: 1,
            minWidth: "140px",
            backgroundColor: "transparent",
            border: "none",
            color: "var(--text-primary)",
            fontSize: "0.875rem",
            outline: "none",
          }}
        />
      )}
    </div>
  );
}
