import apiClient from "./client";
import type {
  CandidateJobDashboard,
  Job,
  JobApplication,
  JobFormData,
  JobListItem,
  JobSearchResult,
  SavedJob,
  RecruiterDashboard,
  RecruiterNote,
} from "../types/jobs";

export const recruiterJobApi = {
  getDashboard: () =>
    apiClient.get<RecruiterDashboard>("/recruiter/jobs/dashboard").then((r) => r.data),

  listJobs: () =>
    apiClient.get<JobListItem[]>("/recruiter/jobs").then((r) => r.data),

  getJob: (id: string) =>
    apiClient.get<Job>(`/recruiter/jobs/${id}`).then((r) => r.data),

  createJob: (data: JobFormData) =>
    apiClient.post<Job>("/recruiter/jobs", data).then((r) => r.data),

  updateJob: (id: string, data: Partial<JobFormData>) =>
    apiClient.put<Job>(`/recruiter/jobs/${id}`, data).then((r) => r.data),

  deleteJob: (id: string) =>
    apiClient.delete(`/recruiter/jobs/${id}`).then((r) => r.data),

  changeStatus: (id: string, status: string) =>
    apiClient.patch<Job>(`/recruiter/jobs/${id}/status?status=${status}`).then((r) => r.data),

  getApplications: (jobId: string) =>
    apiClient.get<JobApplication[]>(`/recruiter/jobs/${jobId}/applications`).then((r) => r.data),

  updateApplicationStatus: (applicationId: string, status: string) =>
    apiClient.patch(`/recruiter/jobs/applications/${applicationId}/status`, { status }).then((r) => r.data),

  addNote: (applicationId: string, note: string) =>
    apiClient.post<RecruiterNote>(`/recruiter/jobs/applications/${applicationId}/notes`, { note }).then((r) => r.data),
};

export const candidateJobApi = {
  getDashboard: () =>
    apiClient.get<CandidateJobDashboard>("/candidate/jobs/dashboard").then((r) => r.data),

  searchJobs: (params: {
    q?: string;
    employment_type?: string;
    location?: string;
    salary_min?: number;
    salary_max?: number;
    skills?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }) =>
    apiClient.get<JobSearchResult>("/candidate/jobs/search", { params }).then((r) => r.data),

  getJob: (id: string) =>
    apiClient.get<Job>(`/candidate/jobs/${id}`).then((r) => r.data),

  apply: (jobId: string, resumeId?: string, coverLetter?: string) =>
    apiClient
      .post<JobApplication>("/candidate/jobs/apply", {
        job_id: jobId,
        resume_id: resumeId,
        cover_letter: coverLetter,
      })
      .then((r) => r.data),

  getMyApplications: () =>
    apiClient.get<JobApplication[]>("/candidate/jobs/applications").then((r) => r.data),

  withdrawApplication: (id: string) =>
    apiClient.post(`/candidate/jobs/applications/${id}/withdraw`).then((r) => r.data),

  saveJob: (jobId: string) =>
    apiClient.post<SavedJob>("/candidate/jobs/saved", null, { params: { job_id: jobId } }).then((r) => r.data),

  unsaveJob: (jobId: string) =>
    apiClient.delete(`/candidate/jobs/saved/${jobId}`).then((r) => r.data),

  getSavedJobs: () =>
    apiClient.get<JobListItem[]>("/candidate/jobs/saved").then((r) => r.data),
};
