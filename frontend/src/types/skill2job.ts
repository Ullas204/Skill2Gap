import type { CandidateIntelligence, CandidateProfile } from "./candidate";

export interface Skill2JobHealth {
  module: string;
  status: string;
}

export interface CapabilityItem {
  key: string;
  label: string;
  status: "available" | "deferred";
  phase: number;
}

export interface Skill2JobCapabilities {
  module: string;
  profile_connected: boolean;
  capabilities: CapabilityItem[];
}

export interface Skill2JobProfile {
  connected: boolean;
  profile: CandidateProfile;
  intelligence: CandidateIntelligence | null;
}

export interface PerceptionRecord {
  id: string;
  input_type: string;
  original_filename: string | null;
  processing_status: string;
  processing_message: string | null;
  field_confidence: number | null;
  skills_count: number;
  experience_count: number;
  education_count: number;
  projects_count: number;
  certifications_count: number;
  languages_count: number;
  created_at: string;
}

export interface PerceptionProvenance {
  source: string;
  section: string | null;
  evidence: string | null;
  confidence: number;
  method: string | null;
}

export interface PerceptionSkill {
  name: string;
  canonical: string | null;
  category: string | null;
  inferred: boolean;
  provenance: PerceptionProvenance | null;
}

export interface PerceptionEducation {
  institution: string | null;
  degree: string | null;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
  raw_text: string | null;
  provenance: PerceptionProvenance | null;
}

export interface PerceptionExperience {
  company: string | null;
  job_title: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  duration_months: number | null;
  description: string[];
  technologies: string[];
  provenance: PerceptionProvenance | null;
}

export interface PerceptionProject {
  name: string | null;
  description: string[];
  technologies: string[];
  provenance: PerceptionProvenance | null;
}

export interface PerceptionCertification {
  name: string | null;
  issuer: string | null;
  date: string | null;
  provenance: PerceptionProvenance | null;
}

export interface PerceptionLanguage {
  language: string | null;
  proficiency: string | null;
  provenance: PerceptionProvenance | null;
}

export interface PerceptionQuality {
  text_quality: number;
  layout_quality: number;
  entity_quality: number;
  overall_confidence: number;
}

export interface PerceptionDocumentInfo {
  type: string | null;
  format: string | null;
  pages: number | null;
  is_scanned: boolean;
  ocr_used: boolean;
  extraction_method: string | null;
  tables_found: number;
}

export interface PerceptionError {
  code: string;
  message: string;
  stage: string | null;
  recoverable: boolean;
}

export interface PerceptionResultData {
  input_type: string;
  parser_version: string;
  source_metadata: Record<string, unknown>;
  extracted_text: string | null;
  summary: string | null;
  skills: PerceptionSkill[];
  education: PerceptionEducation[];
  experience: PerceptionExperience[];
  projects: PerceptionProject[];
  certifications: PerceptionCertification[];
  languages: PerceptionLanguage[];
  interests: string[];
  target_roles: string[];
  location: string | null;
  field_confidence: number;
  provenance: PerceptionProvenance[];
  warnings: string[];
  errors: PerceptionError[];
  processing_status: string;
  processing_message: string | null;
  document: PerceptionDocumentInfo | null;
  quality: PerceptionQuality | null;
}

export interface PerceptionDetail {
  id: string;
  input_type: string;
  original_filename: string | null;
  processing_status: string;
  processing_message: string | null;
  field_confidence: number | null;
  extracted_text: string | null;
  result: PerceptionResultData;
  warnings: string[];
  parser_version: string;
  created_at: string | null;
}

export interface PerceptionStatus {
  has_sense: boolean;
  pocket_sphinx_available: boolean;
  whisper_available: boolean;
  ocr_available: boolean;
  pdf_available: boolean;
  text_source: string;
}

export interface PerceptionListResponse {
  total: number;
  items: PerceptionRecord[];
}

export interface CuratedJob {
  id: string;
  title: string;
  company: string;
  location: string | null;
  remote_type: string | null;
  employment_type: string | null;
  experience_required: string | null;
  education_required: string | null;
  description: string;
  required_skills: string[];
  preferred_skills: string[];
  salary_range: string | null;
  salary_min: number | null;
  salary_max: number | null;
  source: string;
  source_url: string | null;
}

export interface CuratedJobPage {
  total: number;
  offset: number;
  limit: number;
  jobs: CuratedJob[];
}

export interface LocationCount {
  location: string;
  count: number;
}

export interface CuratedJobCounts {
  total: number;
  remote: number;
  on_site: number;
  top_locations: LocationCount[];
  dataset: string;
}

export interface MatchScores {
  skill: number;
  experience: number;
  education: number;
  project: number;
  certification: number;
  location: number;
  employment_type: number;
  semantic: number;
}

export interface JobMatchEntry {
  job_id: string;
  title: string;
  company: string;
  location: string | null;
  remote_type: string | null;
  overall_score: number;
  recommendation: string;
  strength_level: string;
  matched_skills: string[];
  missing_required: string[];
  suggested_skills: string[];
}

export interface SkillGapItem {
  skill: string;
  role: string;
  company: string;
  evidence: string;
  transferable: string[];
  related_existing: string[];
  gap_kind: "skill_gap" | "evidence_gap";
  evidence_note: string | null;
  priority: "high" | "medium" | "low";
}

export interface TeachingPlanStep {
  skill: string;
  jobs_demanding: string[];
  priority: string;
  rationale: string;
}

export interface SkillGapAnalysis {
  job_id: string;
  job_title: string;
  company: string;
  overall_score: number;
  missing_required_skills: string[];
  missing_preferred_skills: string[];
  gap_items: SkillGapItem[];
  experience_gap_description: string | null;
  education_gap_description: string | null;
  certification_gap_description: string | null;
  improvement_suggestions: string[];
  interview_readiness_score: number;
  analysis_version: string;
}

export interface SkillGapSummary {
  total_analyses: number;
  analyzed_jobs: number;
  gap_skills: Array<Record<string, unknown>>;
  teaching_plan: TeachingPlanStep[];
}

export interface SimulatedJob {
  job_id: string;
  title: string;
  company: string;
  location: string | null;
  overall_score: number;
  recommendation: string;
}

export interface SimulateRequest {
  dream_job_title?: string | null;
  own_assessment?: string | null;
  skills_to_add: string[];
  limit?: number;
}

export interface UpliftDetail {
  job_id: string;
  title: string;
  company: string;
  before: number;
  after: number;
  uplift: number;
  newly_matched_skills: string[];
  unlocked: boolean;
}

export interface SimulationResult {
  baseline: SimulatedJob[];
  simulated: SimulatedJob[];
  top_uplift: UpliftDetail[];
  unlocked_count: number;
  target_role: string | null;
  skills_added: string[];
  notes: string[];
  simulation_version: string;
}

export interface OpportunityDashboard {
  top_opportunity: Record<string, unknown> | null;
  potential: number;
  unlocked_count: number;
  top_roles: Array<Record<string, unknown>>;
}

export interface TrainingModule {
  module_key: string;
  skill: string;
  title: string;
  provider: string;
  url: string | null;
  resource_type: string;
}

export interface TrainingPlan {
  modules: TrainingModule[];
  total_modules: number;
  version: string;
}

export interface TrainingProgress {
  items: Array<{
    module_key: string;
    skill: string;
    title: string;
    provider: string;
    url: string | null;
    resource_type: string;
    status: string;
    completed_at: string | null;
  }>;
  total: number;
}

export interface PipelineTraceSummary {
  run_id: string;
  steps: number;
  created_at: string | null;
}

// ─── Overview Dashboard Types ──────────────────────────────────────────

export interface OverviewProfile {
  connected: boolean;
  completeness: number;
  skills_count: number;
  skills: string[];
  has_perceptions: boolean;
  perceptions_count: number;
}

export interface OverviewReadiness {
  score: number;
}

export interface OverviewSkills {
  total: number;
  items: string[];
}

export interface OverviewGapItem {
  skill: string;
  count: number;
  priority: string;
  jobs_demanding: string[];
}

export interface OverviewSkillGaps {
  total: number;
  critical: number;
  items: OverviewGapItem[];
}

export interface OverviewTopMatch {
  job_id: string;
  title: string;
  company: string;
  location: string;
  overall_score: number;
  matched_skills: string[];
  missing_required: string[];
  recommendation: string;
}

export interface OverviewJobs {
  relevant_count: number;
  top_matches: OverviewTopMatch[];
}

export interface OverviewOpportunityUnlock {
  top_opportunity: Record<string, unknown> | null;
  potential: number;
  unlocked_count: number;
  top_roles: Array<Record<string, unknown>>;
}

export interface OverviewTimeToReadyItem {
  job_id: string;
  job_title: string;
  missing_skills_count: number;
  estimated_weeks: number;
  estimated_cost: number;
  currency: string;
  free_only_weeks: number;
  free_only_cost: number;
  coverage_pct: number;
  readiness: number;
}

export interface OverviewTimeToReady {
  items: OverviewTimeToReadyItem[];
  source: string;
}

export interface OverviewLearningProgress {
  total_modules: number;
  completed: number;
  items: Array<{
    module_key: string;
    skill: string;
    title: string;
    provider: string;
    url: string | null;
    resource_type: string;
    source_status: string;
    status: string;
    completed_at: string | null;
  }>;
}

export interface OverviewCareerInsight {
  text: string;
  type: string;
  evidence: string[];
}

export interface OverviewNextAction {
  action: string;
  description: string;
  type: string;
  priority: string;
}

export interface Skill2JobOverview {
  profile: OverviewProfile;
  readiness: OverviewReadiness;
  skills: OverviewSkills;
  skill_gaps: OverviewSkillGaps;
  jobs: OverviewJobs;
  opportunity_unlock: OverviewOpportunityUnlock;
  learning_progress: OverviewLearningProgress;
  time_to_ready: OverviewTimeToReady;
  career_insight: OverviewCareerInsight;
  next_action: OverviewNextAction;
  last_analyzed: string | null;
}

// ─── Skill Graph (candidate-facing, backend aggregation) ──────────────

export interface SkillGraphNode {
  id: string;
  label: string;
  kind: "candidate" | "gap" | "related" | "job" | "required" | "preferred" | "matched";
  category: string | null;
  count: number;
}

export interface SkillGraphEdge {
  source: number;
  target: number;
  relation: "synonym" | "related" | "transferable" | string;
}

export interface Skill2JobSkillGraph {
  nodes: SkillGraphNode[];
  edges: SkillGraphEdge[];
  generated_from: {
    candidate_skills: number;
    gap_skills: number;
  };
}

// ─── Match detail (Phase 2 explainable matching) ────────────────────────

export type MatchCategory = "matched" | "partial" | "missing" | "unknown";
export type SkillEvidenceState = "claimed" | "supported" | "demonstrated" | "verified" | "none";

export interface SkillMatchDetail {
  skill: string;
  kind: "required" | "preferred";
  status: "matched" | "transferable" | "missing";
  evidence_state: SkillEvidenceState;
  similarity: number | null;
  evidence_notes: string;
}

export interface JobMatchDetail {
  job_id: string;
  title: string;
  company: string;
  location: string | null;
  remote_type: string | null;
  overall_score: number;
  category: MatchCategory;
  categories_explained: string;
  scores: MatchScores;
  skill_details: SkillMatchDetail[];
  explanation: string[];
  reasons: string[];
  recommendation: string;
  strength_level: string;
  matched_skills: string[];
  missing_required: string[];
  missing_preferred: string[];
  transferable_skills: string[];
  suggested_skills: string[];
  match_version: string;
}

export interface SkillDemandItem {
  skill: string;
  required_count: number;
  preferred_count: number;
  count: number;
  jobs_demanding: string[];
  demand_level: "high" | "medium" | "low";
}

export interface SkillDemand {
  dataset: string;
  total_jobs: number;
  items: SkillDemandItem[];
  computed_from: string;
}

export interface JobSkillGraph {
  job: CuratedJob;
  nodes: SkillGraphNode[];
  edges: SkillGraphEdge[];
  match: {
    overall_score: number | null;
    matched_skills: string[];
    missing_required: string[];
  };
  generated_from: { job_skills: number };
}

// ─── Skill Proof (candidate-facing, backend aggregation) ──────────────

export interface SkillProofEvidence {
  source: string;
  note: string;
}

export interface SkillProofItem {
  name: string;
  category: string | null;
  proficiency: string | null;
  years: number | null;
  evidence: SkillProofEvidence[];
  supported_by: string[];
  proof_status: "LEARN" | "PROVE" | "VERIFIED";
  proof_plan: SkillProofPlan;
}

export interface SkillProofPlan {
  action: "LEARN" | "PROVE" | "MAINTAIN";
  steps: Array<{
    step: number;
    phase: string;
    description: string;
  }>;
  estimated_effort: "low" | "medium" | "high";
  demand_context: number;
}

export interface Skill2JobSkillProof {
  skills: SkillProofItem[];
  sources: {
    profile: number;
    perception: number;
    matched_jobs: number;
    gap_demand: number;
    training: number;
  };
}

// ─── Phase 3: Skill Proof Detail ───────────────────────────────────────

export interface SkillProofDetail {
  skill: string;
  category: string | null;
  proficiency: string | null;
  years: number | null;
  proof_status: "LEARN" | "PROVE" | "VERIFIED";
  evidence: SkillProofEvidence[];
  supported_by: string[];
  proof_plan: SkillProofPlan;
  learning_resources: Array<{
    title: string;
    provider: string;
    url: string | null;
    duration_hours: number | null;
    cost: number | null;
    is_free: boolean;
    coverage: number;
  }>;
}

// ─── Phase 3: Evidence-Aware Readiness ─────────────────────────────────

export interface EvidenceStrength {
  skill: string;
  evidence_level: string;
  evidence_multiplier: number;
  sources: string[];
  note: string;
}

export interface ReadinessResult {
  job_id: string;
  job_title: string;
  overall_readiness: number;
  skill_coverage: number;
  evidence_quality: number;
  critical_gaps: string[];
  evidence_breakdown: EvidenceStrength[];
  total_required: number;
  matched_count: number;
  missing_count: number;
  version: string;
}

// ─── Phase 3: Per-Job Learning Plan ────────────────────────────────────

export interface LearningPlanForJob {
  job_id: string;
  job_title: string;
  current_readiness: number;
  skill_coverage: number;
  evidence_quality: number;
  critical_gaps: string[];
  missing_skills: Array<{
    skill: string;
    priority: string;
    importance: number;
    dependencies: string[];
    has_free_resource: boolean;
  }>;
  learning_plan: Array<{
    step_number: number;
    skill: string;
    resource_title: string;
    resource_provider: string;
    resource_url: string | null;
    weeks: number;
    hours: number;
    cost: number;
    is_free: boolean;
    can_parallel: boolean;
    explanation: string;
  }>;
  total_weeks: number;
  total_hours: number;
  total_cost: number;
  currency: string;
  free_only_path: {
    weeks: number;
    hours: number;
    cost: number;
    coverage_pct: number;
    remaining_gaps: string[];
  };
  opportunity_unlock: {
    current_jobs: number;
    projected_jobs: number;
    potential_increase: number;
  };
  optimization_mode: string;
  hours_per_week: number;
  version: string;
}

// ─── Phase 3: Enhanced Opportunity Dashboard ───────────────────────────

export interface OpportunityUnlockBySkill {
  skill: string;
  jobs_affected: number;
  avg_uplift: number;
}

export interface OpportunityCostAnalysis {
  total_cost: number;
  currency: string;
  skills_with_cost: number;
}

export interface OpportunityDashboardEnhanced {
  top_opportunity: Record<string, unknown> | null;
  potential: number;
  unlocked_count: number;
  top_roles: Array<Record<string, unknown>>;
  readiness: number;
  readiness_level: string;
  matched_skills_count: number;
  evidence_breakdown: Array<{
    skill: string;
    level: string;
    multiplier: number;
  }>;
  potential_unlock_by_skill: OpportunityUnlockBySkill[];
  cost_analysis: OpportunityCostAnalysis;
}

// ─── Phase 3: Learning Progress States ─────────────────────────────────

export type EvidenceState =
  | "not_started"
  | "in_progress"
  | "completed"
  | "practiced"
  | "assessed"
  | "demonstrated"
  | "verified";

export interface LearningProgressUpdate {
  ok: boolean;
  module_key: string;
  evidence_state: string;
  learning_hours: number;
  reason?: string;
}