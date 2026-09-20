import type { InterviewScorecard } from "../../types/interview";

const DIMENSIONS = [
  { key: "technical_skills", label: "Technical Skills" },
  { key: "communication", label: "Communication" },
  { key: "problem_solving", label: "Problem Solving" },
  { key: "teamwork", label: "Teamwork" },
  { key: "leadership", label: "Leadership" },
  { key: "culture_fit", label: "Culture Fit" },
  { key: "learning_ability", label: "Learning Ability" },
] as const;

const RECOMMENDATION_LABELS: Record<string, string> = {
  strongly_recommend: "Strongly Recommend",
  recommend: "Recommend",
  consider: "Consider",
  not_recommended: "Not Recommended",
};

const RECOMMENDATION_COLORS: Record<string, string> = {
  strongly_recommend: "text-green-700 bg-green-50",
  recommend: "text-blue-700 bg-blue-50",
  consider: "text-amber-700 bg-amber-50",
  not_recommended: "text-red-700 bg-red-50",
};

export function ScorecardView({ scorecard }: { scorecard: InterviewScorecard }) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return "bg-green-500";
    if (score >= 60) return "bg-blue-500";
    if (score >= 40) return "bg-amber-500";
    return "bg-red-500";
  };

  const getScoreTextColor = (score: number) => {
    if (score >= 80) return "text-green-700";
    if (score >= 60) return "text-blue-700";
    if (score >= 40) return "text-amber-700";
    return "text-red-700";
  };

  return (
    <div className="space-y-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Interview Scorecard</h3>
        <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${RECOMMENDATION_COLORS[scorecard.recommendation] || "bg-gray-100 text-gray-600"}`}>
          {RECOMMENDATION_LABELS[scorecard.recommendation] || scorecard.recommendation}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg bg-gray-50 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{scorecard.overall_score}</p>
          <p className="text-xs text-gray-500">Overall Score</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{scorecard.hiring_confidence}%</p>
          <p className="text-xs text-gray-500">Hiring Confidence</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{scorecard.technical_skills}</p>
          <p className="text-xs text-gray-500">Technical Skills</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{scorecard.communication}</p>
          <p className="text-xs text-gray-500">Communication</p>
        </div>
      </div>

      <div className="space-y-3">
        {DIMENSIONS.map((dim) => {
          const score = scorecard[dim.key as keyof InterviewScorecard] as number;
          return (
            <div key={dim.key} className="flex items-center gap-3">
              <span className="w-36 text-sm text-gray-600">{dim.label}</span>
              <div className="flex-1">
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-gray-100">
                  <div
                    className={`h-full rounded-full transition-all ${getScoreColor(score)}`}
                    style={{ width: `${score}%` }}
                  />
                </div>
              </div>
              <span className={`w-10 text-right text-sm font-semibold ${getScoreTextColor(score)}`}>
                {score}
              </span>
            </div>
          );
        })}
      </div>

      {scorecard.ai_summary && (
        <div className="rounded-lg bg-blue-50 p-4">
          <p className="text-sm font-medium text-blue-900">AI Summary</p>
          <p className="mt-1 text-sm text-blue-700">{scorecard.ai_summary}</p>
        </div>
      )}

      {scorecard.recruiter_notes && (
        <div className="rounded-lg bg-gray-50 p-4">
          <p className="text-sm font-medium text-gray-900">Recruiter Notes</p>
          <p className="mt-1 text-sm text-gray-700">{scorecard.recruiter_notes}</p>
        </div>
      )}
    </div>
  );
}
