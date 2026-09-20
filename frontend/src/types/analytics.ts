export interface KPIMetric {
  label: string;
  value: number;
  unit: string;
  change_pct: number;
  trend: string;
  icon: string | null;
}

export interface ChartDataset {
  label: string;
  data: number[];
  color: string | null;
}

export interface ChartData {
  labels: string[];
  datasets: ChartDataset[];
}

export interface DataDistribution {
  label: string;
  count: number;
  percentage: number;
}

export interface StatusBreakdown {
  status: string;
  count: number;
  percentage: number;
}

export interface ChartDataPoint {
  label: string;
  value: number;
  secondary_value: number | null;
  color: string | null;
}

// ── Candidate Analytics ─────────────────────────────────────────────

export interface CandidatePerformance {
  overall_score: number;
  skill_match_pct: number;
  interview_avg_score: number;
  resume_score: number;
  application_count: number;
  interview_count: number;
  strongest_skills: DataDistribution[];
  score_trend: ChartData;
  applications_by_status: StatusBreakdown[];
  improvement_areas: string[];
  rank_percentile: number;
}

// ── Recruiter Analytics ─────────────────────────────────────────────

export interface RecruiterAnalytics {
  total_jobs: number;
  active_jobs: number;
  total_applicants: number;
  avg_time_to_fill: number;
  avg_time_to_screen: number;
  hire_rate: number;
  jobs_by_status: StatusBreakdown[];
  applicants_trend: ChartData;
  top_jobs: ChartDataPoint[];
  source_effectiveness: DataDistribution[];
  pipeline_velocity: ChartDataPoint[];
}

// ── HR Analytics ────────────────────────────────────────────────────

export interface HRAnalytics {
  total_headcount: number;
  open_positions: number;
  avg_time_to_hire: number;
  acceptance_rate: number;
  diversity_index: number;
  turnover_rate: number;
  headcount_trend: ChartData;
  department_distribution: DataDistribution[];
  gender_distribution: DataDistribution[];
  hiring_funnel: StatusBreakdown[];
  recruiter_performance: ChartDataPoint[];
}

// ── Admin Analytics ─────────────────────────────────────────────────

export interface AdminAnalytics {
  total_users: number;
  active_users: number;
  total_jobs: number;
  total_applications: number;
  system_health_score: number;
  storage_used_mb: number;
  api_calls_today: number;
  users_by_role: DataDistribution[];
  users_trend: ChartData;
  security_events: ChartDataPoint[];
  system_load: ChartDataPoint[];
}

// ── Executive KPIs ──────────────────────────────────────────────────

export interface ExecutiveKPIs {
  revenue_per_hire: number;
  cost_per_hire: number;
  quality_of_hire: number;
  time_to_productivity: number;
  hiring_forecast: ChartData;
  department_kpis: ChartDataPoint[];
  quarterly_trends: ChartData;
  risk_indicators: DataDistribution[];
}

// ── Predictive Analytics ────────────────────────────────────────────

export interface PredictiveAnalytics {
  demand_forecast: ChartData;
  attrition_risk: ChartDataPoint[];
  skill_gap_forecast: DataDistribution[];
  hiring_timeline: ChartData;
  budget_projection: ChartData;
  confidence_score: number;
  recommendations: string[];
}

// ── AI Insights ─────────────────────────────────────────────────────

export interface AIInsightItem {
  id: string;
  insight_type: string;
  title: string;
  summary: string;
  data_payload: Record<string, unknown> | null;
  priority: number;
  created_at: string;
}

export interface AIInsightsResponse {
  insights: AIInsightItem[];
  total: number;
  categories: DataDistribution[];
}

// ── Reports ─────────────────────────────────────────────────────────

export interface Report {
  id: string;
  title: string;
  report_type: string;
  config: Record<string, unknown> | null;
  is_scheduled: boolean;
  schedule_cron: string | null;
  last_generated_at: string | null;
  created_at: string;
}

export interface ReportListResponse {
  reports: Report[];
  total: number;
}

export interface ReportCreateRequest {
  title: string;
  report_type: string;
  config?: Record<string, unknown>;
  is_scheduled?: boolean;
  schedule_cron?: string;
}

export interface ExportResponse {
  download_url: string;
  format: string;
  generated_at: string;
}

// ── Alert Rules ─────────────────────────────────────────────────────

export interface AlertRule {
  id: string;
  alert_type: string;
  title: string;
  condition_config: Record<string, unknown>;
  is_active: boolean;
  threshold: number | null;
  last_triggered_at: string | null;
  created_at: string;
}

export interface AlertRuleCreateRequest {
  alert_type: string;
  title: string;
  condition_config: Record<string, unknown>;
  threshold?: number;
}

// ── Dashboard Layout ────────────────────────────────────────────────

export interface DashboardLayout {
  id: string;
  dashboard_key: string;
  layout_config: Record<string, unknown>;
  created_at: string;
}

export interface DashboardLayoutRequest {
  dashboard_key: string;
  layout_config: Record<string, unknown>;
}
