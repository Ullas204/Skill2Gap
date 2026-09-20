import { ArrowRight, Zap } from "lucide-react";
import type { Skill2JobOverview } from "../../../types/skill2job";

export default function NextActionCard({ overview }: { overview: Skill2JobOverview }) {
  const action = overview.next_action;
  const priorityColors: Record<string, string> = {
    high: "border-l-red-500 bg-red-50",
    medium: "border-l-amber-500 bg-amber-50",
    low: "border-l-green-500 bg-green-50",
  };
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6">
      <h2 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
        <Zap className="h-5 w-5 text-primary-600" />Recommended Next Step
      </h2>
      <div className={`border-l-4 p-4 rounded-r-xl ${priorityColors[action.priority] || "border-l-gray-400 bg-gray-50"}`}>
        <div className="font-semibold text-gray-900">{action.action}</div>
        <p className="text-sm text-gray-600 mt-1">{action.description}</p>
        <div className="mt-3">
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-primary-600">
            Take Action <ArrowRight className="h-3 w-3" />
          </span>
        </div>
      </div>
    </div>
  );
}
