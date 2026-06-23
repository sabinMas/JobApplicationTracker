import axios from 'axios'

// Get API URL from environment variable or default to relative path
const apiBaseUrl = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

export const api = axios.create({
  baseURL: apiBaseUrl,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Job {
  id: number
  title: string
  company: string
  location?: string
  job_type?: string
  source?: string
  source_url?: string
  apply_url?: string
  description?: string
  requirements?: string
  salary_range?: string
  posted_date?: string
  status: string
  notes?: string
  score?: number
  score_reasoning?: string
  created_at?: string
}

export interface Application {
  id: number
  job_id: number
  applied_date?: string
  status: string
  ats_platform?: string
  ats_tracking_url?: string
  tailored_resume_id?: number
  tailored_cover_letter_id?: number
  automation_log?: AutomationLogEntry[]
  notes?: string
  created_at?: string
}

export interface AutomationLogEntry {
  step: string
  status: string
  message: string
  timestamp: string
}

export interface Profile {
  id?: number
  full_name?: string
  email?: string
  phone?: string
  location?: string
  linkedin_url?: string
  github_url?: string
  portfolio_url?: string
  summary?: string
  skills?: string[]
  experience?: ExperienceEntry[]
  education?: EducationEntry[]
  certifications?: CertificationEntry[]
}

export interface ExperienceEntry {
  company: string
  title: string
  start?: string
  end?: string
  bullets?: string[]
}

export interface EducationEntry {
  school: string
  degree?: string
  field?: string
  start?: string
  end?: string
  gpa?: string
}

export interface CertificationEntry {
  name: string
  issuer?: string
  date?: string
}

export interface Document {
  id: number
  type: string
  variant: string
  job_id?: number
  filename: string
  file_path: string
  created_at?: string
}

export interface JobsResponse {
  total: number
  skip: number
  limit: number
  jobs: Job[]
}

// ─── API calls ────────────────────────────────────────────────────────────────

// Jobs
export const getJobs = (params?: Record<string, string>) =>
  api.get<JobsResponse>('/jobs', { params }).then(r => r.data.jobs)

export const createJob = (data: Partial<Job>) =>
  api.post<Job>('/jobs', data).then(r => r.data)

export const scrapeJob = (url: string) =>
  api.post<Job>('/jobs/scrape', { url }).then(r => r.data)

export const updateJob = (id: number, data: Partial<Job>) =>
  api.put<Job>(`/jobs/${id}`, data).then(r => r.data)

export const deleteJob = (id: number) =>
  api.delete(`/jobs/${id}`).then(r => r.data)

export const getGreenhouseJobs = (slug: string) =>
  api.get<Job[]>(`/jobs/greenhouse/${slug}`).then(r => r.data)

// Applications
export const getApplications = () =>
  api.get<Application[]>('/applications').then(r => r.data)

export const createApplication = (data: { job_id: number; notes?: string }) =>
  api.post<Application>('/applications', data).then(r => r.data)

export const updateApplication = (id: number, data: Partial<Application>) =>
  api.put<Application>(`/applications/${id}`, data).then(r => r.data)

export const deleteApplication = (id: number) =>
  api.delete(`/applications/${id}`).then(r => r.data)

// Profile
export const getProfile = () =>
  api.get<Profile>('/profile').then(r => r.data)

export const updateProfile = (data: Partial<Profile>) =>
  api.put<Profile>('/profile', data).then(r => r.data)

export const extractProfileFromResume = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<{
    extracted: Profile
    merged: Profile | null
    document_id: number
    changes: string[]
  }>('/profile/extract', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

// Documents
export const getDocuments = () =>
  api.get<Document[]>('/documents').then(r => r.data)

export const uploadDocument = (file: File, doc_type: string) => {
  const form = new FormData()
  form.append('file', file)
  form.append('doc_type', doc_type)
  return api.post<Document>('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

export const deleteDocument = (id: number) =>
  api.delete(`/documents/${id}`).then(r => r.data)

// AI
export const tailorDocuments = (job_id: number) =>
  api.post('/ai/tailor', { job_id }).then(r => r.data)

// Automation
export const startAutomation = (application_id: number) =>
  api.post<{ session_id: string; status: string; message: string }>(
    '/automation/start', { application_id }
  ).then(r => r.data)

export const pauseAutomation = (session_id: string) =>
  api.post(`/automation/pause/${session_id}`).then(r => r.data)

export const resumeAutomation = (session_id: string) =>
  api.post(`/automation/resume/${session_id}`).then(r => r.data)

export const stopAutomation = (session_id: string) =>
  api.post(`/automation/stop/${session_id}`).then(r => r.data)

export const fillForm = (session_id: string) =>
  api.post(`/automation/fill/${session_id}`).then(r => r.data)

export const uploadDocs = (session_id: string, application_id: number) =>
  api.post(`/automation/upload-docs/${session_id}`, null, {
    params: { application_id },
  }).then(r => r.data)
