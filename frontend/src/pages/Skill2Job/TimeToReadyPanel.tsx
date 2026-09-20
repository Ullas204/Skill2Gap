import { useState } from "react";
import {
  Clock,
  IndianRupee,
  BookOpen,
  TrendingUp,
  Zap,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { skill2jobApi } from "../../api/skill2job";

/** Safely extract a displayable string from any API error detail. */
function extractErrorMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === "object" && first !== null) {
      return (first as any).msg || (first as any).message || (first as any).detail || JSON.stringify(first);
    }
    return String(first);
  }
  if (typeof detail === "object" && detail !== null) {
    return (detail as any).msg || (detail as any).message || (detail as any).detail || JSON.stringify(detail);
  }
  return "";
}

interface LearningStep {
  step_number: number;
  skill: string;
  resource: {
    resource_id: string;
    title: string;
    provider: string;
    url: string | null;
    skills: string[];
    duration_hours: number | null;
    cost: number | null;
    is_free: boolean;
    difficulty: string;
    certificate: boolean;
    skill_coverage: number;
    prerequisites: string[];
  };
  weeks: number;
  hours: number;
  cost: number;
  is_free: boolean;
  can_parallel: boolean;
  parallel_group: number | null;
  explanation: string;
}

interface MissingSkill {
  skill: string;
  priority: string;
  importance: number;
  jobs_demanding: string[];
  dependencies: string[];
  has_free_resource: boolean;
}

interface TTRResult {
  target_job: string;
  job_id: string | null;
  current_readiness: number;
  projected_readiness: number;
  missing_skills: MissingSkill[];
  learning_plan: LearningStep[];
  estimated_weeks: number;
  estimated_hours: number;
  estimated_cost: number;
  currency: string;
  free_only: {
    estimated_weeks: number;
    estimated_hours: number;
    estimated_cost: number;
    coverage_pct: number;
    remaining_gaps: string[];
  };
  opportunity_unlock: {
    current_jobs: number;
    projected_jobs: number;
    potential_increase: number;
  };
}

function priorityColor(p: string) {
  if (p === "critical") return "bg-red-100 text-red-700 border-red-200";
  if (p === "high") return "bg-orange-100 text-orange-700 border-orange-200";
  if (p === "medium") return "bg-blue-100 text-blue-700 border-blue-200";
  return "bg-gray-100 text-gray-600 border-gray-200";
}

export function TimeToReadyPanel() {
  const [result, setResult] = useState<TTRResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hoursPerWeek, setHoursPerWeek] = useState(10);
  const [freeOnly, setFreeOnly] = useState(false);
  const [expandedPlan, setExpandedPlan] = useState<number | null>(null);
  const [jobTitle, setJobTitle] = useState("");

  async function calculate() {
    setLoading(true);
    setError("");
    try {
      const data = await skill2jobApi.calculateTimeToReady({
        job_title: jobTitle || undefined,
        hours_per_week: hoursPerWeek,
        free_only: freeOnly,
      });
      setResult(data as unknown as TTRResult);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg = extractErrorMessage(detail);
      setError(msg || "Failed to calculate time-to-ready.");
    } finally {
      setLoading(false);
    }
  }

  const r = result;

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
          <Clock className="h-5 w-5 text-primary-600" />
          Time-to-Ready Estimate
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          How long and how much will it take you to become ready for a target job?
        </p>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label className="block text-sm font-medium text-gray-700">Target Job Title</label>
            <input
              type="text"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              placeholder="e.g. Data Scientist"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Hours per Week</label>
            <select
              value={hoursPerWeek}
              onChange={(e) => setHoursPerWeek(Number(e.target.value))}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
            >
              {[5, 10, 15, 20, 25, 30, 40].map((h) => (
                <option key={h} value={h}>{h}h/week</option>
              ))}
            </select>
          </div>
          <div className="flex items-end gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={freeOnly}
                onChange={(e) => setFreeOnly(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              Free learning only
            </label>
            <button
              onClick={calculate}
              disabled={loading}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? "Calculating..." : "Calculate"}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="mr-1 inline h-4 w-4" /> {error}
        </div>
      )}

      {r && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <SummaryCard
              icon={<Clock className="h-5 w-5 text-blue-600" />}
              label="Estimated Time"
              value={`${r.estimated_weeks} weeks`}
              sub={`${r.estimated_hours} hours total`}
            />
            <SummaryCard
              icon={<IndianRupee className="h-5 w-5 text-green-600" />}
              label="Estimated Cost"
              value={r.estimated_cost === 0 ? "Free" : `${r.currency} ${r.estimated_cost.toLocaleString()}`}
              sub={`${r.missing_skills.length} skills to learn`}
            />
            <SummaryCard
              icon={<TrendingUp className="h-5 w-5 text-purple-600" />}
              label="Current Readiness"
              value={`${Math.round(r.current_readiness * 100)}%`}
              sub={`After plan: ${Math.round(r.projected_readiness * 100)}%`}
            />
            <SummaryCard
              icon={<Zap className="h-5 w-5 text-amber-600" />}
              label="Jobs Unlocked"
              value={`+${r.opportunity_unlock.potential_increase}`}
              sub={`${r.opportunity_unlock.current_jobs} -> ${r.opportunity_unlock.projected_jobs}`}
            />
          </div>

          {/* Free vs Paid comparison */}
          {!freeOnly && r.estimated_cost > 0 && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                <div className="text-xs font-medium uppercase text-blue-600">Fastest Path</div>
                <div className="mt-1 text-lg font-bold text-blue-900">{r.estimated_weeks} weeks</div>
                <div className="text-sm text-blue-700">{r.currency} {r.estimated_cost.toLocaleString()}</div>
              </div>
              <div className="rounded-xl border border-green-200 bg-green-50 p-4">
                <div className="text-xs font-medium uppercase text-green-600">Free Only</div>
                <div className="mt-1 text-lg font-bold text-green-900">{r.free_only.estimated_weeks} weeks</div>
                <div className="text-sm text-green-700">{r.currency} 0</div>
              </div>
              <div className="rounded-xl border border-purple-200 bg-purple-50 p-4">
                <div className="text-xs font-medium uppercase text-purple-600">Free Coverage</div>
                <div className="mt-1 text-lg font-bold text-purple-900">{r.free_only.coverage_pct}%</div>
                {r.free_only.remaining_gaps.length > 0 && (
                  <div className="text-xs text-purple-600">Missing: {r.free_only.remaining_gaps.join(", ")}</div>
                )}
              </div>
            </div>
          )}

          {/* Missing Skills */}
          {r.missing_skills.length > 0 && (
            <div className="rounded-2xl border border-gray-200 bg-white p-6">
              <h3 className="text-base font-bold text-gray-900">Skills to Close</h3>
              <div className="mt-3 flex flex-wrap gap-2">
                {r.missing_skills.map((s) => (
                  <span
                    key={s.skill}
                    className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium ${priorityColor(s.priority)}`}
                  >
                    {s.skill}
                    <span className="text-[10px] opacity-70">({s.priority})</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Learning Plan */}
          {r.learning_plan.length > 0 && (
            <div className="rounded-2xl border border-gray-200 bg-white p-6">
              <h3 className="text-base font-bold text-gray-900">
                <BookOpen className="mr-1 inline h-4 w-4" /> Learning Plan
              </h3>
              <div className="mt-3 space-y-3">
                {r.learning_plan.map((step) => (
                  <div
                    key={step.step_number}
                    className="rounded-xl border border-gray-100 bg-gray-50 p-4"
                  >
                    <div
                      className="flex cursor-pointer items-center justify-between"
                      onClick={() => setExpandedPlan(expandedPlan === step.step_number ? null : step.step_number)}
                    >
                      <div className="flex items-center gap-3">
                        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-700">
                          {step.step_number}
                        </span>
                        <div>
                          <div className="text-sm font-semibold text-gray-900">{step.resource.title}</div>
                          <div className="text-xs text-gray-500">
                            {step.resource.provider} | {step.weeks} weeks | {step.hours}h
                            {step.resource.certificate && " | Certificate"}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${step.is_free ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
                          {step.is_free ? "Free" : `${r.currency} ${step.cost.toLocaleString()}`}
                        </span>
                        {step.can_parallel && (
                          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                            Parallel
                          </span>
                        )}
                        {expandedPlan === step.step_number ? (
                          <ChevronUp className="h-4 w-4 text-gray-400" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-gray-400" />
                        )}
                      </div>
                    </div>
                    {expandedPlan === step.step_number && (
                      <div className="mt-3 border-t border-gray-200 pt-3 text-sm text-gray-600">
                        <p className="mb-2">{step.explanation}</p>
                        {step.resource.url && (
                          <a
                            href={step.resource.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-primary-600 hover:underline"
                          >
                            Open resource <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                        {step.resource.prerequisites.length > 0 && (
                          <p className="mt-1 text-xs text-gray-400">
                            Prerequisites: {step.resource.prerequisites.join(", ")}
                          </p>
                        )}
                        <div className="mt-1 text-xs text-gray-400">
                          Coverage: {Math.round(step.resource.skill_coverage * 100)}% | Difficulty: {step.resource.difficulty}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {r.missing_skills.length === 0 && (
            <div className="rounded-2xl border border-green-200 bg-green-50 p-8 text-center">
              <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
              <h3 className="mt-3 text-lg font-bold text-green-900">You are already ready!</h3>
              <p className="mt-1 text-sm text-green-700">
                Your current skills match all requirements for {r.target_job}.
              </p>
            </div>
          )}
        </>
      )}

      {!result && !loading && !error && (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-gray-50 p-12 text-center text-gray-400">
          <Clock className="mx-auto h-10 w-10 opacity-50" />
          <p className="mt-3 text-sm">Enter a target job title and click Calculate to see your personalized learning path.</p>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub: string }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4">
      <div className="flex items-center gap-2 text-sm text-gray-500">{icon} {label}</div>
      <div className="mt-1 text-xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-400">{sub}</div>
    </div>
  );
}
