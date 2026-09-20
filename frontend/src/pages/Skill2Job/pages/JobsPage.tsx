import { useCallback, useEffect, useState } from "react";
import { Briefcase, ChevronLeft, ChevronRight, RefreshCw, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { skill2jobApi } from "../../../api/skill2job";
import type { CuratedJob, CuratedJobCounts } from "../../../types/skill2job";
import { MatchSection } from "../sections/MatchSection";
import { SnapshotStat } from "../sections/shared";

const PAGE_SIZE = 12;

export default function JobsPage() {
  const [jobs, setJobs] = useState<CuratedJob[]>([]);
  const [counts, setCounts] = useState<CuratedJobCounts | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [cat, cnt] = await Promise.all([
        skill2jobApi.getCatalog({
          ...(keyword ? { keyword } : {}),
          ...(location ? { location } : {}),
          ...(remoteOnly ? { remote_only: true } : {}),
          limit: PAGE_SIZE,
          offset,
        }),
        skill2jobApi.getJobCounts(),
      ]);
      setJobs(cat.jobs);
      setTotal(cat.total);
      setCounts(cnt);
      setFailed(false);
    } catch {
      setFailed(true);
      setJobs([]);
    } finally {
      setBusy(false);
    }
  }, [keyword, location, remoteOnly, offset]);

  useEffect(() => {
    load();
  }, [load]);

  const applyFilters = () => {
    setOffset(0);
    load();
  };

  const resetFilters = () => {
    setKeyword("");
    setLocation("");
    setRemoteOnly(false);
    setOffset(0);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <Briefcase className="h-5 w-5 text-primary-600" aria-hidden="true" />
              Curated Local Job Catalog
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Server-filtered, paginated catalog served by the job intelligence endpoint.
            </p>
          </div>
          <button
            type="button"
            disabled={busy}
            onClick={load}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" /> Refresh
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

        <div className="mt-5 flex flex-wrap items-end gap-3 border-t border-gray-100 pt-4">
          <div className="min-w-52 flex-1">
            <label htmlFor="job-keyword" className="text-xs font-semibold uppercase tracking-wide text-gray-400">
              Keyword
            </label>
            <div className="relative mt-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" aria-hidden="true" />
              <input
                id="job-keyword"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applyFilters()}
                placeholder="title, company, stack…"
                className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-3 text-sm text-gray-700 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
              />
            </div>
          </div>
          <div>
            <label htmlFor="job-location" className="text-xs font-semibold uppercase tracking-wide text-gray-400">
              Location
            </label>
            <select
              id="job-location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="mt-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 outline-none focus:border-primary-500"
            >
              <option value="">All locations</option>
              {counts?.top_locations.map((l) => (
                <option key={l.location} value={l.location}>
                  {l.location} ({l.count})
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 pb-2.5 text-sm font-medium text-gray-600">
            <input
              type="checkbox"
              checked={remoteOnly}
              onChange={(e) => setRemoteOnly(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            Remote / hybrid only
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={applyFilters}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary-700 disabled:opacity-50"
            >
              <Search className="h-4 w-4" aria-hidden="true" /> Apply
            </button>
            <button
              type="button"
              onClick={resetFilters}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Reset
            </button>
          </div>
        </div>
      </section>

      {failed ? (
        <section className="rounded-2xl border border-gray-200 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">No job catalog available yet.</p>
        </section>
      ) : (
        <section className="rounded-2xl border border-gray-200 bg-white p-6">
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-gray-500">
              Showing {jobs.length ? offset + 1 : 0}–{offset + jobs.length} of {total} jobs
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={busy || offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                className="inline-flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
              >
                <ChevronLeft className="h-4 w-4" aria-hidden="true" /> Prev
              </button>
              <span className="text-xs text-gray-500">
                Page {currentPage} / {totalPages}
              </span>
              <button
                type="button"
                disabled={busy || offset + jobs.length >= total}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
                className="inline-flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
              >
                Next <ChevronRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>

          {jobs.length === 0 ? (
            <p className="mt-6 text-center text-sm text-gray-400">Nothing matches your filters.</p>
          ) : (
            <ul className="mt-3 divide-y divide-gray-100">
              {jobs.map((j) => (
                <li key={j.id}>
                  <Link
                    to={`/skill2job/jobs/${j.id}`}
                    className="flex items-start justify-between gap-4 py-4 transition-colors hover:bg-gray-50"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-gray-900">
                        {j.title}
                      </p>
                      <p className="text-xs text-gray-500">
                        {j.company} · {j.location ?? "Remote"} · {j.remote_type ?? "job"}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {j.required_skills.slice(0, 6).map((s) => (
                          <span key={s} className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                            {s}
                          </span>
                        ))}
                        {j.required_skills.length > 6 && (
                          <span className="text-xs text-gray-400">+{j.required_skills.length - 6}</span>
                        )}
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-sm font-extrabold text-primary-700">{j.salary_range ?? "—"}</p>
                      <p className="text-xs text-gray-400">{j.experience_required ?? ""}</p>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <MatchSection />
    </div>
  );
}