import { api } from './client'

export interface PipelineRun {
  id: number
  trigger: string
  status: string
  started_at?: string
  finished_at?: string
  jobs_discovered: number
  jobs_scored: number
  jobs_enriched: number
  applications_prepared: number
  applications_submitted: number
  applications_queued_for_review: number
  errors?: { stage: string; message: string; timestamp: string }[]
}

export interface PipelineJobOut {
  id: number
  title: string
  company: string
  location?: string
  source: string
  apply_url?: string
  score?: number
  score_reasoning?: string
  score_strengths?: string[]
  score_concerns?: string[]
  pipeline_stage: string
  enrichment_data?: string
  pipeline_data?: Record<string, any>
  created_at?: string
}

export interface PipelineVisualizerOut {
  total_jobs: number
  by_stage: Record<string, number>
  jobs_by_stage: Record<string, PipelineJobOut[]>
  timestamp: string
}

export interface ApplicationReviewData {
  application_id: number
  application_status: string
  job: PipelineJobOut & {
    description?: string
    requirements?: string
    salary_range?: string
    posted_date?: string
  }
  tailored_resume: {
    content?: string
    path?: string
  }
  tailored_cover_letter: {
    content?: string
    path?: string
  }
  created_at?: string
}

export const runPipeline = () =>
  api.post<PipelineRun>('/scheduler/run-pipeline').then(r => r.data)

export const getPipelineRuns = (limit = 10) =>
  api.get<PipelineRun[]>('/scheduler/pipeline-runs', { params: { limit } }).then(r => r.data)

// Pipeline Visualizer API
export const getPipelineJobs = (stage?: string) =>
  api
    .get<PipelineVisualizerOut>('/pipeline-visualizer/jobs', {
      params: { ...(stage && { stage }) },
    })
    .then(r => r.data)

export const getPipelineStats = () =>
  api
    .get('/pipeline-visualizer/stats')
    .then(r => r.data)

export const getJobsForReview = (skip: number = 0, limit: number = 10) =>
  api
    .get<PipelineJobOut[]>('/pipeline-visualizer/jobs-for-review', {
      params: { skip, limit },
    })
    .then(r => r.data)

export const reviewJob = (
  jobId: number,
  action: 'approve' | 'reject' | 'edit',
  editedCoverLetter?: string
) =>
  api
    .post('/pipeline-visualizer/review-job', {
      job_id: jobId,
      action,
      edited_cover_letter: editedCoverLetter,
    })
    .then(r => r.data)

// New endpoints for full application review
export const getApplicationForReview = (applicationId: number) =>
  api
    .get<ApplicationReviewData>(`/pipeline-visualizer/application/${applicationId}/full-review`)
    .then(r => r.data)

export const approveAndSubmitApplication = (applicationId: number) =>
  api
    .post(`/pipeline-visualizer/application/${applicationId}/approve-and-submit`, {})
    .then(r => r.data)

export const rejectApplication = (applicationId: number, rejectionReason?: string) =>
  api
    .post(`/pipeline-visualizer/application/${applicationId}/reject`, {}, {
      params: { ...(rejectionReason && { rejection_reason: rejectionReason }) },
    })
    .then(r => r.data)

export const getApplicationsInReview = (limit: number = 20, offset: number = 0) =>
  api
    .get('/pipeline-visualizer/applications-in-review', {
      params: { limit, offset },
    })
    .then(r => r.data)
