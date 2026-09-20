import { useEffect, useState } from "react";

import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { useToast } from "../../contexts/ToastContext";
import { useAuth } from "../../hooks/useAuth";
import { dashboardApi } from "../../api/dashboard";
import type { AdminDashboardData } from "../../api/dashboard";
import {
  DashboardHeader,
  StatCard,
  DashboardCard,
  ActivityCard,
  QuickActions,
  InfoRow,
} from "../../components/dashboard";

const SvgIcons = {
  users: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
    </svg>
  ),
  active: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  candidates: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
    </svg>
  ),
  recruiters: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
    </svg>
  ),
  shield: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  ),
  system: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" />
    </svg>
  ),
};

export function AdminDashboard() {
  const { user } = useAuth();
  const { addToast } = useToast();
  const [data, setData] = useState<AdminDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi
      .getAdmin()
      .then(setData)
      .catch(() => addToast("Failed to load dashboard", "error"))
      .finally(() => setLoading(false));
  }, [addToast]);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;
  if (!data) return <div className="mt-10 text-center text-gray-500">Failed to load dashboard</div>;

  const loginActivity = data.recent_logins.slice(0, 5).map((l) => ({
    id: String(Math.random()),
    title: `Login attempt`,
    description: `User: ${(l as Record<string, unknown>).user_id as string}`.slice(0, 40),
    type: ((l as Record<string, unknown>).success ? "success" : "error") as "success" | "error",
    badge: {
      label: (l as Record<string, unknown>).success ? "Success" : "Failed",
      color: (l as Record<string, unknown>).success ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700",
    },
  }));

  return (
    <div className="space-y-6">
      <DashboardHeader
        title="Admin Dashboard"
        subtitle={`Welcome back, ${user?.full_name ?? "Administrator"}`}
        actions={
          <a href="/admin/users" className="px-4 py-2 rounded-lg bg-primary-600 text-sm font-medium text-white hover:bg-primary-700 transition-colors">
            Manage Users
          </a>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Users" value={data.total_users} color="primary" icon={SvgIcons.users} />
        <StatCard title="Active Users" value={data.active_users} color="green" icon={SvgIcons.active} />
        <StatCard title="Candidates" value={data.total_candidates} color="blue" icon={SvgIcons.candidates} />
        <StatCard title="Recruiters" value={data.total_recruiters} color="purple" icon={SvgIcons.recruiters} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard title="HR Managers" value={data.total_hr} color="indigo" icon={SvgIcons.users} />
        <StatCard title="Admins" value={data.total_admins} color="red" icon={SvgIcons.shield} />
        <StatCard title="System Status" value="Healthy" color="green" icon={SvgIcons.system} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ActivityCard
          title="Recent Logins"
          items={loginActivity}
          emptyMessage="No login activity recorded yet."
        />

        <DashboardCard title="System Overview">
          <InfoRow
            items={[
              { label: "Total Users", value: data.total_users },
              { label: "Active Users", value: data.active_users },
              { label: "Candidates", value: data.total_candidates },
              { label: "Recruiters", value: data.total_recruiters },
              { label: "HR Managers", value: data.total_hr },
              { label: "Admins", value: data.total_admins },
            ]}
          />
        </DashboardCard>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <QuickActions
          title="Quick Actions"
          actions={[
            { label: "Manage users", href: "/admin/users" },
            { label: "View audit logs", href: "/admin/audit-logs" },
          ]}
        />
      </div>
    </div>
  );
}
