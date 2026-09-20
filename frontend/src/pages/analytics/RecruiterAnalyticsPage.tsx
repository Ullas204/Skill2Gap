import { useEffect, useState } from "react";

import { analyticsApi } from "../../api/analytics";
import { KPICard } from "../../components/analytics/KPICard";
import { ChartCard } from "../../components/analytics/ChartCard";
import { DistributionBar } from "../../components/analytics/DistributionBar";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import type { RecruiterAnalytics } from "../../types/analytics";

export function RecruiterAnalytics() {
  const [data, setData] = useState<RecruiterAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analyticsApi
      .getRecruiterAnalytics()
      .then(setData)
      .catch(() => setError("Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!data) return null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Recruiter Analytics</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard label="Active Jobs" value={data.active_jobs} color="green" />
        <KPICard label="Total Applicants" value={data.total_applicants} color="blue" />
        <KPICard label="Avg Time to Fill" value={data.avg_time_to_fill} unit="days" color="yellow" />
        <KPICard label="Hire Rate" value={`${(data.hire_rate * 100).toFixed(0)}%`} color="primary" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ChartCard data={data.applicants_trend} type="line" />
        <DistributionBar data={data.source_effectiveness} title="Source Effectiveness" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Pipeline Velocity</h4>
        <div className="flex items-center gap-4">
          {data.pipeline_velocity.map((step, i) => (
            <div key={step.label} className="flex-1 text-center">
              <div className="text-2xl font-bold text-primary-600">{step.value}</div>
              <div className="text-xs text-gray-500 mt-1">{step.label}</div>
              {i < data.pipeline_velocity.length - 1 && (
                <div className="text-gray-300 text-lg">→</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
