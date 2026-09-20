import { useEffect, useState } from "react";

import { ActivityFeed } from "../../components/candidate/ActivityFeed";
import { ProfileCompletion } from "../../components/candidate/ProfileCompletion";
import { QuickActions } from "../../components/candidate/QuickActions";
import { StatCard } from "../../components/candidate/StatCard";
import { WelcomeCard } from "../../components/candidate/WelcomeCard";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { candidateApi } from "../../api/candidate";
import type { CandidateDashboard as DashboardData, ProfileCompletion as ProfileCompletionData } from "../../types/candidate";

export function CandidateDashboard() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [completion, setCompletion] = useState<ProfileCompletionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [dash, comp] = await Promise.all([
          candidateApi.getDashboard(),
          candidateApi.getProfileCompletion(),
        ]);
        setDashboard(dash);
        setCompletion(comp);
      } catch {
        setError("Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <LoadingSpinner size="lg" className="mt-20" />;

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600">{error}</div>
    );
  }

  if (!dashboard) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Candidate Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your profile and career information
        </p>
      </div>

      <WelcomeCard fullName={dashboard.full_name} profile={dashboard.profile} />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Resumes" value={dashboard.total_resumes} color="blue" />
        <StatCard label="Applications" value="0" color="green" />
        <StatCard label="Interviews" value="0" color="purple" />
        <StatCard label="Notifications" value={dashboard.unread_notifications} color="amber" />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <QuickActions />
        {completion && <ProfileCompletion data={completion} />}
      </div>

      <ActivityFeed activities={dashboard.recent_activity} />
    </div>
  );
}
