import { Sparkles, Eye } from "lucide-react";
import type { Skill2JobOverview } from "../../../types/skill2job";

export default function CareerInsightCard({ overview }: { overview: Skill2JobOverview }) {
  const insight = overview.career_insight;
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6">
      <h2 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-primary-600" />AI Career Insight
      </h2>
      <p className="text-sm text-gray-700 leading-relaxed mb-3">{insight.text}</p>
      {insight.evidence.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {insight.evidence.map((e, i) => (
            <span key={i} className="inline-flex items-center gap-1 rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700 border border-primary-200">
              <Eye className="h-3 w-3" />{e}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
