export interface Job {
  id: string;
  recruiter_id: string;
  title: string;
  company: string;
  department: string | null;
  employment_type: string;
  experience_required: string | null;
  education_required: string | null;
  required_skills: string[];
  preferred_skills: string[] | null;
  location: string;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  description: string;
  benefits: string | null;
  application_deadline: string | null;
  status: string;
  is_archived: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface JobListItem {
  id: string;
  recruiter_id: string;
  title: string;
  company: string;
  department: string | null;
  employment_type: string;
  location: string;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  status: string;
  application_deadline: string | null;
  application_count: number;
  created_at: string;
  updated_at: string;
}

export interface JobFormData {
  title: string;
  company: string;
  department?: string;
  employment_type: string;
  experience_required?: string;
  education_required?: string;
  required_skills: string[];
  preferred_skills: string[];
  location: string;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string;
  description: string;
  benefits?: string;
  application_deadline?: string | null;
  status?: string;
}

export interface JobApplication {
  id: string;
  job_id: string;
  candidate_id: string;
  resume_id: string | null;
  cover_letter: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  candidate_name?: string;
  candidate_email?: string;
  job_title?: string;
  company?: string;
  location?: string;
  employment_type?: string;
  recruiter_notes?: RecruiterNote[];
}

export interface RecruiterNote {
  id: string;
  job_application_id: string;
  recruiter_id: string;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface SavedJob {
  job_id: string;
  created_at: string;
}

export interface JobSearchResult {
  items: JobListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RecruiterDashboard {
  total_jobs: number;
  published_jobs: number;
  draft_jobs: number;
  closed_jobs: number;
  total_applications: number;
  recent_applications: RecentApplication[];
}

export interface RecentApplication {
  id: string;
  job_title: string;
  candidate_name: string;
  status: string;
  created_at: string;
}

export interface CandidateJobDashboard {
  total_applications: number;
  saved_jobs: number;
  status_breakdown: Record<string, number>;
  recent_applications: {
    id: string;
    job_id: string;
    status: string;
    created_at: string;
  }[];
}
