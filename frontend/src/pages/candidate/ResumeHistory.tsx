import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { candidateApi } from "../../api/candidate";
import type { ResumeVersion } from "../../types/candidate";

const STATUS_COLORS: Record<string, string> = {
  uploaded: "bg-yellow-100 text-yellow-800",
  processing: "bg-blue-100 text-blue-800",
  parsed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ResumeHistory() {
  const navigate = useNavigate();
  const [versions, setVersions] = useState<ResumeVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await candidateApi.getResumeVersions();
        setVersions(data);
      } catch {
        setError("Failed to load resume history");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Resume History</h1>
          <p className="mt-1 text-sm text-gray-500">
            View all versions of your uploaded resumes
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>
      )}

      {versions.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No resumes uploaded yet.</p>
          <button
            onClick={() => navigate("/candidate/resume/upload")}
            className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            Upload your first resume
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {versions.map((v) => {
            const statusColor = STATUS_COLORS[v.status] || "bg-gray-100 text-gray-800";
            return (
              <div
                key={v.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-sm"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-50 text-sm font-bold text-primary-700">
                    v{v.version}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-gray-900">
                      {v.original_filename}
                      {v.is_primary && (
                        <span className="ml-2 inline-flex items-center rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-700">
                          Primary
                        </span>
                      )}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                      <span>{formatFileSize(v.file_size)}</span>
                      <span className="text-gray-300">|</span>
                      <span>{v.file_type.toUpperCase()}</span>
                      <span className="text-gray-300">|</span>
                      <span>{new Date(v.created_at).toLocaleDateString()}</span>
                      <span className="text-gray-300">|</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor}`}>
                        {v.status}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => navigate(`/candidate/resume/${v.id}`)}
                  className="rounded px-3 py-1.5 text-xs font-medium text-primary-600 hover:bg-primary-50"
                >
                  View
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
