import React from "react";
import { ScoreHistoryItem } from "../../lib/scores-api";
import { Badge } from "../ui/Badge";

interface ScoreHistoryProps {
  history: ScoreHistoryItem[] | null;
  isLoading: boolean;
  error: Error | null;
}

export function ScoreHistory({ history, isLoading, error }: ScoreHistoryProps): React.ReactElement | null {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 shadow-sm animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
        <div className="space-y-3">
          <div className="h-8 bg-gray-100 rounded w-full"></div>
          <div className="h-8 bg-gray-100 rounded w-full"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-red-200 p-4 mb-4 shadow-sm">
        <h3 className="text-lg font-semibold text-red-800 mb-2">History Error</h3>
        <p className="text-sm text-red-600">Failed to load score history.</p>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden mb-4 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <h3 className="text-lg font-semibold text-gray-800">Score History</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-white">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">Score</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">Prompt Ver</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {history.map((item) => (
              <tr key={item.id} className={item.isCurrent ? "bg-blue-50/30" : ""}>
                <td className="px-4 py-3 whitespace-nowrap text-gray-700">
                  {new Date(item.createdAt).toLocaleDateString()}
                </td>
                <td className="px-4 py-3 whitespace-nowrap font-medium text-gray-900">
                  {item.fitScore}/100
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-gray-500">
                  v{item.promptVersion}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {item.isCurrent ? (
                    <Badge variant="active">Current</Badge>
                  ) : (
                    <span className="text-gray-400 text-xs uppercase font-medium">Superseded</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
