import { httpClient } from "./api";

export interface CandidateSearchResultPayload {
  id: string;
  fullName: string;
  currentTitle: string | null;
  skills: string[];
  totalExperienceYears: number | null;
}

export interface CandidateSearchResultItem {
  candidate: CandidateSearchResultPayload;
  relevanceScore: number;
  highlights: string[];
}

export interface SearchPaginationData {
  hasMore: boolean;
  totalCount: number;
}

export interface SemanticSearchCandidatesResponse {
  data: CandidateSearchResultItem[];
  pagination: SearchPaginationData;
}

export interface SearchCandidateFilters {
  experienceMin?: number;
  experienceMax?: number;
  location?: string;
  skills?: string[];
  q?: string;
}

export interface SearchCandidatesRequest {
  query: string;
  filters?: SearchCandidateFilters;
  limit?: number;
}

export const searchApi = {
  /**
   * Search candidates using semantic search via pgvector.
   */
  async searchCandidates(request: SearchCandidatesRequest): Promise<SemanticSearchCandidatesResponse> {
    return httpClient.post<SemanticSearchCandidatesResponse>("/api/v1/search/candidates", request);
  },
};
