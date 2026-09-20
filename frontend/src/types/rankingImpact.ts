/** Phase 4 — Ranking Impact Analysis types */

export type CandidateMovementCategory =
  | "significantly_improved"
  | "improved"
  | "unchanged"
  | "declined"
  | "significantly_declined";

export type ShortlistChange = "entered" | "left" | "retained" | "unchanged";

export type QualificationChange =
  | "newly_qualified"
  | "newly_disqualified"
  | "remained_qualified"
  | "remained_unqualified";

// ─── Candidate-Level Impact ────────────────────────────────────────

export interface CandidateImpactDetail {
  candidate_id: string;
  candidate_name: string;
  baseline_score: number;
  simulation_score: number;
  score_change: number;
  baseline_rank: number;
  simulation_rank: number;
  rank_change: number;
  baseline_status: string;
  simulation_status: string;
  baseline_shortlisted: boolean;
  simulation_shortlisted: boolean;
  movement_category: CandidateMovementCategory;
  shortlist_change: ShortlistChange;
  qualification_change: QualificationChange;
  reason: string | null;
}

// ─── Overview ──────────────────────────────────────────────────────

export interface RankingOverview {
  total_candidates: number;
  average_score_change: number;
  median_score_change: number;
  average_rank_change: number;
  median_rank_change: number;
  candidates_moved_up: number;
  candidates_moved_down: number;
  candidates_unchanged: number;
  percentage_moved_up: number;
  percentage_moved_down: number;
  percentage_unchanged: number;
  largest_upward_movement: number;
  largest_downward_movement: number;
}

// ─── Score Movement ────────────────────────────────────────────────

export interface ScoreMovement {
  average_change: number;
  median_change: number;
  minimum_change: number;
  maximum_change: number;
  positive_change_count: number;
  negative_change_count: number;
  unchanged_count: number;
  positive_change_percentage: number;
  negative_change_percentage: number;
  unchanged_percentage: number;
}

// ─── Rank Movement ─────────────────────────────────────────────────

export interface RankMovement {
  average_change: number;
  median_change: number;
  largest_upward_movement: number;
  largest_downward_movement: number;
  candidates_moving_up: number;
  candidates_moving_down: number;
  candidates_unchanged: number;
  percentage_moving_up: number;
  percentage_moving_down: number;
  percentage_unchanged: number;
}

// ─── Top Movers ────────────────────────────────────────────────────

export interface TopMover {
  candidate_id: string;
  candidate_name: string;
  baseline_rank: number;
  simulation_rank: number;
  rank_change: number;
  baseline_score: number;
  simulation_score: number;
  score_change: number;
  baseline_status: string;
  simulation_status: string;
  shortlisted_change: string;
  movement_category: CandidateMovementCategory;
}

// ─── Shortlist Impact ──────────────────────────────────────────────

export interface ShortlistImpact {
  baseline_size: number;
  simulation_size: number;
  candidates_entering: number;
  candidates_leaving: number;
  candidates_retained: number;
  overlap_count: number;
  jaccard_similarity: number;
  retention_rate: number;
  turnover_rate: number;
  expansion_count: number;
  expansion_description: string;
}

// ─── Qualification Matrix ──────────────────────────────────────────

export interface QualificationMatrix {
  baseline_qualified_simulation_qualified: number;
  baseline_qualified_simulation_not_qualified: number;
  baseline_not_qualified_simulation_qualified: number;
  baseline_not_qualified_simulation_not_qualified: number;
  newly_qualified: number;
  newly_disqualified: number;
  remained_qualified: number;
  remained_unqualified: number;
  total_qualified_change: number;
}

// ─── Rank Distribution ─────────────────────────────────────────────

export interface RankBucket {
  label: string;
  lower_bound: number;
  upper_bound: number | null;
  baseline_count: number;
  simulation_count: number;
  change: number;
}

export interface RankDistribution {
  buckets: RankBucket[];
}

// ─── Score Distribution ────────────────────────────────────────────

export interface ScoreBucket {
  label: string;
  lower_bound: number;
  upper_bound: number;
  baseline_count: number;
  simulation_count: number;
  change: number;
}

export interface ScoreDistribution {
  buckets: ScoreBucket[];
}

// ─── Threshold Impact ──────────────────────────────────────────────

export interface ThresholdImpact {
  baseline_threshold: number;
  simulation_threshold: number;
  baseline_qualified_count: number;
  simulation_qualified_count: number;
  qualified_change: number;
  description: string;
}

// ─── Stability & Correlation ───────────────────────────────────────

export interface RankStability {
  rank_stability: number;
  rank_correlation: number | null;
  rank_correlation_method: string | null;
  meaningful_movement_count: number;
  meaningful_movement_percentage: number;
}

// ─── Insight Cards ─────────────────────────────────────────────────

export interface InsightCard {
  type: "movement" | "shortlist" | "qualification" | "distribution" | "stability";
  message: string;
  metric_value: number | null;
  metric_unit: string | null;
}

// ─── Movement Category Summary ─────────────────────────────────────

export interface MovementCategorySummary {
  category: CandidateMovementCategory;
  count: number;
  percentage: number;
}

// ─── Main Response ─────────────────────────────────────────────────

export interface RankingImpactResponse {
  simulation_id: string;
  execution_id: string;
  execution_status: string;
  scenario_name: string;
  job_title: string;
  company: string;
  engine_version: string;
  completed_at: string | null;
  overview: RankingOverview;
  score_movement: ScoreMovement;
  rank_movement: RankMovement;
  shortlist_impact: ShortlistImpact;
  qualification_matrix: QualificationMatrix;
  rank_distribution: RankDistribution;
  score_distribution: ScoreDistribution;
  threshold_impact: ThresholdImpact;
  rank_stability: RankStability;
  top_upward_movers: TopMover[];
  top_downward_movers: TopMover[];
  movement_categories: MovementCategorySummary[];
  insights: InsightCard[];
}

// ─── Paginated Candidate Impact ────────────────────────────────────

export interface CandidateImpactListResponse {
  simulation_id: string;
  execution_id: string;
  total: number;
  page: number;
  page_size: number;
  items: CandidateImpactDetail[];
}

// ─── Single Candidate Impact ───────────────────────────────────────

export interface CandidateSingleImpactResponse {
  simulation_id: string;
  execution_id: string;
  candidate: CandidateImpactDetail;
  baseline: Record<string, unknown>;
  simulation: Record<string, unknown>;
  changes: Record<string, unknown>;
  explanation: string;
}

// ─── Filter Types ──────────────────────────────────────────────────

export type ImpactMovementFilter =
  | "significantly_improved"
  | "improved"
  | "unchanged"
  | "declined"
  | "significantly_declined";

export type ImpactShortlistFilter = "entered" | "left" | "retained" | "unchanged";

export type ImpactQualificationFilter =
  | "newly_qualified"
  | "newly_disqualified"
  | "remained_qualified"
  | "remained_unqualified";

// ─── Helpers ───────────────────────────────────────────────────────

export const MOVEMENT_CATEGORY_LABELS: Record<CandidateMovementCategory, string> = {
  significantly_improved: "Significantly Improved",
  improved: "Improved",
  unchanged: "Unchanged",
  declined: "Declined",
  significantly_declined: "Significantly Declined",
};

export const SHORTLIST_CHANGE_LABELS: Record<ShortlistChange, string> = {
  entered: "Entered Shortlist",
  left: "Left Shortlist",
  retained: "Retained",
  unchanged: "Unchanged",
};

export const QUALIFICATION_CHANGE_LABELS: Record<QualificationChange, string> = {
  newly_qualified: "Newly Qualified",
  newly_disqualified: "Newly Disqualified",
  remained_qualified: "Remained Qualified",
  remained_unqualified: "Remained Unqualified",
};

export function formatImpactDelta(value: number): string {
  return value > 0 ? `+${value}` : `${value}`;
}

export function formatImpactPercentage(value: number): string {
  return `${value.toFixed(1)}%`;
}
