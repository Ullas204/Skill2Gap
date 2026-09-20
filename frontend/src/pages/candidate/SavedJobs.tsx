import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { candidateJobApi } from "../../api/jobs";
import type { JobListItem } from "../../types/jobs";

export function SavedJobs() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [savedJobs, setSavedJobs] = useState<JobListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await candidateJobApi.getSavedJobs();
        setSavedJobs(data);
      } catch {
        addToast("Failed to load saved jobs", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [addToast]);

  async function handleUnsave(jobId: string) {
    try {
      await candidateJobApi.unsaveJob(jobId);
      setSavedJobs(savedJobs.filter((j) => j.id !== jobId));
      addToast("Job removed from saved list", "success");
    } catch {
      addToast("Failed to unsave job", "error");
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Saved Jobs</h1>
        <p className="mt-1 text-sm text-gray-500">Jobs you've saved for later</p>
      </div>

      {savedJobs.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No saved jobs yet.</p>
          <button
            onClick={() => navigate("/candidate/jobs")}
            className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            Browse jobs
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {savedJobs.map((job) => (
            <div key={job.id} className="rounded-lg border bg-white p-4">
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
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => navigate(`/candidate/jobs/${job.id}`)}
                    className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                  >
                    Apply
                  </button>
                  <button
                    onClick={() => handleUnsave(job.id)}
                    className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Unsave
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
