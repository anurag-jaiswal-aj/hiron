import React from "react";
import { ScoreBreakdown as ScoreBreakdownType } from "../../lib/scores-api";

interface ScoreBreakdownProps {
  breakdown: ScoreBreakdownType;
}

export function ScoreBreakdown({ breakdown }: ScoreBreakdownProps): React.ReactElement {
  const renderDimension = (title: string, data: { score: number; weight: number; details: string }): React.ReactElement => {
    // Color coding based on score
    let colorClass = "bg-green-500";
    if (data.score < 70) colorClass = "bg-red-500";
    else if (data.score < 85) colorClass = "bg-yellow-500";

    return (
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="font-medium text-gray-700 capitalize">{title}</span>
          <span className="font-semibold text-gray-900">{data.score}/100</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
          <div className={`h-2 rounded-full ${colorClass}`} style={{ width: `${data.score}%` }}></div>
        </div>
        <p className="text-xs text-gray-500">{data.details}</p>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Score Breakdown</h3>
      {renderDimension("Skills", breakdown.skills)}
      {renderDimension("Experience", breakdown.experience)}
      {renderDimension("Education", breakdown.education)}
    </div>
  );
}
