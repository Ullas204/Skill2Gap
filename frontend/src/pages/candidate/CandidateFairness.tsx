import { useState, useEffect } from "react";
import { getMyFairness } from "../../api/fairness";
import { FairnessScoreCard, FairnessProgressBar } from "../../components/fairness/FairnessComponents";
import type { CandidateFairness } from "../../types/fairness";

export function CandidateFairness() {
  const [data, setData] = useState<CandidateFairness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const result = await getMyFairness();
        setData(result);
      } catch {
        setError("Failed to load fairness data.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-800">{error || "No data available."}</p>
        </div>
      </div>
    );
  }

  const statusColor =
    data.fairness_status === "evaluated"
      ? "bg-green-100 text-green-800 border-green-200"
      : "bg-yellow-100 text-yellow-800 border-yellow-200";

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Fairness & Transparency</h1>
        <p className="text-sm text-gray-500 mt-1">
          View your fairness status and how AI evaluates candidates.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="flex justify-center">
          <FairnessScoreCard
            score={data.average_score || 0}
            label="Your Average Score"
          />
        </div>
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 uppercase">Status</p>
            <span className={`inline-flex items-center mt-1 px-3 py-1 rounded-full text-sm font-medium border ${statusColor}`}>
              {data.fairness_status === "evaluated" ? "Evaluated" : "Pending"}
            </span>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 uppercase">Total Evaluations</p>
            <p className="text-2xl font-bold text-gray-900">{data.total_evaluations}</p>
          </div>
        </div>
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 uppercase">Bias Checks</p>
            <p className="text-sm font-medium text-gray-900 mt-1">
              {data.bias_checks_completed ? "Completed" : "Not Yet Completed"}
            </p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 uppercase">Last Evaluation</p>
            <p className="text-sm text-gray-700 mt-1">
              {data.last_evaluation_date
                ? new Date(data.last_evaluation_date).toLocaleDateString()
                : "N/A"}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Evaluation Transparency</h2>
        <div className="space-y-3">
          {data.transparency_summary.map((item, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="mt-1 w-2 h-2 rounded-full bg-green-500 shrink-0" />
              <p className="text-sm text-gray-700">{item}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Protected Attributes</h2>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm text-green-800 font-medium">
            No protected attributes are used in AI evaluations.
          </p>
          <p className="text-sm text-green-700 mt-1">
            Your gender, age, ethnicity, religion, nationality, disability status,
            sexual orientation, and marital status are never used in scoring decisions.
            All evaluations are based purely on skills, experience, and qualifications.
          </p>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Rights</h2>
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <div className="mt-1 w-2 h-2 rounded-full bg-blue-500 shrink-0" />
            <div>
              <p className="text-sm font-medium text-gray-900">Appeal / Review Request</p>
              <p className="text-sm text-gray-600">
                You can request a human review of any AI-powered decision.
                Contact your recruiter or HR team to submit an appeal.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="mt-1 w-2 h-2 rounded-full bg-blue-500 shrink-0" />
            <div>
              <p className="text-sm font-medium text-gray-900">Data Transparency</p>
              <p className="text-sm text-gray-600">
                You can request a copy of the data used in your evaluation at any time.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="mt-1 w-2 h-2 rounded-full bg-blue-500 shrink-0" />
            <div>
              <p className="text-sm font-medium text-gray-900">Fair Evaluation</p>
              <p className="text-sm text-gray-600">
                All candidates are evaluated using the same criteria.
                Our fairness engine continuously monitors for bias.
              </p>
            </div>
          </div>
        </div>
      </div>

      {data.total_evaluations > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Score Overview</h2>
          <FairnessProgressBar value={data.average_score} label="Average Match Score" />
        </div>
      )}
    </div>
  );
}
