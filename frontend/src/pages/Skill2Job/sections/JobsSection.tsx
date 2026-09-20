import { useEffect, useState } from "react";
import { Briefcase } from "lucide-react";
import { skill2jobApi } from "../../../api/skill2job";
import type { CuratedJob, CuratedJobCounts } from "../../../types/skill2job";
import { SnapshotStat } from "./shared";

export function JobsSection() {
  const [jobs, setJobs] = useState<CuratedJob[]>([]);
  const [counts, setCounts] = useState<CuratedJobCounts | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function load() {
    setBusy(true);
    try {
      const [cat, cnt] = await Promise.all([
        skill2jobApi.getCatalog({ limit: 12 }),
        skill2jobApi.getJobCounts(),
      ]);
      setJobs(cat.jobs);
      setCounts(cnt);
      setFailed(false);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
            <Briefcase className="h-5 w-5 text-primary-600" aria-hidden="true" />
            Curated Local Job Catalog
          </h2>
          <p className="mt-1 text-sm text-gray-500">Real local openings served by the job intelligence endpoint.</p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={load}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {counts && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <SnapshotStat label="Total jobs" value={counts.total} />
          <SnapshotStat label="Remote" value={counts.remote} />
          <SnapshotStat label="On-site" value={counts.on_site} />
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Top location</p>
            <p className="text-sm font-bold text-gray-800">{counts.top_locations[0]?.location ?? "—"}</p>
          </div>
        </div>
      )}

      {failed ? (
        <p className="mt-4 text-sm text-gray-400">No job catalog available yet.</p>
      ) : (
        <ul className="mt-4 divide-y divide-gray-100">
          {jobs.map((j) => (
            <li key={j.id} className="flex items-start justify-between gap-4 py-4">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-gray-900">{j.title}</p>
                <p className="text-xs text-gray-500">
                  {j.company} · {j.location ?? "Remote"} · {j.remote_type ?? "job"}
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {j.required_skills.slice(0, 8).map((s) => (
                    <span key={s} className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-sm font-extrabold text-primary-700">{j.salary_range ?? "—"}</p>
                <p className="text-xs text-gray-400">{j.experience_required ?? ""}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}