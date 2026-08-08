import { httpClient } from "./api";
import { SearchCandidateFilters } from "./search-api";

export interface CreateSavedSearchRequest {
  name: string;
  queryText: string;
  filters?: SearchCandidateFilters;
  isShared?: boolean;
}

export interface SavedSearchResponse {
  id: string;
  name: string;
  queryText: string;
  filters: SearchCandidateFilters | null;
  isShared: boolean;
  tenantId: string;
  userId: string;
  createdAt: string;
  updatedAt: string;
}

export const savedSearchesApi = {
  /**
   * Save a semantic search query for reuse
   */
  async createSavedSearch(request: CreateSavedSearchRequest): Promise<{ data: SavedSearchResponse }> {
    return httpClient.post<{ data: SavedSearchResponse }>("/api/v1/saved-searches", request);
  },
};
