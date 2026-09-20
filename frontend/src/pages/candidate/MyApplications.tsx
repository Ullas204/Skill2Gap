import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { candidateJobApi } from "../../api/jobs";
import type { JobApplication } from "../../types/jobs";

export function MyApplications() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await candidateJobApi.getMyApplications();
        setApplications(data);
      } catch {
        addToast("Failed to load applications", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [addToast]);

  async function handleWithdraw(id: string) {
    if (!window.confirm("Withdraw this application?")) return;
    try {
      await candidateJobApi.withdrawApplication(id);
      setApplications(applications.map((a) => (a.id === id ? { ...a, status: "withdrawn" } : a)));
      addToast("Application withdrawn", "success");
    } catch {
      addToast("Failed to withdraw application", "error");
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  const statusColors: Record<string, string> = {
    applied: "bg-blue-100 text-blue-800",
    under_review: "bg-yellow-100 text-yellow-800",
    shortlisted: "bg-purple-100 text-purple-800",
    interview_scheduled: "bg-indigo-100 text-indigo-800",
    offered: "bg-green-100 text-green-800",
    hired: "bg-green-100 text-green-800",
    rejected: "bg-red-100 text-red-800",
    withdrawn: "bg-gray-100 text-gray-800",
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">My Applications</h1>
        <p className="mt-1 text-sm text-gray-500">Track your job applications</p>
      </div>

      {applications.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No applications yet.</p>
          <button
            onClick={() => navigate("/candidate/jobs")}
            className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            Browse jobs
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {applications.map((app) => (
            <div key={app.id} className="rounded-lg border bg-white p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{app.job_title || "Unknown Position"}</h3>
                  <p className="text-sm text-gray-500">{app.company}{app.location ? ` · ${app.location}` : ""}</p>
                  <p className="mt-1 text-xs text-gray-400">Applied: {new Date(app.created_at).toLocaleDateString()}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusColors[app.status] || "bg-gray-100 text-gray-800"}`}>
                    {app.status.replace(/_/g, " ")}
                  </span>
                  {app.status === "applied" || app.status === "under_review" ? (
                    <button onClick={() => handleWithdraw(app.id)} className="text-xs text-red-600 hover:text-red-700">
                      Withdraw
                    </button>
                  ) : null}
                </div>
              </div>
              {app.cover_letter && (
                <p className="mt-2 text-sm text-gray-600 line-clamp-2">{app.cover_letter}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
