import { api } from './client'

export const dashboardAPI = {
  async getMetrics(days: number = 7) {
    const { data } = await api.get('/dashboard/metrics', { params: { days } })
    return data
  },

  async getJobsByScore(minScore: number, maxScore: number, limit: number = 50) {
    const { data } = await api.get('/dashboard/jobs/by-score', {
      params: { min_score: minScore, max_score: maxScore, limit },
    })
    return data
  },

  async getScoredVsUnscored(days: number = 7) {
    const { data } = await api.get('/dashboard/jobs/scored-vs-unscored', { params: { days } })
    return data
  },

  async getApplicationsTimeline(days: number = 7) {
    const { data } = await api.get('/dashboard/applications/timeline', { params: { days } })
    return data
  },

  async getStatusBreakdown() {
    const { data } = await api.get('/dashboard/applications/status-breakdown')
    return data
  },

  async healthCheck() {
    const { data } = await api.get('/dashboard/health')
    return data
  },
}