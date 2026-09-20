import { useEffect, useState } from "react";

import { analyticsApi } from "../../api/analytics";
import { KPICard } from "../../components/analytics/KPICard";
import { ChartCard } from "../../components/analytics/ChartCard";
import { DistributionBar } from "../../components/analytics/DistributionBar";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import type { AdminAnalytics } from "../../types/analytics";

export function AdminAnalyticsPage() {
  const [data, setData] = useState<AdminAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analyticsApi
      .getAdminAnalytics()
      .then(setData)
      .catch(() => setError("Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!data) return null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">System Administration Analytics</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard label="Total Users" value={data.total_users} color="blue" />
        <KPICard label="Active Users" value={data.active_users} color="green" />
        <KPICard label="System Health" value={`${data.system_health_score}%`} color="green" />
        <KPICard label="API Calls Today" value={data.api_calls_today} color="purple" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ChartCard data={data.users_trend} type="line" />
        <DistributionBar data={data.users_by_role} title="Users by Role" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Security Events</h4>
          <div className="space-y-2">
            {data.security_events.map((e) => (
              <div key={e.label} className="flex items-center justify-between text-sm">
                <span className="text-gray-600">{e.label}</span>
                <span className="font-medium text-gray-800">{e.value}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">System Load</h4>
          <div className="space-y-3">
            {data.system_load.map((l) => (
              <div key={l.label} className="flex items-center gap-3">
                <span className="text-sm text-gray-700 w-16">{l.label}</span>
                <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${l.value > 80 ? "bg-red-500" : l.value > 60 ? "bg-yellow-500" : "bg-green-500"}`}
                    style={{ width: `${l.value}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-600 w-12 text-right">{l.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-1">Storage</h4>
        <p className="text-sm text-gray-500">Used: {data.storage_used_mb} MB</p>
      </div>
    </div>
  );
}
