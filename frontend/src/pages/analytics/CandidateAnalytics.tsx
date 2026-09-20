import { useEffect, useState } from "react";

import { analyticsApi } from "../../api/analytics";
import { KPICard } from "../../components/analytics/KPICard";
import { ChartCard } from "../../components/analytics/ChartCard";
import { DistributionBar } from "../../components/analytics/DistributionBar";
import { StatusBreakdownChart } from "../../components/analytics/StatusBreakdownChart";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import type { CandidatePerformance } from "../../types/analytics";

export function CandidateAnalytics() {
  const [data, setData] = useState<CandidatePerformance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analyticsApi
      .getCandidatePerformance()
      .then(setData)
      .catch(() => setError("Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!data) return null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">My Performance Analytics</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard label="Overall Score" value={data.overall_score} unit="/100" color="primary" />
        <KPICard label="Skill Match" value={data.skill_match_pct} unit="%" color="green" />
        <KPICard label="Interview Avg" value={data.interview_avg_score} unit="/100" color="blue" />
        <KPICard label="Rank Percentile" value={`P${data.rank_percentile.toFixed(0)}`} color="purple" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ChartCard data={data.score_trend} type="line" />
        <StatusBreakdownChart data={data.applications_by_status} title="Applications by Status" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DistributionBar data={data.strongest_skills} title="Top Skills" />
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Improvement Areas</h4>
          <ul className="space-y-2">
            {data.improvement_areas.map((area) => (
              <li key={area} className="flex items-center gap-2 text-sm text-gray-600">
                <span className="w-2 h-2 rounded-full bg-yellow-400" />
                {area}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
