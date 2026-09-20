import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import {
  getCandidateExplanation,
  getXAIComparison,
  getTopCandidates,
} from "../../api/screening";
import type {
  CandidateExplanation,
  CandidateComparisonXAI,
  TopCandidatesResponse,
} from "../../types/screening";
import {
  ScoreRing,
  ConfidenceIndicator,
  FeatureImportanceBar,
  FactorList,
  StatBox,
  Badge,
  scoreBgColor,
  recommendationColor,
} from "../../components/xai/XAIComponents";

function ImprovementPanel({ explanation }: { explanation: CandidateExplanation }) {
  const recs = explanation.improvement_suggestions;
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Improvement Suggestions</h3>
      <div className="space-y-4">
        {recs.skill_improvements.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Skills to Acquire</p>
            <div className="space-y-1">
              {recs.skill_improvements.map((s, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <Badge
                    label={s.priority}
                    color={s.priority === "high" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}
                  />
                  <span className="font-medium text-gray-900">{s.skill}</span>
                  <span className="text-gray-500 text-xs">{s.reason}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {recs.certification_recommendations.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Certifications</p>
            {recs.certification_recommendations.map((c, i) => (
              <div key={i} className="text-sm text-gray-700 ml-2">
                {c.suggestion}
              </div>
            ))}
          </div>
        )}
        {recs.resume_improvements.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Resume Improvements</p>
            {recs.resume_improvements.map((r, i) => (
              <div key={i} className="text-sm text-gray-700 ml-2">{r}</div>
            ))}
          </div>
        )}
        {recs.project_suggestions.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Project Ideas</p>
            {recs.project_suggestions.map((p, i) => (
              <div key={i} className="text-sm text-gray-700 ml-2">{p}</div>
            ))}
          </div>
        )}
        {recs.interview_preparation.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Interview Preparation</p>
            {recs.interview_preparation.map((t, i) => (
              <div key={i} className="text-sm text-gray-700 ml-2">{t}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ComparisonView({
  comparison,
  onClear,
}: {
  comparison: CandidateComparisonXAI;
  onClear: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Candidate Comparison — {comparison.job_title}
        </h2>
        <button onClick={onClear} className="text-sm text-gray-500 hover:text-gray-700">
          Clear comparison
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500">Candidate</th>
              <th className="text-center py-2 px-3 text-xs font-medium text-gray-500">Score</th>
              <th className="text-center py-2 px-3 text-xs font-medium text-gray-500">Skills</th>
              <th className="text-center py-2 px-3 text-xs font-medium text-gray-500">Experience</th>
              <th className="text-center py-2 px-3 text-xs font-medium text-gray-500">Education</th>
              <th className="text-center py-2 px-3 text-xs font-medium text-gray-500">Confidence</th>
              <th className="text-center py-2 px-3 text-xs font-medium text-gray-500">Recommendation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {comparison.candidates.map((c) => (
              <tr key={c.candidate_id} className="hover:bg-gray-50">
                <td className="py-3 px-3">
                  <p className="font-medium text-gray-900">{c.candidate_name}</p>
                  <p className="text-xs text-gray-500">{c.candidate_email}</p>
                </td>
                <td className="py-3 px-3 text-center">
                  <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${scoreBgColor(c.overall_score)}`}>
                    {c.overall_score}%
                  </span>
                </td>
                <td className="py-3 px-3 text-center">
                  <span className={`text-xs font-bold ${c.skill_match_score >= 70 ? "text-green-600" : c.skill_match_score >= 40 ? "text-yellow-600" : "text-red-600"}`}>
                    {c.skill_match_score}%
                  </span>
                </td>
                <td className="py-3 px-3 text-center">
                  <span className={`text-xs font-bold ${c.experience_match_score >= 70 ? "text-green-600" : c.experience_match_score >= 40 ? "text-yellow-600" : "text-red-600"}`}>
                    {c.experience_match_score}%
                  </span>
                </td>
                <td className="py-3 px-3 text-center">
                  <span className={`text-xs font-bold ${c.education_match_score >= 70 ? "text-green-600" : c.education_match_score >= 40 ? "text-yellow-600" : "text-red-600"}`}>
                    {c.education_match_score}%
                  </span>
                </td>
                <td className="py-3 px-3 text-center">
                  <ConfidenceIndicator confidence={c.confidence} />
                </td>
                <td className="py-3 px-3 text-center">
                  <Badge label={c.recommendation.replace(/_/g, " ")} color={recommendationColor(c.recommendation)} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {comparison.pairwise_comparisons.map((pw, i) => (
        <div key={i} className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            {pw.higher_name} ({pw.higher_score}%) vs {pw.lower_name} ({pw.lower_score}%)
          </h3>
          <p className="text-sm text-gray-700 mb-3">{pw.summary}</p>
          {pw.key_differences.length > 0 && (
            <div className="space-y-1">
              {pw.key_differences.map((d, j) => (
                <div key={j} className="text-sm text-gray-600">
                  <span className="font-medium">{d.category}:</span>{" "}
                  {d.higher_score} vs {d.lower_score}
                  <span className={`ml-1 font-medium ${d.direction === "ahead" ? "text-green-600" : "text-red-600"}`}>
                    ({d.direction} by {d.difference})
                  </span>
                </div>
              ))}
            </div>
          )}
          {pw.skills_only_higher_has.length > 0 && (
            <div className="mt-2">
              <span className="text-xs font-medium text-gray-500">Skills only {pw.higher_name} has:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {pw.skills_only_higher_has.map((s, k) => (
                  <Badge key={k} label={s} color="bg-green-50 text-green-700" />
                ))}
              </div>
            </div>
          )}
          {pw.skills_only_lower_has.length > 0 && (
            <div className="mt-2">
              <span className="text-xs font-medium text-gray-500">Skills only {pw.lower_name} has:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {pw.skills_only_lower_has.map((s, k) => (
                  <Badge key={k} label={s} color="bg-blue-50 text-blue-700" />
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function ExplainabilityDashboard() {
  const { addToast } = useToast();
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get("job_id") || undefined;

  const [loading, setLoading] = useState(true);
  const [topCandidates, setTopCandidates] = useState<TopCandidatesResponse | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<CandidateExplanation | null>(null);
  const [comparison, setComparison] = useState<CandidateComparisonXAI | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [loadingExplanation, setLoadingExplanation] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const top = await getTopCandidates(jobId, 20);
        setTopCandidates(top);
      } catch {
        addToast("Failed to load candidates", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [addToast, jobId]);

  const handleSelectCandidate = async (candidateId: string) => {
    setSelectedCandidate(candidateId);
    setLoadingExplanation(true);
    setComparison(null);
    try {
      const expl = await getCandidateExplanation(candidateId, jobId);
      setExplanation(expl);
    } catch {
      addToast("Failed to load explanation", "error");
      setExplanation(null);
    } finally {
      setLoadingExplanation(false);
    }
  };

  const handleCompare = async () => {
    if (compareIds.length < 2 || !jobId) {
      addToast("Select at least 2 candidates and specify a job to compare", "error");
      return;
    }
    try {
      const comp = await getXAIComparison(compareIds, jobId);
      setComparison(comp);
      setExplanation(null);
    } catch {
      addToast("Failed to compare candidates", "error");
    }
  };

  const toggleCompare = (cid: string) => {
    setCompareIds((prev) =>
      prev.includes(cid) ? prev.filter((id) => id !== cid) : [...prev, cid],
    );
  };

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Explainability Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Understand why AI made its decisions — transparent scoring and feature importance
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={handleCompare}
          disabled={compareIds.length < 2 || !jobId}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            compareIds.length >= 2 && jobId
              ? "bg-primary-600 text-white hover:bg-primary-700"
              : "bg-gray-100 text-gray-400 cursor-not-allowed"
          }`}
        >
          Compare Selected ({compareIds.length})
        </button>
        {jobId && (
          <span className="text-xs text-gray-500">Job: {jobId.slice(0, 8)}...</span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 space-y-2">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Candidates</h3>
          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
            {topCandidates?.candidates.map((c) => (
              <div
                key={c.candidate_id}
                className={`flex items-center gap-3 p-3 cursor-pointer transition-colors ${
                  selectedCandidate === c.candidate_id ? "bg-primary-50" : "hover:bg-gray-50"
                }`}
              >
                <input
                  type="checkbox"
                  checked={compareIds.includes(c.candidate_id)}
                  onChange={(e) => {
                    e.stopPropagation();
                    toggleCompare(c.candidate_id);
                  }}
                  className="shrink-0"
                />
                <div
                  className="flex-1 min-w-0"
                  onClick={() => handleSelectCandidate(c.candidate_id)}
                >
                  <p className="text-sm font-medium text-gray-900 truncate">{c.candidate_name}</p>
                  <p className="text-xs text-gray-500">
                    {c.overall_score}% &middot; {c.strength_level}
                  </p>
                </div>
                <ScoreRing score={c.overall_score} size={36} />
              </div>
            ))}
            {topCandidates?.candidates.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-8">No candidates to show</p>
            )}
          </div>
        </div>

        <div className="lg:col-span-8">
          {comparison ? (
            <ComparisonView comparison={comparison} onClear={() => setComparison(null)} />
          ) : loadingExplanation ? (
            <div className="flex justify-center py-20">
              <LoadingSpinner size="lg" />
            </div>
          ) : explanation ? (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatBox label="Overall Match" value={`${explanation.overall_score}%`} color={explanation.overall_score >= 70 ? "text-green-600" : "text-yellow-600"} />
                <StatBox label="Strength Level" value={explanation.strength_level} color="text-blue-600" />
                <StatBox label="Matched Skills" value={explanation.matched_skills.length} color="text-purple-600" />
                <StatBox label="Missing Skills" value={explanation.missing_skills.length} color="text-orange-600" />
              </div>

              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">AI Reasoning</h3>
                  <ConfidenceIndicator confidence={explanation.confidence} />
                </div>
                <p className="text-sm text-gray-700 leading-relaxed">{explanation.reasoning_summary}</p>
                <p className="text-xs text-gray-400 mt-2">
                  SHAP: {explanation.shap_available ? "Available" : "Fallback"} &middot; LIME: {explanation.lime_available ? "Available" : "Fallback"} &middot; Confidence data: {explanation.confidence.data_completeness_pct}% complete
                </p>
              </div>

              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Feature Importance</h3>
                <div className="space-y-3">
                  {explanation.feature_importance.map((f) => (
                    <FeatureImportanceBar key={f.category} feature={f} />
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Positive Factors</h3>
                  <FactorList factors={explanation.positive_factors} type="positive" />
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Negative Factors</h3>
                  <FactorList factors={explanation.negative_factors} type="negative" />
                </div>
              </div>

              {explanation.strengths.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Strengths</h3>
                  <div className="flex flex-wrap gap-2">
                    {explanation.strengths.map((s, i) => (
                      <Badge key={i} label={s} color="bg-green-50 text-green-700" />
                    ))}
                  </div>
                </div>
              )}

              {explanation.weaknesses.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Weaknesses</h3>
                  <div className="flex flex-wrap gap-2">
                    {explanation.weaknesses.map((w, i) => (
                      <Badge key={i} label={w} color="bg-red-50 text-red-700" />
                    ))}
                  </div>
                </div>
              )}

              {explanation.matched_skills.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Matched Skills</h3>
                  <div className="flex flex-wrap gap-2">
                    {explanation.matched_skills.map((s, i) => (
                      <Badge key={i} label={s} color="bg-green-50 text-green-700" />
                    ))}
                  </div>
                </div>
              )}

              {explanation.missing_skills.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Missing Skills</h3>
                  <div className="flex flex-wrap gap-2">
                    {explanation.missing_skills.map((s, i) => (
                      <Badge key={i} label={s} color="bg-red-50 text-red-700" />
                    ))}
                  </div>
                </div>
              )}

              <ImprovementPanel explanation={explanation} />
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <p className="text-gray-500">Select a candidate to view their AI explanation</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
