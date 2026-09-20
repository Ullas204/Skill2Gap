import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { assessmentApi } from "../../api/assessment";
import type { AssessmentResponse } from "../../types/assessment";

export function AssessmentLibrary() {
  const navigate = useNavigate();
  const [items, setItems] = useState<AssessmentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    assessmentApi
      .list()
      .then((res) => setItems(res.items))
      .catch(() => setError("Failed to load assessments"))
      .finally(() => setLoading(false));
  }, []);

  function copyTakeLink(id: string) {
    void navigator.clipboard.writeText(`${window.location.origin}/candidate/assessments/take/${id}`);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Assessment Library</h1>
          <p className="mt-1 text-sm text-gray-500">
            AI-generated technical and aptitude assessments
          </p>
        </div>
        <Link
          to="/recruiter/assessments/builder"
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          + New Assessment
        </Link>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <p className="text-gray-500">No assessments yet. Build your first one!</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {["Assessment", "Mode", "Duration", "Questions", "Attempts", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{a.title}</p>
                    <p className="text-xs text-gray-500">
                      pass ≥ {a.passing_score}%{a.negative_marking > 0 ? ` · -${a.negative_marking} wrong` : ""}
                      {a.adaptive ? " · adaptive" : ""}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-sm capitalize text-gray-600">{a.mode}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{a.duration_minutes} min</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{a.question_count}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{a.attempt_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => copyTakeLink(a.id)}
                        className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100"
                      >
                        {copiedId === a.id ? "Copied!" : "Copy take link"}
                      </button>
                      <button
                        onClick={() => navigate(`/recruiter/assessments/${a.id}/analytics`)}
                        className="rounded-lg bg-primary-50 px-3 py-1.5 text-xs font-medium text-primary-700 hover:bg-primary-100"
                      >
                        Analytics
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
