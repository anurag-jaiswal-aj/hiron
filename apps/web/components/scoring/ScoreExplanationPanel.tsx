import React from "react";
import { ScoreExplanationData } from "../../lib/scores-api";

interface ScoreExplanationPanelProps {
  explanation: ScoreExplanationData | null;
  isLoading: boolean;
  error: Error | null;
}

export function ScoreExplanationPanel({ explanation, isLoading, error }: ScoreExplanationPanelProps): React.ReactElement | null {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 shadow-sm animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          <div className="h-4 bg-gray-200 rounded w-4/6"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-red-200 p-4 mb-4 shadow-sm">
        <h3 className="text-lg font-semibold text-red-800 mb-2">Explanation Error</h3>
        <p className="text-sm text-red-600">Failed to load the AI explanation.</p>
      </div>
    );
  }

  if (!explanation) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-800 mb-3">AI Evaluation</h3>
      
      {explanation.warnings && explanation.warnings.length > 0 && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <h4 className="text-sm font-semibold text-yellow-800 mb-1 flex items-center">
            <svg className="w-4 h-4 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Review Warnings
          </h4>
          <ul className="list-disc pl-5 text-sm text-yellow-700 space-y-1">
            {explanation.warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
        {explanation.explanation}
      </p>

      {explanation.confidenceFactors && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Confidence Factors</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <div>
              <span className="text-gray-500 block">Resume Completeness</span>
              <span className="font-medium text-gray-800">{Math.round(explanation.confidenceFactors.resumeCompleteness * 100)}%</span>
            </div>
            <div>
              <span className="text-gray-500 block">Output Consistency</span>
              <span className="font-medium text-gray-800">{Math.round(explanation.confidenceFactors.outputConsistency * 100)}%</span>
            </div>
            <div>
              <span className="text-gray-500 block">Explanation Quality</span>
              <span className="font-medium text-gray-800">{Math.round(explanation.confidenceFactors.explanationQuality * 100)}%</span>
            </div>
            <div>
              <span className="text-gray-500 block">Sanity Check</span>
              <span className={`font-medium ${explanation.confidenceFactors.sanityCheckPassed ? 'text-green-600' : 'text-red-600'}`}>
                {explanation.confidenceFactors.sanityCheckPassed ? 'Passed' : 'Failed'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
