import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { Button } from "../../components/ui/Button";
import { ScenarioBuilder } from "../../components/simulations/ScenarioBuilder";
import { ChangesSection } from "../../components/simulations/ChangesSection";
import { ValidationPanel } from "../../components/simulations/ValidationPanel";
import { useToast } from "../../contexts/ToastContext";
import { recruiterJobApi } from "../../api/jobs";
import { simulationApi } from "../../api/simulations";
import type { Job, JobListItem } from "../../types/jobs";
import {
  computeClientChanges,
  createDefaultSimulationConfiguration,
  simulationConfigFromBaseline,
  validateSimulationConfig,
  type SimulationBaselineConfig,
  type SimulationConfiguration,
} from "../../types/simulations";

function baselineFromJob(job: Job): SimulationBaselineConfig {
  return {
    source: "job_snapshot",
    job_id: job.id,
    job_version: job.version,
    title: job.title,
    company: job.company,
    scoring_weights: createDefaultSimulationConfiguration().scoring_weights,
    threshold: 70,
    shortlist_size: 10,
    requirements: {
      mandatory_skills: job.required_skills ?? [],
      preferred_skills: job.preferred_skills ?? [],
      experience: null,
      education: null,
      experience_required: job.experience_required,
      education_required: job.education_required,
    },
  };
}

export function CreateSimulation() {
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [jobId, setJobId] = useState("");
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [baseline, setBaseline] = useState<SimulationBaselineConfig | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [config, setConfig] = useState<SimulationConfiguration>(
    () => createDefaultSimulationConfiguration(),
  );
  const [saving, setSaving] = useState<"draft" | "ready" | null>(null);
  const [error, setError] = useState("");

  const validation = useMemo(() => validateSimulationConfig(config), [config]);
  const changes = useMemo(
    () => (baseline ? computeClientChanges(baseline, config) : null),
    [baseline, config],
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const list = await recruiterJobApi.listJobs();
        if (!cancelled) setJobs(list);
      } catch {
        if (!cancelled) addToast("Failed to load jobs", "error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [addToast]);

  async function handleJobChange(nextJobId: string) {
    setJobId(nextJobId);
    setSelectedJob(null);
    setBaseline(null);
    if (!nextJobId) {
      setError("");
      return;
    }
    try {
      const job = await recruiterJobApi.getJob(nextJobId);
      setSelectedJob(job);
      const base = baselineFromJob(job);
      setBaseline(base);
      setConfig(simulationConfigFromBaseline(base));
      setError("");
    } catch {
      setError("Failed to load the selected job.");
    }
  }

  async function handleSave(mode: "draft" | "ready") {
    if (!selectedJob) {
      setError("Select a job to simulate.");
      return;
    }
    if (!name.trim()) {
      setError("Give the simulation a name.");
      return;
    }
    if (mode === "ready" && !validation.valid) {
      setError(
        `Configuration is invalid (${validation.errors.length} issue(s)). Fix the errors before marking it ready.`,
      );
      addToast("Validated configuration before saving", "error");
      return;
    }
    setSaving(mode);
    setError("");
    try {
      const created = await simulationApi.create({
        job_id: selectedJob.id,
        name: name.trim(),
        description: description.trim() || undefined,
        simulation_config: config,
      });

      if (mode === "ready") {
        // Server-side authoritative validation & promotion. A draft survives
        // even if promotion fails so the recruiter can fix the config.
        const serverValidation = await simulationApi.validate(created.id);
        if (serverValidation.valid) {
          await simulationApi.update(created.id, { status: "ready" });
          addToast("Simulation validated and marked ready", "success");
        } else {
          addToast(
            `${serverValidation.errors.length} validation issue(s) found — saved as draft`,
            "error",
          );
        }
      } else {
        addToast("Simulation saved as draft", "success");
      }
      navigate(`/recruiter/simulations/${created.id}`);
    } catch {
      setError("Failed to create simulation. Please try again.");
      addToast("Failed to create simulation", "error");
    } finally {
      setSaving(null);
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  const inputClass =
    "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500";

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void handleSave("draft");
      }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">New Simulation</h1>
          <p className="mt-1 text-sm text-gray-500">
            Design a hiring-strategy &quot;what-if&quot; sandbox against a real job
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            type="button"
            variant="secondary"
            onClick={() => navigate("/recruiter/simulations")}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="secondary"
            isLoading={saving === "draft"}
            disabled={saving !== null}
            onClick={() => void handleSave("draft")}
          >
            Save as Draft
          </Button>
          <Button
            type="submit"
            isLoading={saving === "ready"}
            disabled={saving !== null}
            onClick={() => void handleSave("ready")}
          >
            Validate &amp; Mark Ready
          </Button>
        </div>
      </div>

      {baseline && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <span className="mt-0.5 text-base leading-none">&#9888;</span>
          <div>
            <p className="font-semibold">Sandbox Scenario</p>
            <p className="mt-0.5 text-xs text-amber-700">
              No changes have been made to the live hiring process. The job &quot;{baseline.title}
              &quot; is unaffected; this scenario is purely hypothetical.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm font-medium text-gray-700">Target job</span>
            <select
              value={jobId}
              className={`${inputClass} mt-1`}
              onChange={(e) => handleJobChange(e.target.value)}
            >
              <option value="">Select a job…</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title} — {job.company}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium text-gray-700">Name</span>
            <input
              value={name}
              placeholder="e.g. Skills-first screening experiment"
              className={`${inputClass} mt-1`}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
        </div>
        <label className="mt-4 block">
          <span className="text-sm font-medium text-gray-700">Description</span>
          <textarea
            value={description}
            rows={3}
            placeholder="What hiring question does this simulation answer?"
            className={`${inputClass} mt-1`}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
      </div>

      {baseline && selectedJob && (
        <>
          <ValidationPanel validation={validation} />
          <ScenarioBuilder baseline={baseline} config={config} onChange={setConfig} />
          {changes && <ChangesSection changes={changes} title="Review & validate" />}
        </>
      )}

      {jobs.length === 0 && (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No jobs available to simulate.</p>
          <p className="mt-1 text-sm text-gray-400">
            Create a job posting first, then return here to build a simulation.
          </p>
          <button
            type="button"
            onClick={() => navigate("/recruiter/jobs/create")}
            className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            Post a new job
          </button>
        </div>
      )}
    </form>
  );
}