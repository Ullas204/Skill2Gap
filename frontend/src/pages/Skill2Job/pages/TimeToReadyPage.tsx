import { useState, useEffect } from "react";
import { GitCompare } from "lucide-react";
import { skill2jobApi } from "../../../api/skill2job";
import type { OverviewTimeToReadyItem } from "../../../types/skill2job";
import { TimeToReadyPanel } from "../TimeToReadyPanel";

export default function TimeToReadyPage() {
  const [compareHours, setCompareHours] = useState(10);
  const [compareData, setCompareData] = useState<OverviewTimeToReadyItem[]>([]);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setCompareLoading(true);
    setCompareError("");
    skill2jobApi
      .compareJobs(compareHours)
      .then((data) => {
        if (!cancelled) setCompareData(data);
      })
      .catch((err) => {
        if (!cancelled) {
          const detail = err?.response?.data?.detail;
          setCompareError(
            typeof detail === "string" ? detail : "Failed to load comparison data."
          );
        }
      })
      .finally(() => {
        if (!cancelled) setCompareLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [compareHours]);

  return (
    <div className="space-y-8">
      <TimeToReadyPanel />

      {/* Compare Target Jobs */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <GitCompare className="h-5 w-5 text-primary-600" />
              Compare Target Jobs
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Side-by-side comparison of time-to-ready across all matched jobs.
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Hours / Week</label>
            <select
              value={compareHours}
              onChange={(e) => setCompareHours(Number(e.target.value))}
              className="mt-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
            >
              {[5, 10, 15, 20, 25, 30, 40].map((h) => (
                <option key={h} value={h}>
                  {h}h
                </option>
              ))}
            </select>
          </div>
        </div>

        {compareLoading && (
          <div className="mt-6 flex items-center justify-center py-12 text-sm text-gray-400">
            <svg
              className="mr-2 h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Loading comparison…
          </div>
        )}

        {compareError && (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {compareError}
          </div>
        )}

        {!compareLoading && !compareError && compareData.length === 0 && (
          <div className="mt-6 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-8 text-center text-sm text-gray-400">
            No comparison data available. Run a time-to-ready calculation first.
          </div>
        )}

        {!compareLoading && compareData.length > 0 && (
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-xs font-medium uppercase text-gray-500">
                  <th className="px-4 py-3">Job Title</th>
                  <th className="px-4 py-3 text-right">Missing Skills</th>
                  <th className="px-4 py-3 text-right">Weeks</th>
                  <th className="px-4 py-3 text-right">Cost</th>
                  <th className="px-4 py-3 text-right">Free Weeks</th>
                  <th className="px-4 py-3 text-right">Free Cost</th>
                  <th className="px-4 py-3 text-right">Coverage %</th>
                  <th className="px-4 py-3 text-right">Readiness</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {compareData.map((item) => (
                  <tr
                    key={item.job_id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="max-w-[260px] truncate px-4 py-3 font-medium text-gray-900">
                      {item.job_title}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {item.missing_skills_count}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {item.estimated_weeks}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {item.estimated_cost === 0
                        ? "Free"
                        : `${item.currency} ${item.estimated_cost.toLocaleString()}`}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {item.free_only_weeks}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {item.free_only_cost === 0
                        ? "Free"
                        : `${item.currency} ${item.free_only_cost.toLocaleString()}`}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {item.coverage_pct}%
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          item.readiness >= 0.8
                            ? "bg-green-100 text-green-700"
                            : item.readiness >= 0.5
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-red-100 text-red-700"
                        }`}
                      >
                        {Math.round(item.readiness * 100)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
