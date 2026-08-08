import React from "react";
import { Badge } from "../ui/Badge";

interface SkillsAnalysisProps {
  skillsMatched: string[];
  skillsMissing: string[];
}

export function SkillsAnalysis({ skillsMatched, skillsMissing }: SkillsAnalysisProps): React.ReactElement {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Skills Analysis</h3>
      
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Matched Skills ({skillsMatched.length})</h4>
        <div className="flex flex-wrap gap-2">
          {skillsMatched.length > 0 ? (
            skillsMatched.map((skill, index) => (
              <Badge key={index} variant="active">{skill}</Badge>
            ))
          ) : (
            <span className="text-sm text-gray-500">No matched skills</span>
          )}
        </div>
      </div>

      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-2">Missing Skills ({skillsMissing.length})</h4>
        <div className="flex flex-wrap gap-2">
          {skillsMissing.length > 0 ? (
            skillsMissing.map((skill, index) => (
              <Badge key={index} variant="error">{skill}</Badge>
            ))
          ) : (
            <span className="text-sm text-gray-500">No missing skills</span>
          )}
        </div>
      </div>
    </div>
  );
}
