import apiClient from './client'

export const deliverabilityApi = {
  getScore: (days = 30) => apiClient.get('/deliverability/score', { params: { days } }),
}
