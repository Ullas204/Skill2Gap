import { useEffect, useState } from "react";
import { AlertCircle, ArrowUp, RefreshCw, Rocket, Sparkles } from "lucide-react";
import { skill2jobApi } from "../../../api/skill2job";
import type { OpportunityDashboard, SimulationResult, SimulatedJob } from "../../../types/skill2job";
import { extractErrorMessage } from "../sections/shared";

function JobList({ items, highlight }: { items: SimulatedJob[]; highlight?: boolean }) {
  if (items.length === 0) return <p className="mt-2 text-sm text-gray-400">No roles scored.</p>;
  return (
    <ul className="mt-3 divide-y divide-gray-100">
      {items.slice(0, 8).map((j) => (
        <li key={j.job_id} className="flex items-center justify-between gap-3 py-2.5">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-gray-800">{j.title}</p>
            <p className="text-xs text-gray-500">{j.company} · {j.location ?? "Remote"}</p>
          </div>
          <p className="shrink-0 text-sm font-extrabold text-primary-700">{j.overall_score}</p>
        </li>
      ))}
      {highlight && items.length > 8 && (
        <li className="py-2 text-xs text-gray-400">… and {items.length - 8} more</li>
      )}
    </ul>
  );
}

export default function OpportunitiesPage() {
  const [dashboard, setDashboard] = useState<OpportunityDashboard | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [error, setError] = useState("");
  const [skillsToAdd, setSkillsToAdd] = useState("");
  const [dreamJob, setDreamJob] = useState("");
  const [ownAssessment, setOwnAssessment] = useState("");
  const [result, setResult] = useState<SimulationResult | null>(null);

  async function loadDashboard() {
    try {
      setDashboard(await skill2jobApi.getOpportunityDashboard());
    } catch {
      setDashboard(null);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  async function simulate() {
    setError("");
    setResult(null);
    const skills = skillsToAdd
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (skills.length === 0) {
      setError("Add at least one skill to simulate.");
      return;
    }
    setSimulating(true);
    try {
      const res = await skill2jobApi.runSimulation({
        skills_to_add: skills,
        dream_job_title: dreamJob || null,
        own_assessment: ownAssessment || null,
        limit: 10,
      });
      setResult(res);
    } catch (err: any) {
      const msg = extractErrorMessage(err?.response?.data?.detail);
      setError(msg || "Simulation failed. Make sure matching has been run first.");
    } finally {
      setSimulating(false);
    }
  }

  const top = dashboard?.top_opportunity as Record<string, unknown> | null;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <Rocket className="h-5 w-5 text-primary-600" aria-hidden="true" />
              Opportunity Unlock Dashboard
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Roles you could qualify for by adding specific skills — computed from the real
              opportunity engine.
            </p>
          </div>
          <button
            type="button"
            onClick={loadDashboard}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" /> Refresh
          </button>
        </div>

        {dashboard ? (
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-xl bg-primary-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Unlocked Roles</p>
              <p className="mt-1 text-2xl font-extrabold text-primary-700">{dashboard.unlocked_count}</p>
            </div>
            <div className="rounded-xl bg-green-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Potential Score</p>
              <p className="mt-1 text-2xl font-extrabold text-green-700">{dashboard.potential}</p>
            </div>
            <div className="rounded-xl bg-amber-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Top Track</p>
              <p className="mt-1 text-sm font-bold text-gray-800">
                {top?.title ? String(top.title) : (dashboard.top_roles[0] as Record<string, unknown>)?.title
                  ? String((dashboard.top_roles[0] as Record<string, unknown>).title)
                  : "—"}
              </p>
            </div>
          </div>
        ) : (
          <p className="mt-4 text-sm text-gray-400">
            No opportunity profile yet — run matching first, then come back here.
          </p>
        )}
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary-600" aria-hidden="true" />
          <h2 className="text-lg font-bold text-gray-900">What-If Opportunity Simulator</h2>
        </div>
        <p className="mt-1 text-sm text-gray-500">
          Pick skills you plan to learn (comma-separated) and see how your scores change across the
          real job catalog.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <label className="text-xs font-semibold text-gray-600" htmlFor="sim-skills">
              Skills to add *
            </label>
            <input
              id="sim-skills"
              value={skillsToAdd}
              onChange={(e) => setSkillsToAdd(e.target.value)}
              placeholder="e.g. Apache Spark, Docker, Tableau"
              className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600" htmlFor="sim-dream-job">
              Dream job title (optional)
            </label>
            <input
              id="sim-dream-job"
              value={dreamJob}
              onChange={(e) => setDreamJob(e.target.value)}
              placeholder="e.g. Data Engineer"
              className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
            />
          </div>
        </div>
        <label className="mt-3 block text-xs font-semibold text-gray-600" htmlFor="sim-assessment">
          Your own assessment (optional)
        </label>
        <textarea
          id="sim-assessment"
          value={ownAssessment}
          onChange={(e) => setOwnAssessment(e.target.value)}
          rows={2}
          placeholder="e.g. I am comfortable writing Python, need more cloud experience..."
          className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-100"
        />

        <button
          type="button"
          disabled={simulating}
          onClick={simulate}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
        >
          <Rocket className="h-4 w-4" aria-hidden="true" />
          {simulating ? "Simulating…" : "Run simulation"}
        </button>

        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            {error}
          </div>
        )}

        {result && (
          <div className="mt-6 space-y-6">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-green-100 px-3 py-1 text-sm font-bold text-green-700">
                {result.unlocked_count} role(s) unlocked
              </span>
              <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
                using: {result.skills_added.join(", ")}
              </span>
            </div>

            {result.top_uplift.length > 0 && (
              <div>
                <h3 className="text-sm font-bold text-gray-900">Biggest score uplifts</h3>
                <ul className="mt-2 space-y-2">
                  {result.top_uplift.slice(0, 5).map((u) => (
                    <li key={u.job_id} className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-gray-800">{u.title}</p>
                        <p className="shrink-0 text-sm font-bold text-primary-700">
                          {u.before} <ArrowUp className="inline h-4 w-4 text-green-600" aria-hidden="true" /> {u.after}
                          <span className="ml-1 text-xs font-semibold text-green-600">+{u.uplift}</span>
                        </p>
                      </div>
                      {u.newly_matched_skills.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {u.newly_matched_skills.slice(0, 5).map((s) => (
                            <span key={s} className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                              {s}
                            </span>
                          ))}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <h3 className="text-sm font-bold text-gray-900">Before</h3>
                <JobList items={result.baseline} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-gray-900">After adding skills</h3>
                <JobList items={result.simulated} />
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}