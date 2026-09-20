import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ResumeCard } from "../../components/candidate/ResumeCard";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { candidateApi } from "../../api/candidate";
import type { Resume, CandidateIntelligence as Intel } from "../../types/candidate";

export function ResumeDashboard() {
  const navigate = useNavigate();
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [intel, setIntel] = useState<Intel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    try {
      const [resumeData, intelData] = await Promise.allSettled([
        candidateApi.listResumes(),
        candidateApi.getIntelligence(),
      ]);
      if (resumeData.status === "fulfilled") setResumes(resumeData.value);
      if (intelData.status === "fulfilled") setIntel(intelData.value);
    } catch {
      setError("Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSetPrimary(id: string) {
    try {
      await candidateApi.setPrimaryResume(id);
      await load();
    } catch {
      setError("Failed to set primary resume");
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this resume?")) return;
    try {
      await candidateApi.deleteResume(id);
      await load();
    } catch {
      setError("Failed to delete resume");
    }
  }

  function handleView(id: string) {
    navigate(`/candidate/resume/${id}`);
  }

  const parsed = resumes.filter((r) => r.status === "parsed");
  const processing = resumes.filter((r) => r.status === "processing" || r.status === "uploaded");
  const failed = resumes.filter((r) => r.status === "failed");

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Resumes</h1>
          <p className="mt-1 text-sm text-gray-500">
            Upload, manage, and analyze your resumes
          </p>
        </div>
        <button
          onClick={() => navigate("/candidate/resume/upload")}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Upload New Resume
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>
      )}

      {intel && (
        <div className="rounded-lg border border-primary-200 bg-primary-50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-primary-900">Candidate Intelligence</h2>
              <p className="mt-1 text-xs text-primary-700">
                {intel.total_experience_years > 0 && `${intel.total_experience_years} yrs experience`}
                {intel.highest_qualification && ` · ${intel.highest_qualification}`}
                {intel.project_count > 0 && ` · ${intel.project_count} projects`}
                {intel.certification_count > 0 && ` · ${intel.certification_count} certifications`}
              </p>
            </div>
            <div className="text-right">
              <span className="text-2xl font-bold text-primary-700">{intel.profile_strength}%</span>
              <p className="text-xs text-primary-600">Profile Strength</p>
            </div>
          </div>
          <button
            onClick={() => navigate("/candidate/intelligence")}
            className="mt-3 text-xs font-medium text-primary-700 hover:text-primary-800"
          >
            View full intelligence report &rarr;
          </button>
        </div>
      )}

      {resumes.length === 0 && !loading && (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No resumes uploaded yet.</p>
          <button
            onClick={() => navigate("/candidate/resume/upload")}
            className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            Upload your first resume
          </button>
        </div>
      )}

      {parsed.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Parsed Resumes</h2>
          <div className="space-y-3">
            {parsed.map((r) => (
              <ResumeCard
                key={r.id}
                resume={r}
                onView={handleView}
                onDelete={handleDelete}
                onSetPrimary={handleSetPrimary}
              />
            ))}
          </div>
        </div>
      )}

      {processing.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Processing</h2>
          <div className="space-y-3">
            {processing.map((r) => (
              <ResumeCard key={r.id} resume={r} />
            ))}
          </div>
        </div>
      )}

      {failed.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Failed</h2>
          <div className="space-y-3">
            {failed.map((r) => (
              <ResumeCard key={r.id} resume={r} onDelete={handleDelete} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
