import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { recruiterJobApi } from "../../api/jobs";
import type { JobListItem, RecruiterDashboard } from "../../types/jobs";

export function RecruiterJobDashboard() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [dashboard, setDashboard] = useState<RecruiterDashboard | null>(null);
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [dash, jobList] = await Promise.all([
          recruiterJobApi.getDashboard(),
          recruiterJobApi.listJobs(),
        ]);
        setDashboard(dash);
        setJobs(jobList);
      } catch {
        addToast("Failed to load job dashboard", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [addToast]);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Job Management</h1>
          <p className="mt-1 text-sm text-gray-500">
            Create and manage job postings
          </p>
        </div>
        <button
          onClick={() => navigate("/recruiter/jobs/create")}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Post New Job
        </button>
      </div>

      {dashboard && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">Total Jobs</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{dashboard.total_jobs}</p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">Published</p>
            <p className="mt-1 text-2xl font-bold text-green-600">{dashboard.published_jobs}</p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">Drafts</p>
            <p className="mt-1 text-2xl font-bold text-yellow-600">{dashboard.draft_jobs}</p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">Total Applications</p>
            <p className="mt-1 text-2xl font-bold text-primary-600">{dashboard.total_applications}</p>
          </div>
        </div>
      )}

      {jobs.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No job postings yet.</p>
          <button
            onClick={() => navigate("/recruiter/jobs/create")}
            className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            Create your first job posting
          </button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Title</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Applications</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Deadline</th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{job.title}</div>
                    <div className="text-sm text-gray-500">{job.company} · {job.location}</div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                      job.status === "published" ? "bg-green-100 text-green-800" :
                      job.status === "draft" ? "bg-yellow-100 text-yellow-800" :
                      "bg-gray-100 text-gray-800"
                    }`}>
                      {job.status}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">{job.application_count}</td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {job.application_deadline || "No deadline"}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right text-sm">
                    <button
                      onClick={() => navigate(`/recruiter/jobs/${job.id}`)}
                      className="text-primary-600 hover:text-primary-900"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dashboard && dashboard.recent_applications.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Recent Applications</h2>
          <div className="space-y-2">
            {dashboard.recent_applications.map((app) => (
              <div key={app.id} className="rounded-lg border bg-white p-3 text-sm">
                <span className="font-medium text-gray-900">{app.candidate_name}</span>
                <span className="text-gray-500"> applied for </span>
                <span className="font-medium text-gray-900">{app.job_title}</span>
                <span className={`ml-2 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                  app.status === "applied" ? "bg-blue-100 text-blue-800" :
                  app.status === "shortlisted" ? "bg-purple-100 text-purple-800" :
                  "bg-gray-100 text-gray-800"
                }`}>
                  {app.status.replace(/_/g, " ")}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
