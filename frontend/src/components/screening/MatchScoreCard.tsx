import type { ScreeningResult, StrengthLevel, HiringRecommendation } from "../../types/screening";

const strengthColors: Record<StrengthLevel, string> = {
  excellent: "text-green-600 bg-green-50",
  good: "text-blue-600 bg-blue-50",
  average: "text-yellow-600 bg-yellow-50",
  low: "text-red-600 bg-red-50",
};

const recommendationColors: Record<HiringRecommendation, string> = {
  strongly_recommend: "text-green-700 bg-green-100",
  recommend: "text-blue-700 bg-blue-100",
  consider: "text-yellow-700 bg-yellow-100",
  not_recommended: "text-red-700 bg-red-100",
};

function formatRecommendation(rec: string): string {
  return rec.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const color =
    score >= 80 ? "bg-green-500" : score >= 60 ? "bg-blue-500" : score >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-3">
      <span className="w-28 text-xs text-gray-600 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-medium text-gray-700 w-8 text-right">{score}%</span>
    </div>
  );
}

interface MatchScoreCardProps {
  screening: ScreeningResult;
  candidateName?: string;
  jobTitle?: string;
  compact?: boolean;
}

export function MatchScoreCard({ screening, candidateName, jobTitle, compact }: MatchScoreCardProps) {
  const overall = screening.overall_match_score;
  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (overall / 100) * circumference;
  const overallColor =
    overall >= 80 ? "#22c55e" : overall >= 60 ? "#3b82f6" : overall >= 40 ? "#eab308" : "#ef4444";

  if (compact) {
    return (
      <div className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 bg-white">
        <svg width="48" height="48" viewBox="0 0 100 100" className="shrink-0">
          <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" strokeWidth="8" />
          <circle
            cx="50" cy="50" r="40" fill="none" stroke={overallColor} strokeWidth="8"
            strokeDasharray={circumference} strokeDashoffset={offset}
            strokeLinecap="round" transform="rotate(-90 50 50)"
          />
          <text x="50" y="50" textAnchor="middle" dominantBaseline="central"
            className="text-lg font-bold" fill={overallColor}>
            {overall}
          </text>
        </svg>
        <div className="min-w-0">
          {candidateName && <p className="text-sm font-medium text-gray-900 truncate">{candidateName}</p>}
          {jobTitle && <p className="text-xs text-gray-500 truncate">{jobTitle}</p>}
          <span className={`inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded-full ${strengthColors[screening.strength_level as StrengthLevel] || "text-gray-600 bg-gray-50"}`}>
            {screening.strength_level}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          {candidateName && <h3 className="text-lg font-semibold text-gray-900">{candidateName}</h3>}
          {jobTitle && <p className="text-sm text-gray-500">{jobTitle}</p>}
        </div>
        <span className={`px-3 py-1 text-xs font-medium rounded-full ${recommendationColors[screening.recommendation as HiringRecommendation] || "text-gray-600 bg-gray-100"}`}>
          {formatRecommendation(screening.recommendation)}
        </span>
      </div>

      <div className="flex items-center gap-6 mb-6">
        <div className="relative">
          <svg width="100" height="100" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" strokeWidth="8" />
            <circle
              cx="50" cy="50" r="40" fill="none" stroke={overallColor} strokeWidth="8"
              strokeDasharray={circumference} strokeDashoffset={offset}
              strokeLinecap="round" transform="rotate(-90 50 50)"
            />
            <text x="50" y="46" textAnchor="middle" dominantBaseline="central"
              className="text-2xl font-bold" fill={overallColor}>
              {overall}
            </text>
            <text x="50" y="64" textAnchor="middle" className="text-xs fill-gray-500">
              Overall
            </text>
          </svg>
        </div>
        <div className="flex-1 space-y-2">
          <ScoreBar label="Skills" score={screening.skill_match_score} />
          <ScoreBar label="Experience" score={screening.experience_match_score} />
          <ScoreBar label="Education" score={screening.education_match_score} />
          <ScoreBar label="Projects" score={screening.project_match_score} />
          <ScoreBar label="Certifications" score={screening.certification_match_score} />
          <ScoreBar label="Location" score={screening.location_match_score} />
          <ScoreBar label="Semantic" score={screening.semantic_match_score} />
        </div>
      </div>

      {screening.matched_skills && screening.matched_skills.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Matched Skills</p>
          <div className="flex flex-wrap gap-1.5">
            {screening.matched_skills.map((s) => (
              <span key={s} className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded-full">{s}</span>
            ))}
          </div>
        </div>
      )}

      {screening.missing_required_skills && screening.missing_required_skills.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Missing Required Skills</p>
          <div className="flex flex-wrap gap-1.5">
            {screening.missing_required_skills.map((s) => (
              <span key={s} className="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 rounded-full">{s}</span>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 mt-4">
        {screening.strengths && screening.strengths.length > 0 && (
          <div>
            <p className="text-xs font-medium text-green-600 uppercase tracking-wide mb-1">Strengths</p>
            <ul className="space-y-1">
              {screening.strengths.map((s, i) => (
                <li key={i} className="text-xs text-gray-600 flex items-start gap-1">
                  <span className="text-green-500 mt-0.5">+</span> {s}
                </li>
              ))}
            </ul>
          </div>
        )}
        {screening.weaknesses && screening.weaknesses.length > 0 && (
          <div>
            <p className="text-xs font-medium text-red-600 uppercase tracking-wide mb-1">Weaknesses</p>
            <ul className="space-y-1">
              {screening.weaknesses.map((w, i) => (
                <li key={i} className="text-xs text-gray-600 flex items-start gap-1">
                  <span className="text-red-500 mt-0.5">-</span> {w}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
