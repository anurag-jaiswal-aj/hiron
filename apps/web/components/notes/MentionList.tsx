import React, { forwardRef, useEffect, useImperativeHandle, useState } from "react";
import { UserResponse } from "../../lib/users-api";

interface MentionListProps {
  items: UserResponse[];
  command: (props: { id: string; label: string }) => void;
}

export const MentionList = forwardRef((props: MentionListProps, ref) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  const selectItem = (index: number): void => {
    const item = props.items[index];
    if (item) {
      props.command({ id: item.id, label: item.fullName });
    }
  };

  const upHandler = (): void => {
    setSelectedIndex((selectedIndex + props.items.length - 1) % props.items.length);
  };

  const downHandler = (): void => {
    setSelectedIndex((selectedIndex + 1) % props.items.length);
  };

  const enterHandler = (): void => {
    selectItem(selectedIndex);
  };

  useEffect(() => setSelectedIndex(0), [props.items]);

  useImperativeHandle(ref, () => ({
    onKeyDown: ({ event }: { event: KeyboardEvent }) => {
      if (event.key === "ArrowUp") {
        upHandler();
        return true;
      }
      if (event.key === "ArrowDown") {
        downHandler();
        return true;
      }
      if (event.key === "Enter") {
        enterHandler();
        return true;
      }
      return false;
    },
  }));

  if (props.items.length === 0) {
    return (
      <div style={{
        backgroundColor: "var(--bg-surface-secondary)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: "0.5rem 1rem",
        fontSize: "0.875rem",
        color: "var(--text-muted)",
      }}>
        No users found
      </div>
    );
  }

  return (
    <div style={{
      backgroundColor: "var(--bg-surface-secondary)",
      border: "1px solid var(--border-subtle)",
      borderRadius: "var(--radius-md)",
      overflow: "hidden",
      padding: "0.25rem",
      minWidth: "200px",
      boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
    }}>
      {props.items.map((item, index) => {
        const isSelected = index === selectedIndex;
        return (
          <button
            key={item.id}
            onClick={() => selectItem(index)}
            style={{
              width: "100%",
              textAlign: "left",
              padding: "0.5rem 0.75rem",
              fontSize: "0.875rem",
              background: isSelected ? "var(--bg-hover)" : "transparent",
              color: isSelected ? "var(--text-primary)" : "var(--text-secondary)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              transition: "all 0.1s ease",
            }}
          >
            {item.fullName}
          </button>
        );
      })}
    </div>
  );
});

MentionList.displayName = "MentionList";
