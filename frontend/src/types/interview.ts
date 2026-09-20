export interface InterviewQuestion {
  id: string;
  question_text: string;
  category: string;
  difficulty: string;
  order_index: number;
  context: Record<string, unknown> | null;
}

export interface InterviewEvaluation {
  id: string;
  technical_accuracy: number;
  completeness: number;
  communication: number;
  problem_solving: number;
  confidence: number;
  relevance: number;
  overall_score: number;
  feedback: string | null;
  improvement_suggestions: string[] | null;
  follow_up_questions: string[] | null;
}

export interface InterviewAnswer {
  id: string;
  answer_text: string;
  time_taken_seconds: number | null;
  evaluation: InterviewEvaluation | null;
}

export interface QuestionWithAnswer extends InterviewQuestion {
  answer: InterviewAnswer | null;
}

export interface InterviewScorecard {
  id: string;
  interview_id: string;
  technical_skills: number;
  communication: number;
  teamwork: number;
  leadership: number;
  problem_solving: number;
  culture_fit: number;
  learning_ability: number;
  overall_score: number;
  recommendation: string;
  hiring_confidence: number;
  recruiter_notes: string | null;
  ai_summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface InterviewDetail {
  id: string;
  job_id: string;
  job_title: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  recruiter_id: string | null;
  recruiter_name: string;
  interview_type: string;
  status: string;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_minutes: number | null;
  total_questions: number;
  questions_answered: number;
  questions: QuestionWithAnswer[];
  scorecard: InterviewScorecard | null;
  created_at: string;
  updated_at: string;
}

export interface InterviewListItem {
  id: string;
  job_id: string;
  job_title: string;
  candidate_id: string;
  candidate_name: string;
  interview_type: string;
  status: string;
  scheduled_at: string | null;
  completed_at: string | null;
  total_questions: number;
  questions_answered: number;
  overall_score: number | null;
  created_at: string;
}

export interface InterviewGenerateRequest {
  job_id: string;
  categories?: string[];
  difficulty?: string;
  count?: number;
  candidate_id?: string;
}

export interface InterviewGenerateResponse {
  interview_id: string;
  questions: InterviewQuestion[];
  total_questions: number;
  categories: string[];
  difficulty: string;
}

export interface MockInterviewStartResponse {
  interview_id: string;
  job_id: string;
  job_title: string;
  first_question: InterviewQuestion;
  total_questions: number;
  message: string;
}

export interface AnswerSubmitResponse {
  answer_id: string;
  evaluation: InterviewEvaluation;
  next_question: InterviewQuestion | null;
  questions_remaining: number;
}

export interface InterviewCompleteResponse {
  interview_id: string;
  overall_score: number;
  strong_areas: string[];
  weak_areas: string[];
  improvement_suggestions: string[];
  feedback_summary: string;
}

export interface InterviewDashboard {
  total_interviews: number;
  mock_interviews?: number;
  scheduled_interviews?: number;
  upcoming_interviews: number;
  completed_interviews?: number;
  average_score: number;
  recent_interviews?: InterviewListItem[];
  upcoming?: InterviewListItem[];
  recent_scores?: Record<string, unknown>[];
  score_distribution?: Record<string, number>;
  category_performance?: Record<string, number>;
}

export interface InterviewAnalytics {
  total_interviews: number;
  completion_rate: number;
  average_score: number;
  median_score: number;
  score_distribution: Record<string, number>;
  category_averages: Record<string, number>;
  difficulty_distribution: Record<string, number>;
  recommendation_breakdown: Record<string, number>;
  skill_performance: Record<string, number>;
  hiring_prediction: Record<string, number>;
  trends: Record<string, unknown>[];
}

export interface CodingAssessment {
  id: string;
  problem_title: string;
  problem_description: string;
  difficulty: string;
  category: string;
  candidate_solution: string | null;
  is_correct: boolean | null;
  score: number;
}

export interface CodingSubmissionResponse {
  assessment_id: string;
  is_correct: boolean;
  score: number;
  feedback: string;
  expected_approach: string;
}

export interface InterviewScheduleRequest {
  job_id: string;
  candidate_id: string;
  scheduled_at: string;
  duration_minutes?: number;
  categories?: string[];
  difficulty?: string;
  question_count?: number;
}

export interface ScorecardCreateRequest {
  technical_skills: number;
  communication: number;
  teamwork: number;
  leadership: number;
  problem_solving: number;
  culture_fit: number;
  learning_ability: number;
  recommendation: string;
  hiring_confidence: number;
  recruiter_notes?: string;
}

export type QuestionCategory =
  | "technical"
  | "behavioral"
  | "hr"
  | "situational"
  | "coding"
  | "system_design"
  | "problem_solving";

export type InterviewStatus = "scheduled" | "in_progress" | "completed" | "cancelled";

export type InterviewType = "mock" | "recruiter_scheduled";

export const CATEGORY_LABELS: Record<QuestionCategory, string> = {
  technical: "Technical",
  behavioral: "Behavioral",
  hr: "HR",
  situational: "Situational",
  coding: "Coding",
  system_design: "System Design",
  problem_solving: "Problem Solving",
};

export const DIFFICULTY_COLORS: Record<string, string> = {
  easy: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  hard: "bg-red-100 text-red-700",
};

export const STATUS_COLORS: Record<string, string> = {
  scheduled: "bg-blue-100 text-blue-700",
  in_progress: "bg-yellow-100 text-yellow-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-500",
};
