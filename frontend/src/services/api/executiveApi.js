import apiClient from './client'

export const executiveApi = {
  getSummary: () => apiClient.get('/executive/summary'),
  command: (payload) => apiClient.post('/executive/command', payload),
}
