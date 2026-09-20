import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { Button } from "../../components/ui/Button";
import { StatCard } from "../../components/dashboard/StatCard";
import { EmptySimulationState } from "../../components/simulations/EmptySimulationState";
import { ScenarioStatusBadge } from "../../components/simulations/ScenarioStatusBadge";
import { useToast } from "../../contexts/ToastContext";
import { simulationApi } from "../../api/simulations";
import { recruiterJobApi } from "../../api/jobs";
import type { SimulationScenarioListResponse } from "../../types/simulations";
import { isSimulationEditable } from "../../types/simulations";

export function SimulationDashboard() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [data, setData] = useState<SimulationScenarioListResponse | null>(null);
  const [jobCount, setJobCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [list, jobs] = await Promise.all([
        simulationApi.list(),
        recruiterJobApi.listJobs(),
      ]);
      setData(list);
      setJobCount(jobs.length);
    } catch {
      addToast("Failed to load simulations", "error");
    }
  }, [addToast]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await loadData();
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [loadData]);

  async function handleDelete(id: string) {
    try {
      await simulationApi.remove(id);
      addToast("Simulation deleted", "success");
      await loadData();
    } catch {
      addToast("Failed to delete simulation", "error");
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  const stats = data?.stats;
  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Simulation Intelligence</h1>
          <p className="mt-1 text-sm text-gray-500">
            Build hiring-strategy sandboxes to test &quot;what-if&quot; screening configurations
          </p>
        </div>
        <Button onClick={() => navigate("/recruiter/simulations/create")}>
          New Simulation
        </Button>
      </div>

      {stats && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
          <StatCard title="Total" value={stats.total} color="primary" />
          <StatCard title="Drafts" value={stats.drafts} color="amber" />
          <StatCard title="Ready" value={stats.ready} color="blue" />
          <StatCard
            title="Running"
            value={stats.running}
            color="purple"
            subtitle={`${stats.queued} queued`}
          />
          <StatCard title="Completed" value={stats.completed} color="green" />
          <StatCard title="Failed" value={stats.failed} color="red" />
        </div>
      )}

      {items.length === 0 ? (
        jobCount === 0 ? (
          <EmptySimulationState
            title="No simulations yet."
            description="Simulations are built against a job posting. Create a job first."
            actionLabel="Post your first job"
            onAction={() => navigate("/recruiter/jobs/create")}
          />
        ) : (
          <EmptySimulationState
            title="No simulations yet."
            description="Create a hiring-strategy sandbox to test a different screening configuration."
            actionLabel="Create your first simulation"
            onAction={() => navigate("/recruiter/simulations/create")}
          />
        )
      ) : (
        <div className="overflow-hidden rounded-lg border bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Simulation
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Created by
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Created
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-6 py-4">
                    <button
                      onClick={() => navigate(`/recruiter/simulations/${item.id}`)}
                      className="text-sm font-medium text-gray-900 hover:text-primary-600"
                    >
                      {item.name}
                    </button>
                    <div className="text-sm text-gray-500">
                      {item.job_title} · {item.company}
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <ScenarioStatusBadge status={item.status} />
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {item.created_by_name}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {new Date(item.created_at).toLocaleDateString()}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                    <div className="flex items-center justify-end gap-3">
                      <button
                        onClick={() => navigate(`/recruiter/simulations/${item.id}`)}
                        className="text-primary-600 hover:text-primary-900"
                      >
                        View
                      </button>
                      {isSimulationEditable(item.status) && (
                        <button
                          onClick={() => handleDelete(item.id)}
                          className="text-red-600 hover:text-red-800"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}