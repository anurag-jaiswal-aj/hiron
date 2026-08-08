import Link from "next/link";
import React from "react";

import { CandidateSearchResultItem } from "../../lib/search-api";

interface CandidateSearchResultCardProps {
  item: CandidateSearchResultItem;
}

export function CandidateSearchResultCard({ item }: CandidateSearchResultCardProps): React.ReactElement {
  const { candidate, relevanceScore, highlights } = item;
  
  // Format score as integer percentage
  const scorePercent = Math.round(relevanceScore * 100);
  
  // Determine color based on score
  let scoreColorClass = "text-indigo-600 border-indigo-200 bg-indigo-50";
  if (scorePercent >= 90) {
    scoreColorClass = "text-emerald-600 border-emerald-200 bg-emerald-50";
  } else if (scorePercent < 70) {
    scoreColorClass = "text-amber-600 border-amber-200 bg-amber-50";
  }

  return (
    <div className="flex flex-col sm:flex-row gap-4 p-5 bg-white border border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-md transition-all">
      {/* Score Badge */}
      <div className="shrink-0 pt-1">
        <div className={`flex flex-col items-center justify-center w-16 h-16 rounded-full border-2 ${scoreColorClass}`}>
          <span className="text-xl font-bold tracking-tight">{scorePercent}%</span>
          <span className="text-[10px] uppercase font-semibold opacity-80">Match</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 min-w-0 flex flex-col space-y-3">
        {/* Header */}
        <div>
          <Link
            href={`/candidates/${candidate.id}`}
            className="text-lg font-bold text-gray-900 hover:text-indigo-600 transition-colors"
          >
            {candidate.fullName}
          </Link>
          <div className="text-sm text-gray-600 mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-medium text-gray-900">
              {candidate.currentTitle || "No Current Title"}
            </span>
            <span className="text-gray-300">•</span>
            <span>{candidate.totalExperienceYears !== null ? `${candidate.totalExperienceYears}y exp` : "Exp N/A"}</span>
            <span className="text-gray-300">•</span>
            <span className="truncate">{candidate.skills.slice(0, 5).join(", ")}</span>
          </div>
        </div>

        {/* Highlights */}
        {highlights && highlights.length > 0 && (
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Why they matched</h4>
            <ul className="space-y-1.5">
              {highlights.map((highlight, idx) => (
                <li key={idx} className="text-sm text-gray-700 flex items-start">
                  <span className="text-indigo-400 mr-2 flex-shrink-0 mt-0.5">✦</span>
                  <span className="leading-snug">{highlight}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
