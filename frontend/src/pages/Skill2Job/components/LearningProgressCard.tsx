import { BookOpen, CheckCircle2 } from "lucide-react";
import type { Skill2JobOverview } from "../../../types/skill2job";

export default function LearningProgressCard({ overview }: { overview: Skill2JobOverview }) {
  const progress = overview.learning_progress;
  const total = progress.total_modules;
  const completed = progress.completed;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6">
      <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
        <BookOpen className="h-5 w-5 text-primary-600" />Learning Progress
      </h2>
      {total === 0 ? (
        <div className="text-center py-4">
          <BookOpen className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">You haven&apos;t started your learning plan yet.</p>
          <p className="text-xs text-gray-400 mt-1">Select a target job to generate your learning path.</p>
        </div>
      ) : (
        <>
          <div className="mb-4">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600">Overall Progress</span>
              <span className="font-semibold text-gray-900">{pct}%</span>
            </div>
            <div className="w-full h-3 bg-gray-100 rounded-full">
              <div className="h-full bg-primary-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
            </div>
            <div className="text-xs text-gray-400 mt-1">{completed}/{total} modules completed</div>
          </div>
          <div className="space-y-2">
            {progress.items.slice(0, 4).map((item) => (
              <div key={item.module_key} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="flex items-center gap-2">
                  {item.status === "completed" ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : (
                    <div className="h-4 w-4 rounded-full border-2 border-gray-300" />
                  )}
                  <span className="text-sm text-gray-700">{item.title || item.skill}</span>
                </div>
                <span className="text-xs text-gray-400">{item.provider}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
