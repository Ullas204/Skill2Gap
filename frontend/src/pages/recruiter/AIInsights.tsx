import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { getRecruiterAIDashboard, getTopCandidates } from "../../api/screening";
import type { RecruiterDashboardSummary, TopCandidatesResponse } from "../../types/screening";

function ScoreRing({ score, size = 80 }: { score: number; size?: number }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = score >= 80 ? "#22c55e" : score >= 60 ? "#3b82f6" : score >= 40 ? "#eab308" : "#ef4444";
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#e5e7eb" strokeWidth="6" />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="6"
        strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`} />
      <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="central"
        className="font-bold" fill={color} fontSize={size * 0.25}>
        {score}
      </text>
    </svg>
  );
}

function StatBox({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  );
}

export function RecruiterAIInsights() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<RecruiterDashboardSummary | null>(null);
  const [topCandidates, setTopCandidates] = useState<TopCandidatesResponse | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [dash, top] = await Promise.all([
          getRecruiterAIDashboard(),
          getTopCandidates(undefined, 5),
        ]);
        setDashboard(dash);
        setTopCandidates(top);
      } catch {
        addToast("Failed to load AI insights", "error");
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
        <h1 className="text-2xl font-bold text-gray-900">AI Hiring Intelligence</h1>
        <p className="mt-1 text-sm text-gray-500">Comprehensive AI-powered insights across your recruitment pipeline</p>
      </div>

      {dashboard && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatBox label="Total Jobs" value={dashboard.total_jobs} color="text-blue-600" />
            <StatBox label="Applications" value={dashboard.total_applications} color="text-purple-600" />
            <StatBox label="AI Screened" value={dashboard.total_screened} color="text-green-600" />
            <StatBox label="Avg Score" value={`${dashboard.average_score}%`} color={dashboard.average_score >= 70 ? "text-green-600" : "text-yellow-600"} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Job Pipeline Overview</h3>
              <div className="space-y-3">
                {dashboard.job_summaries.map((job) => (
                  <Link
                    key={job.job_id}
                    to={`/recruiter/jobs/${job.job_id}/rankings`}
                    className="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{job.job_title}</p>
                      <p className="text-xs text-gray-500">{job.applicant_count} applicants &middot; {job.screened_count} screened</p>
                    </div>
                    <div className="flex items-center gap-3">
                      {job.top_candidate_name && (
                        <div className="text-right hidden sm:block">
                          <p className="text-xs text-gray-500">Top: {job.top_candidate_name}</p>
                          <p className="text-xs font-bold text-green-600">{job.top_candidate_score}%</p>
                        </div>
                      )}
                      <ScoreRing score={job.average_score} size={48} />
                    </div>
                  </Link>
                ))}
                {dashboard.job_summaries.length === 0 && (
                  <p className="text-sm text-gray-500 text-center py-4">No jobs created yet</p>
                )}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Candidate Activity</h3>
              <div className="space-y-3">
                {dashboard.recent_rankings.map((r, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-gray-100">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{r.candidate_name}</p>
                      <p className="text-xs text-gray-500">{r.job_title}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-gray-400">#{r.rank}</span>
                      <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                        r.score >= 80 ? "bg-green-100 text-green-800" :
                        r.score >= 60 ? "bg-blue-100 text-blue-800" :
                        r.score >= 40 ? "bg-yellow-100 text-yellow-800" :
                        "bg-red-100 text-red-800"
                      }`}>
                        {r.score}%
                      </span>
                      {r.rank_change > 0 && <span className="text-green-500 text-xs">+{r.rank_change}</span>}
                      {r.rank_change < 0 && <span className="text-red-500 text-xs">{r.rank_change}</span>}
                    </div>
                  </div>
                ))}
                {dashboard.recent_rankings.length === 0 && (
                  <p className="text-sm text-gray-500 text-center py-4">No recent activity</p>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {topCandidates && topCandidates.candidates.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Candidates Across All Jobs</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Rank</th>
                  <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Candidate</th>
                  <th className="text-center py-2 px-3 text-xs font-medium text-gray-500 uppercase">Score</th>
                  <th className="text-center py-2 px-3 text-xs font-medium text-gray-500 uppercase">Level</th>
                  <th className="text-center py-2 px-3 text-xs font-medium text-gray-500 uppercase">Recommendation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {topCandidates.candidates.map((c, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="py-3 px-3 font-bold text-gray-400">#{c.rank}</td>
                    <td className="py-3 px-3">
                      <p className="font-medium text-gray-900">{c.candidate_name}</p>
                      <p className="text-xs text-gray-500">{c.candidate_email}</p>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                        c.overall_score >= 80 ? "bg-green-100 text-green-800" :
                        c.overall_score >= 60 ? "bg-blue-100 text-blue-800" :
                        c.overall_score >= 40 ? "bg-yellow-100 text-yellow-800" :
                        "bg-red-100 text-red-800"
                      }`}>
                        {c.overall_score}%
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={`text-xs font-medium capitalize ${
                        c.strength_level === "excellent" ? "text-green-600" :
                        c.strength_level === "good" ? "text-blue-600" :
                        c.strength_level === "average" ? "text-yellow-600" : "text-red-600"
                      }`}>
                        {c.strength_level}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={`text-xs font-medium ${
                        c.recommendation === "strongly_recommend" ? "text-green-700" :
                        c.recommendation === "recommend" ? "text-blue-700" :
                        c.recommendation === "consider" ? "text-yellow-700" : "text-red-700"
                      }`}>
                        {c.recommendation.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase())}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
