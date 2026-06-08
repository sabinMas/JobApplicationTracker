const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const dashboardAPI = {
  async getMetrics(days: number = 7) {
    const response = await fetch(`${API_URL}/api/dashboard/metrics?days=${days}`);
    if (!response.ok) {
      throw new Error('Failed to fetch metrics');
    }
    return response.json();
  },

  async getJobsByScore(minScore: number, maxScore: number, limit: number = 50) {
    const params = new URLSearchParams({
      min_score: minScore.toString(),
      max_score: maxScore.toString(),
      limit: limit.toString(),
    });
    const response = await fetch(`${API_URL}/api/dashboard/jobs/by-score?${params}`);
    if (!response.ok) {
      throw new Error('Failed to fetch jobs by score');
    }
    return response.json();
  },

  async getScoredVsUnscored(days: number = 7) {
    const response = await fetch(
      `${API_URL}/api/dashboard/jobs/scored-vs-unscored?days=${days}`
    );
    if (!response.ok) {
      throw new Error('Failed to fetch scoring status');
    }
    return response.json();
  },

  async getApplicationsTimeline(days: number = 7) {
    const response = await fetch(
      `${API_URL}/api/dashboard/applications/timeline?days=${days}`
    );
    if (!response.ok) {
      throw new Error('Failed to fetch timeline');
    }
    return response.json();
  },

  async getStatusBreakdown() {
    const response = await fetch(`${API_URL}/api/dashboard/applications/status-breakdown`);
    if (!response.ok) {
      throw new Error('Failed to fetch status breakdown');
    }
    return response.json();
  },

  async healthCheck() {
    const response = await fetch(`${API_URL}/api/dashboard/health`);
    if (!response.ok) {
      throw new Error('Dashboard health check failed');
    }
    return response.json();
  },
};