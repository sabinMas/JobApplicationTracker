import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getJobs, createJob, updateJob, deleteJob, scrapeJob, Job } from '../api/client'

export const useJobs = (filters?: Record<string, string>) => {
  return useQuery({
    queryKey: ['jobs', filters],
    queryFn: () => getJobs(filters),
  })
}

export const useCreateJob = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createJob,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export const useScrapeJob = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (url: string) => scrapeJob(url),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export const useUpdateJob = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Job> }) => updateJob(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export const useDeleteJob = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: deleteJob,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}
