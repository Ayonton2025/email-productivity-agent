import apiClient from './client'

export const briefingsApi = {
  getToday: () => apiClient.get('/briefings/today'),
  regenerateToday: () => apiClient.post('/briefings/regenerate'),
  getPreferences: () => apiClient.get('/briefings/preferences'),
  updatePreferences: (data) => apiClient.put('/briefings/preferences', data),
}
