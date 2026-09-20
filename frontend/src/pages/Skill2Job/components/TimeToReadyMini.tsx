import { Clock, DollarSign } from "lucide-react";
import type { Skill2JobOverview } from "../../../types/skill2job";

export default function TimeToReadyMini({ overview }: { overview: Skill2JobOverview }) {
  const items = overview.time_to_ready?.items ?? [];

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
          <Clock className="h-5 w-5 text-primary-600" />Time to Ready
        </h2>
        <p className="text-sm text-gray-500">Select a target job to see your preparation timeline.</p>
      </div>
    );
  }

  const top = items[0];

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6">
      <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
        <Clock className="h-5 w-5 text-primary-600" />Time to Ready
      </h2>
      <div className="mb-4 p-3 rounded-xl bg-gray-50">
        <div className="text-xs text-gray-500">Target Job</div>
        <div className="font-semibold text-gray-900">{top.job_title}</div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-xl bg-gray-50 flex items-center gap-3">
          <Clock className="h-5 w-5 text-primary-500" />
          <div>
            <div className="text-xs text-gray-500">Estimated Time</div>
            <div className="font-bold text-gray-900">{top.estimated_weeks} weeks</div>
          </div>
        </div>
        <div className="p-3 rounded-xl bg-gray-50 flex items-center gap-3">
          <DollarSign className="h-5 w-5 text-green-500" />
          <div>
            <div className="text-xs text-gray-500">Estimated Cost</div>
            <div className="font-bold text-gray-900">
              {top.currency ?? "USD"} {top.estimated_cost}
            </div>
          </div>
        </div>
      </div>
      <div className="mt-4">
        <div className="text-xs font-semibold text-gray-500 mb-2">
          Skills to Learn · {top.missing_skills_count} gap(s)
        </div>
        <div className="space-y-2">
          {items.slice(0, 3).map((item) => (
            <div key={item.job_id} className="flex items-center justify-between text-sm">
              <span className="text-gray-700">{item.job_title}</span>
              <span className="text-gray-400">{item.estimated_weeks} weeks</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}