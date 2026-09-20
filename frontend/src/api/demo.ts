import apiClient from "./client";

export type ResumeFormat = "pdf" | "docx" | "txt" | "mixed";
export type HiringDifficulty = "easy" | "medium" | "hard";

interface DemoRequestBase {
  num_candidates: number;
  num_recruiters: number;
  num_hr: number;
  num_jobs: number;
  num_companies?: number | null;
  candidates_per_job: number;
  hiring_difficulty?: HiringDifficulty;
  skill_categories?: string[];
  include_screening: boolean;
  include_interviews: boolean;
  include_reports: boolean;
  include_agent_indexing: boolean;
  resume_format: ResumeFormat;
  seed?: number | null;
}

export interface DemoGenerateRequest extends DemoRequestBase {
  scenario_slug?: string | null;
}

export interface DemoCustomRequest extends DemoRequestBase {
  companies: string[];
  job_titles: string[];
}

export interface DemoRun {
  id: string;
  scenario_id: string | null;
  status: string;
  progress: number;
  current_stage: string | null;
  stage_message: string | null;
  stats: Record<string, unknown> | null;
  error: string | null;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface DemoEvent {
  id: string;
  stage: string | null;
  event_type: string;
  message: string;
  details: Record<string, unknown> | null;
  created_at: string | null;
}

export interface DemoRunDetail {
  run: DemoRun;
  events: DemoEvent[];
}

export interface DemoScenario {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  config: Record<string, unknown> | null;
  tags: string[] | null;
}

export interface DemoStatus {
  latest_run: DemoRun | null;
  runs: DemoRun[];
  totals: Record<string, number>;
}

export interface DemoExport {
  generated_at: string;
  companies: Record<string, unknown>[];
  users: Record<string, unknown>[];
  jobs: Record<string, unknown>[];
  applications: Record<string, unknown>[];
  screenings: Record<string, unknown>[];
  interviews: Record<string, unknown>[];
  reports: Record<string, unknown>[];
  summary: Record<string, unknown>;
}

export interface MessageResponse {
  message: string;
  detail?: string | Record<string, unknown> | null;
}

export const demoApi = {
  getScenarios: () =>
    apiClient.get<DemoScenario[]>("/demo/scenarios").then((r) => r.data),

  generate: (body: DemoGenerateRequest) =>
    apiClient.post<DemoRun>("/demo/generate", body).then((r) => r.data),

  generateCustom: (body: DemoCustomRequest) =>
    apiClient.post<DemoRun>("/demo/custom", body).then((r) => r.data),

  getStatus: () =>
    apiClient.get<DemoStatus>("/demo/status").then((r) => r.data),

  getRunDetail: (runId: string) =>
    apiClient.get<DemoRunDetail>(`/demo/runs/${runId}`).then((r) => r.data),

  reset: () =>
    apiClient.post<MessageResponse>("/demo/reset").then((r) => r.data),

  export: () =>
    apiClient.get<DemoExport>("/demo/export").then((r) => r.data),
};
