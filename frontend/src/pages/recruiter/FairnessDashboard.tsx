import { useState, useEffect } from "react";
import {
  getFairnessOverview,
  getFairnessMetrics,
  getBiasAlerts,
} from "../../api/fairness";
import {
  FairnessScoreCard,
  FairnessMetricsTable,
  BiasAlertPanel,
  DiversityStat,
} from "../../components/fairness/FairnessComponents";
import type { FairnessOverview, FairnessMetrics, BiasAlert } from "../../types/fairness";

export function RecruiterFairnessDashboard() {
  const [overview, setOverview] = useState<FairnessOverview | null>(null);
  const [metrics, setMetrics] = useState<FairnessMetrics | null>(null);
  const [alerts, setAlerts] = useState<BiasAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [ov, met, al] = await Promise.all([
          getFairnessOverview(),
          getFairnessMetrics(),
          getBiasAlerts(20),
        ]);
        setOverview(ov);
        setMetrics(met);
        setAlerts(al);
      } catch {
        setError("Failed to load fairness data. You may not have permission.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Fairness & Bias Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Monitor AI fairness, detect bias, and ensure ethical hiring.</p>
      </div>

      {overview && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="col-span-1 md:col-span-2 flex justify-center">
              <FairnessScoreCard score={overview.overall_fairness_score} label="Overall Fairness" />
            </div>
            <DiversityStat label="Total Screened" value={overview.total_screened} color="blue" />
            <DiversityStat label="Total Candidates" value={overview.total_candidates} color="green" />
            <DiversityStat label="Total Jobs" value={overview.total_jobs} color="purple" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <DiversityStat
              label="Gender Diversity Index"
              value={overview.diversity_indicators?.gender_diversity_index?.toFixed(3) || "N/A"}
              color="orange"
            />
            <DiversityStat
              label="Location Diversity Index"
              value={overview.diversity_indicators?.location_diversity_index?.toFixed(3) || "N/A"}
              color="green"
            />
            <DiversityStat
              label="Compliance Status"
              value={overview.compliance_status?.replace(/_/g, " ") || "N/A"}
              color={overview.compliance_status === "compliant" ? "green" : "orange"}
            />
          </div>
        </>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {metrics && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Fairness Metrics</h2>
            <FairnessMetricsTable
              metrics={{
                statistical_parity_difference: metrics.statistical_parity_difference,
                disparate_impact_ratio: metrics.disparate_impact_ratio,
                equal_opportunity_difference: metrics.equal_opportunity_difference,
                demographic_parity: metrics.demographic_parity,
                consistency_score: metrics.consistency_score,
                composite_fairness_score: metrics.composite_fairness_score,
              }}
            />
            <p className="text-xs text-gray-500 mt-2">Based on {metrics.data_points} data points</p>
          </div>
        )}

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Bias Alerts</h2>
          <BiasAlertPanel alerts={alerts} />
        </div>
      </div>

      {overview?.diversity_indicators && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Candidate Distribution</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Gender Distribution</h3>
              {Object.entries(overview.diversity_indicators.gender_distribution || {}).map(([gender, count]) => (
                <div key={gender} className="flex items-center gap-2 mb-1">
                  <span className="text-sm text-gray-600 w-32">{gender.replace(/_/g, " ")}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-blue-500"
                      style={{ width: `${(count / Math.max(overview.total_candidates, 1)) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-8">{count}</span>
                </div>
              ))}
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Location Distribution</h3>
              {Object.entries(overview.diversity_indicators.location_distribution || {}).map(([loc, count]) => (
                <div key={loc} className="flex items-center gap-2 mb-1">
                  <span className="text-sm text-gray-600 w-32 truncate">{loc}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-purple-500"
                      style={{ width: `${(count / Math.max(overview.total_candidates, 1)) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-8">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
