import apiClient from "./client";

export interface CandidateDashboardData {
  total_applications: number;
  saved_jobs: number;
  resume_score: number;
  ats_score: number;
  profile_completion: number;
  recommended_jobs_count: number;
  recent_applications: Record<string, unknown>[];
  ai_suggestions: string[];
}

export interface RecruiterDashboardData {
  total_jobs: number;
  active_jobs: number;
  total_applications: number;
  candidates_screened: number;
  top_candidates: Record<string, unknown>[];
  interview_pipeline: Record<string, number>;
  hiring_status: Record<string, unknown>;
  recent_applications: Record<string, unknown>[];
}

export interface HRDashboardData {
  open_positions: number;
  total_candidates: number;
  total_recruiters: number;
  hiring_funnel: Record<string, number>;
  department_hiring: Record<string, unknown>[];
  recent_activity: Record<string, unknown>[];
  time_to_hire_avg: number;
  hiring_trends: Record<string, unknown>[];
}

export interface AdminDashboardData {
  total_users: number;
  active_users: number;
  total_candidates: number;
  total_recruiters: number;
  total_hr: number;
  total_admins: number;
  system_health: Record<string, unknown>;
  recent_logins: Record<string, unknown>[];
  user_growth: Record<string, unknown>[];
}

export interface AdminUserItem {
  id: string;
  full_name: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  roles: string[];
  created_at: string;
  updated_at: string;
}

export interface AuditLogItem {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  success: boolean;
  created_at: string;
}

export const dashboardApi = {
  getCandidate: () =>
    apiClient.get<CandidateDashboardData>("/dashboard/candidate").then((r) => r.data),

  getRecruiter: () =>
    apiClient.get<RecruiterDashboardData>("/dashboard/recruiter").then((r) => r.data),

  getHR: () =>
    apiClient.get<HRDashboardData>("/dashboard/hr").then((r) => r.data),

  getAdmin: () =>
    apiClient.get<AdminDashboardData>("/dashboard/admin").then((r) => r.data),

  getAdminUsers: (page = 1, pageSize = 50) =>
    apiClient.get<AdminUserItem[]>("/dashboard/admin/users", { params: { page, page_size: pageSize } }).then((r) => r.data),

  getAdminAuditLogs: (page = 1, pageSize = 50) =>
    apiClient.get<AuditLogItem[]>("/dashboard/admin/audit-logs", { params: { page, page_size: pageSize } }).then((r) => r.data),

  getAdminStats: () =>
    apiClient.get<Record<string, number>>("/dashboard/admin/stats").then((r) => r.data),
};
