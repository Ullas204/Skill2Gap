import { AlertTriangle, BarChart3 } from "lucide-react";
import type { Skill2JobOverview, OverviewGapItem } from "../../../types/skill2job";
import { priorityColor } from "./helpers";

function GapRow({ gap }: { gap: OverviewGapItem }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-50 last:border-0">
      <div className="flex items-center gap-3">
        <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0" />
        <div>
          <span className="font-semibold text-gray-900">{gap.skill}</span>
          <p className="text-xs text-gray-500">Required by {gap.count} relevant job{gap.count !== 1 ? "s" : ""}</p>
        </div>
      </div>
      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${priorityColor(gap.priority)}`}>
        {gap.priority}
      </span>
    </div>
  );
}

export default function SkillGapIntelligence({ overview }: { overview: Skill2JobOverview }) {
  const gaps = overview.skill_gaps.items;
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary-600" />Your Skill Gaps
        </h2>
        <span className="text-sm text-gray-500">{overview.skill_gaps.total} gaps identified</span>
      </div>
      {gaps.length === 0 ? (
        <div className="rounded-2xl border border-gray-200 bg-white p-6 text-center">
          <BarChart3 className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-gray-500">No significant skill gaps detected.</p>
        </div>
      ) : (
        <div className="rounded-2xl border border-gray-200 bg-white p-5">
          {gaps.slice(0, 8).map((g) => <GapRow key={g.skill} gap={g} />)}
        </div>
      )}
    </div>
  );
}
