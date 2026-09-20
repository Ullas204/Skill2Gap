import apiClient from "./client";
import type {
  InterviewGenerateRequest,
  InterviewGenerateResponse,
  InterviewDetail,
  InterviewListItem,
  InterviewDashboard,
  InterviewAnalytics,
  MockInterviewStartResponse,
  AnswerSubmitResponse,
  InterviewCompleteResponse,
  InterviewScheduleRequest,
  ScorecardCreateRequest,
  CodingSubmissionResponse,
} from "../types/interview";

export const interviewApi = {
  generateQuestions: async (data: InterviewGenerateRequest): Promise<InterviewGenerateResponse> => {
    const res = await apiClient.post("/interview/generate", data);
    return res.data;
  },

  scheduleInterview: async (data: InterviewScheduleRequest): Promise<{ message: string; interview_id: string; status: string }> => {
    const res = await apiClient.post("/interview/schedule", data);
    return res.data;
  },

  startMockInterview: async (jobId: string): Promise<MockInterviewStartResponse> => {
    const res = await apiClient.post("/interview/mock/start", { interview_id: jobId });
    return res.data;
  },

  submitAnswer: async (questionId: string, answerText: string, timeTaken?: number): Promise<AnswerSubmitResponse> => {
    const res = await apiClient.post("/interview/mock/answer", {
      question_id: questionId,
      answer_text: answerText,
      time_taken_seconds: timeTaken,
    });
    return res.data;
  },

  completeMockInterview: async (interviewId: string): Promise<InterviewCompleteResponse> => {
    const res = await apiClient.post("/interview/mock/complete", { interview_id: interviewId });
    return res.data;
  },

  listInterviews: async (): Promise<{ items: InterviewListItem[]; total: number }> => {
    const res = await apiClient.get("/interview/list");
    return res.data;
  },

  getInterviewDetail: async (interviewId: string): Promise<InterviewDetail> => {
    const res = await apiClient.get(`/interview/${interviewId}`);
    return res.data;
  },

  evaluateInterview: async (interviewId: string): Promise<Record<string, unknown>> => {
    const res = await apiClient.post(`/interview/${interviewId}/evaluate`);
    return res.data;
  },

  getScorecard: async (interviewId: string): Promise<Record<string, unknown>> => {
    const res = await apiClient.get(`/interview/${interviewId}/scorecard`);
    return res.data;
  },

  createScorecard: async (interviewId: string, data: ScorecardCreateRequest): Promise<Record<string, unknown>> => {
    const res = await apiClient.post(`/interview/${interviewId}/scorecard`, data);
    return res.data;
  },

  addNotes: async (interviewId: string, notes: string): Promise<{ message: string }> => {
    const res = await apiClient.post(`/interview/${interviewId}/notes`, { notes });
    return res.data;
  },

  getCandidateScorecards: async (candidateId: string): Promise<Record<string, unknown>[]> => {
    const res = await apiClient.get(`/interview/scorecard/${candidateId}`);
    return res.data;
  },

  getDashboard: async (): Promise<InterviewDashboard> => {
    const res = await apiClient.get("/interview/dashboard");
    return res.data;
  },

  getAnalytics: async (): Promise<InterviewAnalytics> => {
    const res = await apiClient.get("/interview/analytics");
    return res.data;
  },

  generateCodingAssessment: async (interviewId: string, category: string, difficulty: string, count: number): Promise<{ assessments: Record<string, unknown>[]; total: number }> => {
    const res = await apiClient.post("/interview/coding/generate", {
      interview_id: interviewId,
      category,
      difficulty,
      count,
    });
    return res.data;
  },

  submitCodingSolution: async (assessmentId: string, solution: string): Promise<CodingSubmissionResponse> => {
    const res = await apiClient.post("/interview/coding/submit", {
      assessment_id: assessmentId,
      solution,
    });
    return res.data;
  },
};
