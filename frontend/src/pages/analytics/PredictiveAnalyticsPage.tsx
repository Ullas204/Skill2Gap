import { useEffect, useState } from "react";

import { analyticsApi } from "../../api/analytics";
import { ChartCard } from "../../components/analytics/ChartCard";
import { DistributionBar } from "../../components/analytics/DistributionBar";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import type { PredictiveAnalytics } from "../../types/analytics";

export function PredictiveAnalyticsPage() {
  const [data, setData] = useState<PredictiveAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analyticsApi
      .getPredictions()
      .then(setData)
      .catch(() => setError("Failed to load predictions"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!data) return null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Predictive Analytics</h1>
        <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
          Confidence: {data.confidence_score.toFixed(0)}%
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ChartCard data={data.demand_forecast} type="line" />
        <ChartCard data={data.hiring_timeline} type="line" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Attrition Risk by Department</h4>
          <div className="space-y-3">
            {data.attrition_risk.map((r) => (
              <div key={r.label} className="flex items-center gap-3">
                <span className="text-sm text-gray-700 w-24">{r.label}</span>
                <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${r.value > 60 ? "bg-red-500" : r.value > 40 ? "bg-yellow-500" : "bg-green-500"}`}
                    style={{ width: `${r.value}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-600 w-12 text-right">{r.value.toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
        <DistributionBar data={data.skill_gap_forecast} title="Skill Gap Forecast" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">AI Recommendations</h4>
        <ul className="space-y-2">
          {data.recommendations.map((rec, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
              <span className="text-primary-500 font-bold mt-0.5">•</span>
              {rec}
            </li>
          ))}
        </ul>
      </div>

      <ChartCard data={data.budget_projection} />
    </div>
  );
}
