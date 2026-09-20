import { useEffect, useState } from "react";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { getMyExplanation } from "../../api/screening";
import type { CandidateExplanation } from "../../types/screening";
import {
  ConfidenceIndicator,
  FeatureImportanceBar,
  FactorList,
  StatBox,
  Badge,
} from "../../components/xai/XAIComponents";

export function CandidateExplainability() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [explanation, setExplanation] = useState<CandidateExplanation | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const expl = await getMyExplanation();
        setExplanation(expl);
      } catch {
        addToast("No AI explanation available yet. Apply for a job and complete screening first.", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [addToast]);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  if (!explanation) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My AI Explanation</h1>
          <p className="mt-1 text-sm text-gray-500">Understand how AI evaluates your profile</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500">No AI explanation available yet.</p>
          <p className="text-sm text-gray-400 mt-2">Apply for a job and complete screening to see your explanation.</p>
        </div>
      </div>
    );
  }

  const recs = explanation.improvement_suggestions;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">My AI Explanation</h1>
        <p className="mt-1 text-sm text-gray-500">
          Understand how AI evaluates your profile for: {explanation.job_title}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatBox label="Overall Match" value={`${explanation.overall_score}%`} color={explanation.overall_score >= 70 ? "text-green-600" : "text-yellow-600"} />
        <StatBox label="Strength Level" value={explanation.strength_level} color="text-blue-600" />
        <StatBox label="Matched Skills" value={explanation.matched_skills.length} color="text-purple-600" />
        <StatBox label="Missing Skills" value={explanation.missing_skills.length} color="text-orange-600" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">AI Assessment</h3>
          <ConfidenceIndicator confidence={explanation.confidence} />
        </div>
        <p className="text-sm text-gray-700 leading-relaxed">{explanation.reasoning_summary}</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Feature Importance</h3>
        <p className="text-xs text-gray-500 mb-3">How different parts of your profile contributed to the score</p>
        <div className="space-y-3">
          {explanation.feature_importance.map((f) => (
            <FeatureImportanceBar key={f.category} feature={f} />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Strengths</h3>
          <FactorList factors={explanation.positive_factors} type="positive" />
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Areas for Improvement</h3>
          <FactorList factors={explanation.negative_factors} type="negative" />
        </div>
      </div>

      {explanation.matched_skills.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Your Matched Skills</h3>
          <div className="flex flex-wrap gap-2">
            {explanation.matched_skills.map((s, i) => (
              <Badge key={i} label={s} color="bg-green-50 text-green-700" />
            ))}
          </div>
        </div>
      )}

      {explanation.missing_skills.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Skills to Develop</h3>
          <div className="flex flex-wrap gap-2">
            {explanation.missing_skills.map((s, i) => (
              <Badge key={i} label={s} color="bg-red-50 text-red-700" />
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Personalized Recommendations</h3>
        <div className="space-y-4">
          {recs.skill_improvements.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Skills to Acquire</p>
              {recs.skill_improvements.map((s, i) => (
                <div key={i} className="flex items-center gap-2 text-sm ml-2 mb-1">
                  <Badge label={s.priority} color={s.priority === "high" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"} />
                  <span className="font-medium text-gray-900">{s.skill}</span>
                </div>
              ))}
            </div>
          )}
          {recs.certification_recommendations.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Recommended Certifications</p>
              {recs.certification_recommendations.map((c, i) => (
                <div key={i} className="text-sm text-gray-700 ml-2">{c.suggestion}</div>
              ))}
            </div>
          )}
          {recs.resume_improvements.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Resume Tips</p>
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

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Learning Roadmap</h3>
        <div className="space-y-3">
          {recs.skill_improvements.map((s, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                {i + 1}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Learn {s.skill}</p>
                <p className="text-xs text-gray-500">{s.reason}</p>
              </div>
            </div>
          ))}
          {recs.certification_recommendations.map((c, i) => (
            <div key={`cert-${i}`} className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                {recs.skill_improvements.length + i + 1}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{c.area}</p>
                <p className="text-xs text-gray-500">{c.suggestion}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
