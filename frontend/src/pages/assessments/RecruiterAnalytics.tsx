import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { assessmentApi } from "../../api/assessment";
import type { AnalyticsResponse } from "../../types/assessment";

const REC_STYLES: Record<string, string> = {
  strong_hire: "bg-green-100 text-green-800",
  hire: "bg-emerald-100 text-emerald-800",
  consider: "bg-yellow-100 text-yellow-800",
  reject: "bg-red-100 text-red-700",
};

export function RecruiterAssessmentAnalytics() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!assessmentId) return;
    assessmentApi
      .analytics(assessmentId)
      .then(setData)
      .catch(() => setError("Failed to load analytics."));
  }, [assessmentId]);

  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>;
  if (!data) return <LoadingSpinner size="lg" className="mt-20" />;

  const kpis = [
    { label: "Assigned", value: data.total_assigned },
    { label: "Completed", value: data.completed },
    { label: "In progress", value: data.in_progress },
    { label: "Completion", value: `${Math.round(data.completion_rate)}%` },
    { label: "Avg score", value: `${Math.round(data.average_score)}%` },
    { label: "Pass rate", value: `${Math.round(data.pass_rate)}%` },
    { label: "Median time", value: `${Math.round(data.median_time_minutes)}m` },
    { label: "Coding success", value: `${Math.round(data.coding_success_rate)}%` },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{data.title}</h1>
          <p className="mt-1 text-sm text-gray-500">Assessment analytics &amp; candidate comparison</p>
        </div>
        <Link
          to="/recruiter/assessments"
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Back to library
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
        {kpis.map((k) => (
          <div key={k.label} className="rounded-xl border border-gray-200 bg-white p-4 text-center shadow-sm">
            <p className="text-xl font-bold text-primary-700">{k.value}</p>
            <p className="mt-1 text-xs text-gray-500">{k.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Skill performance */}
        {Object.keys(data.skill_performance).length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Skill performance</h2>
            <div className="space-y-3">
              {Object.entries(data.skill_performance).sort((a, b) => b[1] - a[1]).map(([skill, pct]) => (
                <div key={skill}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="font-medium capitalize text-gray-700">{skill}</span>
                    <span className="text-gray-500">{Math.round(pct)}%</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
                    <div
                      className={`h-full rounded-full ${pct >= 70 ? "bg-green-500" : pct >= 50 ? "bg-yellow-400" : "bg-red-400"}`}
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Difficulty performance */}
        {Object.keys(data.difficulty_performance).length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Difficulty performance</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {Object.entries(data.difficulty_performance).map(([d, pct]) => (
                <div key={d} className="rounded-lg bg-gray-50 p-3 text-center">
                  <p className={`text-lg font-bold ${pct >= 70 ? "text-green-600" : pct >= 50 ? "text-yellow-600" : "text-red-500"}`}>
                    {Math.round(pct)}%
                  </p>
                  <p className="text-xs capitalize text-gray-500">{d}</p>
                </div>
              ))}
            </div>
            <h2 className="mb-3 mt-6 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Question-level accuracy (hardest first)
            </h2>
            <div className="max-h-56 space-y-2 overflow-y-auto pr-1">
              {[...data.question_accuracy].sort((a, b) => a.accuracy - b.accuracy).slice(0, 12).map((q) => (
                <div key={q.question_id} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 text-sm">
                  <span className="truncate capitalize text-gray-600">{q.topic.replace(/_/g, " ")} · {q.type.replace(/_/g, " ")}</span>
                  <span className="ml-3 shrink-0 font-semibold text-gray-700">{q.accuracy}% ({q.responses})</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Candidate leaderboard */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <h2 className="border-b border-gray-200 px-4 py-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Candidates
        </h2>
        {data.candidates.length === 0 ? (
          <p className="p-8 text-center text-sm text-gray-400">No completed attempts yet.</p>
        ) : (
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                {["#", "Candidate", "Attempts", "Best", "Latest", "Recommendation"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.candidates.map((c, i) => (
                <tr key={c.candidate_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-400">{i + 1}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{c.candidate_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{c.attempts}</td>
                  <td className="px-4 py-3 text-sm font-bold text-primary-700">{Math.round(c.best_score)}%</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{Math.round(c.latest_score)}%</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${REC_STYLES[c.recommendation] || "bg-gray-100"}`}>
                      {c.recommendation.replace(/_/g, " ")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
