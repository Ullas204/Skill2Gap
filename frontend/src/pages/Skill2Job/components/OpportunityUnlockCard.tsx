import { Unlock, Zap } from "lucide-react";
import type { Skill2JobOverview } from "../../../types/skill2job";

export default function OpportunityUnlockCard({ overview }: { overview: Skill2JobOverview }) {
  const opp = overview.opportunity_unlock;
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6">
      <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
        <Unlock className="h-5 w-5 text-primary-600" />What Could You Unlock?
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="text-center p-4 rounded-xl bg-gray-50">
          <div className="text-xs text-gray-500 mb-1">Current Profile</div>
          <div className="text-2xl font-bold text-gray-900">{overview.jobs.relevant_count}</div>
          <div className="text-xs text-gray-500">relevant jobs</div>
        </div>
        <div className="text-center p-4 rounded-xl bg-primary-50">
          <div className="text-xs text-primary-600 mb-1 font-semibold">Potential</div>
          <div className="text-2xl font-bold text-primary-700">{opp.potential}</div>
          <div className="text-xs text-primary-600">more opportunities</div>
        </div>
        <div className="text-center p-4 rounded-xl bg-green-50">
          <div className="text-xs text-green-600 mb-1 font-semibold">Unlocked</div>
          <div className="text-2xl font-bold text-green-700">{opp.unlocked_count}</div>
          <div className="text-xs text-green-600">newly accessible</div>
        </div>
      </div>
      {opp.top_roles && opp.top_roles.length > 0 && (
        <div className="mt-4">
          <div className="text-xs font-semibold text-gray-500 mb-2">Top Roles You Could Unlock</div>
          <div className="flex flex-wrap gap-2">
            {opp.top_roles.slice(0, 3).map((r, i) => (
              <span key={i} className="inline-flex items-center gap-1 rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700 border border-primary-200">
                <Zap className="h-3 w-3" />{String(r.title || r.role || "Role")}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
