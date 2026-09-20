import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { getJobCandidateFit } from "../../api/screening";
import type {
  FitEvidenceItem,
  FitRequirementResult,
  JobFitResponse,
  MatchStatus,
} from "../../types/screening";

const STATUS_STYLES: Record<MatchStatus, string> = {
  match: "bg-green-100 text-green-800",
  partial: "bg-yellow-100 text-yellow-800",
  gap: "bg-red-100 text-red-800",
  unknown: "bg-gray-100 text-gray-600",
};

const CLASSIFICATION_STYLES: Record<string, string> = {
  strong_match: "bg-green-100 text-green-800",
  good_match: "bg-emerald-100 text-emerald-800",
  partial_match: "bg-yellow-100 text-yellow-800",
  low_match: "bg-red-100 text-red-800",
  insufficient_evidence: "bg-gray-100 text-gray-600",
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

function RequirementRow({ requirement }: { requirement: FitRequirementResult }) {
  const [showEvidence, setShowEvidence] = useState(false);
  const hasEvidence = requirement.evidence.length > 0;
  return (
    <div className="border-b py-3 last:border-b-0">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${STATUS_STYLES[requirement.status]}`}
        >
          {requirement.status}
        </span>
        <span className="text-sm font-medium text-gray-900">
          {requirement.requirement}
        </span>
        {requirement.level === "preferred" && (
          <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700">
            preferred
          </span>
        )}
        {requirement.category && (
          <span className="text-xs text-gray-400">{requirement.category}</span>
        )}
        {hasEvidence && (
          <button
            onClick={() => setShowEvidence(!showEvidence)}
            className="ml-auto text-xs font-medium text-primary-600 hover:text-primary-800"
          >
            {showEvidence ? "Hide evidence" : `Evidence (${requirement.evidence.length})`}
          </button>
        )}
      </div>
      <p className="mt-1 text-sm text-gray-600">{requirement.reason}</p>
      {showEvidence && hasEvidence && <EvidenceList evidence={requirement.evidence} />}
    </div>
  );
}

export function CandidateFit() {
  const { id, candidateId } = useParams<{ id: string; candidateId: string }>();
  const { addToast } = useToast();
  const [fit, setFit] = useState<JobFitResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id || !candidateId) return;
    async function load() {
      try {
        const data = await getJobCandidateFit(id!, candidateId!);
        setFit(data);
      } catch {
        addToast("Failed to load job fit analysis", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, candidateId, addToast]);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;
  if (!fit)
    return (
      <div className="mt-10 space-y-4 text-center">
        <p className="text-gray-500">Fit analysis unavailable.</p>
        <Link
          to={`/recruiter/jobs/${id}/applicants`}
          className="text-sm font-medium text-primary-600 hover:text-primary-800"
        >
          Back to applicants
        </Link>
      </div>
    );

  const classificationStyle =
    CLASSIFICATION_STYLES[fit.overall.classification] || "bg-gray-100 text-gray-600";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Job Fit: {fit.candidate_name}</h1>
          <p className="text-sm text-gray-500">{fit.job_title}</p>
          <Link
            to={`/recruiter/jobs/${id}/candidates/${candidateId}/intelligence`}
            className="text-sm font-medium text-primary-600 hover:text-primary-800"
          >
            Full candidate intelligence →
          </Link>
        </div>
        <Link
          to={`/recruiter/jobs/${id}/applicants`}
          className="text-sm font-medium text-primary-600 hover:text-primary-800"
        >
          Back to applicants
        </Link>
      </div>

      <div className="rounded-lg border bg-white p-6">
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${classificationStyle}`}
          >
            {formatLabel(fit.overall.classification)}
          </span>
          <span className="text-2xl font-bold text-gray-900">{fit.overall.score}</span>
          <span className="text-sm text-gray-400">/ 100</span>
          {fit.cached && (
            <span className="ml-auto rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
              cached result
            </span>
          )}
        </div>
        <p className="mt-3 text-sm text-gray-700">{fit.overall.summary}</p>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Object.entries(fit.overall.breakdown.components).map(([name, value]) => (
            <div key={name} className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                {formatLabel(name)}
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-900">
                {Math.round(value * 100)}%
              </p>
              <p className="text-xs text-gray-400">
                weight {Math.round((fit.overall.breakdown.weights[name] || 0) * 100)}%
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <div className="rounded-lg border bg-white p-6">
            <h2 className="mb-2 font-semibold text-gray-900">Requirements</h2>
            <div className="divide-y-0">
              {fit.requirements.map((req, i) => (
                <RequirementRow key={i} requirement={req} />
              ))}
            </div>
          </div>

          {fit.responsibilities.length > 0 && (
            <div className="rounded-lg border bg-white p-6">
              <h2 className="mb-2 font-semibold text-gray-900">Responsibilities</h2>
              {fit.responsibilities.map((resp, i) => (
                <ResponsibilityRow key={i} responsibility={resp} />
              ))}
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="rounded-lg border bg-white p-6">
            <h2 className="mb-2 font-semibold text-gray-900">Experience</h2>
            <span
              className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${STATUS_STYLES[fit.experience_alignment.status]}`}
            >
              {fit.experience_alignment.status}
            </span>
            <dl className="mt-3 space-y-1 text-sm">
              {fit.experience_alignment.required_years != null && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Required</dt>
                  <dd className="font-medium text-gray-900">
                    {fit.experience_alignment.required_years} yrs
                  </dd>
                </div>
              )}
              {fit.experience_alignment.relevant_years != null && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Relevant</dt>
                  <dd className="font-medium text-gray-900">
                    {fit.experience_alignment.relevant_years} yrs
                  </dd>
                </div>
              )}
              {fit.experience_alignment.total_years != null && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Total</dt>
                  <dd className="font-medium text-gray-900">
                    {fit.experience_alignment.total_years} yrs
                  </dd>
                </div>
              )}
            </dl>
            <p className="mt-2 text-sm text-gray-600">{fit.experience_alignment.reason}</p>
          </div>

          <div className="rounded-lg border bg-white p-6">
            <h2 className="mb-2 font-semibold text-gray-900">Skill Gaps</h2>
            <SkillGapGroup label="Strengths" skills={fit.skill_gaps.strengths} tone="green" />
            <SkillGapGroup label="Partial" skills={fit.skill_gaps.partial} tone="yellow" />
            <SkillGapGroup label="Gaps" skills={fit.skill_gaps.gaps} tone="red" />
            <SkillGapGroup label="Unknown" skills={fit.skill_gaps.unknown} tone="gray" />
          </div>

          <div className="rounded-lg border bg-white p-6">
            <h2 className="mb-2 font-semibold text-gray-900">About this analysis</h2>
            <p className="text-xs italic text-gray-500">{fit.overall.disclaimer}</p>
            <p className="mt-2 text-xs text-gray-400">
              Engine {fit.engine_version} · Extracted{" "}
              {fit.requirements_info.extracted_count} requirements · Summary source:{" "}
              {formatLabel(fit.overall.summary_source)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ResponsibilityRow({ responsibility }: { responsibility: { responsibility: string; alignment: string; evidence: FitEvidenceItem[] } }) {
  const [showEvidence, setShowEvidence] = useState(false);
  const alignmentStyles: Record<string, string> = {
    strong: "bg-green-100 text-green-800",
    moderate: "bg-yellow-100 text-yellow-800",
    weak: "bg-orange-100 text-orange-800",
    none: "bg-red-100 text-red-800",
  };
  return (
    <div className="border-b py-3 last:border-b-0">
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${
            alignmentStyles[responsibility.alignment] || "bg-gray-100 text-gray-600"
          }`}
        >
          {responsibility.alignment}
        </span>
        <span className="text-sm text-gray-900">{responsibility.responsibility}</span>
        {responsibility.evidence.length > 0 && (
          <button
            onClick={() => setShowEvidence(!showEvidence)}
            className="ml-auto text-xs font-medium text-primary-600 hover:text-primary-800"
          >
            {showEvidence ? "Hide evidence" : "Evidence"}
          </button>
        )}
      </div>
      {showEvidence && responsibility.evidence.length > 0 && (
        <EvidenceList evidence={responsibility.evidence} />
      )}
    </div>
  );
}

function SkillGapGroup({
  label,
  skills,
  tone,
}: {
  label: string;
  skills: string[];
  tone: "green" | "yellow" | "red" | "gray";
}) {
  if (skills.length === 0) return null;
  const tones = {
    green: "bg-green-100 text-green-800",
    yellow: "bg-yellow-100 text-yellow-800",
    red: "bg-red-100 text-red-800",
    gray: "bg-gray-100 text-gray-600",
  };
  return (
    <div className="mb-3 last:mb-0">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1">
        {skills.map((skill) => (
          <span
            key={skill}
            className={`rounded px-2 py-0.5 text-xs font-medium ${tones[tone]}`}
          >
            {skill}
          </span>
        ))}
      </div>
    </div>
  );
}
