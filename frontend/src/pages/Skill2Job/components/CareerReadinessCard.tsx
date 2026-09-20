import { Target } from "lucide-react";
import type { Skill2JobOverview } from "../../../types/skill2job";

export default function CareerReadinessCard({
  overview,
}: {
  overview: Skill2JobOverview;
}) {
  const score = overview.readiness.score;
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6">
      <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
        <Target className="h-5 w-5 text-primary-600" />
        Career Readiness
      </h2>
      <div className="flex flex-col sm:flex-row items-center gap-6">
        <div className="relative flex-shrink-0">
          <svg width="130" height="130" viewBox="0 0 120 120">
            <circle
              cx="60"
              cy="60"
              r="54"
              fill="none"
              stroke="#e5e7eb"
              strokeWidth="8"
            />
            <circle
              cx="60"
              cy="60"
              r="54"
              fill="none"
              stroke={
                score >= 70 ? "#22c55e" : score >= 40 ? "#f59e0b" : "#ef4444"
              }
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              transform="rotate(-90 60 60)"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold text-gray-900">{score}%</span>
            <span className="text-xs text-gray-500">Job Readiness</span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 flex-1 w-full">
          <div className="text-center p-3 rounded-xl bg-gray-50">
            <div className="text-2xl font-bold text-gray-900">
              {overview.skills.total}
            </div>
            <div className="text-xs text-gray-500">Skills Identified</div>
          </div>
          <div className="text-center p-3 rounded-xl bg-gray-50">
            <div className="text-2xl font-bold text-red-600">
              {overview.skill_gaps.critical}
            </div>
            <div className="text-xs text-gray-500">Critical Gaps</div>
          </div>
          <div className="text-center p-3 rounded-xl bg-gray-50">
            <div className="text-2xl font-bold text-primary-600">
              {overview.jobs.relevant_count}
            </div>
            <div className="text-xs text-gray-500">Relevant Jobs</div>
          </div>
          <div className="text-center p-3 rounded-xl bg-gray-50">
            <div className="text-2xl font-bold text-gray-900">
              {overview.skill_gaps.total}
            </div>
            <div className="text-xs text-gray-500">Skills to Learn</div>
          </div>
        </div>
      </div>
    </div>
  );
}
