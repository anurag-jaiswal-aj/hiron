"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { EmptyState } from "../../components/ui/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { useRouter } from "next/navigation";
import { ApiError } from "../../lib/api";
import { searchApi, CandidateSearchResultItem, SearchCandidateFilters } from "../../lib/search-api";
import { savedSearchesApi } from "../../lib/saved-searches-api";
import { CandidateSearchResultCard } from "../../components/candidates/CandidateSearchResultCard";

// SVG Icons
const SparklesIcon = ({ className }: { className?: string }): React.ReactElement => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
    <path d="M5 3v4" />
    <path d="M19 17v4" />
    <path d="M3 5h4" />
    <path d="M17 19h4" />
  </svg>
);

const SearchIcon = ({ className }: { className?: string }): React.ReactElement => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.3-4.3" />
  </svg>
);

const XIcon = ({ className }: { className?: string }): React.ReactElement => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <path d="M18 6 6 18" />
    <path d="m6 6 12 12" />
  </svg>
);

interface ActiveFilter {
  id: string;
  type: "skills" | "location" | "experience";
  label: string;
  value: string;
}

function SemanticSearchContent(): React.ReactElement {
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user && user.role === "hiring_manager") {
      router.replace("/");
    }
  }, [user, router]);

  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>([]);

  // Search Results State
  const [results, setResults] = useState<CandidateSearchResultItem[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [searchTime, setSearchTime] = useState<number | null>(null);

  // Modal State
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [saveSearchName, setSaveSearchName] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSearch = async (e?: React.FormEvent): Promise<void> => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsLoading(true);
    setErrorMsg(null);
    setSaveSuccess(false);

    const startTime = performance.now();

    // Map filters for API
    const apiFilters: SearchCandidateFilters = {};
    activeFilters.forEach((f) => {
      if (f.type === "experience") {
        const minStr = f.value.replace(/[^0-9]/g, "");
        if (minStr) apiFilters.experienceMin = parseInt(minStr, 10);
      }
      if (f.type === "location") apiFilters.location = f.value;
      if (f.type === "skills") {
        if (!apiFilters.skills) apiFilters.skills = [];
        apiFilters.skills.push(f.value);
      }
    });

    try {
      const response = await searchApi.searchCandidates({
        query: searchQuery,
        filters: Object.keys(apiFilters).length > 0 ? apiFilters : undefined,
        limit: 20,
      });

      setResults(response.data);
      const endTime = performance.now();
      setSearchTime(Math.round(endTime - startTime));
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("An unexpected error occurred while searching.");
      }
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveSearch = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!saveSearchName.trim()) return;

    setIsSaving(true);

    const apiFilters: SearchCandidateFilters = {};
    activeFilters.forEach((f) => {
      if (f.type === "experience") {
        const minStr = f.value.replace(/[^0-9]/g, "");
        if (minStr) apiFilters.experienceMin = parseInt(minStr, 10);
      }
      if (f.type === "location") apiFilters.location = f.value;
      if (f.type === "skills") {
        if (!apiFilters.skills) apiFilters.skills = [];
        apiFilters.skills.push(f.value);
      }
    });

    try {
      await savedSearchesApi.createSavedSearch({
        name: saveSearchName,
        queryText: searchQuery,
        filters: Object.keys(apiFilters).length > 0 ? apiFilters : undefined,
        isShared: false,
      });
      setSaveSuccess(true);
      setTimeout(() => {
        setIsSaveModalOpen(false);
        setSaveSearchName("");
      }, 1500);
    } catch (err) {
      console.error("Failed to save search:", err);
      alert("Failed to save search. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const removeFilter = (id: string): void => {
    setActiveFilters((prev) => prev.filter((f) => f.id !== id));
  };

  const addDummyFilter = (): void => {
    if (!activeFilters.find((f) => f.id === "exp")) {
      setActiveFilters((prev) => [
        ...prev,
        { id: "exp", type: "experience", label: "Exp", value: "5+ yrs" },
      ]);
    } else if (!activeFilters.find((f) => f.id === "loc")) {
      setActiveFilters((prev) => [
        ...prev,
        { id: "loc", type: "location", label: "Location", value: "San Francisco" },
      ]);
    }
  };

  return (
    <div className="flex flex-col h-full items-center p-6 lg:p-12">
      <div className="w-full max-w-4xl space-y-8 mt-12 transition-all">
        {/* Header Section */}
        <div className={`text-center space-y-4 transition-all duration-500 ${results ? 'hidden' : 'block'}`}>
          <div className="inline-flex items-center justify-center space-x-2 bg-indigo-50 text-indigo-700 px-4 py-1.5 rounded-full text-sm font-medium border border-indigo-100 shadow-sm">
            <SparklesIcon className="w-4 h-4" />
            <span>Semantic Search</span>
          </div>
          <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight">
            Find candidates using natural language
          </h1>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto">
            Our AI understands context, skills, and experience to find the perfect match across your talent pool.
          </p>
        </div>

        {/* Search Input Section */}
        <div className="relative group">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <SearchIcon className="h-6 w-6 text-indigo-400 group-focus-within:text-indigo-600 transition-colors" />
          </div>
          <form onSubmit={handleSearch}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Try: 'Senior backend engineers with fintech experience who know Python'"
              style={{
                display: "block",
                width: "100%",
                padding: "1.25rem 8rem 1.25rem 3rem",
                backgroundColor: "var(--bg-surface)",
                border: "2px solid var(--border-subtle)",
                borderRadius: "1rem",
                fontSize: "1.125rem",
                color: "var(--text-primary)",
                boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
                outline: "none",
                transition: "border-color 0.15s ease",
              }}
            />
            <div className="absolute inset-y-2 right-2 flex items-center">
              <Button type="submit" size="lg" className="h-full rounded-xl px-6 font-semibold" disabled={isLoading || !searchQuery.trim()}>
                {isLoading ? "Searching..." : "Search"}
              </Button>
            </div>
          </form>
        </div>

        {/* Filters Section */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-gray-500 mr-2">Filters:</span>
            {activeFilters.length === 0 ? (
              <span className="text-sm text-gray-400 italic">No active filters</span>
            ) : (
              activeFilters.map((filter) => (
                <div
                  key={filter.id}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-800 border border-gray-200"
                >
                  <span className="font-medium mr-1">{filter.label}:</span>
                  <span>{filter.value}</span>
                  <button
                    type="button"
                    onClick={() => removeFilter(filter.id)}
                    className="ml-1.5 p-0.5 rounded-full hover:bg-gray-200 text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <XIcon className="w-3 h-3" />
                    <span className="sr-only">Remove filter {filter.label}</span>
                  </button>
                </div>
              ))
            )}
          </div>

          <Button variant="secondary" size="sm" onClick={addDummyFilter} className="shrink-0 rounded-full border-gray-300 text-gray-600">
            <span className="mr-1">+</span> Add Filter
          </Button>
        </div>

        {/* Error State */}
        {errorMsg && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex justify-between items-center">
            <span>{errorMsg}</span>
            <Button variant="secondary" size="sm" onClick={() => handleSearch()}>Retry</Button>
          </div>
        )}

        {/* Results Section */}
        {results !== null && !errorMsg && (
          <div className="space-y-6 pt-4 border-t border-gray-100">
            <div className="flex justify-between items-end">
              <p className="text-sm text-gray-500 font-medium">
                {isLoading ? "Searching..." : `${results.length} results • Searched in ${(searchTime! / 1000).toFixed(1)}s`}
              </p>
              {!isLoading && results.length > 0 && (
                <Button variant="secondary" size="sm" onClick={() => setIsSaveModalOpen(true)}>
                  Save this search
                </Button>
              )}
            </div>

            {isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="flex gap-4 p-5 bg-white border border-gray-100 rounded-xl animate-pulse">
                    <div className="w-16 h-16 rounded-full bg-gray-200 shrink-0"></div>
                    <div className="flex-1 space-y-3 py-1">
                      <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                      <div className="h-16 bg-gray-100 rounded w-full mt-2"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : results.length === 0 ? (
              <EmptyState
                title="No candidates match your search"
                description="Try broader terms, check your spelling, or remove some filters."
              />
            ) : (
              <div className="space-y-4">
                {results.map(item => (
                  <CandidateSearchResultCard key={item.candidate.id} item={item} />
                ))}
              </div>
            )}
          </div>
        )}

      </div>

      <Modal
        isOpen={isSaveModalOpen}
        onClose={() => setIsSaveModalOpen(false)}
        title="Save Search"
      >
        {saveSuccess ? (
          <div className="text-center py-6 text-emerald-600">
            <svg className="w-12 h-12 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <p className="text-lg font-medium">Search saved successfully!</p>
          </div>
        ) : (
          <form onSubmit={handleSaveSearch} className="space-y-4">
            <div>
              <label htmlFor="searchName" className="block text-sm font-medium text-gray-700 mb-1">Search Name</label>
              <Input
                id="searchName"
                value={saveSearchName}
                onChange={(e) => setSaveSearchName(e.target.value)}
                placeholder="e.g. Fintech Backend Engineers"
              />
            </div>
            <div className="bg-gray-50 p-3 rounded text-sm text-gray-600">
              <p><span className="font-medium">Query:</span> &quot;{searchQuery}&quot;</p>
              {activeFilters.length > 0 && (
                <p className="mt-1"><span className="font-medium">Filters:</span> {activeFilters.map(f => `${f.label} (${f.value})`).join(", ")}</p>
              )}
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" onClick={() => setIsSaveModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSaving || !saveSearchName.trim()}>
                {isSaving ? "Saving..." : "Save Search"}
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}

export default function SemanticSearchPage(): React.ReactElement {
  return (
    <ProtectedRoute>
      <AppShell>
        <SemanticSearchContent />
      </AppShell>
    </ProtectedRoute>
  );
}
