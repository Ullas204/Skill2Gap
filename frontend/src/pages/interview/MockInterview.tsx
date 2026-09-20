import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { MockInterviewConsole } from "../../components/interview/MockInterviewConsole";
import { interviewApi } from "../../api/interview";
import { candidateJobApi } from "../../api/jobs";
import type { InterviewQuestion, InterviewEvaluation, InterviewCompleteResponse } from "../../types/interview";
import type { JobSearchResult } from "../../types/jobs";

export function MockInterview() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get("jobId");

  const [phase, setPhase] = useState<"select" | "interview" | "complete">("select");
  const [questions, setQuestions] = useState<InterviewQuestion[]>([]);
  const [interviewId, setInterviewId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<InterviewCompleteResponse | null>(null);
  const [jobs, setJobs] = useState<JobSearchResult | null>(null);
  const [selectedJobId, setSelectedJobId] = useState("");

  useEffect(() => {
    if (!jobId) {
      candidateJobApi
        .searchJobs({ page_size: 20 })
        .then(setJobs)
        .catch(() => setJobs(null));
    }
  }, [jobId]);

  useEffect(() => {
    if (jobId) {
      startInterview(jobId);
    }
  }, [jobId]);

  const startInterview = async (jid: string) => {
    setLoading(true);
    setError("");
    try {
      const response = await interviewApi.startMockInterview(jid);
      setInterviewId(response.interview_id);
      setQuestions([response.first_question]);
      setPhase("interview");
    } catch {
      setError("Failed to start mock interview. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async (
    questionId: string,
    answer: string,
    timeSeconds: number,
  ): Promise<InterviewEvaluation> => {
    const response = await interviewApi.submitAnswer(questionId, answer, timeSeconds);
    if (response.next_question) {
      setQuestions((prev) => [...prev, response.next_question!]);
    }
    return response.evaluation;
  };

  const handleComplete = async () => {
    setLoading(true);
    try {
      const response = await interviewApi.completeMockInterview(interviewId);
      setResult(response);
      setPhase("complete");
    } catch {
      setError("Failed to complete interview.");
    } finally {
      setLoading(false);
    }
  };

  if (loading && phase === "select") {
    return <LoadingSpinner size="lg" className="mt-20" />;
  }

  if (phase === "complete" && result) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <svg className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900">Interview Complete!</h2>
          <p className="mt-2 text-gray-500">{result.feedback_summary}</p>
          <div className="mt-6 inline-flex items-baseline gap-2">
            <span className="text-4xl font-bold text-primary-600">{result.overall_score}</span>
            <span className="text-sm text-gray-500">/ 100</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-xl border border-green-200 bg-green-50 p-4">
            <h3 className="text-sm font-semibold text-green-800">Strong Areas</h3>
            <ul className="mt-2 space-y-1">
              {(result.strong_areas).map((area, i) => (
                <li key={i} className="text-sm text-green-700 capitalize">{area.replace(/_/g, " ")}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <h3 className="text-sm font-semibold text-amber-800">Areas to Improve</h3>
            <ul className="mt-2 space-y-1">
              {(result.weak_areas).map((area, i) => (
                <li key={i} className="text-sm text-amber-700 capitalize">{area.replace(/_/g, " ")}</li>
              ))}
            </ul>
          </div>
        </div>

        {result.improvement_suggestions && result.improvement_suggestions.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h3 className="font-semibold text-gray-900">Improvement Suggestions</h3>
            <ul className="mt-2 space-y-2">
              {result.improvement_suggestions.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary-500" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex justify-center gap-3">
          <button
            onClick={() => navigate("/candidate/interview-history")}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            View History
          </button>
          <button
            onClick={() => { setPhase("select"); setResult(null); }}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Start Another
          </button>
        </div>
      </div>
    );
  }

  if (phase === "interview") {
    return (
      <div className="mx-auto max-w-3xl">
        <MockInterviewConsole
          questions={questions}
          onSubmitAnswer={handleSubmitAnswer}
          onComplete={handleComplete}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mock Interview</h1>
        <p className="mt-1 text-sm text-gray-500">
          Practice with AI-generated interview questions and receive instant feedback
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>
      )}

      <div className="rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary-100">
          <svg className="h-8 w-8 text-primary-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold text-gray-900">Start a Mock Interview</h2>
        <p className="mt-2 text-sm text-gray-500">
          Select a job to practice interview questions tailored to that role.
        </p>
        {jobs && jobs.items.length > 0 ? (
          <div className="mx-auto mt-6 flex max-w-md items-center gap-2">
            <select
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(e.target.value)}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Select a job...</option>
              {jobs.items.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title} — {j.company}
                </option>
              ))}
            </select>
            <button
              onClick={() => selectedJobId && startInterview(selectedJobId)}
              disabled={!selectedJobId}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              Start
            </button>
          </div>
        ) : (
          <p className="mt-4 text-sm text-gray-400">
            Select a job from the Job Portal and click "Mock Interview" to begin,
            or pass a jobId as a URL parameter.
          </p>
        )}
      </div>
    </div>
  );
}
