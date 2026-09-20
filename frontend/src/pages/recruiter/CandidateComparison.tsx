import { useEffect, useState } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { compareCandidates } from "../../api/screening";
import type { CandidateComparisonResponse } from "../../types/screening";

function ScoreBarVisual({ label, scoreA, scoreB }: { label: string; scoreA: number; scoreB: number }) {
  const colorA = scoreA >= 80 ? "bg-green-500" : scoreA >= 60 ? "bg-blue-500" : scoreA >= 40 ? "bg-yellow-500" : "bg-red-500";
  const colorB = scoreB >= 80 ? "bg-green-500" : scoreB >= 60 ? "bg-blue-500" : scoreB >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-gray-500 text-center">{label}</p>
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${colorA}`} style={{ width: `${scoreA}%` }} />
        </div>
        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${colorB}`} style={{ width: `${scoreB}%` }} />
        </div>
      </div>
    </div>
  );
}

export function CandidateComparison() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [comparison, setComparison] = useState<CandidateComparisonResponse | null>(null);

  const candidateIds = searchParams.get("ids")?.split(",") || [];

  useEffect(() => {
    if (!id || candidateIds.length < 2) {
      setLoading(false);
      return;
    }
    async function load() {
      try {
        const data = await compareCandidates(id!, candidateIds);
        setComparison(data);
      } catch {
        addToast("Failed to load comparison", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, candidateIds.join(","), addToast]);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  if (!comparison || comparison.candidates.length < 2) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-700">&larr; Back</button>
          <h1 className="text-2xl font-bold text-gray-900">Candidate Comparison</h1>
        </div>
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">Select at least 2 candidates to compare from the rankings page.</p>
        </div>
      </div>
    );
  }

  const [a, b] = comparison.candidates;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-700">&larr; Back</button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Candidate Comparison</h1>
          <p className="mt-1 text-sm text-gray-500">{comparison.job_title}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {[a, b].map((c, idx) => (
          <div key={c.candidate_id} className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <span className="text-xs font-bold text-gray-400">{idx === 0 ? "Candidate A" : "Candidate B"}</span>
                <h3 className="text-lg font-semibold text-gray-900">{c.candidate_name}</h3>
                <p className="text-sm text-gray-500">{c.candidate_email}</p>
              </div>
              <span className={`px-3 py-1 text-sm font-bold rounded-full ${
                c.overall_match_score >= 80 ? "bg-green-100 text-green-800" :
                c.overall_match_score >= 60 ? "bg-blue-100 text-blue-800" :
                c.overall_match_score >= 40 ? "bg-yellow-100 text-yellow-800" :
                "bg-red-100 text-red-800"
              }`}>
                {c.overall_match_score}%
              </span>
            </div>

            <div className="space-y-1.5 mb-4">
              {[
                { label: "Skills", score: c.skill_match_score },
                { label: "Experience", score: c.experience_match_score },
                { label: "Education", score: c.education_match_score },
                { label: "Projects", score: c.project_match_score },
                { label: "Certifications", score: c.certification_match_score },
              ].map(({ label, score }) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="w-24 text-xs text-gray-500 shrink-0">{label}</span>
                  <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        score >= 80 ? "bg-green-500" : score >= 60 ? "bg-blue-500" : score >= 40 ? "bg-yellow-500" : "bg-red-500"
                      }`}
                      style={{ width: `${score}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-gray-700 w-8 text-right">{score}%</span>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap gap-1.5 mb-3">
              {c.matched_skills?.map((s: string) => (
                <span key={s} className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded-full">{s}</span>
              ))}
            </div>
            {c.missing_required_skills && c.missing_required_skills.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {c.missing_required_skills.map((s: string) => (
                  <span key={s} className="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 rounded-full">{s}</span>
                ))}
              </div>
            )}
            <p className={`text-sm font-medium ${
              c.recommendation === "strongly_recommend" || c.recommendation === "recommend"
                ? "text-green-700" : c.recommendation === "consider" ? "text-yellow-700" : "text-red-700"
            }`}>
              {c.recommendation.replace(/_/g, " ").replace(/\b\w/g, (ch: string) => ch.toUpperCase())}
            </p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Head-to-Head</h3>
        <div className="space-y-2">
          {[
            { label: "Overall", scoreA: a.overall_match_score, scoreB: b.overall_match_score },
            { label: "Skills", scoreA: a.skill_match_score, scoreB: b.skill_match_score },
            { label: "Experience", scoreA: a.experience_match_score, scoreB: b.experience_match_score },
            { label: "Education", scoreA: a.education_match_score, scoreB: b.education_match_score },
            { label: "Projects", scoreA: a.project_match_score, scoreB: b.project_match_score },
            { label: "Certifications", scoreA: a.certification_match_score, scoreB: b.certification_match_score },
          ].map((item) => (
            <ScoreBarVisual key={item.label} label={item.label} scoreA={item.scoreA} scoreB={item.scoreB} />
          ))}
        </div>
        <div className="flex items-center justify-between mt-4 text-xs text-gray-500">
          <span className="font-medium">{a.candidate_name}</span>
          <span className="font-medium">{b.candidate_name}</span>
        </div>
      </div>
    </div>
  );
}
