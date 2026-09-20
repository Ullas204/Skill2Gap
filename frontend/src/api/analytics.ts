import apiClient from "./client";
import type {
  AdminAnalytics,
  AIInsightsResponse,
  AlertRule,
  AlertRuleCreateRequest,
  CandidatePerformance,
  DashboardLayout,
  DashboardLayoutRequest,
  ExecutiveKPIs,
  ExportResponse,
  HRAnalytics,
  PredictiveAnalytics,
  RecruiterAnalytics,
  Report,
  ReportCreateRequest,
  ReportListResponse,
} from "../types/analytics";

export const analyticsApi = {
  getCandidatePerformance: async (): Promise<CandidatePerformance> => {
    const res = await apiClient.get("/analytics/candidate");
    return res.data;
  },

  getRecruiterAnalytics: async (): Promise<RecruiterAnalytics> => {
    const res = await apiClient.get("/analytics/recruiter");
    return res.data;
  },

  getHRAnalytics: async (): Promise<HRAnalytics> => {
    const res = await apiClient.get("/analytics/hr");
    return res.data;
  },

  getAdminAnalytics: async (): Promise<AdminAnalytics> => {
    const res = await apiClient.get("/analytics/admin");
    return res.data;
  },

  getExecutiveKPIs: async (): Promise<ExecutiveKPIs> => {
    const res = await apiClient.get("/analytics/executive");
    return res.data;
  },

  getPredictions: async (): Promise<PredictiveAnalytics> => {
    const res = await apiClient.get("/analytics/predictions");
    return res.data;
  },

  getInsights: async (insightType?: string): Promise<AIInsightsResponse> => {
    const params = insightType ? { insight_type: insightType } : {};
    const res = await apiClient.get("/analytics/insights", { params });
    return res.data;
  },

  getReports: async (): Promise<ReportListResponse> => {
    const res = await apiClient.get("/analytics/reports");
    return res.data;
  },

  createReport: async (data: ReportCreateRequest): Promise<Report> => {
    const res = await apiClient.post("/analytics/reports", data);
    return res.data;
  },

  exportReport: async (reportType: string, format: string = "pdf"): Promise<ExportResponse> => {
    const res = await apiClient.post("/analytics/export", { report_type: reportType, format });
    return res.data;
  },

  getAlertRules: async (): Promise<AlertRule[]> => {
    const res = await apiClient.get("/analytics/alerts");
    return res.data;
  },

  createAlertRule: async (data: AlertRuleCreateRequest): Promise<AlertRule> => {
    const res = await apiClient.post("/analytics/alerts", data);
    return res.data;
  },

  getDashboardLayout: async (dashboardKey: string): Promise<DashboardLayout | null> => {
    const res = await apiClient.get("/analytics/dashboard-layout", { params: { dashboard_key: dashboardKey } });
    return res.data;
  },

  saveDashboardLayout: async (data: DashboardLayoutRequest): Promise<DashboardLayout> => {
    const res = await apiClient.post("/analytics/dashboard-layout", data);
    return res.data;
  },
};
