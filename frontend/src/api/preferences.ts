import { api } from './client'

export interface SearchPreferences {
  id: number
  target_roles?: string[]
  niches?: string[]
  must_have_keywords?: string[]
  avoid_keywords?: string[]
  salary_floor?: number
  locations?: string[]
  remote_ok?: boolean
  seniority?: string
  job_types?: string[]
  min_score_to_apply?: number
  auto_submit_enabled?: boolean
  daily_application_limit?: number
  created_at?: string
  updated_at?: string
}

export type SearchPreferencesUpdate = Omit<SearchPreferences, 'id' | 'created_at' | 'updated_at'>

export const getPreferences = () =>
  api.get<SearchPreferences>('/profile/preferences').then(r => r.data)

export const updatePreferences = (data: Partial<SearchPreferencesUpdate>) =>
  api.put<SearchPreferences>('/profile/preferences', data).then(r => r.data)

export const seedPreferences = () =>
  api.post<SearchPreferences>('/profile/preferences/seed').then(r => r.data)
