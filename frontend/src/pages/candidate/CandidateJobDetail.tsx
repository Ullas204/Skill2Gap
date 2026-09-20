import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { candidateJobApi } from "../../api/jobs";
import { candidateApi } from "../../api/candidate";
import type { Job } from "../../types/jobs";

export function CandidateJobDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [job, setJob] = useState<Job | null>(null);
  const [resumes, setResumes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [showApply, setShowApply] = useState(false);
  const [resumeId, setResumeId] = useState("");
  const [coverLetter, setCoverLetter] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [hasApplied, setHasApplied] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    if (!id) return;
    async function load() {
      try {
        const [jobData, resumeData] = await Promise.all([
          candidateJobApi.getJob(id!),
          candidateApi.listResumes(),
        ]);
        setJob(jobData);
        setResumes(resumeData);
        const primary = resumeData.find((r) => r.is_primary);
        if (primary) setResumeId(primary.id);

        try {
          const myApps = await candidateJobApi.getMyApplications();
          setHasApplied(myApps.some((a) => a.job_id === id && a.status !== "withdrawn"));
        } catch { /* ignore */ }

        try {
          const saved = await candidateJobApi.getSavedJobs();
          setIsSaved(saved.some((j) => j.id === id));
        } catch { /* ignore */ }
      } catch {
        setError("Failed to load job details");
        addToast("Failed to load job details", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, addToast]);

  async function handleApply() {
    if (!id) return;
    setApplying(true);
    setError("");
    try {
      await candidateJobApi.apply(id, resumeId || undefined, coverLetter || undefined);
      setSuccess("Application submitted successfully!");
      setShowApply(false);
      setHasApplied(true);
      addToast("Application submitted!", "success");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to submit application";
      setError(msg);
      addToast(msg, "error");
    } finally {
      setApplying(false);
    }
  }

  async function handleSave() {
    if (!id) return;
    try {
      await candidateJobApi.saveJob(id);
      setSuccess("Job saved!");
      setIsSaved(true);
      addToast("Job saved", "success");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to save job";
      setError(msg);
      addToast(msg, "error");
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;
  if (!job) return <div className="mt-10 text-center text-gray-500">Job not found</div>;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <button onClick={() => navigate("/candidate/jobs")} className="text-sm text-primary-600 hover:text-primary-700">
        &larr; Back to Jobs
      </button>

      {error && <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>}
      {success && <div className="rounded-lg bg-green-50 p-4 text-sm text-green-600">{success}</div>}

      <div className="rounded-lg border bg-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{job.title}</h1>
            <p className="mt-1 text-lg text-gray-600">{job.company}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className="inline-flex rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800">
                {job.employment_type.replace(/_/g, " ")}
              </span>
              <span className="inline-flex rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-800">
                {job.location}
              </span>
              {job.salary_min && job.salary_max && (
                <span className="inline-flex rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-800">
                  {job.salary_currency} {job.salary_min.toLocaleString()} - {job.salary_max.toLocaleString()}
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigate(`/candidate/mock-interview?jobId=${id}`)}
              className="rounded-lg border border-primary-300 bg-white px-4 py-2 text-sm font-medium text-primary-700 hover:bg-primary-50"
            >
              Mock Interview
            </button>
            <button
              onClick={handleSave}
              disabled={isSaved}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
            >
              {isSaved ? "Saved" : "Save"}
            </button>
            {hasApplied ? (
              <span className="rounded-lg bg-green-100 px-4 py-2 text-sm font-medium text-green-800">
                Applied
              </span>
            ) : (
              <button onClick={() => setShowApply(true)} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
                Apply Now
              </button>
            )}
          </div>
        </div>

        {(job.experience_required || job.education_required || job.department) && (
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            {job.department && (
              <div>
                <p className="text-xs font-medium uppercase text-gray-500">Department</p>
                <p className="mt-1 text-sm text-gray-900">{job.department}</p>
              </div>
            )}
            {job.experience_required && (
              <div>
                <p className="text-xs font-medium uppercase text-gray-500">Experience</p>
                <p className="mt-1 text-sm text-gray-900">{job.experience_required}</p>
              </div>
            )}
            {job.education_required && (
              <div>
                <p className="text-xs font-medium uppercase text-gray-500">Education</p>
                <p className="mt-1 text-sm text-gray-900">{job.education_required}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {job.required_skills.length > 0 && (
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Required Skills</h2>
          <div className="flex flex-wrap gap-2">
            {job.required_skills.map((s) => (
              <span key={s} className="rounded-full bg-primary-100 px-3 py-1 text-sm font-medium text-primary-800">{s}</span>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-lg border bg-white p-6">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Job Description</h2>
        <p className="whitespace-pre-wrap text-sm text-gray-700">{job.description}</p>
      </div>

      {job.benefits && (
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Benefits</h2>
          <p className="whitespace-pre-wrap text-sm text-gray-700">{job.benefits}</p>
        </div>
      )}

      {job.application_deadline && (
        <div className="rounded-lg border bg-white p-4">
          <p className="text-sm text-gray-600">
            <span className="font-medium">Application Deadline:</span> {job.application_deadline}
          </p>
        </div>
      )}

      {showApply && (
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Apply for this Job</h2>
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Resume</label>
              <select
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={resumeId}
                onChange={(e) => setResumeId(e.target.value)}
              >
                <option value="">Select a resume</option>
                {resumes.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.original_filename} ({r.status})
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-700">Cover Letter (Optional)</label>
              <textarea
                rows={5}
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={coverLetter}
                onChange={(e) => setCoverLetter(e.target.value)}
                placeholder="Write a brief cover letter..."
              />
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowApply(false)} className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                Cancel
              </button>
              <button onClick={handleApply} disabled={applying} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">
                {applying ? "Submitting..." : "Submit Application"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
