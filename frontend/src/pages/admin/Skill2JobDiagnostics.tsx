import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Gauge,
  Play,
  RefreshCw,
  Server,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { skill2jobApi } from "../../api/skill2job";
import type {
  PipelineTraceSummary,
  Skill2JobCapabilities,
  Skill2JobHealth,
} from "../../types/skill2job";
import { extractErrorMessage } from "../Skill2Job/sections/shared";

export function Skill2JobDiagnostics() {
  const [health, setHealth] = useState<Skill2JobHealth | null>(null);
  const [capabilities, setCapabilities] = useState<Skill2JobCapabilities | null>(null);
  const [traces, setTraces] = useState<PipelineTraceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [h, c, t] = await Promise.all([
        skill2jobApi.getHealth(),
        skill2jobApi.getCapabilities(),
        skill2jobApi.getPipelineTraces(),
      ]);
      setHealth(h);
      setCapabilities(c);
      setTraces(t);
    } catch (err: any) {
      const msg = extractErrorMessage(err?.response?.data?.detail);
      setError(msg || "Failed to load Skill2Job diagnostics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runPipeline() {
    setRunning(true);
    try {
      await skill2jobApi.runPipeline();
      await load();
    } catch (err: any) {
      const msg = extractErrorMessage(err?.response?.data?.detail);
      setError(msg || "Pipeline run failed.");
    } finally {
      setRunning(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-gray-200 bg-white p-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
        <span className="ml-3 text-sm text-gray-500">Loading diagnostics...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gray-200 bg-white p-6">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
            <ShieldCheck className="h-5 w-5 text-primary-600" aria-hidden="true" />
            Skill2Job Diagnostics (Admin)
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Internal implementation status, capabilities, and pipeline execution traces. Hidden from
            candidates; access is restricted to super_admin/admin.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={runPipeline}
            disabled={running}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:opacity-50"
          >
            <Play className="h-4 w-4" aria-hidden="true" />
            {running ? "Running pipeline…" : "Run full pipeline"}
          </button>
          <button
            type="button"
            onClick={load}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-gray-200 bg-white p-6">
          <h3 className="flex items-center gap-2 text-sm font-bold text-gray-900">
            <Server className="h-4 w-4 text-gray-400" aria-hidden="true" /> Health
          </h3>
          <p className="mt-2 text-sm text-gray-600">
            Module: <span className="font-semibold">{health?.module ?? "—"}</span> · Status:{" "}
            <span
              className={`font-semibold ${health?.status === "ok" || health?.status === "healthy" ? "text-green-600" : "text-amber-600"}`}
            >
              {health?.status ?? "unknown"}
            </span>
          </p>
        </section>

        <section className="rounded-2xl border border-gray-200 bg-white p-6">
          <h3 className="flex items-center gap-2 text-sm font-bold text-gray-900">
            <Gauge className="h-4 w-4 text-gray-400" aria-hidden="true" /> Capabilities
          </h3>
          <ul className="mt-3 divide-y divide-gray-100">
            {capabilities?.capabilities.map((c) => (
              <li key={c.key} className="flex items-center justify-between gap-3 py-2">
                <div>
                  <p className="text-sm font-medium text-gray-800">{c.label}</p>
                  <p className="text-xs text-gray-400">
                    phase {c.phase} &middot; {c.key}
                  </p>
                </div>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    c.status === "available" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {c.status}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <h3 className="flex items-center gap-2 text-sm font-bold text-gray-900">
          <Workflow className="h-4 w-4 text-gray-400" aria-hidden="true" /> Pipeline Executions
        </h3>
        {traces.length === 0 ? (
          <p className="mt-3 text-sm text-gray-400">No pipeline runs recorded yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-gray-100">
            {traces.map((t) => (
              <li key={t.run_id} className="flex items-center justify-between gap-4 py-2">
                <span className="flex items-center gap-2 text-xs text-gray-500">
                  <Activity className="h-3.5 w-3.5" aria-hidden="true" />
                  <code className="truncate">{t.run_id}</code>
                </span>
                <span className="shrink-0 text-xs text-gray-400">
                  {t.steps} steps{t.created_at ? ` · ${new Date(t.created_at).toLocaleString()}` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}