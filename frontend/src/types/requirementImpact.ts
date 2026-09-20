/** Phase 5 — What-If Requirement Impact Analysis types */

export type RequirementType = "skill" | "experience" | "education";

export type RequirementChangeType = "added" | "removed" | "promoted" | "demoted" | "modified";

export type SatisfactionStatus = "SATISFIED" | "MISSING" | "NOT_APPLICABLE";

export type ImpactCategory =
  | "NO_CANDIDATE_IMPACT"
  | "LOW_CANDIDATE_IMPACT"
  | "MODERATE_CANDIDATE_IMPACT"
  | "HIGH_CANDIDATE_IMPACT";

export type QualificationChange =
  | "newly_qualified"
  | "newly_disqualified"
  | "remained_qualified"
  | "remained_unqualified";

export type ShortlistChange = "entered" | "left" | "retained" | "never_shortlisted";

// ─── Changed Requirement Status ───────────────────────────────────

export interface ChangedRequirementStatus {
  requirement_type: RequirementType;
  requirement_name: string;
  baseline_satisfied: boolean;
  simulation_satisfied: boolean;
  baseline_status: SatisfactionStatus;
  simulation_status: SatisfactionStatus;
}

// ─── Requirement Change Detail ────────────────────────────────────

export interface RequirementChangeDetail {
  requirement_type: RequirementType;
  requirement_name: string;
  change_type: RequirementChangeType;
  baseline_value: string;
  simulation_value: string;
  affected_candidates: number;
  newly_disqualified: number;
  newly_qualified: number;
  avg_score_impact: number;
  impact_category: ImpactCategory;
}

// ─── Summary ──────────────────────────────────────────────────────

export interface RequirementChangeSummary {
  total_requirements_changed: number;
  skills_added: number;
  skills_removed: number;
  skills_promoted: number;
  skills_demoted: number;
  experience_changed: boolean;
  education_changed: boolean;
}

export interface RequirementImpactSummary {
  candidates_affected: number;
  candidates_newly_qualified: number;
  candidates_newly_disqualified: number;
  candidates_score_changed: number;
  candidates_rank_changed: number;
  candidates_shortlist_changed: number;
}

// ─── Candidate Impact ─────────────────────────────────────────────

export interface CandidateRequirementImpactDetail {
  candidate_id: string;
  candidate_name: string;
  baseline_score: number;
  simulation_score: number;
  score_change: number;
  baseline_rank: number;
  simulation_rank: number;
  rank_change: number;
  baseline_qualified: boolean;
  simulation_qualified: boolean;
  qualification_change: QualificationChange;
  shortlist_change: ShortlistChange;
  affected_requirements: ChangedRequirementStatus[];
  explanation: string;
}

// ─── Main Response ────────────────────────────────────────────────

export interface RequirementImpactResponse {
  simulation_id: string;
  execution_id: string;
  execution_status: string;
  scenario_name: string;
  job_title: string;
  company: string;
  completed_at: string | null;
  change_summary: RequirementChangeSummary;
  impact_summary: RequirementImpactSummary;
  requirement_changes: RequirementChangeDetail[];
}

// ─── Paginated Lists ──────────────────────────────────────────────

export interface RequirementImpactListResponse {
  simulation_id: string;
  execution_id: string;
  total: number;
  page: number;
  page_size: number;
  items: RequirementChangeDetail[];
}

export interface CandidateRequirementImpactListResponse {
  simulation_id: string;
  execution_id: string;
  total: number;
  page: number;
  page_size: number;
  items: CandidateRequirementImpactDetail[];
}

export interface CandidateRequirementImpactDetailResponse {
  simulation_id: string;
  execution_id: string;
  candidate: CandidateRequirementImpactDetail;
  baseline: Record<string, unknown>;
  simulation: Record<string, unknown>;
  changes: Record<string, unknown>;
  explanation: string;
}

// ─── Display Helpers ──────────────────────────────────────────────

export const CHANGE_TYPE_LABELS: Record<RequirementChangeType, string> = {
  added: "Added",
  removed: "Removed",
  promoted: "Promoted",
  demoted: "Demoted",
  modified: "Modified",
};

export const CHANGE_TYPE_COLORS: Record<RequirementChangeType, string> = {
  added: "bg-green-100 text-green-700",
  removed: "bg-red-100 text-red-700",
  promoted: "bg-blue-100 text-blue-700",
  demoted: "bg-amber-100 text-amber-700",
  modified: "bg-purple-100 text-purple-700",
};

export const IMPACT_CATEGORY_LABELS: Record<ImpactCategory, string> = {
  NO_CANDIDATE_IMPACT: "No Impact",
  LOW_CANDIDATE_IMPACT: "Low Impact",
  MODERATE_CANDIDATE_IMPACT: "Moderate Impact",
  HIGH_CANDIDATE_IMPACT: "High Impact",
};

export const IMPACT_CATEGORY_COLORS: Record<ImpactCategory, string> = {
  NO_CANDIDATE_IMPACT: "bg-gray-100 text-gray-600",
  LOW_CANDIDATE_IMPACT: "bg-blue-100 text-blue-600",
  MODERATE_CANDIDATE_IMPACT: "bg-amber-100 text-amber-600",
  HIGH_CANDIDATE_IMPACT: "bg-red-100 text-red-600",
};

export const QUALIFICATION_CHANGE_LABELS: Record<QualificationChange, string> = {
  newly_qualified: "Newly Qualified",
  newly_disqualified: "Newly Disqualified",
  remained_qualified: "Remained Qualified",
  remained_unqualified: "Remained Unqualified",
};

export const SHORTLIST_CHANGE_LABELS: Record<ShortlistChange, string> = {
  entered: "Entered Shortlist",
  left: "Left Shortlist",
  retained: "Retained in Shortlist",
  never_shortlisted: "Never Shortlisted",
};

export function formatRequirementChange(change: RequirementChangeDetail): string {
  return `${change.baseline_value} → ${change.simulation_value}`;
}

export function formatSatisfactionStatus(status: SatisfactionStatus): string {
  switch (status) {
    case "SATISFIED":
      return "Satisfied";
    case "MISSING":
      return "Missing";
    case "NOT_APPLICABLE":
      return "N/A";
  }
}
