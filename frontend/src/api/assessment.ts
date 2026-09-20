import apiClient from "./client";
import type {
  AnalyticsResponse,
  AnswerResultResponse,
  AssessmentCreateRequest,
  AssessmentResponse,
  AttemptListItem,
  AttemptStartResponse,
  AttemptState,
  CodeRunResponse,
  ResultResponse,
} from "../types/assessment";

export const assessmentApi = {
  generate: async (data: AssessmentCreateRequest): Promise<AssessmentResponse> => {
    const res = await apiClient.post("/assessments/generate", data);
    return res.data;
  },

  list: async (): Promise<{ items: AssessmentResponse[]; total: number }> => {
    const res = await apiClient.get("/assessments");
    return res.data;
  },

  get: async (assessmentId: string): Promise<AssessmentResponse> => {
    const res = await apiClient.get(`/assessments/${assessmentId}`);
    return res.data;
  },

  analytics: async (assessmentId: string): Promise<AnalyticsResponse> => {
    const res = await apiClient.get(`/assessments/${assessmentId}/analytics`);
    return res.data;
  },

  myAttempts: async (): Promise<{ items: AttemptListItem[]; total: number }> => {
    const res = await apiClient.get("/assessments/me");
    return res.data;
  },

  start: async (assessmentId: string): Promise<AttemptStartResponse> => {
    const res = await apiClient.post(`/assessments/${assessmentId}/start`);
    return res.data;
  },

  state: async (attemptId: string): Promise<AttemptState> => {
    const res = await apiClient.get(`/assessments/attempts/${attemptId}`);
    return res.data;
  },

  answer: async (
    attemptId: string,
    questionId: string,
    answer: Record<string, unknown>,
    timeTakenSeconds?: number,
  ): Promise<AnswerResultResponse> => {
    const res = await apiClient.post(`/assessments/${attemptId}/answer`, {
      question_id: questionId,
      answer,
      time_taken_seconds: timeTakenSeconds,
    });
    return res.data;
  },

  runCode: async (
    attemptId: string,
    questionId: string,
    code: string,
    language = "python",
  ): Promise<CodeRunResponse> => {
    const res = await apiClient.post(`/assessments/${attemptId}/code/run`, {
      question_id: questionId,
      language,
      code,
    });
    return res.data;
  },

  submitCode: async (
    attemptId: string,
    questionId: string,
    code: string,
    language = "python",
  ): Promise<AnswerResultResponse> => {
    const res = await apiClient.post(`/assessments/${attemptId}/code/submit`, {
      question_id: questionId,
      language,
      code,
    });
    return res.data;
  },

  integrityEvent: async (attemptId: string, eventType: string, detail?: string): Promise<void> => {
    await apiClient.post(`/assessments/${attemptId}/integrity`, {
      event_type: eventType,
      detail,
    });
  },

  submitAttempt: async (attemptId: string): Promise<ResultResponse> => {
    const res = await apiClient.post(`/assessments/${attemptId}/submit`);
    return res.data;
  },

  result: async (attemptId: string): Promise<ResultResponse> => {
    const res = await apiClient.get(`/assessments/${attemptId}/result`);
    return res.data;
  },
};
