import { apiFetch, ResponseEnvelope } from "./api";

export interface TagUserPayload {
  id: string;
  fullName: string;
}

export interface TagData {
  id: string;
  tagName: string;
  taggedBy: TagUserPayload | null;
  createdAt: string;
}

export interface AddTagRequest {
  tagName: string;
}

export const tagsApi = {
  listTenantTags: () => {
    return apiFetch<ResponseEnvelope<string[]>>(`/api/v1/tags`).then(
      (res) => res.data
    );
  },

  listCandidateTags: (candidateId: string) => {
    return apiFetch<ResponseEnvelope<TagData[]>>(
      `/api/v1/candidates/${candidateId}/tags`
    ).then((res) => res.data);
  },

  addTag: (candidateId: string, request: AddTagRequest) => {
    return apiFetch<ResponseEnvelope<TagData>>(
      `/api/v1/candidates/${candidateId}/tags`,
      {
        method: "POST",
        body: request,
      }
    ).then((res) => res.data);
  },

  removeTag: (candidateId: string, tagId: string) => {
    return apiFetch<void>(`/api/v1/candidates/${candidateId}/tags/${tagId}`, {
      method: "DELETE",
    });
  },
};
