import { useEffect, useState } from "react";
import { ArrowRight, GraduationCap } from "lucide-react";
import { skill2jobApi } from "../../../api/skill2job";
import type { TrainingModule, TrainingPlan, TrainingProgress } from "../../../types/skill2job";

export function LearningSection() {
  const [plan, setPlan] = useState<TrainingPlan | null>(null);
  const [progress, setProgress] = useState<TrainingProgress | null>(null);

  async function refresh() {
    try {
      const [p, pr] = await Promise.all([
        skill2jobApi.getTrainingPlan(),
        skill2jobApi.getTrainingProgress(),
      ]);
      setPlan(p);
      setProgress(pr);
    } catch {
      setPlan(null);
      setProgress(null);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function complete(m: TrainingModule) {
    await skill2jobApi.completeModule(m.module_key);
    await refresh();
  }

  const completedKeys = new Set(progress?.items.map((i) => i.module_key) ?? []);

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="max-w-2xl">
            <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
              <GraduationCap className="h-5 w-5 text-primary-600" aria-hidden="true" />
              Training Plan
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              A grounded learning plan built only from official provider resources that target your
              real skill gaps. Mark modules complete to track your progress.
            </p>
          </div>
        </div>
      </section>

      {plan && plan.modules.length > 0 && (
        <section className="rounded-2xl border border-gray-200 bg-white p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-gray-900">Learning Modules</h3>
            <span className="text-xs text-gray-400">{plan.version}</span>
          </div>
          <ul className="mt-4 divide-y divide-gray-100">
            {plan.modules.map((m) => {
              const done = completedKeys.has(m.module_key);
              return (
                <li key={m.module_key} className="flex items-center justify-between gap-4 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-gray-900">
                      {m.title}
                      {done && <span className="ml-2 inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">done</span>}
                    </p>
                    <p className="text-xs text-gray-500">
                      {m.skill} · {m.provider} · {m.resource_type}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {m.url && (
                      <a
                        href={m.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
                      >
                        Open resource <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                      </a>
                    )}
                    {!done && (
                      <button
                        type="button"
                        onClick={() => complete(m)}
                        className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-700"
                      >
                        Mark complete
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {plan && plan.modules.length === 0 && (
        <section className="rounded-2xl border-2 border-dashed border-gray-300 p-12 text-center">
          <p className="text-sm text-gray-500">No training plan yet — run the pipeline or matching to surface skill gaps.</p>
        </section>
      )}
    </div>
  );
}