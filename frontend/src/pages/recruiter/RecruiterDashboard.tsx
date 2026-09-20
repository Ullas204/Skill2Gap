import { useEffect, useState } from "react";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { useAuth } from "../../hooks/useAuth";
import { dashboardApi } from "../../api/dashboard";
import type { RecruiterDashboardData } from "../../api/dashboard";
import {
  DashboardHeader,
  StatCard,
  PipelineCard,
  UserListCard,
  ActivityCard,
  QuickActions,
} from "../../components/dashboard";

const SvgIcons = {
  jobs: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0" />
    </svg>
  ),
  applications: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
    </svg>
  ),
  screened: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
    </svg>
  ),
  active: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
    </svg>
  ),
};

export function RecruiterDashboard() {
  const { user } = useAuth();
  const { addToast } = useToast();
  const [data, setData] = useState<RecruiterDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi
      .getRecruiter()
      .then(setData)
      .catch(() => addToast("Failed to load dashboard", "error"))
      .finally(() => setLoading(false));
  }, [addToast]);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;
  if (!data) return <div className="mt-10 text-center text-gray-500">Failed to load dashboard</div>;

  const topCandidates = data.top_candidates.map((c) => ({
    id: String((c as Record<string, unknown>).candidate_id ?? ""),
    name: `Candidate #${String((c as Record<string, unknown>).candidate_id ?? "").slice(0, 8)}`,
    score: (c as Record<string, unknown>).overall_score as number,
  }));

  const recentApps = data.recent_applications.slice(0, 5).map((a) => ({
    id: String((a as Record<string, unknown>).id ?? ""),
    title: `Application #${String((a as Record<string, unknown>).id ?? "").slice(0, 8)}`,
    description: `Job #${String((a as Record<string, unknown>).job_id ?? "").slice(0, 8)}`,
    type: "info" as const,
    badge: {
      label: ((a as Record<string, unknown>).status as string)?.replace(/_/g, " ") ?? "unknown",
      color: "bg-blue-100 text-blue-700",
    },
  }));

  return (
    <div className="space-y-6">
      <DashboardHeader
        title="Recruiter Dashboard"
        subtitle={`Welcome back, ${user?.full_name ?? "Recruiter"}`}
        actions={
          <>
            <a href="/recruiter/jobs/create" className="px-4 py-2 rounded-lg bg-primary-600 text-sm font-medium text-white hover:bg-primary-700 transition-colors">
              Post New Job
            </a>
            <a href="/recruiter/jobs" className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
              View All Jobs
            </a>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Jobs" value={data.total_jobs} color="primary" icon={SvgIcons.jobs} />
        <StatCard title="Active Jobs" value={data.active_jobs} color="green" icon={SvgIcons.active} />
        <StatCard title="Applications" value={data.total_applications} color="blue" icon={SvgIcons.applications} />
        <StatCard title="Screened" value={data.candidates_screened} color="purple" icon={SvgIcons.screened} />
      </div>

      <PipelineCard
        title="Interview Pipeline"
        stages={data.interview_pipeline}
        action={{ label: "View all", href: "/recruiter/rankings" }}
        color="blue"
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <UserListCard
          title="Top Candidates"
          users={topCandidates}
          emptyMessage="No screened candidates yet. Run AI screening to see top candidates."
        />

        <ActivityCard
          title="Recent Applications"
          items={recentApps}
          emptyMessage="No applications yet."
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <QuickActions
          title="Quick Actions"
          actions={[
            { label: "Post a new job", href: "/recruiter/jobs/create" },
            { label: "View all jobs", href: "/recruiter/jobs" },
            { label: "Candidate rankings", href: "/recruiter/rankings" },
          ]}
        />
      </div>
    </div>
  );
}
