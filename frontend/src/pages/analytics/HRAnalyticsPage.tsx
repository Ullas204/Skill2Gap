import { useEffect, useState } from "react";

import { analyticsApi } from "../../api/analytics";
import { KPICard } from "../../components/analytics/KPICard";
import { ChartCard } from "../../components/analytics/ChartCard";
import { DistributionBar } from "../../components/analytics/DistributionBar";
import { StatusBreakdownChart } from "../../components/analytics/StatusBreakdownChart";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import type { HRAnalytics } from "../../types/analytics";

export function HRAnalyticsPage() {
  const [data, setData] = useState<HRAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analyticsApi
      .getHRAnalytics()
      .then(setData)
      .catch(() => setError("Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!data) return null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">HR Analytics</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard label="Headcount" value={data.total_headcount} color="blue" />
        <KPICard label="Open Positions" value={data.open_positions} color="green" />
        <KPICard label="Avg Time to Hire" value={data.avg_time_to_hire} unit="days" color="yellow" />
        <KPICard label="Diversity Index" value={data.diversity_index.toFixed(2)} color="purple" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ChartCard data={data.headcount_trend} type="line" />
        <StatusBreakdownChart data={data.hiring_funnel} title="Hiring Funnel" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <DistributionBar data={data.department_distribution} title="Department Distribution" />
        <DistributionBar data={data.gender_distribution} title="Gender Distribution" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Recruiter Performance</h4>
        <div className="space-y-3">
          {data.recruiter_performance.map((r) => (
            <div key={r.label} className="flex items-center gap-3">
              <span className="text-sm text-gray-700 w-24">{r.label}</span>
              <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-primary-500 rounded-full" style={{ width: `${r.value}%` }} />
              </div>
              <span className="text-sm font-medium text-gray-600 w-12 text-right">{r.value}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
