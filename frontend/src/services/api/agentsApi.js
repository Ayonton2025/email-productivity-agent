import apiClient from './client'

export const agentsApi = {
  getAgents: (agentType = null) => apiClient.get('/agents/', { params: agentType ? { agent_type: agentType } : {} }),
  getAgent: (agentId) => apiClient.get(`/agents/${agentId}`),
  createAgent: (data) => apiClient.post('/agents/', data),
  updateAgent: (agentId, data) => apiClient.put(`/agents/${agentId}`, data),
  deleteAgent: (agentId) => apiClient.delete(`/agents/${agentId}`),
  getActivities: (agentId, limit = 50) => apiClient.get(`/agents/${agentId}/activities`, { params: { limit } }),
  getMemory: (agentId, memoryType = null, limit = 100) =>
    apiClient.get(`/agents/${agentId}/memory`, {
      params: { memory_type: memoryType, limit },
    }),
}
