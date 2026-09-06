import apiClient from './client'

export const agentApi = {
  processEmail: (requestData) => apiClient.post('/agent/process', requestData),
  chatWithAgent: (message) => apiClient.post('/agent/chat', { message }),
  getAgentStatus: () => apiClient.get('/agent/status'),
}
