import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { candidateApi } from "../../api/candidate";
import { useToast } from "../../contexts/ToastContext";
import type { SyncDiffResponse, SyncDiffItem } from "../../types/candidate";

export function ProfileSync() {
  const { id } = useParams<{ id: string }>();
  const { addToast } = useToast();
  const [syncData, setSyncData] = useState<SyncDiffResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [applying, setApplying] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const resumeId = id;
    async function load() {
      try {
        const data = await candidateApi.getSyncDiff(resumeId);
        setSyncData(data);
      } catch {
        setError("Failed to load sync data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  async function handleAccept(section: string, index: number, field?: string) {
    if (!id) return;
    setApplying(`${section}-${index}`);
    try {
      await candidateApi.acceptSync(id, section, index, field);
      addToast(`Accepted ${section} item`, "success");
      const data = await candidateApi.getSyncDiff(id);
      setSyncData(data);
    } catch {
      addToast("Failed to accept", "error");
    } finally {
      setApplying(null);
    }
  }

  async function handleReject(section: string, index: number, field?: string) {
    if (!id) return;
    setApplying(`${section}-${index}`);
    try {
      await candidateApi.rejectSync(id, section, index, field);
      addToast(`Rejected ${section} item`, "info");
    } catch {
      addToast("Failed to reject", "error");
    } finally {
      setApplying(null);
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>;

  const sections = [
    { key: "personal_info", label: "Personal Info", items: syncData?.personal_info || [] },
    { key: "education", label: "Education", items: syncData?.education || [] },
    { key: "experience", label: "Experience", items: syncData?.experience || [] },
    { key: "skills", label: "Skills", items: syncData?.skills || [] },
    { key: "projects", label: "Projects", items: syncData?.projects || [] },
    { key: "certifications", label: "Certifications", items: syncData?.certifications || [] },
    { key: "languages", label: "Languages", items: syncData?.languages || [] },
  ];

  const hasDiffs = sections.some((s) => s.items.length > 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profile Synchronization</h1>
        <p className="mt-1 text-sm text-gray-500">
          Compare parsed resume data with your profile and sync changes
        </p>
      </div>

      {!hasDiffs ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">
            No differences found. Your profile is already in sync with this resume.
          </p>
        </div>
      ) : (
        sections.map(
          (section) =>
            section.items.length > 0 && (
              <div key={section.key} className="rounded-lg border border-gray-200 bg-white p-6">
                <h2 className="mb-4 text-lg font-semibold text-gray-900">{section.label}</h2>
                <div className="space-y-3">
                  {section.items.map((item: SyncDiffItem, idx: number) => (
                    <div
                      key={`${section.key}-${idx}`}
                      className="flex items-center justify-between rounded-md border border-gray-100 bg-gray-50 p-3"
                    >
                      <div className="flex-1">
                        <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                          {item.field}
                        </p>
                        <div className="mt-1 grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-gray-400">Resume: </span>
                            <span className="font-medium text-green-700">
                              {item.parsed_value || "—"}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-400">Profile: </span>
                            <span className="font-medium text-blue-700">
                              {item.profile_value || "—"}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <button
                          onClick={() => handleAccept(section.key, idx, item.field)}
                          disabled={applying === `${section.key}-${idx}`}
                          className="rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
                        >
                          Accept
                        </button>
                        <button
                          onClick={() => handleReject(section.key, idx, item.field)}
                          disabled={applying === `${section.key}-${idx}`}
                          className="rounded bg-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-400 disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ),
        )
      )}
    </div>
  );
}
