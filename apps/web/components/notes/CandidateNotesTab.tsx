import React, { useEffect, useState, useCallback } from "react";
import DOMPurify from "dompurify";
import { notesApi, NoteData } from "../../lib/notes-api";
import { useAuth } from "../../context/AuthContext";
import { EmptyState } from "../ui/EmptyState";
import { Button } from "../ui/Button";
import dynamic from "next/dynamic";

const NoteEditor = dynamic(
  () => import("./NoteEditor").then((mod) => mod.NoteEditor),
  {
    ssr: false,
    loading: () => (
      <div style={{
        minHeight: "120px",
        padding: "0.75rem",
        background: "var(--bg-surface-secondary)",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border-subtle)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "var(--text-muted)"
      }}>
        Loading editor...
      </div>
    )
  }
);

interface CandidateNotesTabProps {
  candidateId: string;
}

export function CandidateNotesTab({ candidateId }: CandidateNotesTabProps): React.ReactElement {
  const { user } = useAuth();
  const [notes, setNotes] = useState<NoteData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isAdding, setIsAdding] = useState(false);
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchNotes = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await notesApi.listCandidateNotes(candidateId);
      setNotes(data);
    } catch (err: unknown) {
      const error = err as Error;
      setError(error.message || "Failed to load notes.");
    } finally {
      setIsLoading(false);
    }
  }, [candidateId]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const handleAddNote = async (content: string, isPrivate: boolean): Promise<void> => {
    setIsSubmitting(true);
    try {
      await notesApi.createNote(candidateId, { content, isPrivate });
      await fetchNotes();
      setIsAdding(false);
    } catch (err: unknown) {
      const error = err as Error;
      console.error(error);
      alert(error.message || "Failed to create note");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditNote = async (noteId: string, content: string, isPrivate: boolean): Promise<void> => {
    setIsSubmitting(true);
    try {
      await notesApi.updateNote(candidateId, noteId, { content, isPrivate });
      await fetchNotes();
      setEditingNoteId(null);
    } catch (err: unknown) {
      const error = err as Error;
      console.error(error);
      alert(error.message || "Failed to update note");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteNote = async (noteId: string): Promise<void> => {
    if (!confirm("Are you sure you want to delete this note?")) {
      return;
    }

    try {
      await notesApi.deleteNote(candidateId, noteId);
      await fetchNotes();
    } catch (err: unknown) {
      const error = err as Error;
      console.error(error);
      alert(error.message || "Failed to delete note");
    }
  };

  if (isLoading) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-secondary)" }}>
        Loading notes...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <p style={{ color: "#F87171", marginBottom: "1rem" }}>{error}</p>
        <Button onClick={fetchNotes}>Retry</Button>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Add Note Section */}
      {!isAdding && !editingNoteId && (
        <button
          type="button"
          onClick={() => setIsAdding(true)}
          style={{
            width: "100%",
            textAlign: "left",
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            padding: "1rem",
            display: "flex",
            alignItems: "center",
            gap: "1rem",
            cursor: "text",
            boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
          }}
        >
          <div style={{
            width: "32px",
            height: "32px",
            borderRadius: "50%",
            backgroundColor: "var(--bg-hover)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--text-primary)",
            fontWeight: 600,
            flexShrink: 0,
            fontSize: "0.875rem",
          }}>
            {user?.fullName.charAt(0).toUpperCase()}
          </div>
          <div style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Add a note... (use @ to mention)
          </div>
        </button>
      )}

      {isAdding && (
        <div style={{
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-lg)",
          padding: "1rem",
          boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
        }}>
          <NoteEditor
            onSubmit={handleAddNote}
            onCancel={() => setIsAdding(false)}
            isSubmitting={isSubmitting}
          />
        </div>
      )}

      {/* Notes Feed */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {notes.length === 0 ? (
          <EmptyState
            title="No notes on this candidate"
            description="Add a note to start a conversation or share thoughts with your team."
          />
        ) : (
          notes.map((note) => (
            <div key={note.id} style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-lg)",
              padding: "1rem",
              boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
            }}>
              {editingNoteId === note.id ? (
                <NoteEditor
                  initialContent={note.content}
                  defaultIsPrivate={note.isPrivate}
                  onSubmit={(content, isPrivate) => handleEditNote(note.id, content, isPrivate)}
                  onCancel={() => setEditingNoteId(null)}
                  isSubmitting={isSubmitting}
                />
              ) : (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                      <span style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.875rem" }}>
                        {note.author?.fullName || "Unknown User"}
                      </span>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {new Date(note.createdAt).toLocaleString()}
                      </span>
                      {note.isPrivate && (
                        <span style={{
                          padding: "0.125rem 0.375rem",
                          borderRadius: "var(--radius-sm)",
                          fontSize: "0.75rem",
                          backgroundColor: "var(--bg-hover)",
                          color: "var(--text-secondary)",
                          border: "1px solid var(--border-subtle)",
                        }}>
                          Private
                        </span>
                      )}
                    </div>
                    {/* Only author or admin can edit/delete, but we'll show buttons based on frontend simple role matching and let backend enforce */}
                    {user && (user.role === "org_admin" || user.id === note.author?.id) && (
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <button
                          onClick={() => setEditingNoteId(note.id)}
                          style={{
                            background: "none", border: "none", cursor: "pointer",
                            fontSize: "0.75rem", color: "var(--text-muted)",
                          }}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteNote(note.id)}
                          style={{
                            background: "none", border: "none", cursor: "pointer",
                            fontSize: "0.75rem", color: "#F87171",
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                  <div
                    className="tiptap-content"
                    style={{
                      fontSize: "0.875rem",
                      lineHeight: "1.5",
                      color: "var(--text-primary)",
                      whiteSpace: "pre-wrap",
                    }}
                    dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(note.content) }}
                  />
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
