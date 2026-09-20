import { useEffect, useState } from "react";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { getMyAISummary, getMyScores } from "../../api/screening";
import type { CandidateAISummary, ScreeningResult } from "../../types/screening";

function Badge({ label, color }: { label: string; color: string }) {
  return <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${color}`}>{label}</span>;
}

function InfoCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      {children}
    </div>
  );
}

export function CandidateAIDashboard() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<CandidateAISummary | null>(null);
  const [scores, setScores] = useState<ScreeningResult[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const [sum, sc] = await Promise.all([
          getMyAISummary(),
          getMyScores(),
        ]);
        setSummary(sum);
        setScores(sc);
      } catch {
        addToast("Failed to load AI dashboard", "error");
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
        <h1 className="text-2xl font-bold text-gray-900">My AI Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">AI-powered insights about your profile and job matches</p>
      </div>

      {summary && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs font-medium text-gray-500 uppercase">Experience Level</p>
              <p className="text-lg font-bold text-blue-600 mt-1">{summary.experience_level}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs font-medium text-gray-500 uppercase">Technical Expertise</p>
              <p className="text-lg font-bold text-purple-600 mt-1">{summary.technical_expertise}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs font-medium text-gray-500 uppercase">Leadership Potential</p>
              <p className="text-lg font-bold text-green-600 mt-1">{summary.leadership_potential}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs font-medium text-gray-500 uppercase">Learning Ability</p>
              <p className="text-lg font-bold text-orange-600 mt-1">{summary.learning_ability}</p>
            </div>
          </div>

          <InfoCard title="Professional Summary">
            <p className="text-sm text-gray-700 leading-relaxed">{summary.professional_summary}</p>
          </InfoCard>

          {summary.top_skills.length > 0 && (
            <InfoCard title="Top Skills">
              <div className="space-y-2">
                {summary.top_skills.map((s) => (
                  <div key={s.skill} className="flex items-center gap-3">
                    <span className="w-32 text-sm text-gray-700 shrink-0">{s.skill}</span>
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          s.relevance >= 80 ? "bg-green-500" : s.relevance >= 60 ? "bg-blue-500" : "bg-yellow-500"
                        }`}
                        style={{ width: `${s.relevance}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-gray-600 w-8 text-right">{s.relevance}%</span>
                  </div>
                ))}
              </div>
            </InfoCard>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <InfoCard title="Strengths">
              <ul className="space-y-2">
                {summary.strengths.map((s, i) => (
                  <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                    <span className="text-green-500 mt-0.5">+</span> {s}
                  </li>
                ))}
              </ul>
            </InfoCard>
            <InfoCard title="Areas for Improvement">
              <ul className="space-y-2">
                {summary.weaknesses.map((w, i) => (
                  <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                    <span className="text-yellow-500 mt-0.5">!</span> {w}
                  </li>
                ))}
              </ul>
            </InfoCard>
          </div>

          <InfoCard title="Career Highlights">
            <ul className="space-y-2">
              {summary.career_highlights.map((h, i) => (
                <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                  <span className="text-blue-500 mt-0.5">&#x2022;</span> {h}
                </li>
              ))}
            </ul>
          </InfoCard>

          <InfoCard title="Risk Assessment">
            <ul className="space-y-2">
              {summary.risk_factors.map((r, i) => (
                <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                  <span className="text-orange-500 mt-0.5">&#x26A0;</span> {r}
                </li>
              ))}
            </ul>
          </InfoCard>

          {summary.education_summary.length > 0 && (
            <InfoCard title="Education">
              <div className="flex flex-wrap gap-2">
                {summary.education_summary.map((e, i) => (
                  <Badge key={i} label={e} color="bg-blue-50 text-blue-700" />
                ))}
              </div>
            </InfoCard>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-3xl font-bold text-primary-600">{summary.certification_count}</p>
              <p className="text-xs font-medium text-gray-500 uppercase mt-1">Certifications</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-3xl font-bold text-primary-600">{summary.project_count}</p>
              <p className="text-xs font-medium text-gray-500 uppercase mt-1">Projects</p>
            </div>
          </div>
        </>
      )}

      {scores.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">My Job Match Scores</h3>
          <div className="space-y-3">
            {scores.map((s) => {
              const scoreColor =
                s.overall_match_score >= 80 ? "bg-green-500" :
                s.overall_match_score >= 60 ? "bg-blue-500" :
                s.overall_match_score >= 40 ? "bg-yellow-500" : "bg-red-500";
              return (
                <div key={s.id} className="flex items-center gap-4 p-3 rounded-lg border border-gray-100">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">Job: {s.job_id.slice(0, 8)}...</p>
                    <div className="flex items-center gap-3 mt-1">
                      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${scoreColor}`} style={{ width: `${s.overall_match_score}%` }} />
                      </div>
                      <span className="text-sm font-bold text-gray-700">{s.overall_match_score}%</span>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                    s.strength_level === "excellent" ? "bg-green-100 text-green-700" :
                    s.strength_level === "good" ? "bg-blue-100 text-blue-700" :
                    s.strength_level === "average" ? "bg-yellow-100 text-yellow-700" :
                    "bg-red-100 text-red-700"
                  }`}>
                    {s.strength_level}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
