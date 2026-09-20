import { useEffect, useState } from "react";

import { analyticsApi } from "../../api/analytics";
import { KPICard } from "../../components/analytics/KPICard";
import { ChartCard } from "../../components/analytics/ChartCard";
import { DistributionBar } from "../../components/analytics/DistributionBar";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import type { ExecutiveKPIs } from "../../types/analytics";

export function ExecutiveKPIsPage() {
  const [data, setData] = useState<ExecutiveKPIs | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analyticsApi
      .getExecutiveKPIs()
      .then(setData)
      .catch(() => setError("Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!data) return null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Executive KPIs</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard label="Revenue per Hire" value={`$${data.revenue_per_hire.toLocaleString()}`} color="green" />
        <KPICard label="Cost per Hire" value={`$${data.cost_per_hire.toLocaleString()}`} color="yellow" />
        <KPICard label="Quality of Hire" value={data.quality_of_hire.toFixed(1)} unit="/100" color="primary" />
        <KPICard label="Time to Productivity" value={data.time_to_productivity} unit="days" color="blue" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ChartCard data={data.hiring_forecast} type="line" />
        <ChartCard data={data.quarterly_trends} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Department KPIs</h4>
          <div className="space-y-3">
            {data.department_kpis.map((d) => (
              <div key={d.label} className="flex items-center gap-3">
                <span className="text-sm text-gray-700 w-28">{d.label}</span>
                <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-primary-500 rounded-full" style={{ width: `${d.value}%` }} />
                </div>
                <span className="text-sm font-medium text-gray-600 w-12 text-right">{d.value}%</span>
              </div>
            ))}
          </div>
        </div>
        <DistributionBar data={data.risk_indicators} title="Risk Indicators" />
      </div>
    </div>
  );
}
