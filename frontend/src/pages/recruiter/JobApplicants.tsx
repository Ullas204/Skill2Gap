import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { recruiterJobApi } from "../../api/jobs";
import type { Job, JobApplication } from "../../types/jobs";

export function RecruiterJobApplicants() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const { addToast } = useToast();
  const [job, setJob] = useState<Job | null>(null);
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApp, setSelectedApp] = useState<JobApplication | null>(null);
  const [noteText, setNoteText] = useState("");

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
        const appId = searchParams.get("application");
        if (appId) {
          const found = appData.find((a) => a.id === appId);
          if (found) setSelectedApp(found);
        }
      } catch {
        addToast("Failed to load applicants", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, searchParams, addToast]);

  async function handleStatusChange(appId: string, status: string) {
    try {
      await recruiterJobApi.updateApplicationStatus(appId, status);
      setApplications(applications.map((a) => (a.id === appId ? { ...a, status } : a)));
      if (selectedApp?.id === appId) setSelectedApp({ ...selectedApp, status });
      addToast(`Status updated to ${status.replace(/_/g, " ")}`, "success");
    } catch {
      addToast("Failed to update status", "error");
    }
  }

  async function handleAddNote(appId: string) {
    if (!noteText.trim()) return;
    try {
      const note = await recruiterJobApi.addNote(appId, noteText);
      setSelectedApp((prev) =>
        prev?.id === appId
          ? { ...prev, recruiter_notes: [...(prev.recruiter_notes || []), note] }
          : prev
      );
      setNoteText("");
      addToast("Note added", "success");
    } catch {
      addToast("Failed to add note", "error");
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;
  if (!job) return <div className="mt-10 text-center text-gray-500">Job not found</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Applicants for {job.title}</h1>
        <p className="text-sm text-gray-500">{applications.length} total applicants</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <div className="rounded-lg border bg-white">
            <div className="border-b px-4 py-3">
              <h2 className="font-semibold text-gray-900">Applicants</h2>
            </div>
            <div className="divide-y">
              {applications.map((app) => (
                <button
                  key={app.id}
                  onClick={() => setSelectedApp(app)}
                  className={`w-full px-4 py-3 text-left hover:bg-gray-50 ${selectedApp?.id === app.id ? "bg-primary-50" : ""}`}
                >
                  <p className="text-sm font-medium text-gray-900">{app.candidate_name}</p>
                  <p className="text-xs text-gray-500">{app.candidate_email}</p>
                  <span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                    app.status === "applied" ? "bg-blue-100 text-blue-800" :
                    app.status === "shortlisted" ? "bg-purple-100 text-purple-800" :
                    app.status === "under_review" ? "bg-yellow-100 text-yellow-800" :
                    app.status === "rejected" ? "bg-red-100 text-red-800" :
                    app.status === "hired" ? "bg-green-100 text-green-800" :
                    app.status === "offered" ? "bg-indigo-100 text-indigo-800" :
                    "bg-gray-100 text-gray-800"
                  }`}>
                    {app.status.replace(/_/g, " ")}
                  </span>
                </button>
              ))}
              {applications.length === 0 && (
                <p className="p-4 text-sm text-gray-500">No applicants yet</p>
              )}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2">
          {selectedApp ? (
            <div className="space-y-4">
              <div className="rounded-lg border bg-white p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">{selectedApp.candidate_name}</h2>
                    <p className="text-sm text-gray-500">{selectedApp.candidate_email}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Link
                      to={`/recruiter/jobs/${id}/candidates/${selectedApp.candidate_id}/fit`}
                      className="rounded-lg border border-primary-600 px-3 py-1.5 text-sm font-medium text-primary-600 hover:bg-primary-50"
                    >
                      View Job Fit
                    </Link>
                    <select
                      value={selectedApp.status}
                      onChange={(e) => handleStatusChange(selectedApp.id, e.target.value)}
                      className="rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="applied">Applied</option>
                      <option value="under_review">Under Review</option>
                      <option value="shortlisted">Shortlisted</option>
                      <option value="interview_scheduled">Interview Scheduled</option>
                      <option value="offered">Offered</option>
                      <option value="hired">Hired</option>
                      <option value="rejected">Rejected</option>
                    </select>
                  </div>
                </div>

                {selectedApp.cover_letter && (
                  <div className="mt-4">
                    <h3 className="text-sm font-semibold text-gray-900">Cover Letter</h3>
                    <p className="mt-1 whitespace-pre-wrap text-sm text-gray-700">{selectedApp.cover_letter}</p>
                  </div>
                )}
              </div>

              <div className="rounded-lg border bg-white p-6">
                <h3 className="mb-3 text-sm font-semibold text-gray-900">Recruiter Notes</h3>
                <div className="mb-4 space-y-2">
                  {(selectedApp.recruiter_notes || []).length === 0 && (
                    <p className="text-sm text-gray-400">No notes yet</p>
                  )}
                  {(selectedApp.recruiter_notes || []).map((note) => (
                    <div key={note.id} className="rounded-lg bg-gray-50 p-3 text-sm">
                      <p className="text-gray-700">{note.note}</p>
                      <p className="mt-1 text-xs text-gray-400">{new Date(note.created_at).toLocaleString()}</p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <textarea
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Add a note..."
                    rows={2}
                    className="block flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  <button
                    onClick={() => handleAddNote(selectedApp.id)}
                    disabled={!noteText.trim()}
                    className="self-end rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                  >
                    Add Note
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
              <p className="text-gray-500">Select an applicant to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
