import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { interviewApi } from "../../api/interview";
import { STATUS_COLORS } from "../../types/interview";
import type { InterviewListItem } from "../../types/interview";

export function InterviewHistory() {
  const navigate = useNavigate();
  const [interviews, setInterviews] = useState<InterviewListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const result = await interviewApi.listInterviews();
        setInterviews(result.items);
      } catch {
        setError("Failed to load interview history");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Interview History</h1>
        <p className="mt-1 text-sm text-gray-500">View all your past and upcoming interviews</p>
      </div>

      {interviews.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <p className="text-gray-500">No interviews yet. Start a mock interview to begin!</p>
          <button
            onClick={() => navigate("/candidate/mock-interview")}
            className="mt-4 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Start Mock Interview
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {interviews.map((iv) => (
            <div
              key={iv.id}
              onClick={() => navigate(`/candidate/interviews/${iv.id}`)}
              className="cursor-pointer rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">{iv.job_title || "Interview"}</h3>
                  <p className="text-sm text-gray-500">
                    {iv.interview_type === "mock" ? "Mock Interview" : "Scheduled Interview"}
                    {" · "}
                    {iv.questions_answered}/{iv.total_questions} questions answered
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {iv.overall_score !== null && (
                    <span className="text-lg font-bold text-primary-600">{iv.overall_score}</span>
                  )}
                  <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[iv.status] || "bg-gray-100 text-gray-500"}`}>
                    {iv.status.replace("_", " ")}
                  </span>
                </div>
              </div>
              <p className="mt-1 text-xs text-gray-400">
                {new Date(iv.created_at).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
