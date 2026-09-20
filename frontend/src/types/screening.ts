export interface ScreeningWeights {
  skills: number;
  experience: number;
  education: number;
  projects: number;
  certifications: number;
  location: number;
  employment_type: number;
  semantic: number;
}

export interface ScreeningConfig {
  weights?: ScreeningWeights;
}

export interface ScreeningResult {
  id: string;
  job_id: string;
  candidate_id: string;
  resume_id: string | null;
  overall_match_score: number;
  skill_match_score: number;
  experience_match_score: number;
  education_match_score: number;
  project_match_score: number;
  certification_match_score: number;
  location_match_score: number;
  employment_type_match_score: number;
  semantic_match_score: number;
  matched_skills: string[] | null;
  missing_required_skills: string[] | null;
  missing_preferred_skills: string[] | null;
  strengths: string[] | null;
  weaknesses: string[] | null;
  recommendation: HiringRecommendation;
  strength_level: StrengthLevel;
  created_at: string;
  updated_at: string;
}

export type StrengthLevel = "excellent" | "good" | "average" | "low";
export type HiringRecommendation =
  | "strongly_recommend"
  | "recommend"
  | "consider"
  | "not_recommended";

export interface CandidateRanking {
  id: string;
  job_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  screening_result_id: string;
  rank: number;
  previous_rank: number | null;
  rank_change: number;
  overall_score: number;
  strength_level: StrengthLevel;
  created_at: string;
  updated_at: string;
}

export interface SkillGapAnalysis {
  id: string;
  screening_result_id: string;
  missing_required_skills: string[] | null;
  missing_preferred_skills: string[] | null;
  experience_gap_description: string | null;
  education_gap_description: string | null;
  certification_gap_description: string | null;
  skill_suggestions: string[] | null;
  improvement_suggestions: string[] | null;
  interview_readiness_score: number;
  created_at: string;
  updated_at: string;
}

export interface CandidateComparisonItem {
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  overall_match_score: number;
  skill_match_score: number;
  experience_match_score: number;
  education_match_score: number;
  project_match_score: number;
  certification_match_score: number;
  matched_skills: string[] | null;
  missing_required_skills: string[] | null;
  strengths: string[] | null;
  weaknesses: string[] | null;
  recommendation: HiringRecommendation;
  strength_level: StrengthLevel;
}

export interface CandidateComparisonResponse {
  job_id: string;
  job_title: string;
  candidates: CandidateComparisonItem[];
}

export interface RankingListResponse {
  items: CandidateRanking[];
  total: number;
  job_id: string;
  job_title: string;
}

export interface ScreeningTriggerResponse {
  message: string;
  job_id: string;
  candidates_screened: number;
}

export interface CandidateMatchReport {
  job_id: string;
  job_title: string;
  candidate_id: string;
  candidate_name: string;
  screening: ScreeningResult | null;
  skill_gap: SkillGapAnalysis | null;
  interview_readiness_score: number | null;
  improvement_suggestions: string[] | null;
}

// ─── AI Search ──────────────────────────────────────────────────────

export interface AISearchRequest {
  query: string;
  job_id?: string;
  limit?: number;
  offset?: number;
}

export interface AISearchResultItem {
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  overall_score: number;
  relevance_score: number;
  matched_skills: string[];
  missing_skills: string[];
  recommendation: string;
  strength_level: string;
  experience_years: number;
  location: string;
  has_screening: boolean;
}

export interface AISearchResponse {
  results: AISearchResultItem[];
  total: number;
  query_skills: string[];
  query_years: number | null;
  query_location: string | null;
  job_id: string | null;
  job_title: string | null;
}

// ─── Candidate AI Summary ───────────────────────────────────────────

export interface TopSkill {
  skill: string;
  relevance: number;
}

export interface CandidateAISummary {
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  professional_summary: string;
  top_skills: TopSkill[];
  strengths: string[];
  weaknesses: string[];
  career_highlights: string[];
  risk_factors: string[];
  experience_level: string;
  technical_expertise: string;
  leadership_potential: string;
  learning_ability: string;
  total_experience_years: number;
  education_summary: string[];
  certification_count: number;
  project_count: number;
  job_match_score: number | null;
  hiring_recommendation: string | null;
  matched_skills: string[] | null;
  missing_skills: string[] | null;
  strengths_from_screening: string[] | null;
  weaknesses_from_screening: string[] | null;
  interview_readiness: number | null;
  improvement_suggestions: string[] | null;
}

// ─── Job AI Summary ─────────────────────────────────────────────────

export interface SkillCount {
  skill: string;
  count: number;
}

export interface JobAISummary {
  job_id: string;
  job_title: string;
  total_applicants: number;
  total_screened: number;
  average_score: number;
  top_candidates: Array<{
    candidate_id: string;
    candidate_name: string;
    rank: number;
    score: number;
    strength_level: string;
    recommendation: string;
  }>;
  score_distribution: Record<string, number>;
  recommendation_breakdown: Record<string, number>;
  most_common_matched_skills: SkillCount[];
  most_common_missing_skills: SkillCount[];
}

// ─── Top Candidates ─────────────────────────────────────────────────

export interface TopCandidateItem {
  rank: number;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  overall_score: number;
  strength_level: string;
  recommendation: string;
  skill_match: number;
  experience_match: number;
  matched_skills: string[];
  rank_change: number;
}

export interface TopCandidatesResponse {
  job_id: string | null;
  job_title: string | null;
  candidates: TopCandidateItem[];
  total_ranked: number;
  total_jobs: number;
}

// ─── Hiring Recommendation ──────────────────────────────────────────

export interface HiringRecommendationExplanation {
  title: string;
  summary: string;
  factors: string[];
  next_steps: string[];
  score_breakdown: Record<string, number>;
}

export interface HiringRecommendationResponse {
  job_id: string;
  job_title: string;
  candidate_id: string;
  candidate_name: string;
  recommendation: string;
  overall_score: number;
  confidence_score: number;
  strength_level: string;
  explanation: HiringRecommendationExplanation;
  matched_skills: string[];
  missing_skills: string[];
  strengths: string[];
  weaknesses: string[];
  interview_readiness: number | null;
  improvement_suggestions: string[];
}

// ─── Recruiter AI Dashboard ─────────────────────────────────────────

export interface RecruiterDashboardSummary {
  total_jobs: number;
  total_applications: number;
  total_screened: number;
  average_score: number;
  job_summaries: Array<{
    job_id: string;
    job_title: string;
    applicant_count: number;
    screened_count: number;
    average_score: number;
    top_candidate_name: string;
    top_candidate_score: number;
    status: string;
  }>;
  recent_rankings: Array<{
    job_title: string;
    candidate_name: string;
    score: number;
    rank: number;
    rank_change: number;
  }>;
}

// ─── XAI (Explainable AI) ──────────────────────────────────────────

export interface FeatureImportanceItem {
  category: string;
  label: string;
  score: number;
  weight: number;
  contribution_pct: number;
  impact: "positive" | "negative" | "neutral";
  impact_description: string;
  shap_value?: number;
  method?: string;
}

export interface FactorItem {
  category: string;
  score: number;
  contribution_pct: number;
  reason: string;
}

export interface ConfidenceScore {
  score: number;
  level: "very_high" | "high" | "medium" | "low";
  description: string;
  data_completeness_pct: number;
  data_points_available: number;
  data_points_max: number;
}

export interface SkillImprovement {
  skill: string;
  priority: string;
  reason: string;
}

export interface CertificationSuggestion {
  area: string;
  suggestion: string;
  priority: string;
}

export interface ImprovementRecommendations {
  skill_improvements: SkillImprovement[];
  certification_recommendations: CertificationSuggestion[];
  project_suggestions: string[];
  resume_improvements: string[];
  interview_preparation: string[];
}

export interface CandidateExplanation {
  candidate_id: string;
  candidate_name: string;
  job_id: string;
  job_title: string;
  overall_score: number;
  feature_importance: FeatureImportanceItem[];
  positive_factors: FactorItem[];
  negative_factors: FactorItem[];
  reasoning_summary: string;
  confidence: ConfidenceScore;
  improvement_suggestions: ImprovementRecommendations;
  strengths: string[];
  weaknesses: string[];
  matched_skills: string[];
  missing_skills: string[];
  recommendation: string;
  strength_level: string;
  shap_available: boolean;
  lime_available: boolean;
}

export interface PairwiseComparison {
  higher_candidate: string;
  higher_name: string;
  higher_score: number;
  lower_candidate: string;
  lower_name: string;
  lower_score: number;
  score_difference: number;
  key_differences: Array<{
    category: string;
    higher_score: number;
    lower_score: number;
    difference: number;
    direction: string;
  }>;
  skills_only_higher_has: string[];
  skills_only_lower_has: string[];
  summary: string;
}

// ─── Evidence-Grounded Job Fit (Phase 2) ────────────────────────────

export type MatchStatus = "match" | "partial" | "gap" | "unknown";
export type EvidenceStrength = "strong" | "moderate" | "weak" | "none";
export type EvidenceSource =
  | "experience"
  | "project"
  | "certification"
  | "education"
  | "skills_section"
  | "resume_text";

export interface FitEvidenceItem {
  source: EvidenceSource;
  quote: string;
  context: string;
  section: string;
}

export interface FitRequirementResult {
  requirement: string;
  requirement_type: string;
  level: string;
  category: string;
  status: MatchStatus;
  evidence_strength: EvidenceStrength;
  reason: string;
  evidence: FitEvidenceItem[];
}

export interface FitExperienceAlignment {
  status: MatchStatus;
  required_years: number | null;
  relevant_years: number | null;
  total_years: number | null;
  relevance_basis: string;
  reason: string;
}

export interface FitResponsibilityAlignment {
  responsibility: string;
  alignment: EvidenceStrength;
  evidence: FitEvidenceItem[];
}

export interface FitSkillGapSummary {
  strengths: string[];
  partial: string[];
  gaps: string[];
  unknown: string[];
}

export interface FitScoreBreakdown {
  weights: Record<string, number>;
  components: Record<string, number>;
  formula: string;
}

export interface FitOverall {
  classification: string;
  score: number;
  breakdown: FitScoreBreakdown;
  summary: string;
  summary_source: string;
  disclaimer: string;
}

export interface JobRequirementsInfo {
  extracted_count: number;
  extractor_version: string;
}

export interface JobFitResponse {
  job_id: string;
  job_title: string;
  candidate_id: string;
  candidate_name: string;
  resume_id: string | null;
  requirements: FitRequirementResult[];
  experience_alignment: FitExperienceAlignment;
  responsibilities: FitResponsibilityAlignment[];
  skill_gaps: FitSkillGapSummary;
  overall: FitOverall;
  requirements_info: JobRequirementsInfo;
  cached: boolean;
  engine_version: string;
}

export interface CandidateComparisonXAI {
  job_id: string;
  job_title: string;
  candidates: Array<{
    candidate_id: string;
    candidate_name: string;
    candidate_email: string;
    overall_score: number;
    skill_match_score: number;
    experience_match_score: number;
    education_match_score: number;
    project_match_score: number;
    certification_match_score: number;
    matched_skills: string[];
    missing_skills: string[];
    strengths: string[];
    weaknesses: string[];
    recommendation: string;
    strength_level: string;
    feature_importance: FeatureImportanceItem[];
    confidence: ConfidenceScore;
  }>;
  pairwise_comparisons: PairwiseComparison[];
}

// ─── Candidate Evidence Intelligence (Phase 3) ──────────────────────

export type SkillDepth =
  | "expert_level_evidence"
  | "strong"
  | "moderate"
  | "limited"
  | "mention_only"
  | "no_evidence";

export type IntelConfidence = "high" | "medium" | "low" | "insufficient";

export type ReviewFlagSeverity = "info" | "warning";

export type ReviewFlagType =
  | "stated_vs_timeline_mismatch"
  | "overlapping_employment"
  | "date_inconsistency"
  | "missing_dates"
  | "employment_gap";

export interface ProfileSnapshot {
  total_experience_months: number;
  total_experience_years: number | null;
  experience_count: number;
  project_count: number;
  certification_count: number;
  education_count: number;
  skills_mentioned: number;
  highest_degree: string | null;
}

export interface TimelineInfo {
  computed_months: number;
  stated_years_found: boolean;
  stated_years_value: number | null;
  entries_with_dates: number;
  entries_total: number;
}

export interface SkillAssessment {
  skill: string;
  category: string | null;
  depth: SkillDepth;
  confidence: IntelConfidence;
  professional_months: number;
  counts: Record<string, number>;
  reason: string;
  evidence: FitEvidenceItem[];
}

export interface StrengthInsight {
  title: string;
  category: string | null;
  depth: SkillDepth;
  confidence: IntelConfidence;
  reason: string;
  evidence: FitEvidenceItem[];
}

export interface AchievementInsight {
  text: string;
  context: string | null;
  source_type: "experience" | "project";
  label: string;
}

export interface ReviewFlag {
  flag_type: ReviewFlagType;
  severity: ReviewFlagSeverity;
  title: string;
  description: string;
  possible_explanation: string | null;
  evidence: FitEvidenceItem[];
}

export interface ScreeningQuestionSuggestion {
  question: string;
  topic: string;
  reason: string;
}

export interface EvidenceGapInsight {
  skill: string;
  current_depth: SkillDepth;
  note: string;
}

export interface IntelSummary {
  text: string;
  source: "deterministic" | "llm_polished";
  disclaimer: string;
}

export interface CandidateEvidenceIntelResponse {
  candidate_id: string;
  candidate_name: string;
  resume_id: string | null;
  engine_version: string;
  cached: boolean;
  snapshot: ProfileSnapshot;
  timeline: TimelineInfo;
  strengths: StrengthInsight[];
  skill_assessments: SkillAssessment[];
  achievements: AchievementInsight[];
  review_flags: ReviewFlag[];
  evidence_gaps: EvidenceGapInsight[];
  screening_questions: ScreeningQuestionSuggestion[];
  summary: IntelSummary;
}

export interface JobContextBlock {
  job_id: string;
  job_title: string;
  fit_classification: string;
  fit_score: number;
  required_years: number | null;
  relevant_years: number | null;
  total_years: number | null;
  relevance_basis: string | null;
  requirement_gaps: string[];
  requirement_unknown: string[];
  additional_questions: ScreeningQuestionSuggestion[];
  summary: IntelSummary;
}

export interface JobIntelligenceResponse {
  candidate_id: string;
  candidate_name: string;
  job_id: string;
  job_title: string;
  engine_version: string;
  cached: boolean;
  candidate_intelligence: CandidateEvidenceIntelResponse;
  job_context: JobContextBlock;
}
