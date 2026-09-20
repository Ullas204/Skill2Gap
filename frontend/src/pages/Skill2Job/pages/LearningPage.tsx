import { useEffect, useState, useCallback } from "react";
import {
  GraduationCap,
  Clock,
  IndianRupee,
  TrendingUp,
  Zap,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  AlertCircle,
} from "lucide-react";
import { skill2jobApi } from "../../../api/skill2job";
import type {
  LearningPlanForJob,
  OverviewTimeToReadyItem,
} from "../../../types/skill2job";

const HOURS_OPTIONS = [5, 10, 15, 20, 30, 40];
const MODES = ["fastest", "balanced", "lowest_cost", "free_only"] as const;
const MODE_LABELS: Record<string, string> = {
  fastest: "Fastest",
  balanced: "Balanced",
  lowest_cost: "Lowest Cost",
  free_only: "Free Only",
};

export default function LearningPage() {
  const [matchedJobs, setMatchedJobs] = useState<OverviewTimeToReadyItem[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [hoursPerWeek, setHoursPerWeek] = useState(10);
  const [mode, setMode] = useState<string>("fastest");
  const [plan, setPlan] = useState<LearningPlanForJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [jobsLoading, setJobsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setJobsLoading(true);
        const jobs = await skill2jobApi.compareJobs();
        if (!cancelled) {
          setMatchedJobs(jobs);
          if (jobs.length > 0 && selectedJobId === null) {
            setSelectedJobId(jobs[0].job_id);
          }
        }
      } catch {
        if (!cancelled) setError("Failed to load matched jobs.");
      } finally {
        if (!cancelled) setJobsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const fetchPlan = useCallback(async () => {
    if (selectedJobId === null) return;
    setLoading(true);
    setError(null);
    setPlan(null);
    try {
      const freeOnly = mode === "free_only";
      const res = await skill2jobApi.getLearningPlanForJob(selectedJobId, {
        hours_per_week: hoursPerWeek,
        free_only: freeOnly,
        optimization_mode: freeOnly ? undefined : mode,
      });
      setPlan(res);
    } catch {
      setError("Failed to load learning plan.");
    } finally {
      setLoading(false);
    }
  }, [selectedJobId, hoursPerWeek, mode]);

  useEffect(() => {
    if (selectedJobId !== null) fetchPlan();
  }, [selectedJobId, fetchPlan]);

  const toggleStep = (idx: number) => {
    setExpandedStep((prev) => (prev === idx ? null : idx));
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-10 space-y-8">
      <div className="flex items-center gap-3">
        <GraduationCap className="w-8 h-8 text-primary-600" />
        <h1 className="text-2xl font-bold text-gray-900">Learning Plan</h1>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[220px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Target Job
            </label>
            {jobsLoading ? (
              <div className="h-10 bg-gray-100 rounded-lg animate-pulse" />
            ) : matchedJobs.length === 0 ? (
              <p className="text-sm text-gray-500">No matched jobs found.</p>
            ) : (
              <select
                value={selectedJobId ?? ""}
                onChange={(e) => {
                  setSelectedJobId(e.target.value);
                  setExpandedStep(null);
                }}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                {matchedJobs.map((j) => (
                  <option key={j.job_id} value={j.job_id}>
                    {j.job_title} — {j.missing_skills_count} gaps, ~{j.estimated_weeks}w
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="w-40">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Hours / Week
            </label>
            <select
              value={hoursPerWeek}
              onChange={(e) => setHoursPerWeek(Number(e.target.value))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              {HOURS_OPTIONS.map((h) => (
                <option key={h} value={h}>
                  {h}h
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {MODES.map((m) => (
            <button
              key={m}
              onClick={() => {
                setMode(m);
                setExpandedStep(null);
              }}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                mode === m
                  ? "bg-primary-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {MODE_LABELS[m] ?? m}
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-16">
          <div className="w-10 h-10 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && !plan && matchedJobs.length > 0 && (
        <p className="text-center text-gray-400 py-12">
          Select a job and configure options to see your learning plan.
        </p>
      )}

      {/* Plan Content */}
      {!loading && !error && plan && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <SummaryCard
              icon={<TrendingUp className="w-5 h-5 text-primary-600" />}
              label="Readiness"
              value={`${Math.round(plan.current_readiness)}%`}
            />
            <SummaryCard
              icon={<Clock className="w-5 h-5 text-blue-600" />}
              label="Est. Weeks"
              value={String(plan.total_weeks)}
            />
            <SummaryCard
              icon={<IndianRupee className="w-5 h-5 text-green-600" />}
              label="Est. Cost"
              value={`₹${plan.total_cost.toLocaleString()}`}
            />
            <SummaryCard
              icon={<GraduationCap className="w-5 h-5 text-amber-600" />}
              label="Jobs Unlocked"
              value={`${plan.opportunity_unlock.current_jobs} → ${plan.opportunity_unlock.projected_jobs}`}
            />
          </div>

          {/* Free Only Comparison */}
          {mode !== "free_only" && plan.free_only_path && (
            <div className="bg-white rounded-2xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Free Only Path
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Weeks</p>
                  <p className="font-semibold text-gray-900">{plan.free_only_path.weeks}</p>
                </div>
                <div>
                  <p className="text-gray-500">Hours</p>
                  <p className="font-semibold text-gray-900">{plan.free_only_path.hours}</p>
                </div>
                <div>
                  <p className="text-gray-500">Cost</p>
                  <p className="font-semibold text-green-600">₹{plan.free_only_path.cost.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-gray-500">Coverage</p>
                  <p className="font-semibold text-gray-900">{Math.round(plan.free_only_path.coverage_pct)}%</p>
                </div>
              </div>
              {plan.free_only_path.remaining_gaps.length > 0 && (
                <p className="mt-3 text-sm text-amber-700">
                  Remaining gaps (free): {plan.free_only_path.remaining_gaps.join(", ")}
                </p>
              )}
            </div>
          )}

          {/* Missing Skills */}
          {plan.missing_skills.length > 0 && (
            <div className="bg-white rounded-2xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Missing Skills
              </h2>
              <div className="flex flex-wrap gap-3">
                {plan.missing_skills.map((skill) => (
                  <span
                    key={skill.skill}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${
                      skill.priority === "high"
                        ? "bg-red-100 text-red-700"
                        : skill.priority === "medium"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {skill.skill}
                    <span className="text-xs opacity-70">
                      ({skill.priority})
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Learning Steps */}
          {plan.learning_plan.length === 0 ? (
            <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center">
              <Zap className="w-10 h-10 text-primary-600 mx-auto mb-3" />
              <p className="text-gray-600 font-medium">
                You are already well-matched for this role!
              </p>
              <p className="text-sm text-gray-400 mt-1">
                No additional learning steps recommended.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-gray-900">
                Learning Steps
              </h2>
              {plan.learning_plan.map((step, idx) => {
                const isOpen = expandedStep === idx;
                return (
                  <div
                    key={idx}
                    className="bg-white rounded-2xl border border-gray-200 overflow-hidden"
                  >
                    <button
                      onClick={() => toggleStep(idx)}
                      className="w-full flex items-center gap-4 p-5 text-left hover:bg-gray-50 transition-colors"
                    >
                      <span className="w-8 h-8 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-sm font-bold shrink-0">
                        {step.step_number}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 truncate">
                          {step.resource_title}
                        </p>
                        <p className="text-sm text-gray-500">
                          {step.resource_provider} &middot; {step.weeks}w
                          {step.cost > 0
                            ? ` · ₹${step.cost.toLocaleString()}`
                            : " · Free"}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {step.is_free && (
                          <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-medium">
                            Free
                          </span>
                        )}
                        {step.can_parallel && (
                          <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-medium">
                            Parallel
                          </span>
                        )}
                        {isOpen ? (
                          <ChevronUp className="w-4 h-4 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-gray-400" />
                        )}
                      </div>
                    </button>

                    {isOpen && (
                      <div className="px-5 pb-5 border-t border-gray-100 pt-4 space-y-3">
                        {step.explanation && (
                          <p className="text-sm text-gray-600 leading-relaxed">
                            {step.explanation}
                          </p>
                        )}
                        {step.resource_url && (
                          <a
                            href={step.resource_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary-600 hover:text-primary-700"
                          >
                            Open Resource
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SummaryCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
    </div>
  );
}
