import React, { useEffect } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Mention from "@tiptap/extension-mention";
import { mentionSuggestion } from "./mentionSuggestion";
import { Button } from "../ui/Button";

interface NoteEditorProps {
  initialContent?: string;
  isSubmitting?: boolean;
  onSubmit: (content: string, isPrivate: boolean) => void;
  onCancel?: () => void;
  defaultIsPrivate?: boolean;
}

export function NoteEditor({
  initialContent = "",
  isSubmitting = false,
  onSubmit,
  onCancel,
  defaultIsPrivate = false,
}: NoteEditorProps): React.ReactElement | null {
  const [isPrivate, setIsPrivate] = React.useState(defaultIsPrivate);
  const [isEmpty, setIsEmpty] = React.useState(!initialContent);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Mention.configure({
        HTMLAttributes: {
          class: "mention",
          style: "color: #3b82f6; font-weight: 600; background: rgba(59, 130, 246, 0.1); padding: 0.1rem 0.3rem; border-radius: 4px;",
        },
        suggestion: mentionSuggestion,
      }),
    ],
    content: initialContent,
    editorProps: {
      attributes: {
        style:
          "min-height: 120px; outline: none; padding: 0.75rem; color: var(--text-primary); font-size: 0.875rem; line-height: 1.5; background: var(--bg-surface-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); font-family: inherit;",
      },
    },
    onUpdate: ({ editor }) => {
      setIsEmpty(editor.isEmpty);
    },
  });

  const handleSubmit = (): void => {
    if (editor && !editor.isEmpty) {
      onSubmit(editor.getHTML(), isPrivate);
    }
  };

  useEffect(() => {
    if (editor && initialContent !== editor.getHTML()) {
      editor.commands.setContent(initialContent);
    }
  }, [initialContent, editor]);

  if (!editor) {
    return null;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ position: "relative" }}>
        <EditorContent editor={editor} />
        {/* Tiptap injects its own wrapper, we styled the inner editable div via editorProps */}
      </div>

      <div style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "1rem",
      }}>
        <label style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          fontSize: "0.875rem",
          color: "var(--text-secondary)",
          cursor: "pointer",
        }}>
          <input
            type="checkbox"
            checked={isPrivate}
            onChange={(e) => setIsPrivate(e.target.checked)}
            style={{ cursor: "pointer" }}
          />
          <span>Private Note (only visible to org admins)</span>
        </label>

        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          {onCancel && (
            <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
              Cancel
            </Button>
          )}
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || isEmpty}
          >
            {isSubmitting ? "Saving..." : "Save Note"}
          </Button>
        </div>
      </div>
    </div>
  );
}
