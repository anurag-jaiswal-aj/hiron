import { apiFetch, ResponseEnvelope } from "./api";

export interface NoteAuthorInfo {
  id: string;
  fullName: string;
}

export interface NoteData {
  id: string;
  candidateId: string;
  author: NoteAuthorInfo | null;
  jobId: string | null;
  content: string;
  isPrivate: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CreateNoteRequest {
  content: string;
  jobId?: string | null;
  isPrivate?: boolean;
}

export interface UpdateNoteRequest {
  content?: string | null;
  isPrivate?: boolean | null;
}

export const notesApi = {
  listCandidateNotes: (candidateId: string, jobId?: string) => {
    return apiFetch<ResponseEnvelope<NoteData[]>>(
      `/api/v1/candidates/${candidateId}/notes`,
      {
        params: jobId ? { jobId } : undefined,
      }
    ).then((res) => res.data);
  },

  createNote: (candidateId: string, request: CreateNoteRequest) => {
    return apiFetch<ResponseEnvelope<NoteData>>(
      `/api/v1/candidates/${candidateId}/notes`,
      {
        method: "POST",
        body: request,
      }
    ).then((res) => res.data);
  },

  updateNote: (candidateId: string, noteId: string, request: UpdateNoteRequest) => {
    return apiFetch<ResponseEnvelope<NoteData>>(
      `/api/v1/candidates/${candidateId}/notes/${noteId}`,
      {
        method: "PATCH",
        body: request,
      }
    ).then((res) => res.data);
  },

  deleteNote: (candidateId: string, noteId: string) => {
    return apiFetch<void>(
      `/api/v1/candidates/${candidateId}/notes/${noteId}`,
      {
        method: "DELETE",
      }
    );
  },
};
