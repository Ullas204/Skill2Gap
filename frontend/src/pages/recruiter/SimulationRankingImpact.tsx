import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { Button } from "../../components/ui/Button";
import { ScenarioStatusBadge } from "../../components/simulations/ScenarioStatusBadge";
import { useToast } from "../../contexts/ToastContext";
import { simulationApi } from "../../api/simulations";
import {
  MOVEMENT_CATEGORY_LABELS,
  SHORTLIST_CHANGE_LABELS,
  formatImpactDelta,
  formatImpactPercentage,
  type CandidateImpactDetail,
  type CandidateImpactListResponse,
  type ImpactMovementFilter,
  type RankingImpactResponse,
} from "../../types/rankingImpact";
import type {
  SimulationExecution,
  SimulationScenario,
} from "../../types/simulations";

const PAGE_SIZE = 20;

// ─── Helper Components ─────────────────────────────────────────────

function StatCard({
  label,
  value,
  delta,
  deltaLabel,
  positive,
}: {
  label: string;
  value: string | number;
  delta?: number;
  deltaLabel?: string;
  positive?: boolean;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      {delta !== undefined && (
        <p
          className={`mt-0.5 text-xs font-medium ${
            positive === true
              ? "text-green-600"
              : positive === false
                ? "text-red-600"
                : "text-gray-500"
          }`}
        >
          {deltaLabel ?? formatImpactDelta(delta)}
        </p>
      )}
    </div>
  );
}

function SectionCard({
  title,
  children,
  className = "",
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white p-5 ${className}`}>
      <h2 className="mb-3 text-lg font-semibold text-gray-900">{title}</h2>
      {children}
    </div>
  );
}

function InsightCardItem({ message, type }: { message: string; type: string }) {
  const icons: Record<string, string> = {
    movement: "↕",
    shortlist: "★",
    qualification: "✓",
    distribution: "📊",
    stability: "🔒",
  };
  return (
    <div className="flex items-start gap-2 rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-sm">
      <span className="mt-0.5 text-base" aria-hidden="true">
        {icons[type] ?? "•"}
      </span>
      <span className="text-gray-700">{message}</span>
    </div>
  );
}

function MoverRow({ mover, direction }: { mover: RankingImpactResponse["top_upward_movers"][0]; direction: "up" | "down" }) {
  const color = direction === "up" ? "text-green-600" : "text-red-600";
  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-sm">
      <div className="flex items-center gap-3">
        <span className="font-medium text-gray-900">{mover.candidate_name}</span>
        <span className="text-xs text-gray-500">
          #{mover.baseline_rank} → #{mover.simulation_rank}
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-gray-500">
          {mover.baseline_score} → {mover.simulation_score}
        </span>
        <span className={`font-semibold ${color}`}>
          {formatImpactDelta(mover.rank_change)} rank
        </span>
      </div>
    </div>
  );
}

function DistributionBar({
  baseline,
  simulation,
  max,
}: {
  baseline: number;
  simulation: number;
  max: number;
}) {
  const bWidth = max > 0 ? (baseline / max) * 100 : 0;
  const sWidth = max > 0 ? (simulation / max) * 100 : 0;
  return (
    <div className="flex flex-col gap-1">
      <div className="h-3 w-full rounded bg-gray-100">
        <div
          className="h-3 rounded bg-gray-400"
          style={{ width: `${bWidth}%` }}
          title={`Baseline: ${baseline}`}
        />
      </div>
      <div className="h-3 w-full rounded bg-gray-100">
        <div
          className="h-3 rounded bg-primary-500"
          style={{ width: `${sWidth}%` }}
          title={`Simulation: ${simulation}`}
        />
      </div>
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────

export function SimulationRankingImpact() {
  const { simulationId } = useParams<{ simulationId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { addToast } = useToast();

  const [scenario, setScenario] = useState<SimulationScenario | null>(null);
  const [executions, setExecutions] = useState<SimulationExecution[]>([]);
  const [impact, setImpact] = useState<RankingImpactResponse | null>(null);
  const [candidates, setCandidates] = useState<CandidateImpactListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [candidatePage, setCandidatePage] = useState(1);
  const [movementFilter, setMovementFilter] = useState<"" | ImpactMovementFilter>("");

  const selectedExecutionId = searchParams.get("execution_id");

  const latestCompleted = executions
    .filter((e) => e.status === "completed")
    .sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null;

  const loadScenario = useCallback(async () => {
    if (!simulationId) return;
    try {
      const data = await simulationApi.get(simulationId);
      setScenario(data);
    } catch {
      setNotFound(true);
    }
  }, [simulationId]);

  const loadExecutions = useCallback(async () => {
    if (!simulationId) return;
    const data = await simulationApi.listExecutions(simulationId);
    setExecutions(data.items);
    return data.items;
  }, [simulationId]);

  const loadImpact = useCallback(
    async (executionId: string | null) => {
      if (!simulationId) return;
      try {
        const data = await simulationApi.getRankingImpact(
          simulationId,
          executionId ?? undefined,
        );
        setImpact(data);
      } catch {
        addToast("Failed to load ranking impact analysis", "error");
      }
    },
    [simulationId, addToast],
  );

  const loadCandidates = useCallback(async () => {
    if (!simulationId) return;
    try {
      const data = await simulationApi.getRankingImpactCandidates(simulationId, {
        execution_id: selectedExecutionId ?? undefined,
        page: candidatePage,
        page_size: PAGE_SIZE,
        movement: movementFilter === "" ? undefined : movementFilter,
        sort_by: "simulation_rank",
        order: "asc",
      });
      setCandidates(data);
    } catch {
      // Silently handle — the main impact data is still available
    }
  }, [simulationId, selectedExecutionId, candidatePage, movementFilter]);

  useEffect(() => {
    setLoading(true);
    setNotFound(false);
    (async () => {
      try {
        await Promise.all([loadScenario(), loadExecutions()]);
      } catch {
        addToast("Failed to load simulation", "error");
      } finally {
        setLoading(false);
      }
    })();
  }, [loadScenario, loadExecutions, addToast]);

  useEffect(() => {
    if (!simulationId) return;
    void loadImpact(selectedExecutionId);
    void loadCandidates();
  }, [simulationId, selectedExecutionId, candidatePage, movementFilter, loadImpact, loadCandidates]);

  function selectExecution(executionId: string) {
    setSearchParams({ execution_id: executionId });
    setCandidatePage(1);
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  if (notFound || !scenario) {
    return (
      <div className="py-20 text-center">
        <p className="text-gray-500">Simulation not found.</p>
        <Link
          to="/recruiter/simulations"
          className="mt-4 inline-block text-sm font-medium text-primary-600 hover:text-primary-700"
        >
          Back to simulations
        </Link>
      </div>
    );
  }

  const selectedExecution =
    executions.find((e) => e.id === selectedExecutionId) ??
    (selectedExecutionId ? null : latestCompleted);

  if (!impact) {
    if (selectedExecution && selectedExecution.status !== "completed") {
      return (
        <div className="space-y-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {scenario.name} — Ranking Impact
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                {scenario.job_title} · {scenario.company}
              </p>
            </div>
            <Link
              to={`/recruiter/simulations/${scenario.id}`}
              className="text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              Back to scenario
            </Link>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-10 text-center">
            <ScenarioStatusBadge status={selectedExecution.status} />
            <p className="mt-3 text-gray-500">
              {selectedExecution.status === "draft"
                ? "Complete and save the scenario before running it."
                : selectedExecution.status === "ready"
                  ? "Run the simulation to generate ranking impact."
                  : selectedExecution.status === "queued" || selectedExecution.status === "running"
                    ? "Run in progress. Results will appear here when complete."
                    : selectedExecution.status === "failed"
                      ? "This execution failed. Please retry."
                      : "No completed execution available."}
            </p>
          </div>
        </div>
      );
    }
    return (
      <div className="py-20 text-center">
        <p className="text-gray-500">No completed simulation run available.</p>
        <Link
          to={`/recruiter/simulations/${scenario.id}`}
          className="mt-3 inline-block text-sm font-medium text-primary-600 hover:text-primary-700"
        >
          Run this simulation from the scenario page
        </Link>
      </div>
    );
  }

  const { overview, score_movement, rank_movement, shortlist_impact, qualification_matrix } = impact;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">
              {scenario.name} — Ranking Impact
            </h1>
            {selectedExecution && <ScenarioStatusBadge status={selectedExecution.status} />}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {scenario.job_title} · {scenario.company}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Link
            to={`/recruiter/simulations/${scenario.id}/results`}
            className="text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            View Results
          </Link>
          <Link
            to={`/recruiter/simulations/${scenario.id}`}
            className="text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            Back to scenario
          </Link>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        <span className="font-semibold">Read-only analysis.</span> All values are derived from
        persisted simulation results. No live hiring data was created or modified.
      </div>

      {/* Execution selector */}
      {executions.length > 0 && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">Execution:</span>
          <select
            value={selectedExecution?.id ?? ""}
            onChange={(e) => selectExecution(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none"
          >
            <option value="" disabled>
              Select an execution
            </option>
            {executions
              .slice()
              .sort((a, b) => b.created_at.localeCompare(a.created_at))
              .map((execution) => (
                <option key={execution.id} value={execution.id}>
                  {new Date(execution.created_at).toLocaleString()} · {execution.status} ·{" "}
                  {execution.total_candidates} candidates
                </option>
              ))}
          </select>
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Total Candidates"
          value={overview.total_candidates}
        />
        <StatCard
          label="Avg Score Change"
          value={overview.average_score_change.toFixed(1)}
          delta={overview.average_score_change}
          positive={overview.average_score_change > 0}
        />
        <StatCard
          label="Moved Up"
          value={overview.candidates_moved_up}
          delta={overview.candidates_moved_up}
          deltaLabel={`${formatImpactPercentage(overview.percentage_moved_up)} of pool`}
          positive
        />
        <StatCard
          label="Moved Down"
          value={overview.candidates_moved_down}
          delta={overview.candidates_moved_down}
          deltaLabel={`${formatImpactPercentage(overview.percentage_moved_down)} of pool`}
          positive={false}
        />
      </div>

      {/* Movement Categories */}
      {impact.movement_categories.length > 0 && (
        <SectionCard title="Movement Categories">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {impact.movement_categories.map((cat) => (
              <div
                key={cat.category}
                className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-center"
              >
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                  {MOVEMENT_CATEGORY_LABELS[cat.category] ?? cat.category}
                </p>
                <p className="mt-1 text-xl font-bold text-gray-900">{cat.count}</p>
                <p className="text-xs text-gray-500">{formatImpactPercentage(cat.percentage)}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Top Movers */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SectionCard title="Top Upward Movers">
          {impact.top_upward_movers.length === 0 ? (
            <p className="text-sm text-gray-500">No candidates moved upward.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {impact.top_upward_movers.map((mover) => (
                <MoverRow key={mover.candidate_id} mover={mover} direction="up" />
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Top Downward Movers">
          {impact.top_downward_movers.length === 0 ? (
            <p className="text-sm text-gray-500">No candidates moved downward.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {impact.top_downward_movers.map((mover) => (
                <MoverRow key={mover.candidate_id} mover={mover} direction="down" />
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      {/* Shortlist Impact + Qualification Matrix */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SectionCard title="Shortlist Impact">
          <dl className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Baseline shortlist</dt>
              <dd className="font-semibold text-gray-900">{shortlist_impact.baseline_size}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Simulation shortlist</dt>
              <dd className="font-semibold text-gray-900">{shortlist_impact.simulation_size}</dd>
            </div>
            <hr className="border-gray-100" />
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Retained</dt>
              <dd className="font-semibold text-gray-900">{shortlist_impact.candidates_retained}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Entered</dt>
              <dd className="font-semibold text-green-600">{shortlist_impact.candidates_entering}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Exited</dt>
              <dd className="font-semibold text-red-600">{shortlist_impact.candidates_leaving}</dd>
            </div>
            <hr className="border-gray-100" />
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Retention rate</dt>
              <dd className="font-semibold text-gray-900">
                {formatImpactPercentage(shortlist_impact.retention_rate * 100)}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Jaccard similarity</dt>
              <dd className="font-semibold text-gray-900">
                {shortlist_impact.jaccard_similarity.toFixed(4)}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Turnover rate</dt>
              <dd className="font-semibold text-gray-900">
                {formatImpactPercentage(shortlist_impact.turnover_rate * 100)}
              </dd>
            </div>
            <p className="text-xs text-gray-500">{shortlist_impact.expansion_description}</p>
          </dl>
        </SectionCard>

        <SectionCard title="Qualification Changes">
          {/* Qualification Matrix */}
          <div className="mb-4 overflow-x-auto">
            <table className="w-full text-sm" role="table" aria-label="Qualification matrix">
              <thead>
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">
                    Baseline \ Simulation
                  </th>
                  <th className="px-3 py-2 text-center text-xs font-medium uppercase text-gray-500">
                    Qualified
                  </th>
                  <th className="px-3 py-2 text-center text-xs font-medium uppercase text-gray-500">
                    Not Qualified
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-gray-100">
                  <td className="px-3 py-2 font-medium text-gray-900">Qualified</td>
                  <td className="px-3 py-2 text-center font-semibold text-green-600">
                    {qualification_matrix.baseline_qualified_simulation_qualified}
                  </td>
                  <td className="px-3 py-2 text-center font-semibold text-red-600">
                    {qualification_matrix.baseline_qualified_simulation_not_qualified}
                  </td>
                </tr>
                <tr className="border-t border-gray-100">
                  <td className="px-3 py-2 font-medium text-gray-900">Not Qualified</td>
                  <td className="px-3 py-2 text-center font-semibold text-green-600">
                    {qualification_matrix.baseline_not_qualified_simulation_qualified}
                  </td>
                  <td className="px-3 py-2 text-center font-semibold text-gray-600">
                    {qualification_matrix.baseline_not_qualified_simulation_not_qualified}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <dl className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Newly qualified</dt>
              <dd className="font-semibold text-green-600">{qualification_matrix.newly_qualified}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Newly disqualified</dt>
              <dd className="font-semibold text-red-600">{qualification_matrix.newly_disqualified}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Remained qualified</dt>
              <dd className="font-semibold text-gray-900">{qualification_matrix.remained_qualified}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Remained unqualified</dt>
              <dd className="font-semibold text-gray-900">{qualification_matrix.remained_unqualified}</dd>
            </div>
          </dl>
        </SectionCard>
      </div>

      {/* Threshold Impact */}
      <SectionCard title="Threshold Impact">
        <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-xs font-medium uppercase text-gray-500">Baseline threshold</dt>
            <dd className="mt-1 text-lg font-bold text-gray-900">
              {impact.threshold_impact.baseline_threshold}%
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-gray-500">Simulation threshold</dt>
            <dd className="mt-1 text-lg font-bold text-gray-900">
              {impact.threshold_impact.simulation_threshold}%
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-gray-500">Baseline qualified</dt>
            <dd className="mt-1 text-lg font-bold text-gray-900">
              {impact.threshold_impact.baseline_qualified_count}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase text-gray-500">Simulation qualified</dt>
            <dd className="mt-1 text-lg font-bold text-gray-900">
              {impact.threshold_impact.simulation_qualified_count}
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-sm text-gray-600">{impact.threshold_impact.description}</p>
      </SectionCard>

      {/* Rank Distribution + Score Distribution */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SectionCard title="Rank Distribution">
          <div className="space-y-3">
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-gray-400" /> Baseline
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-primary-500" /> Simulation
              </span>
            </div>
            {impact.rank_distribution.buckets.length === 0 ? (
              <p className="text-sm text-gray-500">No rank data available.</p>
            ) : (
              impact.rank_distribution.buckets.map((bucket) => {
                const maxCount = Math.max(
                  ...impact.rank_distribution.buckets.map((b) =>
                    Math.max(b.baseline_count, b.simulation_count),
                  ),
                  1,
                );
                return (
                  <div key={bucket.label} className="flex items-center gap-3">
                    <span className="w-16 shrink-0 text-xs font-medium text-gray-700">
                      Rank {bucket.label}
                    </span>
                    <div className="flex-1">
                      <DistributionBar
                        baseline={bucket.baseline_count}
                        simulation={bucket.simulation_count}
                        max={maxCount}
                      />
                    </div>
                    <span className="w-20 shrink-0 text-right text-xs text-gray-500">
                      {bucket.baseline_count} → {bucket.simulation_count}{" "}
                      <span
                        className={
                          bucket.change > 0
                            ? "text-green-600"
                            : bucket.change < 0
                              ? "text-red-600"
                              : ""
                        }
                      >
                        ({formatImpactDelta(bucket.change)})
                      </span>
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </SectionCard>

        <SectionCard title="Score Distribution">
          <div className="space-y-3">
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-gray-400" /> Baseline
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-primary-500" /> Simulation
              </span>
            </div>
            {impact.score_distribution.buckets.length === 0 ? (
              <p className="text-sm text-gray-500">No score data available.</p>
            ) : (
              impact.score_distribution.buckets.map((bucket) => {
                const maxCount = Math.max(
                  ...impact.score_distribution.buckets.map((b) =>
                    Math.max(b.baseline_count, b.simulation_count),
                  ),
                  1,
                );
                return (
                  <div key={bucket.label} className="flex items-center gap-3">
                    <span className="w-16 shrink-0 text-xs font-medium text-gray-700">
                      {bucket.label}
                    </span>
                    <div className="flex-1">
                      <DistributionBar
                        baseline={bucket.baseline_count}
                        simulation={bucket.simulation_count}
                        max={maxCount}
                      />
                    </div>
                    <span className="w-20 shrink-0 text-right text-xs text-gray-500">
                      {bucket.baseline_count} → {bucket.simulation_count}{" "}
                      <span
                        className={
                          bucket.change > 0
                            ? "text-green-600"
                            : bucket.change < 0
                              ? "text-red-600"
                              : ""
                        }
                      >
                        ({formatImpactDelta(bucket.change)})
                      </span>
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </SectionCard>
      </div>

      {/* Rank Stability + Score Movement + Rank Movement */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <SectionCard title="Rank Stability">
          <dl className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Stability</dt>
              <dd className="font-semibold text-gray-900">
                {formatImpactPercentage(impact.rank_stability.rank_stability * 100)}
              </dd>
            </div>
            {impact.rank_stability.rank_correlation !== null && (
              <div className="flex items-center justify-between">
                <dt className="text-gray-600">Spearman correlation</dt>
                <dd className="font-semibold text-gray-900">
                  {impact.rank_stability.rank_correlation.toFixed(4)}
                </dd>
              </div>
            )}
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Meaningful movement</dt>
              <dd className="font-semibold text-gray-900">
                {impact.rank_stability.meaningful_movement_count} (
                {formatImpactPercentage(impact.rank_stability.meaningful_movement_percentage)})
              </dd>
            </div>
          </dl>
        </SectionCard>

        <SectionCard title="Score Movement">
          <dl className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Avg change</dt>
              <dd className="font-semibold text-gray-900">
                {formatImpactDelta(score_movement.average_change)}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Median change</dt>
              <dd className="font-semibold text-gray-900">
                {formatImpactDelta(score_movement.median_change)}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Range</dt>
              <dd className="font-semibold text-gray-900">
                {formatImpactDelta(score_movement.minimum_change)} to{" "}
                {formatImpactDelta(score_movement.maximum_change)}
              </dd>
            </div>
            <hr className="border-gray-100" />
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Improved</dt>
              <dd className="font-semibold text-green-600">
                {score_movement.positive_change_count} (
                {formatImpactPercentage(score_movement.positive_change_percentage)})
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Declined</dt>
              <dd className="font-semibold text-red-600">
                {score_movement.negative_change_count} (
                {formatImpactPercentage(score_movement.negative_change_percentage)})
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Unchanged</dt>
              <dd className="font-semibold text-gray-600">
                {score_movement.unchanged_count} (
                {formatImpactPercentage(score_movement.unchanged_percentage)})
              </dd>
            </div>
          </dl>
        </SectionCard>

        <SectionCard title="Rank Movement">
          <dl className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Avg change</dt>
              <dd className="font-semibold text-gray-900">
                {formatImpactDelta(rank_movement.average_change)}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Median change</dt>
              <dd className="font-semibold text-gray-900">
                {formatImpactDelta(rank_movement.median_change)}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Largest upward</dt>
              <dd className="font-semibold text-green-600">
                +{rank_movement.largest_upward_movement}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Largest downward</dt>
              <dd className="font-semibold text-red-600">
                {rank_movement.largest_downward_movement}
              </dd>
            </div>
            <hr className="border-gray-100" />
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Moving up</dt>
              <dd className="font-semibold text-green-600">
                {rank_movement.candidates_moving_up} (
                {formatImpactPercentage(rank_movement.percentage_moving_up)})
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Moving down</dt>
              <dd className="font-semibold text-red-600">
                {rank_movement.candidates_moving_down} (
                {formatImpactPercentage(rank_movement.percentage_moving_down)})
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-gray-600">Unchanged</dt>
              <dd className="font-semibold text-gray-600">
                {rank_movement.candidates_unchanged} (
                {formatImpactPercentage(rank_movement.percentage_unchanged)})
              </dd>
            </div>
          </dl>
        </SectionCard>
      </div>

      {/* Insights */}
      {impact.insights.length > 0 && (
        <SectionCard title="Insights">
          <div className="flex flex-col gap-2">
            {impact.insights.map((insight, idx) => (
              <InsightCardItem key={idx} message={insight.message} type={insight.type} />
            ))}
          </div>
        </SectionCard>
      )}

      {/* Candidate Impact Table */}
      <SectionCard title="Candidate Impact Details">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="text-sm text-gray-500">Filter:</span>
          <select
            value={movementFilter}
            onChange={(e) => {
              setMovementFilter(e.target.value as "" | ImpactMovementFilter);
              setCandidatePage(1);
            }}
            className="rounded-lg border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-primary-500 focus:outline-none"
          >
            <option value="">All candidates</option>
            <option value="significantly_improved">Significantly improved</option>
            <option value="improved">Improved</option>
            <option value="unchanged">Unchanged</option>
            <option value="declined">Declined</option>
            <option value="significantly_declined">Significantly declined</option>
          </select>
        </div>

        {candidates && candidates.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {["Rank", "Candidate", "Base Score", "Sim Score", "Δ Score", "Δ Rank", "Status", "Shortlist", "Movement"].map(
                    (header) => (
                      <th
                        key={header}
                        className="whitespace-nowrap px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                      >
                        {header}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {candidates.items.map((row: CandidateImpactDetail) => (
                  <tr key={row.candidate_id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-3 py-2 text-sm font-medium text-gray-900">
                      #{row.simulation_rank}
                      <span className="ml-1 text-xs text-gray-400">base #{row.baseline_rank}</span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm text-gray-900">
                      {row.candidate_name}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm text-gray-500">
                      {row.baseline_score}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm font-semibold text-gray-900">
                      {row.simulation_score}
                    </td>
                    <td
                      className={`whitespace-nowrap px-3 py-2 text-sm font-medium ${
                        row.score_change > 0
                          ? "text-green-600"
                          : row.score_change < 0
                            ? "text-red-600"
                            : "text-gray-500"
                      }`}
                    >
                      {formatImpactDelta(row.score_change)}
                    </td>
                    <td
                      className={`whitespace-nowrap px-3 py-2 text-sm font-medium ${
                        row.rank_change > 0
                          ? "text-green-600"
                          : row.rank_change < 0
                            ? "text-red-600"
                            : "text-gray-500"
                      }`}
                    >
                      {formatImpactDelta(row.rank_change)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          row.simulation_status === "qualified"
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {row.simulation_status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          row.shortlist_change === "entered"
                            ? "bg-green-100 text-green-800"
                            : row.shortlist_change === "left"
                              ? "bg-red-100 text-red-800"
                              : row.shortlist_change === "retained"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {SHORTLIST_CHANGE_LABELS[row.shortlist_change] ?? row.shortlist_change}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          row.movement_category === "significantly_improved" || row.movement_category === "improved"
                            ? "bg-green-100 text-green-800"
                            : row.movement_category === "significantly_declined" || row.movement_category === "declined"
                              ? "bg-red-100 text-red-800"
                              : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {MOVEMENT_CATEGORY_LABELS[row.movement_category] ?? row.movement_category}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-5 py-10 text-center text-sm text-gray-500">
            {candidates && candidates.total === 0
              ? "No results for the current filter."
              : "No candidates to display."}
          </div>
        )}

        {candidates && candidates.total > 0 && (
          <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3">
            <span className="text-xs text-gray-500">
              Showing {(candidates.page - 1) * PAGE_SIZE + 1}–
              {Math.min(candidates.page * PAGE_SIZE, candidates.total)} of {candidates.total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={candidates.page <= 1}
                onClick={() => setCandidatePage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={candidates.page * PAGE_SIZE >= candidates.total}
                onClick={() => setCandidatePage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </SectionCard>
    </div>
  );
}
