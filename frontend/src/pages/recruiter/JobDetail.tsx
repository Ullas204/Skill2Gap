import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { recruiterJobApi } from "../../api/jobs";
import type { Job, JobApplication } from "../../types/jobs";

export function RecruiterJobDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [job, setJob] = useState<Job | null>(null);
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    async function load() {
      try {
        const [jobData, appData] = await Promise.all([
          recruiterJobApi.getJob(id!),
          recruiterJobApi.getApplications(id!),
        ]);
        setJob(jobData);
        setApplications(appData);
      } catch {
        addToast("Failed to load job details", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, addToast]);

  async function handleStatusChange(status: string) {
    if (!id) return;
    try {
      const updated = await recruiterJobApi.changeStatus(id, status);
      setJob(updated);
      addToast(`Job status updated to ${status.replace(/_/g, " ")}`, "success");
    } catch {
      addToast("Failed to update job status", "error");
    }
  }

  async function handleDelete() {
    if (!id || !window.confirm("Delete this job posting?")) return;
    try {
      await recruiterJobApi.deleteJob(id);
      addToast("Job deleted", "success");
      navigate("/recruiter/jobs");
    } catch {
      addToast("Failed to delete job", "error");
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;
  if (!job) return <div className="mt-10 text-center text-gray-500">Job not found</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => navigate("/recruiter/jobs")} className="mb-2 text-sm text-primary-600 hover:text-primary-700">
            &larr; Back to Jobs
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{job.title}</h1>
          <p className="text-sm text-gray-500">{job.company} · {job.location} · {job.employment_type.replace(/_/g, " ")}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${
            job.status === "published" ? "bg-green-100 text-green-800" :
            job.status === "draft" ? "bg-yellow-100 text-yellow-800" :
            "bg-gray-100 text-gray-800"
          }`}>
            {job.status}
          </span>
          <button onClick={() => navigate(`/recruiter/jobs/${id}/edit`)} className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            Edit
          </button>
          <button onClick={handleDelete} className="rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50">
            Delete
          </button>
        </div>
      </div>

      {job.status === "draft" && (
        <div className="rounded-lg bg-yellow-50 p-4">
          <p className="text-sm text-yellow-800">This job is in draft mode. <button onClick={() => handleStatusChange("published")} className="font-medium underline">Publish now</button></p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-lg border bg-white p-6">
            <h2 className="mb-3 text-lg font-semibold text-gray-900">Description</h2>
            <p className="whitespace-pre-wrap text-sm text-gray-700">{job.description}</p>
          </div>

          {job.benefits && (
            <div className="rounded-lg border bg-white p-6">
              <h2 className="mb-3 text-lg font-semibold text-gray-900">Benefits</h2>
              <p className="whitespace-pre-wrap text-sm text-gray-700">{job.benefits}</p>
            </div>
          )}

          <div className="rounded-lg border bg-white p-6">
            <h2 className="mb-3 text-lg font-semibold text-gray-900">Applicants ({applications.length})</h2>
            {applications.length === 0 ? (
              <p className="text-sm text-gray-500">No applications yet.</p>
            ) : (
              <div className="space-y-3">
                {applications.map((app) => (
                  <div key={app.id} className="rounded-lg border p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{app.candidate_name}</p>
                        <p className="text-xs text-gray-500">{app.candidate_email}</p>
                      </div>
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                        app.status === "applied" ? "bg-blue-100 text-blue-800" :
                        app.status === "shortlisted" ? "bg-purple-100 text-purple-800" :
                        app.status === "rejected" ? "bg-red-100 text-red-800" :
                        app.status === "hired" ? "bg-green-100 text-green-800" :
                        "bg-gray-100 text-gray-800"
                      }`}>
                        {app.status.replace(/_/g, " ")}
                      </span>
                    </div>
                    {app.cover_letter && (
                      <p className="mt-2 text-xs text-gray-600 line-clamp-2">{app.cover_letter}</p>
                    )}
                    <button
                      onClick={() => navigate(`/recruiter/jobs/${id}/applicants?application=${app.id}`)}
                      className="mt-2 text-xs font-medium text-primary-600 hover:text-primary-700"
                    >
                      View Details
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border bg-white p-4">
            <h3 className="mb-3 text-sm font-semibold text-gray-900">Job Details</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Department</dt>
                <dd className="font-medium text-gray-900">{job.department || "-"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Experience</dt>
                <dd className="font-medium text-gray-900">{job.experience_required || "-"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Education</dt>
                <dd className="font-medium text-gray-900">{job.education_required || "-"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Salary</dt>
                <dd className="font-medium text-gray-900">
                  {job.salary_min && job.salary_max ? `${job.salary_currency} ${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()}` : "Not specified"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Deadline</dt>
                <dd className="font-medium text-gray-900">{job.application_deadline || "None"}</dd>
              </div>
            </dl>
          </div>

          <div className="rounded-lg border bg-white p-4">
            <h3 className="mb-3 text-sm font-semibold text-gray-900">Required Skills</h3>
            <div className="flex flex-wrap gap-2">
              {job.required_skills.map((s) => (
                <span key={s} className="rounded-full bg-primary-100 px-2 py-1 text-xs font-medium text-primary-800">{s}</span>
              ))}
              {job.required_skills.length === 0 && <span className="text-xs text-gray-400">None</span>}
            </div>
          </div>

          {job.preferred_skills && job.preferred_skills.length > 0 && (
            <div className="rounded-lg border bg-white p-4">
              <h3 className="mb-3 text-sm font-semibold text-gray-900">Preferred Skills</h3>
              <div className="flex flex-wrap gap-2">
                {job.preferred_skills.map((s) => (
                  <span key={s} className="rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-800">{s}</span>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-900">Actions</h3>
            {job.status === "published" && (
              <button onClick={() => handleStatusChange("closed")} className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                Close Job
              </button>
            )}
            {job.status === "closed" && (
              <button onClick={() => handleStatusChange("published")} className="w-full rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700">
                Reopen Job
              </button>
            )}
            {job.status !== "archived" && (
              <button onClick={() => handleStatusChange("archived")} className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                Archive
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
