import type { SkillGapAnalysis } from "../../types/screening";

interface SkillGapReportProps {
  skillGap: SkillGapAnalysis;
}

export function SkillGapReport({ skillGap }: SkillGapReportProps) {
  const readiness = skillGap.interview_readiness_score;
  const readinessColor =
    readiness >= 80 ? "text-green-600" : readiness >= 60 ? "text-blue-600" : readiness >= 40 ? "text-yellow-600" : "text-red-600";
  const readinessBg =
    readiness >= 80 ? "bg-green-100" : readiness >= 60 ? "bg-blue-100" : readiness >= 40 ? "bg-yellow-100" : "bg-red-100";

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-lg font-semibold text-gray-900">Skill Gap Analysis</h3>
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${readinessBg}`}>
          <span className={`text-sm font-bold ${readinessColor}`}>{readiness}%</span>
          <span className="text-xs text-gray-600">Interview Ready</span>
        </div>
      </div>

      {skillGap.missing_required_skills && skillGap.missing_required_skills.length > 0 && (
        <div className="mb-5">
          <h4 className="text-sm font-medium text-red-600 mb-2">Missing Required Skills</h4>
          <div className="flex flex-wrap gap-1.5">
            {skillGap.missing_required_skills.map((s) => (
              <span key={s} className="px-2.5 py-1 text-xs font-medium bg-red-50 text-red-700 border border-red-200 rounded-full">{s}</span>
            ))}
          </div>
        </div>
      )}

      {skillGap.missing_preferred_skills && skillGap.missing_preferred_skills.length > 0 && (
        <div className="mb-5">
          <h4 className="text-sm font-medium text-yellow-600 mb-2">Missing Preferred Skills</h4>
          <div className="flex flex-wrap gap-1.5">
            {skillGap.missing_preferred_skills.map((s) => (
              <span key={s} className="px-2.5 py-1 text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-200 rounded-full">{s}</span>
            ))}
          </div>
        </div>
      )}

      {(skillGap.experience_gap_description || skillGap.education_gap_description || skillGap.certification_gap_description) && (
        <div className="mb-5 space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Gaps</h4>
          {skillGap.experience_gap_description && (
            <div className="flex items-start gap-2 text-sm text-gray-600">
              <span className="text-yellow-500 mt-0.5">!</span> {skillGap.experience_gap_description}
            </div>
          )}
          {skillGap.education_gap_description && (
            <div className="flex items-start gap-2 text-sm text-gray-600">
              <span className="text-yellow-500 mt-0.5">!</span> {skillGap.education_gap_description}
            </div>
          )}
          {skillGap.certification_gap_description && (
            <div className="flex items-start gap-2 text-sm text-gray-600">
              <span className="text-yellow-500 mt-0.5">!</span> {skillGap.certification_gap_description}
            </div>
          )}
        </div>
      )}

      {skillGap.skill_suggestions && skillGap.skill_suggestions.length > 0 && (
        <div className="mb-5">
          <h4 className="text-sm font-medium text-blue-600 mb-2">Skill Suggestions</h4>
          <ul className="space-y-1.5">
            {skillGap.skill_suggestions.map((s, i) => (
              <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                <span className="text-blue-500 mt-0.5">&#x2022;</span> {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {skillGap.improvement_suggestions && skillGap.improvement_suggestions.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-green-600 mb-2">Improvement Suggestions</h4>
          <ul className="space-y-1.5">
            {skillGap.improvement_suggestions.map((s, i) => (
              <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                <span className="text-green-500 mt-0.5">&#x2713;</span> {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
