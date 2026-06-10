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

export const runPipeline = () =>
  api.post<PipelineRun>('/scheduler/run-pipeline').then(r => r.data)

export const getPipelineRuns = (limit = 10) =>
  api.get<PipelineRun[]>('/scheduler/pipeline-runs', { params: { limit } }).then(r => r.data)
