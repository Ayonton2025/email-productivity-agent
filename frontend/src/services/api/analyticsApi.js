import apiClient from './client'

export const analyticsApi = {
  getStats: () => apiClient.get('/analytics/stats'),
  getProductivity: (period = 'week') => apiClient.get('/analytics/productivity', { params: { period } }),
}
