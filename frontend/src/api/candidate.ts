import apiClient from "./client";
import type {
  CandidateDashboard,
  CandidateIntelligence,
  CandidateProfile,
  Certification,
  CertificationFormData,
  ChangePasswordRequest,
  Education,
  EducationFormData,
  Experience,
  ExperienceFormData,
  CandidateSkill,
  CandidateSkillFormData,
  Language,
  LanguageFormData,
  Notification,
  ProfileCompletion,
  Project,
  ProjectFormData,
  Resume,
  ResumeAnalysis,
  ResumeCompareReport,
  ResumeDetail,
  ResumeIntelligenceReport,
  ResumeStatus,
  ResumeUploadResponse,
  ResumeVersion,
  SyncDiffResponse,
  SyncActionResult,
  UpdateEmailRequest,
  Skill,
} from "../types/candidate";

export const candidateApi = {
  // Dashboard
  getDashboard: () =>
    apiClient.get<CandidateDashboard>("/candidates/dashboard").then((r) => r.data),

  // Profile
  getProfile: () =>
    apiClient.get<CandidateProfile>("/candidates/profile").then((r) => r.data),

  updateProfile: (data: Partial<CandidateProfile>) =>
    apiClient.put<CandidateProfile>("/candidates/profile", data).then((r) => r.data),

  getProfileCompletion: () =>
    apiClient.get<ProfileCompletion>("/candidates/profile/completion").then((r) => r.data),

  // Avatar
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient
      .post<CandidateProfile>("/candidates/avatar", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  removeAvatar: () =>
    apiClient.delete<CandidateProfile>("/candidates/avatar").then((r) => r.data),

  // Education
  listEducation: () =>
    apiClient.get<Education[]>("/candidates/education").then((r) => r.data),

  createEducation: (data: EducationFormData) =>
    apiClient.post<Education>("/candidates/education", data).then((r) => r.data),

  updateEducation: (id: string, data: Partial<EducationFormData>) =>
    apiClient.put<Education>(`/candidates/education/${id}`, data).then((r) => r.data),

  deleteEducation: (id: string) =>
    apiClient.delete(`/candidates/education/${id}`).then((r) => r.data),

  // Experience
  listExperience: () =>
    apiClient.get<Experience[]>("/candidates/experience").then((r) => r.data),

  createExperience: (data: ExperienceFormData) =>
    apiClient.post<Experience>("/candidates/experience", data).then((r) => r.data),

  updateExperience: (id: string, data: Partial<ExperienceFormData>) =>
    apiClient.put<Experience>(`/candidates/experience/${id}`, data).then((r) => r.data),

  deleteExperience: (id: string) =>
    apiClient.delete(`/candidates/experience/${id}`).then((r) => r.data),

  // Skills
  listSkills: () =>
    apiClient.get<CandidateSkill[]>("/candidates/skills").then((r) => r.data),

  addSkill: (data: CandidateSkillFormData) =>
    apiClient.post<CandidateSkill>("/candidates/skills", data).then((r) => r.data),

  updateSkill: (skillId: number, data: Partial<CandidateSkillFormData>) =>
    apiClient.put<CandidateSkill>(`/candidates/skills/${skillId}`, data).then((r) => r.data),

  removeSkill: (skillId: number) =>
    apiClient.delete(`/candidates/skills/${skillId}`).then((r) => r.data),

  searchSkills: (query: string) =>
    apiClient.get<Skill[]>(`/candidates/skills/search?q=${query}`).then((r) => r.data),

  // Projects
  listProjects: () =>
    apiClient.get<Project[]>("/candidates/projects").then((r) => r.data),

  createProject: (data: ProjectFormData) =>
    apiClient.post<Project>("/candidates/projects", data).then((r) => r.data),

  updateProject: (id: string, data: Partial<ProjectFormData>) =>
    apiClient.put<Project>(`/candidates/projects/${id}`, data).then((r) => r.data),

  deleteProject: (id: string) =>
    apiClient.delete(`/candidates/projects/${id}`).then((r) => r.data),

  // Certifications
  listCertifications: () =>
    apiClient.get<Certification[]>("/candidates/certifications").then((r) => r.data),

  createCertification: (data: CertificationFormData) =>
    apiClient.post<Certification>("/candidates/certifications", data).then((r) => r.data),

  updateCertification: (id: string, data: Partial<CertificationFormData>) =>
    apiClient.put<Certification>(`/candidates/certifications/${id}`, data).then((r) => r.data),

  deleteCertification: (id: string) =>
    apiClient.delete(`/candidates/certifications/${id}`).then((r) => r.data),

  // Languages
  listLanguages: () =>
    apiClient.get<Language[]>("/candidates/languages").then((r) => r.data),

  createLanguage: (data: LanguageFormData) =>
    apiClient.post<Language>("/candidates/languages", data).then((r) => r.data),

  updateLanguage: (id: string, data: Partial<LanguageFormData>) =>
    apiClient.put<Language>(`/candidates/languages/${id}`, data).then((r) => r.data),

  deleteLanguage: (id: string) =>
    apiClient.delete(`/candidates/languages/${id}`).then((r) => r.data),

  // Notifications
  listNotifications: () =>
    apiClient.get<Notification[]>("/candidates/notifications").then((r) => r.data),

  markNotificationRead: (id: string) =>
    apiClient.put<Notification>(`/candidates/notifications/${id}/read`).then((r) => r.data),

  markAllNotificationsRead: () =>
    apiClient.put("/candidates/notifications/read-all").then((r) => r.data),

  deleteNotification: (id: string) =>
    apiClient.delete(`/candidates/notifications/${id}`).then((r) => r.data),

  getUnreadCount: () =>
    apiClient.get<{ unread_count: number }>("/candidates/notifications/unread-count").then((r) => r.data),

  // Resumes
  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient
      .post<ResumeUploadResponse>("/candidates/resume/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  listResumes: () =>
    apiClient.get<Resume[]>("/candidates/resumes").then((r) => r.data),

  getResume: (id: string) =>
    apiClient.get<ResumeDetail>(`/candidates/resume/${id}`).then((r) => r.data),

  deleteResume: (id: string) =>
    apiClient.delete(`/candidates/resume/${id}`).then((r) => r.data),

  setPrimaryResume: (resumeId: string) =>
    apiClient.put<ResumeUploadResponse>("/candidates/resume/primary", { resume_id: resumeId }).then((r) => r.data),

  getResumeStatus: (id: string) =>
    apiClient.get<ResumeStatus>(`/candidates/resume/${id}/status`).then((r) => r.data),

  getParsedResumeData: (id: string) =>
    apiClient.get(`/candidates/resume/${id}/parsed`).then((r) => r.data),

  getResumeAnalysis: (id: string) =>
    apiClient.get<ResumeAnalysis>(`/candidates/resume/${id}/analysis`).then((r) => r.data),

  // Resume Intelligence (Phase 3)
  getResumeIntelligence: (id: string) =>
    apiClient.get<ResumeIntelligenceReport>(`/candidates/resume/${id}/intelligence`).then((r) => r.data),

  getResumeScores: (id: string) =>
    apiClient.get(`/candidates/resume/${id}/intelligence/scores`).then((r) => r.data),

  getATSReport: (id: string) =>
    apiClient.get(`/candidates/resume/${id}/intelligence/ats`).then((r) => r.data),

  getSkillAnalysis: (id: string) =>
    apiClient.get(`/candidates/resume/${id}/intelligence/skills`).then((r) => r.data),

  getKeywordAnalysis: (id: string) =>
    apiClient.get(`/candidates/resume/${id}/intelligence/keywords`).then((r) => r.data),

  getRecommendations: (id: string) =>
    apiClient.get(`/candidates/resume/${id}/intelligence/recommendations`).then((r) => r.data),

  compareResumeIntelligence: (id: string) =>
    apiClient.get<ResumeCompareReport>(`/candidates/resume/${id}/intelligence/compare`).then((r) => r.data),

  // Candidate Intelligence
  getIntelligence: () =>
    apiClient.get<CandidateIntelligence>("/candidates/intelligence").then((r) => r.data),

  // Profile Sync
  getSyncDiff: (resumeId: string) =>
    apiClient.get<SyncDiffResponse>(`/candidates/resume/${resumeId}/sync-diff`).then((r) => r.data),

  acceptSync: (resumeId: string, section: string, itemIndex?: number, field?: string) =>
    apiClient.post<SyncActionResult>("/candidates/resume/sync-accept", { resume_id: resumeId, section, item_index: itemIndex, field }).then((r) => r.data),

  rejectSync: (resumeId: string, section: string, itemIndex?: number, field?: string) =>
    apiClient.post<SyncActionResult>("/candidates/resume/sync-reject", { resume_id: resumeId, section, item_index: itemIndex, field }).then((r) => r.data),

  mergeSync: (resumeId: string, section: string, itemIndex?: number, field?: string) =>
    apiClient.post<SyncActionResult>("/candidates/resume/sync-merge", { resume_id: resumeId, section, item_index: itemIndex, field }).then((r) => r.data),

  retryResume: (id: string) =>
    apiClient.post<ResumeDetail>(`/candidates/resume/${id}/retry`).then((r) => r.data),

  downloadResume: (id: string) =>
    apiClient.get(`/candidates/resume/${id}/download`, { responseType: "blob" }).then((r) => r.data),

  // Resume Versions
  getResumeVersions: () =>
    apiClient.get<ResumeVersion[]>("/candidates/resume/versions").then((r) => r.data),

  compareResumeVersion: (versionId: string) =>
    apiClient.get(`/candidates/resume/versions/${versionId}`).then((r) => r.data),

  // Settings
  changePassword: (data: ChangePasswordRequest) =>
    apiClient.put("/candidates/settings/password", data).then((r) => r.data),

  updateEmail: (data: UpdateEmailRequest) =>
    apiClient.put("/candidates/settings/email", data).then((r) => r.data),

  deleteAccount: () =>
    apiClient.delete("/candidates/settings/account").then((r) => r.data),
};
