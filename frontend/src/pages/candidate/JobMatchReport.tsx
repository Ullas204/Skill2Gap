import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { MatchScoreCard } from "../../components/screening/MatchScoreCard";
import { SkillGapReport } from "../../components/screening/SkillGapReport";
import { useToast } from "../../contexts/ToastContext";
import { getMyMatch } from "../../api/screening";
import type { CandidateMatchReport } from "../../types/screening";

export function CandidateJobMatchReport() {
  const { id } = useParams<{ id: string }>();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState<CandidateMatchReport | null>(null);

  useEffect(() => {
    if (!id) return;
    async function load() {
      try {
        const data = await getMyMatch(id!);
        setReport(data);
      } catch {
        addToast("Failed to load match report", "error");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, addToast]);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  if (!report || !report.screening) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Match Report</h1>
          <p className="mt-1 text-sm text-gray-500">See how you match against this job</p>
        </div>
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No screening data available for this job yet. Apply and wait for the recruiter to run screening.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">My Match Report</h1>
        <p className="mt-1 text-sm text-gray-500">Detailed breakdown of your match for {report.job_title}</p>
      </div>

      <MatchScoreCard
        screening={report.screening}
        candidateName={report.candidate_name}
        jobTitle={report.job_title}
      />

      {report.skill_gap && <SkillGapReport skillGap={report.skill_gap} />}

      {report.improvement_suggestions && report.improvement_suggestions.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">General Improvement Suggestions</h3>
          <ul className="space-y-1.5">
            {report.improvement_suggestions.map((s, i) => (
              <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                <span className="text-green-500 mt-0.5">&#x2713;</span> {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
