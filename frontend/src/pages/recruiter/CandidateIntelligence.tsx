import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import {
  getCandidateIntelligence,
  getCandidateJobIntelligence,
} from "../../api/screening";
import type {
  CandidateEvidenceIntelResponse,
  FitEvidenceItem,
  IntelConfidence,
  JobContextBlock,
  ReviewFlag,
  SkillDepth,
  StrengthInsight,
} from "../../types/screening";

const DEPTH_STYLES: Record<SkillDepth, string> = {
  expert_level_evidence: "bg-emerald-100 text-emerald-800",
  strong: "bg-green-100 text-green-800",
  moderate: "bg-blue-100 text-blue-800",
  limited: "bg-yellow-100 text-yellow-800",
  mention_only: "bg-orange-100 text-orange-800",
  no_evidence: "bg-gray-100 text-gray-600",
};

const CONFIDENCE_STYLES: Record<IntelConfidence, string> = {
  high: "bg-primary-100 text-primary-800",
  medium: "bg-indigo-100 text-indigo-700",
  low: "bg-gray-100 text-gray-600",
  insufficient: "bg-gray-100 text-gray-400",
};

function formatLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function EvidenceList({ evidence }: { evidence: FitEvidenceItem[] }) {
  if (evidence.length === 0) return null;
  return (
    <ul className="mt-2 space-y-2">
      {evidence.map((item, i) => (
        <li key={i} className="rounded-lg bg-gray-50 p-3">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-800">
              {formatLabel(item.source)}
            </span>
            {item.context && (
              <span className="text-xs text-gray-500">{item.context}</span>
            )}
          </div>
          <blockquote className="mt-1 border-l-2 border-gray-300 pl-2 text-sm italic text-gray-700">
            "{item.quote}"
          </blockquote>
        </li>
      ))}
    </ul>
  );
}

function StrengthCard({ strength }: { strength: StrengthInsight }) {
  const [showEvidence, setShowEvidence] = useState(false);
  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold text-gray-900">{strength.title}</h3>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${DEPTH_STYLES[strength.depth]}`}
        >
          {formatLabel(strength.depth)}
        </span>
        <span
          className={`ml-auto rounded-full px-2 py-0.5 text-xs font-medium capitalize ${CONFIDENCE_STYLES[strength.confidence]}`}
        >
          {strength.confidence} confidence
        </span>
      </div>
      <p className="mt-1 text-sm text-gray-600">{strength.reason}</p>
      {strength.evidence.length > 0 && (
        <>
          <button
            onClick={() => setShowEvidence(!showEvidence)}
            className="mt-2 text-xs font-medium text-primary-600 hover:text-primary-800"
          >
            {showEvidence
              ? "Hide evidence"
              : `View evidence (${strength.evidence.length})`}
          </button>
          {showEvidence && <EvidenceList evidence={strength.evidence} />}
        </>
      )}
    </div>
  );
}

function FlagCard({ flag }: { flag: ReviewFlag }) {
  const [showEvidence, setShowEvidence] = useState(false);
  const warning = flag.severity === "warning";
  return (
    <div
      className={`rounded-lg border p-4 ${
        warning ? "border-amber-200 bg-amber-50" : "border-blue-100 bg-blue-50"
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${
            warning ? "bg-amber-200 text-amber-900" : "bg-blue-100 text-blue-800"
          }`}
        >
          {flag.severity}
        </span>
        <h3 className="font-medium text-gray-900">{flag.title}</h3>
      </div>
      <p className="mt-1 text-sm text-gray-700">{flag.description}</p>
      {flag.possible_explanation && (
        <p className="mt-1 text-xs italic text-gray-500">
          Note: {flag.possible_explanation}
        </p>
      )}
      {flag.evidence.length > 0 && (
        <>
          <button
            onClick={() => setShowEvidence(!showEvidence)}
            className="mt-2 text-xs font-medium text-primary-600 hover:text-primary-800"
          >
            {showEvidence ? "Hide details" : "Show details"}
          </button>
          {showEvidence && <EvidenceList evidence={flag.evidence} />}
        </>
      )}
    </div>
  );
}

function SnapshotChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white px-3 py-2 shadow-sm ring-1 ring-gray-200">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
        {label}
      </p>
      <p className="text-sm font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function JobContextCard({ context }: { context: JobContextBlock }) {
  const classificationStyles: Record<string, string> = {
    strong_match: "bg-green-100 text-green-800",
    good_match: "bg-emerald-100 text-emerald-800",
    partial_match: "bg-yellow-100 text-yellow-800",
    low_match: "bg-red-100 text-red-800",
    insufficient_evidence: "bg-gray-100 text-gray-600",
  };
  const style =
    classificationStyles[context.fit_classification] || "bg-gray-100 text-gray-600";
  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold text-gray-900">
          Alignment for this role: {context.job_title}
        </h2>
        <Link
          to={`/recruiter/jobs/${context.job_id}/applicants`}
          className="text-sm font-medium text-primary-600 hover:text-primary-800"
        >
          Open full fit analysis →
        </Link>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <span className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${style}`}>
          {formatLabel(context.fit_classification)}
        </span>
        <span className="text-xl font-bold text-gray-900">{context.fit_score}</span>
        <span className="text-sm text-gray-400">/ 100</span>
        {context.required_years != null && (
          <span className="text-sm text-gray-500">
            · role asks ~{context.required_years} yrs
          </span>
        )}
      </div>
      <p className="mt-3 text-sm text-gray-700">{context.summary.text}</p>

      {(context.requirement_gaps.length > 0 || context.requirement_unknown.length > 0) && (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {context.requirement_gaps.length > 0 && (
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                No supporting evidence found for
              </p>
              <div className="mt-1 flex flex-wrap gap-1">
                {context.requirement_gaps.map((req) => (
                  <span key={req} className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                    {req}
                  </span>
                ))}
              </div>
            </div>
          )}
          {context.requirement_unknown.length > 0 && (
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Not enough resume information for
              </p>
              <div className="mt-1 flex flex-wrap gap-1">
                {context.requirement_unknown.map((req) => (
                  <span key={req} className="rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700">
                    {req}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {context.additional_questions.length > 0 && (
        <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-gray-700">
          {context.additional_questions.map((q, i) => (
            <li key={i}>{q.question}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function CandidateIntelligence() {
  const { id: jobIdParam, candidateId } = useParams<{
    id?: string;
    candidateId: string;
  }>();
  const { addToast } = useToast();
  const [intel, setIntel] = useState<CandidateEvidenceIntelResponse | null>(null);
  const [jobContext, setJobContext] = useState<JobContextBlock | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!candidateId) return;
    async function load() {
      try {
        if (jobIdParam) {
          const data = await getCandidateJobIntelligence(jobIdParam!, candidateId!);
          setIntel(data.candidate_intelligence);
          setJobContext(data.job_context);
        } else {
          const data = await getCandidateIntelligence(candidateId!);
          setIntel(data);
        }
      } catch {
        addToast("Failed to load candidate intelligence", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [candidateId, jobIdParam, addToast]);

  if (loading)
    return (
      <div className="mt-16 space-y-3 text-center">
        <LoadingSpinner size="lg" />
        <p className="text-sm text-gray-500">Analyzing candidate evidence...</p>
      </div>
    );

  if (!intel)
    return (
      <div className="mt-10 space-y-4 text-center">
        <p className="text-gray-500">Candidate intelligence unavailable.</p>
        {jobIdParam && (
          <Link
            to={`/recruiter/jobs/${jobIdParam}/applicants`}
            className="text-sm font-medium text-primary-600 hover:text-primary-800"
          >
            Back to applicants
          </Link>
        )}
      </div>
    );

  const snapshot = intel.snapshot;
  const years = snapshot.total_experience_years;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Candidate Intelligence: {intel.candidate_name}
          </h1>
          <p className="text-sm text-gray-500">
            Evidence-based profile analysis · engine {intel.engine_version}
            {intel.cached && " · cached result"}
          </p>
        </div>
        {jobIdParam && (
          <Link
            to={`/recruiter/jobs/${jobIdParam}/applicants`}
            className="text-sm font-medium text-primary-600 hover:text-primary-800"
          >
            Back to applicants
          </Link>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <SnapshotChip
          label="Experience"
          value={years != null ? `~${years} yrs` : "Not determinable"}
        />
        <SnapshotChip label="Roles listed" value={String(snapshot.experience_count)} />
        <SnapshotChip label="Projects" value={String(snapshot.project_count)} />
        <SnapshotChip label="Certifications" value={String(snapshot.certification_count)} />
        <SnapshotChip label="Skills mentioned" value={String(snapshot.skills_mentioned)} />
        <SnapshotChip label="Highest degree" value={snapshot.highest_degree || "—"} />
      </div>

      <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
        <h2 className="font-semibold text-blue-900">AI Summary</h2>
        <p className="mt-1 text-sm text-blue-900">{intel.summary.text}</p>
        <p className="mt-2 text-xs italic text-blue-700">
          {intel.summary.disclaimer} Summary source:{" "}
          {formatLabel(intel.summary.source)}. Confidence reflects the quality of
          resume evidence, not a judgment of the candidate.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <section>
            <h2 className="mb-3 font-semibold text-gray-900">
              Top Strengths{" "}
              <span className="text-sm font-normal text-gray-400">
                (backed by resume evidence)
              </span>
            </h2>
            {intel.strengths.length === 0 ? (
              <p className="rounded-lg border bg-white p-4 text-sm text-gray-500">
                No strongly evidenced strengths were identified — this reflects the
                available evidence in the resume, not a judgment of the candidate.
              </p>
            ) : (
              <div className="space-y-3">
                {intel.strengths.map((s) => (
                  <StrengthCard key={s.title} strength={s} />
                ))}
              </div>
            )}
          </section>

          {intel.review_flags.length > 0 && (
            <section>
              <h2 className="mb-3 font-semibold text-gray-900">
                Timeline Observations{" "}
                <span className="text-sm font-normal text-gray-400">
                  (for human review — not accusations)
                </span>
              </h2>
              <div className="space-y-3">
                {intel.review_flags.map((f, i) => (
                  <FlagCard key={i} flag={f} />
                ))}
              </div>
            </section>
          )}

          {intel.screening_questions.length > 0 && (
            <section className="rounded-lg border bg-white p-6">
              <h2 className="font-semibold text-gray-900">Suggested Screening Questions</h2>
              <ol className="mt-3 space-y-3">
                {intel.screening_questions.map((q, i) => (
                  <li key={i} className="border-b pb-3 last:border-b-0 last:pb-0">
                    <p className="text-sm font-medium text-gray-900">{q.question}</p>
                    <p className="mt-0.5 text-xs text-gray-500">
                      Topic: {formatLabel(q.topic)} · {q.reason}
                    </p>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {jobContext && <JobContextCard context={jobContext} />}
        </div>

        <div className="space-y-6">
          {intel.evidence_gaps.length > 0 && (
            <section className="rounded-lg border bg-white p-6">
              <h2 className="font-semibold text-gray-900">Evidence Gaps</h2>
              <p className="mt-1 text-xs text-gray-400">
                Mentions without detailed support — no claim is made either way.
              </p>
              <ul className="mt-3 space-y-2">
                {intel.evidence_gaps.map((g) => (
                  <li key={g.skill} className="border-b pb-2 last:border-b-0 last:pb-0">
                    <span
                      className={`mr-2 inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${DEPTH_STYLES[g.current_depth]}`}
                    >
                      {g.current_depth === "mention_only" ? "mention only" : formatLabel(g.current_depth)}
                    </span>
                    <span className="text-sm font-medium text-gray-900">{g.skill}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {intel.achievements.length > 0 && (
            <section className="rounded-lg border bg-white p-6">
              <h2 className="font-semibold text-gray-900">
                Notable Claims{" "}
                <span className="text-sm font-normal text-gray-400">(self-reported)</span>
              </h2>
              <ul className="mt-3 space-y-3">
                {intel.achievements.map((a, i) => (
                  <li key={i} className="border-b pb-2 last:border-b-0 last:pb-0">
                    <p className="text-sm text-gray-800">"{a.text}"</p>
                    <p className="mt-0.5 text-xs text-gray-400">
                      {a.label} · {a.context || formatLabel(a.source_type)}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="rounded-lg border bg-white p-6">
            <h2 className="font-semibold text-gray-900">Timeline</h2>
            <dl className="mt-3 space-y-1 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Dated roles</dt>
                <dd className="font-medium text-gray-900">
                  {intel.timeline.entries_with_dates} / {intel.timeline.entries_total}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Computed span</dt>
                <dd className="font-medium text-gray-900">
                  {Math.floor(intel.timeline.computed_months / 12)}y{" "}
                  {intel.timeline.computed_months % 12}m
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Self-stated years</dt>
                <dd className="font-medium text-gray-900">
                  {intel.timeline.stated_years_found
                    ? `~${intel.timeline.stated_years_value}`
                    : "not stated"}
                </dd>
              </div>
            </dl>
          </section>

          <section className="rounded-lg border bg-white p-6">
            <h2 className="mb-2 font-semibold text-gray-900">About this analysis</h2>
            <p className="text-xs italic text-gray-500">
              All findings quote the candidate's own resume. Absence of evidence means
              "no supporting evidence found" — it is never a negative judgment.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
