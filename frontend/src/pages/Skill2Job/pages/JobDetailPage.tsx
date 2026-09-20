import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Briefcase, Lightbulb, ShieldCheck, Target } from "lucide-react";
import { skill2jobApi } from "../../../api/skill2job";
import type { CuratedJob, JobMatchDetail } from "../../../types/skill2job";

const EVIDENCE_COLORS: Record<string, string> = {
  verified: "bg-emerald-100 text-emerald-700",
  demonstrated: "bg-green-100 text-green-700",
  supported: "bg-blue-100 text-blue-700",
  claimed: "bg-amber-50 text-amber-700",
  none: "bg-gray-100 text-gray-500",
};

const STATUS_COLORS: Record<string, string> = {
  matched: "text-green-700",
  transferable: "text-blue-700",
  missing: "text-red-700",
};

const SCORE_META: Array<{ key: keyof JobMatchDetail["scores"]; label: string }> = [
  { key: "skill", label: "Skills" },
  { key: "experience", label: "Experience" },
  { key: "education", label: "Education" },
  { key: "project", label: "Projects" },
  { key: "certification", label: "Certifications" },
  { key: "location", label: "Location" },
  { key: "employment_type", label: "Employment" },
  { key: "semantic", label: "Semantic" },
];

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-gray-600">{label}</span>
        <span className="font-bold text-gray-900">{value}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-primary-600 transition-all"
          style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<CuratedJob | null>(null);
  const [match, setMatch] = useState<JobMatchDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    async function load() {
      if (!id) return;
      try {
        const [j, m] = await Promise.all([
          skill2jobApi.getJob(id),
          skill2jobApi.getJobMatch(id),
        ]);
        if (!alive) return;
        setJob(j);
        setMatch(m);
      } catch {
        if (alive) {
          setJob(null);
          setMatch(null);
        }
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-gray-200 bg-white p-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        <span className="ml-3 text-sm text-gray-500">Loading job details...</span>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-12 text-center">
        <p className="text-sm text-gray-500">Job not found in the curated catalog.</p>
        <Link to="/skill2job/jobs" className="mt-2 inline-block text-sm font-semibold text-primary-600">
          Back to Local Jobs
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link
        to="/skill2job/jobs"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to Local Jobs
      </Link>

      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-bold text-gray-900">
              <Briefcase className="h-5 w-5 text-primary-600" aria-hidden="true" />
              {job.title}
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              {job.company} · {job.location ?? "Remote"} · {job.remote_type ?? "job"} · {job.employment_type ?? "full-time"}
            </p>
          </div>
          <div className="text-right">
            <p className="text-lg font-extrabold text-primary-700">{job.salary_range ?? "—"}</p>
            <p className="text-xs text-gray-400">{job.experience_required ?? ""}</p>
          </div>
        </div>

        {match && (
          <div className="mt-5 rounded-xl border border-primary-100 bg-primary-50/60 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="flex flex-wrap items-center gap-2 text-sm font-bold text-gray-900">
                  Your match score
                  <span className="rounded-full bg-primary-600 px-2.5 py-0.5 text-xs font-bold text-white">
                    {match.overall_score}
                  </span>
                  <span className="inline-flex items-center rounded-full bg-white px-2.5 py-0.5 text-xs font-bold capitalize text-primary-700 ring-1 ring-primary-200">
                    {match.category}
                  </span>
                  <span className="text-xs font-medium capitalize text-gray-500">{match.strength_level}</span>
                </p>
                <p className="mt-1 text-xs text-gray-600">{match.categories_explained}</p>
                <p className="mt-0.5 text-xs text-gray-400">matcher {match.match_version}</p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
              {SCORE_META.map((m) => (
                <ScoreBar key={m.key} label={m.label} value={match.scores[m.key]} />
              ))}
            </div>
          </div>
        )}

        <div className="mt-6">
          <h3 className="text-sm font-bold text-gray-900">About this role</h3>
          <p className="mt-2 text-sm leading-relaxed text-gray-600">{job.description}</p>
        </div>

        {job.required_skills.length > 0 && (
          <div className="mt-6">
            <h3 className="text-sm font-bold text-gray-900">Required Skills</h3>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {job.required_skills.map((s) => (
                <span key={s} className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {job.preferred_skills.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-bold text-gray-900">Preferred Skills</h3>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {job.preferred_skills.map((s) => (
                <span key={s} className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {job.education_required && (
          <div className="mt-4">
            <h3 className="text-sm font-bold text-gray-900">Education</h3>
            <p className="mt-1 text-sm text-gray-600">{job.education_required}</p>
          </div>
        )}

        {job.source_url && (
          <a
            href={job.source_url}
            target="_blank"
            rel="noreferrer"
            className="mt-6 inline-flex items-center gap-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700"
          >
            View original listing
          </a>
        )}
      </section>

      {match && (
        <>
          <section className="rounded-2xl border border-gray-200 bg-white p-6">
            <h3 className="flex items-center gap-2 text-sm font-bold text-gray-900">
              <Target className="h-4 w-4 text-primary-600" aria-hidden="true" />
              Skill-by-skill breakdown
              <span className="text-xs font-medium text-gray-400">
                status · evidence state ({match.skill_details.length} skills)
              </span>
            </h3>
            <ul className="mt-4 divide-y divide-gray-100">
              {match.skill_details.map((sd) => (
                <li key={`${sd.kind}-${sd.skill}`} className="py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900">
                        {sd.skill}
                        <span className="ml-2 text-xs font-medium text-gray-400">{sd.kind}</span>
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className={`text-xs font-bold capitalize ${STATUS_COLORS[sd.status] ?? "text-gray-500"}`}>
                        {sd.status}
                        {sd.similarity != null ? ` · ${Math.round(sd.similarity * 100)}%` : ""}
                      </span>
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${EVIDENCE_COLORS[sd.evidence_state] ?? "bg-gray-100 text-gray-500"}`}>
                        {sd.evidence_state}
                      </span>
                    </div>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">{sd.evidence_notes}</p>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-6">
            <h3 className="flex items-center gap-2 text-sm font-bold text-gray-900">
              <Lightbulb className="h-4 w-4 text-amber-500" aria-hidden="true" />
              How this score was derived
            </h3>
            <ul className="mt-3 space-y-1.5">
              {match.explanation.map((line, i) => (
                <li key={i} className="text-xs leading-relaxed text-gray-600">
                  · {line}
                </li>
              ))}
            </ul>
            {match.reasons.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {match.reasons.map((r) => (
                  <span key={r} className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
                    {r}
                  </span>
                ))}
              </div>
            )}
            {match.suggested_skills.length > 0 && (
              <div className="mt-4">
                <h4 className="flex items-center gap-1.5 text-xs font-bold text-gray-900">
                  <ShieldCheck className="h-3.5 w-3.5 text-primary-600" aria-hidden="true" />
                  Suggested to close the gap
                </h4>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {match.suggested_skills.slice(0, 12).map((s) => (
                    <span key={s} className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}