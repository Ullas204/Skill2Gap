import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { RefreshCw, AlertCircle } from "lucide-react";
import { skill2jobApi } from "../../api/skill2job";
import type { Skill2JobOverview } from "../../types/skill2job";
import CareerHero from "./components/CareerHero";
import CareerReadinessCard from "./components/CareerReadinessCard";
import LocalOpportunities from "./components/LocalOpportunities";
import SkillGapIntelligence from "./components/SkillGapIntelligence";
import OpportunityUnlockCard from "./components/OpportunityUnlockCard";
import TimeToReadyMini from "./components/TimeToReadyMini";
import LearningProgressCard from "./components/LearningProgressCard";
import CareerInsightCard from "./components/CareerInsightCard";
import NextActionCard from "./components/NextActionCard";
import { CardSkeleton, ReadinessSkeleton, JobCardSkeleton } from "./components/Skeletons";
import { extractErrorMessage } from "./components/helpers";

const TAB_ROUTES: Record<string, string> = {
  perception: "/skill2job/profile",
  jobs: "/skill2job/jobs",
  match: "/skill2job/jobs",
  gaps: "/skill2job/skill-gaps",
  learning: "/skill2job/learning",
  ttr: "/skill2job/time-to-ready",
};

export default function Skill2JobOverview({
  onNavigate,
}: {
  onNavigate?: (tab: string) => void;
}) {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<Skill2JobOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const go = useCallback(
    (tab: string) => {
      const route = TAB_ROUTES[tab];
      if (route) {
        navigate(route);
        return;
      }
      onNavigate?.(tab);
    },
    [navigate, onNavigate]
  );

  const fetchOverview = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await skill2jobApi.getOverview();
      setOverview(data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  const handleAnalyze = async () => {
    try {
      setAnalyzing(true);
      await skill2jobApi.buildDossier();
      await skill2jobApi.runMatching();
      await skill2jobApi.analyzeSkillGaps();
      await fetchOverview();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setAnalyzing(false);
    }
  };

  const handleViewGap = () => {
    go("gaps");
  };

  // ─── Loading State ───────────────────────────────────────────────
  if (loading && !overview) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl bg-gradient-to-br from-primary-600 to-primary-800 p-8">
          <div className="h-8 w-64 bg-white/20 rounded animate-pulse mb-3" />
          <div className="h-4 w-96 bg-white/10 rounded animate-pulse mb-2" />
          <div className="h-3 w-80 bg-white/10 rounded animate-pulse" />
        </div>
        <ReadinessSkeleton />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <JobCardSkeleton key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardSkeleton lines={4} />
          <CardSkeleton lines={4} />
        </div>
      </div>
    );
  }

  // ─── Error State ─────────────────────────────────────────────────
  if (error && !overview) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center">
        <AlertCircle className="h-10 w-10 text-red-400 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-red-700 mb-2">
          Unable to load Career Intelligence
        </h3>
        <p className="text-sm text-red-600 mb-4">{error}</p>
        <button
          onClick={fetchOverview}
          className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
        >
          <RefreshCw className="h-4 w-4" /> Retry
        </button>
      </div>
    );
  }

  // ─── Empty State (No Profile) ────────────────────────────────────
  if (overview && !overview.profile.connected) {
    return (
      <div className="space-y-6">
        <CareerHero overview={overview} onAnalyze={handleAnalyze} analyzing={analyzing} />
        <div className="rounded-2xl border-2 border-dashed border-gray-300 p-12 text-center">
          <div className="text-4xl mb-4">&#127891;</div>
          <h3 className="text-lg font-bold text-gray-900 mb-2">
            Your career intelligence starts here.
          </h3>
          <p className="text-gray-500 max-w-md mx-auto mb-4">
            Complete your profile to discover relevant jobs and personalized skill gaps.
          </p>
          <button
            onClick={() => go("perception")}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-700"
          >
            Complete Profile
          </button>
        </div>
      </div>
    );
  }

  if (!overview) return null;

  return (
    <div className="space-y-6">
      {/* Hero */}
      <CareerHero overview={overview} onAnalyze={handleAnalyze} analyzing={analyzing} />

      {/* Error banner (non-blocking) */}
      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-amber-500 flex-shrink-0" />
          <span className="text-sm text-amber-700">{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-amber-600 hover:text-amber-700">
            &times;
          </button>
        </div>
      )}

      {/* Career Readiness */}
      <CareerReadinessCard overview={overview} />

      {/* Local Opportunities */}
      <LocalOpportunities overview={overview} onViewGap={handleViewGap} />

      {/* Skill Gaps + Opportunity Unlock */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SkillGapIntelligence overview={overview} />
        <OpportunityUnlockCard overview={overview} />
      </div>

      {/* Time to Ready + Learning Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TimeToReadyMini overview={overview} />
        <LearningProgressCard overview={overview} />
      </div>

      {/* Career Insight + Next Action */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CareerInsightCard overview={overview} />
        <NextActionCard overview={overview} />
      </div>

      {/* Refresh */}
      <div className="flex justify-center pt-2">
        <button
          onClick={fetchOverview}
          disabled={loading}
          className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh Analysis
        </button>
      </div>
    </div>
  );
}
