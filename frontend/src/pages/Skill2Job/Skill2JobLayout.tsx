import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  Bot,
  Briefcase,
  Clock,
  GitBranch,
  GraduationCap,
  LayoutDashboard,
  ListChecks,
  Rocket,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { skill2jobApi } from "../../api/skill2job";
import type { Skill2JobOverview } from "../../types/skill2job";
import { useAuth } from "../../hooks/useAuth";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/skill2job", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/skill2job/profile", label: "My Profile", icon: UserRound },
  { to: "/skill2job/jobs", label: "Local Jobs", icon: Briefcase },
  { to: "/skill2job/skill-gaps", label: "Skill Gaps", icon: ListChecks },
  { to: "/skill2job/skill-graph", label: "Skill Graph", icon: GitBranch },
  { to: "/skill2job/opportunities", label: "Opportunities", icon: Rocket },
  { to: "/skill2job/learning", label: "Learning Path", icon: GraduationCap },
  { to: "/skill2job/time-to-ready", label: "Time to Ready", icon: Clock },
  { to: "/skill2job/skill-proof", label: "Skill Proof", icon: ShieldCheck },
  { to: "/skill2job/agent", label: "AI Career Agent", icon: Bot },
];

const READINESS_STYLES: Record<string, { label: string; cls: string }> = {
  excellent: { label: "Excellent", cls: "bg-green-100 text-green-700" },
  strong: { label: "Strong", cls: "bg-emerald-100 text-emerald-700" },
  competitive: { label: "Competitive", cls: "bg-blue-100 text-blue-700" },
  developing: { label: "Developing", cls: "bg-amber-100 text-amber-700" },
  needs_work: { label: "Needs Work", cls: "bg-orange-100 text-orange-700" },
  locked: { label: "Locked", cls: "bg-gray-100 text-gray-600" },
};

function readinessStyleFor(score: number): { label: string; cls: string } {
  if (score >= 85) return READINESS_STYLES.excellent!;
  if (score >= 70) return READINESS_STYLES.strong!;
  if (score >= 55) return READINESS_STYLES.competitive!;
  if (score >= 40) return READINESS_STYLES.developing!;
  if (score > 0) return READINESS_STYLES.needs_work!;
  return READINESS_STYLES.locked!;
}

export default function Skill2JobLayout() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<Skill2JobOverview | null>(null);

  useEffect(() => {
    skill2jobApi
      .getOverview()
      .then(setOverview)
      .catch(() => undefined);
  }, []);

  const readiness = overview?.readiness;
  const readinessStyle = readiness ? readinessStyleFor(readiness.score) : null;

  return (
    <div className="space-y-6">
      {/* ─── Header ─────────────────────────────────────────────── */}
      <div className="relative overflow-hidden rounded-3xl border border-primary-100 bg-gradient-to-br from-primary-700 via-primary-600 to-indigo-600 p-6 text-white sm:p-8">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_85%_0%,rgba(255,255,255,0.18),transparent)]"
          aria-hidden="true"
        />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-primary-100">
              Skill2Job · Candidate Career Intelligence
            </p>
            <h1 className="mt-1 text-2xl font-extrabold tracking-tight sm:text-3xl">
              {user?.full_name ? `${user.full_name.split(" ")[0]}'s Career Hub` : "Career Hub"}
            </h1>
            <p className="mt-1 max-w-xl text-sm text-primary-100">
              Perceive your skills, discover matched roles, close gaps, and follow a grounded plan to your next opportunity.
            </p>
          </div>
          {readinessStyle && (
            <div className="rounded-2xl border border-white/20 bg-white/10 px-5 py-4 text-right backdrop-blur">
              <p className="text-xs font-semibold uppercase tracking-wide text-primary-100">Career Readiness</p>
              <p className={`mt-1 inline-flex items-center rounded-full px-3 py-1 text-sm font-bold ${readinessStyle.cls}`}>
                {readinessStyle.label} · {Math.round(readiness!.score)}%
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ─── Body ───────────────────────────────────────────────── */}
      <div className="flex flex-col gap-6 lg:flex-row">
        {/* Nav */}
        <nav
          aria-label="Career Intelligence"
          className="shrink-0 lg:w-60"
        >
          <div className="flex flex-row gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition-colors ${
                    isActive
                      ? "bg-primary-600 text-white shadow-sm"
                      : "border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 lg:border-transparent lg:bg-transparent"
                  }`
                }
              >
                <item.icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <Outlet />
        </div>
      </div>
    </div>
  );
}