import { Brain, Briefcase, Loader2 } from "lucide-react";
import type { Skill2JobOverview } from "../../../types/skill2job";

export default function CareerHero({
  overview,
  onAnalyze,
  analyzing,
}: {
  overview: Skill2JobOverview | null;
  onAnalyze: () => void;
  analyzing: boolean;
}) {
  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="rounded-2xl bg-gradient-to-br from-primary-600 to-primary-800 p-8 text-white">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="space-y-3">
          <h1 className="text-2xl md:text-3xl font-bold">{greeting}</h1>
          <p className="text-lg text-primary-100 max-w-xl">
            Turn your skills into your next opportunity.
          </p>
          <p className="text-sm text-primary-200 max-w-lg">
            Skill2Job analyzes your profile, discovers relevant local jobs,
            identifies the skills you're missing, and creates a measurable path
            toward job readiness.
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <button
              onClick={onAnalyze}
              disabled={analyzing}
              className="inline-flex items-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-primary-700 hover:bg-primary-50 disabled:opacity-50 transition"
            >
              {analyzing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Brain className="h-4 w-4" />
              )}
              {analyzing ? "Analyzing..." : "Analyze My Profile"}
            </button>
            <button
              onClick={() =>
                document
                  .getElementById("local-opportunities")
                  ?.scrollIntoView({ behavior: "smooth" })
              }
              className="inline-flex items-center gap-2 rounded-lg border border-white/30 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/10 transition"
            >
              <Briefcase className="h-4 w-4" />
              Explore Local Jobs
            </button>
          </div>
        </div>
        <div className="flex flex-col gap-3 md:text-right">
          <div className="rounded-xl bg-white/10 px-5 py-3">
            <div className="text-xs text-primary-200">Profile completeness</div>
            <div className="text-2xl font-bold">
              {overview?.profile.completeness ?? 0}%
            </div>
          </div>
          {overview?.last_analyzed && (
            <div className="rounded-xl bg-white/10 px-5 py-3">
              <div className="text-xs text-primary-200">Last analyzed</div>
              <div className="text-sm font-semibold">
                {new Date(overview.last_analyzed).toLocaleDateString("en-IN", {
                  hour: "2-digit",
                  minute: "2-digit",
                  day: "numeric",
                  month: "short",
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
