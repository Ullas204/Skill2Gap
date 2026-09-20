import { useEffect, useState } from "react";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { getTopCandidates } from "../../api/screening";
import type { TopCandidatesResponse, TopCandidateItem } from "../../types/screening";

function RankBadge({ rank }: { rank: number }) {
  if (rank <= 3) {
    const colors = ["bg-yellow-100 text-yellow-800 border-yellow-300", "bg-gray-100 text-gray-700 border-gray-300", "bg-orange-100 text-orange-800 border-orange-300"];
    return (
      <span className={`inline-flex items-center justify-center w-7 h-7 text-xs font-bold rounded-full border ${colors[rank - 1]}`}>
        {rank}
      </span>
    );
  }
  return <span className="text-sm font-bold text-gray-400">#{rank}</span>;
}

function CandidateCard({ candidate }: { candidate: TopCandidateItem }) {
  const scoreColor =
    candidate.overall_score >= 80 ? "text-green-600" :
    candidate.overall_score >= 60 ? "text-blue-600" :
    candidate.overall_score >= 40 ? "text-yellow-600" : "text-red-600";

  const levelColor =
    candidate.strength_level === "excellent" ? "bg-green-100 text-green-700" :
    candidate.strength_level === "good" ? "bg-blue-100 text-blue-700" :
    candidate.strength_level === "average" ? "bg-yellow-100 text-yellow-700" :
    "bg-red-100 text-red-700";

  const recLabel = candidate.recommendation.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const recColor =
    candidate.recommendation === "strongly_recommend" ? "text-green-700" :
    candidate.recommendation === "recommend" ? "text-blue-700" :
    candidate.recommendation === "consider" ? "text-yellow-700" : "text-red-700";

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-4">
        <RankBadge rank={candidate.rank} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-gray-900">{candidate.candidate_name}</h3>
              <p className="text-sm text-gray-500">{candidate.candidate_email}</p>
            </div>
            <div className="text-right">
              <p className={`text-2xl font-bold ${scoreColor}`}>{candidate.overall_score}%</p>
              {candidate.rank_change !== 0 && (
                <p className={`text-xs font-medium ${candidate.rank_change > 0 ? "text-green-500" : "text-red-500"}`}>
                  {candidate.rank_change > 0 ? `+${candidate.rank_change}` : candidate.rank_change} positions
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 mt-3">
            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${levelColor}`}>
              {candidate.strength_level}
            </span>
            <span className={`text-xs font-medium ${recColor}`}>{recLabel}</span>
          </div>

          <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
            <span>Skills: {candidate.skill_match}%</span>
            <span>Experience: {candidate.experience_match}%</span>
          </div>

          {candidate.matched_skills.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {candidate.matched_skills.slice(0, 6).map((s) => (
                <span key={s} className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded-full">{s}</span>
              ))}
              {candidate.matched_skills.length > 6 && (
                <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-500 rounded-full">
                  +{candidate.matched_skills.length - 6} more
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function TopCandidatesPage() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<TopCandidatesResponse | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const result = await getTopCandidates(undefined, 20);
        setData(result);
      } catch {
        addToast("Failed to load top candidates", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [addToast]);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Top Candidates</h1>
        <p className="mt-1 text-sm text-gray-500">AI-ranked best-fit candidates across your job postings</p>
      </div>

      {data && data.candidates.length > 0 ? (
        <div className="space-y-3">
          {data.candidates.map((c) => (
            <CandidateCard key={`${c.candidate_id}-${c.candidate_name}`} candidate={c} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No candidates have been ranked yet. Run AI screening on your job postings first.</p>
        </div>
      )}
    </div>
  );
}
