import apiClient from "./client";
import type {
  FairnessOverview,
  FairnessMetrics,
  FairnessReport,
  AdversarialTestResult,
  JDAnalysis,
  CandidateFairness,
  BiasAlert,
} from "../types/fairness";

export async function getFairnessOverview(): Promise<FairnessOverview> {
  const response = await apiClient.get<FairnessOverview>("/fairness/overview");
  return response.data;
}

export async function getFairnessMetrics(): Promise<FairnessMetrics> {
  const response = await apiClient.get<FairnessMetrics>("/fairness/metrics");
  return response.data;
}

export async function getFairnessReport(jobId: string): Promise<FairnessReport> {
  const response = await apiClient.get<FairnessReport>(`/fairness/report/${jobId}`);
  return response.data;
}

export async function analyzeFairness(jobId?: string): Promise<FairnessOverview | FairnessReport> {
  const params = jobId ? `?job_id=${jobId}` : "";
  const response = await apiClient.post<FairnessOverview | FairnessReport>(
    `/fairness/analyze${params}`,
  );
  return response.data;
}

export async function detectRankingBias(
  jobId: string,
): Promise<{ job_id: string; alerts: BiasAlert[]; total_alerts: number; severity_counts: Record<string, number> }> {
  const response = await apiClient.get(`/fairness/bias-detection/${jobId}`);
  return response.data;
}

export async function runAdversarialTest(
  jobId: string,
  candidateId: string,
): Promise<AdversarialTestResult> {
  const response = await apiClient.post<AdversarialTestResult>(
    `/fairness/adversarial-test?job_id=${jobId}&candidate_id=${candidateId}`,
  );
  return response.data;
}

export async function analyzeJobDescription(jobId: string): Promise<JDAnalysis> {
  const response = await apiClient.get<JDAnalysis>(`/fairness/jd-analysis/${jobId}`);
  return response.data;
}

export async function getBiasAlerts(limit: number = 50): Promise<BiasAlert[]> {
  const response = await apiClient.get<BiasAlert[]>(`/fairness/bias-alerts?limit=${limit}`);
  return response.data;
}

export async function getCandidateFairness(candidateId: string): Promise<CandidateFairness> {
  const response = await apiClient.get<CandidateFairness>(`/fairness/candidate/${candidateId}`);
  return response.data;
}

export async function getMyFairness(): Promise<CandidateFairness> {
  const response = await apiClient.get<CandidateFairness>("/fairness/my-fairness");
  return response.data;
}
