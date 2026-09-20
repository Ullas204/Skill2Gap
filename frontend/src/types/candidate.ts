export interface CandidateProfile {
  id: string;
  user_id: string;
  phone: string | null;
  date_of_birth: string | null;
  gender: string | null;
  location: string | null;
  nationality: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  website_url: string | null;
  bio: string | null;
  current_role: string | null;
  avatar_url: string | null;
  profile_completion: number;
  created_at: string;
  updated_at: string;
}

export interface CandidateDashboard {
  profile: CandidateProfile;
  full_name: string;
  email: string;
  total_resumes: number;
  total_notifications: number;
  unread_notifications: number;
  recent_activity: ActivityItem[];
}

export interface ActivityItem {
  type: string;
  title: string;
  message: string;
  created_at: string;
}

export interface Education {
  id: string;
  profile_id: string;
  institution: string;
  degree: string;
  branch: string | null;
  specialization: string | null;
  cgpa: number | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  created_at: string;
  updated_at: string;
}

export interface EducationFormData {
  institution: string;
  degree: string;
  branch?: string;
  specialization?: string;
  cgpa?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  is_current?: boolean;
}

export interface Experience {
  id: string;
  profile_id: string;
  company: string;
  job_title: string;
  employment_type: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  responsibilities: string | null;
  technologies: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExperienceFormData {
  company: string;
  job_title: string;
  employment_type?: string;
  start_date?: string | null;
  end_date?: string | null;
  is_current?: boolean;
  responsibilities?: string;
  technologies?: string;
}

export interface Skill {
  id: number;
  name: string;
  category: string;
}

export interface CandidateSkill {
  profile_id: string;
  skill_id: number;
  proficiency: string;
  years_of_experience: number | null;
  skill: Skill | null;
  created_at: string;
  updated_at: string;
}

export interface CandidateSkillFormData {
  skill_id: number;
  proficiency?: string;
  years_of_experience?: number | null;
}

export interface Project {
  id: string;
  profile_id: string;
  title: string;
  description: string | null;
  technologies: string | null;
  github_link: string | null;
  live_demo: string | null;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectFormData {
  title: string;
  description?: string;
  technologies?: string;
  github_link?: string;
  live_demo?: string;
  start_date?: string | null;
  end_date?: string | null;
}

export interface Certification {
  id: string;
  profile_id: string;
  name: string;
  organization: string;
  issue_date: string | null;
  expiry_date: string | null;
  credential_id: string | null;
  credential_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface CertificationFormData {
  name: string;
  organization: string;
  issue_date?: string | null;
  expiry_date?: string | null;
  credential_id?: string;
  credential_url?: string;
}

export interface Language {
  id: string;
  profile_id: string;
  language: string;
  reading: string;
  writing: string;
  speaking: string;
  created_at: string;
  updated_at: string;
}

export interface LanguageFormData {
  language: string;
  reading?: string;
  writing?: string;
  speaking?: string;
}

export interface Notification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfileCompletion {
  completion_percentage: number;
  sections: Record<string, boolean>;
  missing_sections: string[];
  recommendations: string[];
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface UpdateEmailRequest {
  new_email: string;
}

export interface Resume {
  id: string;
  user_id: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  status: string;
  language: string | null;
  is_primary: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ResumeUploadResponse {
  id: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  status: string;
  is_primary: boolean;
  version: number;
  created_at: string;
}

export interface ResumeDetail {
  resume: Resume;
  parsed_data: ParsedData | null;
  analysis: ResumeAnalysis | null;
}

export interface ParsedData {
  id: string;
  resume_id: string;
  personal_info: Record<string, unknown> | null;
  education: Record<string, unknown>[] | null;
  experience: Record<string, unknown>[] | null;
  skills: Record<string, unknown>[] | null;
  projects: Record<string, unknown>[] | null;
  certifications: Record<string, unknown>[] | null;
  languages: Record<string, unknown>[] | null;
  summary?: string | null;
  resume_profile?: Record<string, unknown> | null;
  created_at: string;
}

export interface ResumeAnalysis {
  id: string;
  resume_id: string;
  quality_score: number;
  completeness_score: number;
  readability_score: number;
  professionalism_score: number;
  keyword_optimization_score: number;
  ats_score: number;
  missing_sections: string[] | null;
  recommendations: string[] | null;
  section_scores: Record<string, number> | null;
  keyword_analysis: Record<string, unknown> | null;
  formatting_issues: string[] | null;
  skill_analysis: Record<string, unknown> | null;
  industry_keywords: Record<string, unknown> | null;
  strengths: string[] | null;
  weaknesses: string[] | null;
  created_at: string;
}

export interface ResumeStatus {
  id: string;
  status: string;
  progress: number;
}

export interface SkillSummaryItem {
  name: string;
  category: string;
  proficiency: string | null;
  years: number | null;
}

export interface CandidateIntelligence {
  profile_id: string;
  total_experience_years: number;
  total_experience_months: number;
  highest_qualification: string | null;
  education_level: string;
  skill_summary: SkillSummaryItem[];
  skills_by_category: Record<string, string[]>;
  project_count: number;
  certification_count: number;
  language_count: number;
  profile_strength: number;
  missing_sections: string[];
  recommendations: string[];
}

export interface SyncDiffItem {
  section: string;
  field: string;
  parsed_value: string | null;
  profile_value: string | null;
  status: string;
}

export interface SyncActionResult {
  message: string;
  applied: number;
}

export interface SyncDiffResponse {
  resume_id: string;
  personal_info: SyncDiffItem[];
  education: SyncDiffItem[];
  experience: SyncDiffItem[];
  skills: SyncDiffItem[];
  projects: SyncDiffItem[];
  certifications: SyncDiffItem[];
  languages: SyncDiffItem[];
}

export interface ScoreDetail {
  score: number;
  max_score: number;
  label: string;
  description: string;
}

export interface ResumeIntelligenceScores {
  overall: ScoreDetail;
  completeness: ScoreDetail;
  readability: ScoreDetail;
  professionalism: ScoreDetail;
  keyword_optimization: ScoreDetail;
  ats_compatibility: ScoreDetail;
}

export interface SkillAnalysisReport {
  skill_names: string[];
  total_skills: number;
  categorized: Record<string, string[]>;
  duplicates: string[];
  missing_essential: string[];
  suggestions: string[];
}

export interface KeywordAnalysisReport {
  action_keywords_found: string[];
  action_keywords_missing: string[];
  total_action_keywords: number;
  matched_action_keywords: number;
  keyword_density: Record<string, number>;
}

export interface ATSReport {
  score: number;
  formatting_issues: string[];
  sections_valid: Record<string, boolean>;
  contact_info_found: Record<string, boolean>;
  has_email: boolean;
  has_phone: boolean;
  has_linkedin: boolean;
  has_github: boolean;
  resume_length: string;
  file_format_ok: boolean;
  section_count: number;
  action_verb_count: number;
  quantifiable_achievements: number;
}

export interface Recommendation {
  category: string;
  text: string;
  priority: string;
}

export interface IndustryKeywordSuggestions {
  category: string;
  matched: string[];
  suggested: string[];
}

export interface ResumeIntelligenceReport {
  resume_id: string;
  filename: string;
  scores: ResumeIntelligenceScores;
  strengths: string[];
  weaknesses: string[];
  recommendations: Recommendation[];
  skill_analysis: SkillAnalysisReport;
  keyword_analysis: KeywordAnalysisReport;
  ats_report: ATSReport;
  industry_keywords: Record<string, IndustryKeywordSuggestions>;
  generated_at: string;
}

export interface ResumeCompareItem {
  version: number;
  filename: string;
  scores: ResumeIntelligenceScores;
  strengths: string[];
  weaknesses: string[];
  total_skills: number;
  created_at: string;
}

export interface ResumeCompareReport {
  current: ResumeCompareItem;
  previous: ResumeCompareItem | null;
  score_changes: Record<string, number>;
  skills_added: string[];
  skills_removed: string[];
}

export interface ResumeVersion {
  id: string;
  version: number;
  original_filename: string;
  file_size: number;
  file_type: string;
  status: string;
  is_primary: boolean;
  created_at: string;
}
