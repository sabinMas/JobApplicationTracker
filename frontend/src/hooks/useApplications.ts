import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getApplications, createApplication, updateApplication, deleteApplication, Application } from '../api/client'

export const useApplications = () => {
  return useQuery({
    queryKey: ['applications'],
    queryFn: getApplications,
  })
}

export const useCreateApplication = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createApplication,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['applications'] }),
  })
}

export const useUpdateApplication = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Application> }) =>
      updateApplication(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['applications'] }),
  })
}

export const useDeleteApplication = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: deleteApplication,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['applications'] }),
  })
}
