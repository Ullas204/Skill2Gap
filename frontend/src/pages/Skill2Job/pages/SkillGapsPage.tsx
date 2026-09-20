import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { skill2jobApi } from "../../../api/skill2job";
import type { SkillDemand } from "../../../types/skill2job";
import { GapsSection } from "../sections/GapsSection";

const LEVEL_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-blue-100 text-blue-700",
};

export function SkillDemandPanel() {
  const [demand, setDemand] = useState<SkillDemand | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    skill2jobApi
      .getSkillDemand()
      .then(setDemand)
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <p className="text-sm text-gray-500">Skill demand is unavailable right now.</p>
      </section>
    );
  }

  const items = (demand?.items ?? []).slice(0, 25);

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-6">
      <h3 className="flex items-center gap-2 text-lg font-bold text-gray-900">
        <BarChart3 className="h-5 w-5 text-primary-600" aria-hidden="true" />
        Skill Demand
      </h3>
      <p className="mt-1 text-sm text-gray-500">
        Which skills the {demand?.total_jobs ?? "local"} curated jobs ask for most — derived
        directly from the dataset ({demand?.dataset ?? "skill2job curated"}).
      </p>
      <ul className="mt-4 divide-y divide-gray-100">
        {items.map((item) => (
          <li key={item.skill} className="py-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-gray-900">{item.skill}</p>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">
                  {item.required_count} required · {item.preferred_count} preferred
                </span>
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${LEVEL_COLORS[item.demand_level] ?? "bg-gray-100 text-gray-600"}`}>
                  {item.demand_level}
                </span>
              </div>
            </div>
            {item.count > 0 && (
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-100">
                <div
                  className="h-full rounded-full bg-primary-600"
                  style={{ width: `${Math.min((item.count / (demand?.items[0]?.count ?? 1)) * 100, 100)}%` }}
                />
              </div>
            )}
            {item.jobs_demanding.length > 0 && (
              <p className="mt-1 text-[11px] text-gray-400">
                {item.jobs_demanding.slice(0, 3).join(" · ")}
                {item.jobs_demanding.length > 3 ? ` · +${item.jobs_demanding.length - 3}` : ""}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function SkillGapsPage() {
  return (
    <div className="space-y-6">
      <GapsSection />
      <SkillDemandPanel />
    </div>
  );
}