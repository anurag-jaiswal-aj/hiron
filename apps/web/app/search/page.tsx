"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { Button } from "../../components/ui/Button";

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

import { useAuth } from "../../context/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

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

  const handleSearch = (e: React.FormEvent): void => {
    e.preventDefault();
    // Implementation deferred to Checkpoint 3
    console.log("Searching for:", searchQuery, "with filters:", activeFilters);
  };

  const removeFilter = (id: string): void => {
    setActiveFilters((prev) => prev.filter((f) => f.id !== id));
  };

  const addDummyFilter = (): void => {
    // Just a placeholder to show filter chips functionality for Checkpoint 2
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
      <div className="w-full max-w-4xl space-y-8 mt-12">
        {/* Header Section */}
        <div className="text-center space-y-4">
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
              className="block w-full pl-12 pr-32 py-5 bg-white border-2 border-gray-200 rounded-2xl text-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-0 focus:border-indigo-500 shadow-sm transition-all hover:border-gray-300"
            />
            <div className="absolute inset-y-2 right-2 flex items-center">
              <Button type="submit" size="lg" className="h-full rounded-xl px-6 font-semibold">
                Search
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

      </div>
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
