import type {
  CandidateRequirementImpactDetail,
  ChangedRequirementStatus,
} from "../../types/requirementImpact";
import {
  QUALIFICATION_CHANGE_LABELS,
  SHORTLIST_CHANGE_LABELS,
  formatSatisfactionStatus,
} from "../../types/requirementImpact";

interface CandidateRequirementDetailProps {
  candidate: CandidateRequirementImpactDetail;
  onClose: () => void;
}

function SatisfactionBadge({ status }: { status: ChangedRequirementStatus["baseline_status"] }) {
  const colors = {
    SATISFIED: "bg-green-100 text-green-700",
    MISSING: "bg-red-100 text-red-700",
    NOT_APPLICABLE: "bg-gray-100 text-gray-500",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[status]}`}>
      {formatSatisfactionStatus(status)}
    </span>
  );
}

function QualificationBadge({ change }: { change: string }) {
  const colors: Record<string, string> = {
    newly_qualified: "bg-green-100 text-green-700",
    newly_disqualified: "bg-red-100 text-red-700",
    remained_qualified: "bg-blue-100 text-blue-700",
    remained_unqualified: "bg-gray-100 text-gray-600",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[change] || "bg-gray-100 text-gray-600"}`}>
      {QUALIFICATION_CHANGE_LABELS[change as keyof typeof QUALIFICATION_CHANGE_LABELS] || change}
    </span>
  );
}

function ShortlistBadge({ change }: { change: string }) {
  const colors: Record<string, string> = {
    entered: "bg-green-100 text-green-700",
    left: "bg-red-100 text-red-700",
    retained: "bg-blue-100 text-blue-700",
    never_shortlisted: "bg-gray-100 text-gray-500",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[change] || "bg-gray-100 text-gray-600"}`}>
      {SHORTLIST_CHANGE_LABELS[change as keyof typeof SHORTLIST_CHANGE_LABELS] || change}
    </span>
  );
}

export function CandidateRequirementDetail({ candidate, onClose }: CandidateRequirementDetailProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-bold text-gray-900">{candidate.candidate_name}</h2>
            <p className="mt-0.5 text-sm text-gray-500">Requirement Impact Detail</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Score & Rank Changes */}
        <div className="grid grid-cols-2 gap-4 border-b border-gray-200 px-6 py-4 sm:grid-cols-4">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Score</dt>
            <dd className="mt-1 text-lg font-bold text-gray-900">
              {candidate.simulation_score}
              <span className="ml-1 text-sm text-gray-500">
                (base {candidate.baseline_score})
              </span>
            </dd>
            <dd
              className={`text-xs font-medium ${
                candidate.score_change > 0
                  ? "text-green-600"
                  : candidate.score_change < 0
                    ? "text-red-600"
                    : "text-gray-500"
              }`}
            >
              {candidate.score_change > 0 ? "+" : ""}
              {candidate.score_change} change
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Rank</dt>
            <dd className="mt-1 text-lg font-bold text-gray-900">
              #{candidate.simulation_rank}
              <span className="ml-1 text-sm text-gray-500">
                (base #{candidate.baseline_rank})
              </span>
            </dd>
            <dd
              className={`text-xs font-medium ${
                candidate.rank_change > 0
                  ? "text-green-600"
                  : candidate.rank_change < 0
                    ? "text-red-600"
                    : "text-gray-500"
              }`}
            >
              {candidate.rank_change > 0 ? "+" : ""}
              {candidate.rank_change} change
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Qualification</dt>
            <dd className="mt-1">
              <QualificationBadge change={candidate.qualification_change} />
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Shortlist</dt>
            <dd className="mt-1">
              <ShortlistBadge change={candidate.shortlist_change} />
            </dd>
          </div>
        </div>

        {/* Affected Requirements */}
        <div className="px-6 py-4">
          <h3 className="text-sm font-semibold text-gray-900">Changed Requirements</h3>
          {candidate.affected_requirements.length === 0 ? (
            <p className="mt-2 text-sm text-gray-500">
              No requirement changes affected this candidate&apos;s satisfaction status.
            </p>
          ) : (
            <div className="mt-3 space-y-3">
              {candidate.affected_requirements.map((req, idx) => (
                <div
                  key={`${req.requirement_type}-${req.requirement_name}-${idx}`}
                  className="rounded-lg border border-gray-200 bg-gray-50 p-4"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-sm font-medium text-gray-900">{req.requirement_name}</span>
                      <span className="ml-2 text-xs text-gray-500 capitalize">({req.requirement_type})</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <SatisfactionBadge status={req.baseline_status} />
                      <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                      </svg>
                      <SatisfactionBadge status={req.simulation_status} />
                    </div>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    {req.baseline_satisfied === req.simulation_satisfied
                      ? "Satisfaction status unchanged"
                      : req.simulation_satisfied
                        ? "Candidate now satisfies this requirement"
                        : "Candidate no longer satisfies this requirement"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Explanation */}
        {candidate.explanation && (
          <div className="border-t border-gray-200 px-6 py-4">
            <h3 className="text-sm font-semibold text-gray-900">Analysis</h3>
            <p className="mt-2 text-sm text-gray-600">{candidate.explanation}</p>
          </div>
        )}
      </div>
    </div>
  );
}
