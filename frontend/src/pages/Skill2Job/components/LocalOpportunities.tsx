import { Briefcase, ArrowRight, CheckCircle2, AlertTriangle } from "lucide-react";
import type { Skill2JobOverview, OverviewTopMatch } from "../../../types/skill2job";
import { formatRecommendation } from "./helpers";

function JobCard({ match, onViewGap }: { match: OverviewTopMatch; onViewGap: () => void }) {
  const scoreColor = match.overall_score >= 80 ? "text-green-600" : match.overall_score >= 60 ? "text-primary-600" : "text-amber-600";
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 hover:shadow-md transition-shadow flex-shrink-0 w-[320px] md:w-auto">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-bold text-gray-900">{match.title}</h3>
          <p className="text-sm text-gray-500">{match.company && `${match.company} \u00b7 `}{match.location || "Remote"}</p>
        </div>
        <div className={`text-2xl font-bold ${scoreColor}`}>{match.overall_score}%</div>
      </div>
      <div className="w-full h-2 bg-gray-100 rounded-full mb-3">
        <div className={`h-full rounded-full transition-all ${match.overall_score >= 80 ? "bg-green-500" : match.overall_score >= 60 ? "bg-primary-500" : "bg-amber-500"}`} style={{ width: `${match.overall_score}%` }} />
      </div>
      {match.matched_skills.length > 0 && (
        <div className="mb-2">
          <div className="text-xs font-semibold text-gray-500 mb-1">Matched Skills</div>
          <div className="flex flex-wrap gap-1">
            {match.matched_skills.slice(0, 5).map((s) => (
              <span key={s} className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700 border border-green-200">
                <CheckCircle2 className="h-3 w-3" />{s}
              </span>
            ))}
          </div>
        </div>
      )}
      {match.missing_required.length > 0 && (
        <div className="mb-3">
          <div className="text-xs font-semibold text-gray-500 mb-1">Missing Skills</div>
          <div className="flex flex-wrap gap-1">
            {match.missing_required.slice(0, 3).map((s) => (
              <span key={s} className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 border border-amber-200">
                <AlertTriangle className="h-3 w-3" />{s}
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="flex items-center justify-between pt-2 border-t border-gray-100">
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold border ${match.recommendation === "strongly_recommend" ? "text-green-700 bg-green-50 border-green-200" : match.recommendation === "recommend" ? "text-blue-700 bg-blue-50 border-blue-200" : "text-amber-700 bg-amber-50 border-amber-200"}`}>
          {formatRecommendation(match.recommendation)}
        </span>
        <button onClick={onViewGap} className="inline-flex items-center gap-1 text-xs font-semibold text-primary-600 hover:text-primary-700">
          Analyze Gap <ArrowRight className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

export default function LocalOpportunities({ overview, onViewGap }: { overview: Skill2JobOverview; onViewGap: () => void }) {
  const matches = overview.jobs.top_matches;
  return (
    <div id="local-opportunities">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
          <Briefcase className="h-5 w-5 text-primary-600" />Local Opportunities
        </h2>
        <span className="text-sm text-gray-500">{overview.jobs.relevant_count} relevant jobs found</span>
      </div>
      {matches.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-gray-300 p-8 text-center">
          <Briefcase className="h-10 w-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No matching jobs yet</p>
          <p className="text-sm text-gray-400 mt-1">Upload your resume or complete your profile to discover opportunities.</p>
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-2 md:grid md:grid-cols-2 lg:grid-cols-3 md:overflow-visible">
          {matches.map((m) => <JobCard key={m.job_id} match={m} onViewGap={onViewGap} />)}
        </div>
      )}
    </div>
  );
}
