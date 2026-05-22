import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProfile, updateProfile, extractProfileFromResume, Profile } from '../api/client'

export const useProfile = () => {
  return useQuery({
    queryKey: ['profile'],
    queryFn: () => getProfile(),
  })
}

export const useUpdateProfile = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Profile>) => updateProfile(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profile'] }),
  })
}

export const useExtractProfile = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => extractProfileFromResume(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['profile'] }),
  })
}
