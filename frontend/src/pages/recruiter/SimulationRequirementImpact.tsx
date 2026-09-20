import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { Button } from "../../components/ui/Button";
import { ScenarioStatusBadge } from "../../components/simulations/ScenarioStatusBadge";
import { RequirementImpactTable } from "../../components/simulations/RequirementImpactTable";
import { CandidateRequirementDetail } from "../../components/simulations/CandidateRequirementDetail";
import { useToast } from "../../contexts/ToastContext";
import { simulationApi } from "../../api/simulations";
import type {
  CandidateRequirementImpactDetail,
  CandidateRequirementImpactListResponse,
  RequirementImpactResponse,
} from "../../types/requirementImpact";
import type {
  SimulationScenario,
} from "../../types/simulations";

const PAGE_SIZE = 20;

// ─── Helper Components ─────────────────────────────────────────────

function StatCard({
  label,
  value,
  delta,
  positive,
}: {
  label: string;
  value: string | number;
  delta?: number;
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
          {delta > 0 ? "+" : ""}
          {delta} change
        </p>
      )}
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────

export function SimulationRequirementImpact() {
  const { simulationId } = useParams<{ simulationId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { addToast } = useToast();

  const [scenario, setScenario] = useState<SimulationScenario | null>(null);
  const [loading, setLoading] = useState(true);
  const [impact, setImpact] = useState<RequirementImpactResponse | null>(null);
  const [candidates, setCandidates] = useState<CandidateRequirementImpactListResponse | null>(null);
  const [candidatesPage, setCandidatesPage] = useState(1);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateRequirementImpactDetail | null>(null);
  const [candidateDetailLoading, setCandidateDetailLoading] = useState(false);

  const executionId = searchParams.get("execution_id") || undefined;

  // Load scenario
  useEffect(() => {
    const id = simulationId;
    if (!id) return;
    let cancelled = false;
    async function load() {
      try {
        const data = await simulationApi.get(id!);
        if (cancelled) return;
        setScenario(data);
      } catch {
        if (!cancelled) {
          addToast("Failed to load simulation", "error");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [simulationId, addToast]);

  // Load requirement impact
  useEffect(() => {
    const id = simulationId;
    if (!id) return;
    let cancelled = false;
    async function load() {
      try {
        const data = await simulationApi.getRequirementImpact(id!, executionId);
        if (cancelled) return;
        setImpact(data);
      } catch (err) {
        if (!cancelled) {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          addToast(detail || "Failed to load requirement impact", "error");
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, [simulationId, executionId, addToast]);

  // Load candidates
  const loadCandidates = useCallback(
    async (page: number) => {
      const id = simulationId;
      if (!id) return;
      try {
        const data = await simulationApi.getRequirementImpactCandidates(id, {
          execution_id: executionId,
          page,
          page_size: PAGE_SIZE,
          sort_by: "simulation_rank",
          order: "asc",
        });
        setCandidates(data);
        setCandidatesPage(page);
      } catch {
        // Candidates are a progressive enhancement
      }
    },
    [simulationId, executionId],
  );

  useEffect(() => {
    if (impact) {
      loadCandidates(1);
    }
  }, [impact, loadCandidates]);

  // Handle candidate click
  async function handleCandidateClick(candidateId: string) {
    const id = simulationId;
    if (!id) return;
    setCandidateDetailLoading(true);
    try {
      const detail = await simulationApi.getCandidateRequirementImpactDetail(id, candidateId, executionId);
      setSelectedCandidate(detail.candidate);
    } catch {
      addToast("Failed to load candidate detail", "error");
    } finally {
      setCandidateDetailLoading(false);
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  if (!scenario) {
    return (
      <div className="py-20 text-center">
        <p className="text-gray-500">Simulation not found.</p>
        <button
          onClick={() => navigate("/recruiter/simulations")}
          className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-700"
        >
          Back to simulations
        </button>
      </div>
    );
  }

  if (!impact) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Link
            to={`/recruiter/simulations/${scenario.id}`}
            className="text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            {scenario.name}
          </Link>
          <span className="text-gray-400">/</span>
          <span className="text-sm text-gray-600">Requirement Impact</span>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
          <LoadingSpinner size="md" className="mx-auto" />
          <p className="mt-4 text-sm text-gray-500">Loading requirement impact analysis...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Link
              to={`/recruiter/simulations/${scenario.id}`}
              className="text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              {scenario.name}
            </Link>
            <span className="text-gray-400">/</span>
            <h1 className="text-2xl font-bold text-gray-900">Requirement Impact</h1>
            <ScenarioStatusBadge status={scenario.status} />
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {scenario.job_title} · {scenario.company}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate(`/recruiter/simulations/${scenario.id}/impact`)}
          >
            Ranking Impact
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate(`/recruiter/simulations/${scenario.id}/results`)}
          >
            Results
          </Button>
        </div>
      </div>

      {/* Sandbox Warning */}
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        <span className="font-semibold">What-if analysis.</span> These scores rank candidates under a
        hypothetical configuration. No live hiring data (job, applications, rankings) was created or
        modified by this run — results are stored separately as simulation records.
      </div>

      {/* Change Summary */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          label="Requirements Changed"
          value={impact.change_summary.total_requirements_changed}
        />
        <StatCard
          label="Skills Added"
          value={impact.change_summary.skills_added}
          delta={impact.change_summary.skills_added}
          positive={undefined}
        />
        <StatCard
          label="Skills Promoted"
          value={impact.change_summary.skills_promoted}
          delta={impact.change_summary.skills_promoted}
          positive={undefined}
        />
        <StatCard
          label="Skills Demoted"
          value={impact.change_summary.skills_demoted}
          delta={impact.change_summary.skills_demoted}
          positive={undefined}
        />
      </div>

      {/* Impact Summary */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          label="Candidates Affected"
          value={impact.impact_summary.candidates_affected}
        />
        <StatCard
          label="Newly Qualified"
          value={impact.impact_summary.candidates_newly_qualified}
          delta={impact.impact_summary.candidates_newly_qualified}
          positive={impact.impact_summary.candidates_newly_qualified > 0}
        />
        <StatCard
          label="Newly Disqualified"
          value={impact.impact_summary.candidates_newly_disqualified}
          delta={-impact.impact_summary.candidates_newly_disqualified}
          positive={impact.impact_summary.candidates_newly_disqualified === 0}
        />
        <StatCard
          label="Score Changes"
          value={impact.impact_summary.candidates_score_changed}
        />
      </div>

      {/* Requirement Changes Table */}
      <RequirementImpactTable requirements={impact.requirement_changes} />

      {/* Affected Candidates */}
      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
        <div className="border-b border-gray-200 bg-gray-50 px-5 py-3">
          <h3 className="text-sm font-semibold text-gray-900">Affected Candidates</h3>
          <p className="mt-0.5 text-xs text-gray-500">
            Candidates whose requirement satisfaction changed.
          </p>
        </div>
        {candidates && candidates.items.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                      Candidate
                    </th>
                    <th className="px-5 py-3 text-right text-xs font-medium uppercase tracking-wide text-gray-500">
                      Score
                    </th>
                    <th className="px-5 py-3 text-right text-xs font-medium uppercase tracking-wide text-gray-500">
                      Rank
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                      Affected Requirements
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                      Qualification
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                      Shortlist
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {candidates.items.map((c) => (
                    <tr
                      key={c.candidate_id}
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() => handleCandidateClick(c.candidate_id)}
                    >
                      <td className="whitespace-nowrap px-5 py-4">
                        <div className="text-sm font-medium text-gray-900">{c.candidate_name}</div>
                      </td>
                      <td className="whitespace-nowrap px-5 py-4 text-right">
                        <span className="text-sm font-semibold text-gray-900">
                          {c.simulation_score}
                        </span>
                        <span
                          className={`ml-1 text-xs font-medium ${
                            c.score_change > 0
                              ? "text-green-600"
                              : c.score_change < 0
                                ? "text-red-600"
                                : "text-gray-500"
                          }`}
                        >
                          ({c.score_change > 0 ? "+" : ""}{c.score_change})
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-5 py-4 text-right">
                        <span className="text-sm text-gray-900">#{c.simulation_rank}</span>
                        <span
                          className={`ml-1 text-xs ${
                            c.rank_change > 0
                              ? "text-green-600"
                              : c.rank_change < 0
                                ? "text-red-600"
                                : "text-gray-500"
                          }`}
                        >
                          ({c.rank_change > 0 ? "+" : ""}{c.rank_change})
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex flex-wrap gap-1">
                          {c.affected_requirements.map((ar, idx) => (
                            <span
                              key={idx}
                              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                                ar.simulation_satisfied
                                  ? "bg-green-100 text-green-700"
                                  : "bg-red-100 text-red-700"
                              }`}
                            >
                              {ar.requirement_name}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-5 py-4">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            c.qualification_change === "newly_qualified"
                              ? "bg-green-100 text-green-700"
                              : c.qualification_change === "newly_disqualified"
                                ? "bg-red-100 text-red-700"
                                : c.qualification_change === "remained_qualified"
                                  ? "bg-blue-100 text-blue-700"
                                  : "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {c.qualification_change.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-5 py-4">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            c.shortlist_change === "entered"
                              ? "bg-green-100 text-green-700"
                              : c.shortlist_change === "left"
                                ? "bg-red-100 text-red-700"
                                : c.shortlist_change === "retained"
                                  ? "bg-blue-100 text-blue-700"
                                  : "bg-gray-100 text-gray-500"
                          }`}
                        >
                          {c.shortlist_change.replace(/_/g, " ")}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Pagination */}
            {candidates.total > PAGE_SIZE && (
              <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-5 py-3">
                <p className="text-xs text-gray-500">
                  Showing {(candidatesPage - 1) * PAGE_SIZE + 1}-
                  {Math.min(candidatesPage * PAGE_SIZE, candidates.total)} of {candidates.total}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => loadCandidates(candidatesPage - 1)}
                    disabled={candidatesPage <= 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => loadCandidates(candidatesPage + 1)}
                    disabled={candidatesPage * PAGE_SIZE >= candidates.total}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="px-5 py-8 text-center">
            <p className="text-sm text-gray-500">No candidates were affected by requirement changes.</p>
          </div>
        )}
      </div>

      {/* Candidate Detail Drawer */}
      {selectedCandidate && (
        <CandidateRequirementDetail
          candidate={selectedCandidate}
          onClose={() => setSelectedCandidate(null)}
        />
      )}

      {/* Loading overlay for candidate detail */}
      {candidateDetailLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <LoadingSpinner size="lg" />
        </div>
      )}
    </div>
  );
}
