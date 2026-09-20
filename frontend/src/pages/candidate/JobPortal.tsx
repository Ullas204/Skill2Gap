import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { candidateJobApi } from "../../api/jobs";
import type { CandidateJobDashboard, JobSearchResult } from "../../types/jobs";

export function JobPortal() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [dashboard, setDashboard] = useState<CandidateJobDashboard | null>(null);
  const [searchResult, setSearchResult] = useState<JobSearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [q, setQ] = useState("");
  const [employmentType, setEmploymentType] = useState("");
  const [location, setLocation] = useState("");
  const [page, setPage] = useState(1);

  async function doSearch(pageNum = 1) {
    setSearching(true);
    try {
      const result = await candidateJobApi.searchJobs({
        q: q || undefined,
        employment_type: employmentType || undefined,
        location: location || undefined,
        page: pageNum,
        page_size: 10,
      });
      setSearchResult(result);
      setPage(pageNum);
    } catch {
      addToast("Failed to search jobs", "error");
    } finally {
      setSearching(false);
    }
  }

  useEffect(() => {
    async function load() {
      try {
        const [dash] = await Promise.all([
          candidateJobApi.getDashboard(),
        ]);
        setDashboard(dash);
      } catch {
        addToast("Failed to load job dashboard", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
    doSearch();
  }, []);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Job Portal</h1>
          <p className="mt-1 text-sm text-gray-500">Browse and apply for jobs</p>
        </div>
      </div>

      {dashboard && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">Applications</p>
            <p className="mt-1 text-2xl font-bold text-primary-600">{dashboard.total_applications}</p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">Saved Jobs</p>
            <p className="mt-1 text-2xl font-bold text-yellow-600">{dashboard.saved_jobs}</p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">Active Applications</p>
            <p className="mt-1 text-2xl font-bold text-green-600">{dashboard.status_breakdown?.applied || 0}</p>
          </div>
        </div>
      )}

      <div className="rounded-lg border bg-white p-4">
        <div className="flex flex-wrap gap-3">
          <input
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="Search jobs..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doSearch()}
          />
          <select
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
            value={employmentType}
            onChange={(e) => setEmploymentType(e.target.value)}
          >
            <option value="">All Types</option>
            <option value="full_time">Full Time</option>
            <option value="part_time">Part Time</option>
            <option value="contract">Contract</option>
            <option value="internship">Internship</option>
            <option value="freelance">Freelance</option>
          </select>
          <input
            className="w-48 rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="Location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doSearch()}
          />
          <button onClick={() => doSearch()} disabled={searching} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-60">
            {searching ? "Searching..." : "Search"}
          </button>
        </div>
      </div>

      {searchResult && searchResult.items.length === 0 && (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No jobs found matching your criteria.</p>
        </div>
      )}

      {searchResult && searchResult.items.length > 0 && (
        <div className="space-y-3">
          {searchResult.items.map((job) => (
            <div key={job.id} className="rounded-lg border bg-white p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3
                    className="text-lg font-semibold text-primary-600 cursor-pointer hover:text-primary-700"
                    onClick={() => navigate(`/candidate/jobs/${job.id}`)}
                  >
                    {job.title}
                  </h3>
                  <p className="text-sm text-gray-600">{job.company} · {job.location}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                      {job.employment_type.replace(/_/g, " ")}
                    </span>
                    {job.salary_min && job.salary_max && (
                      <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                        {job.salary_currency} {job.salary_min.toLocaleString()} - {job.salary_max.toLocaleString()}
                      </span>
                    )}
                    {job.application_deadline && (
                      <span className="inline-flex rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800">
                        Deadline: {job.application_deadline}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <button
                    onClick={() => navigate(`/candidate/jobs/${job.id}`)}
                    className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                  >
                    Apply
                  </button>
                  <button
                    onClick={() => navigate(`/candidate/mock-interview?jobId=${job.id}`)}
                    className="rounded-lg border border-primary-300 px-4 py-2 text-sm font-medium text-primary-700 hover:bg-primary-50"
                  >
                    Mock Interview
                  </button>
                </div>
              </div>
            </div>
          ))}

          {searchResult.total_pages > 1 && (
            <div className="flex justify-center gap-2">
              {Array.from({ length: searchResult.total_pages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => doSearch(p)}
                  className={`rounded-lg px-3 py-1 text-sm ${page === p ? "bg-primary-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
                >
                  {p}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
