import apiClient from './client'

export const workflowsApi = {
  getWorkflows: () => apiClient.get('/workflows/'),
  getWorkflow: (workflowId) => apiClient.get(`/workflows/${workflowId}`),
  createWorkflow: (data) => apiClient.post('/workflows/', data),
  updateWorkflow: (workflowId, data) => apiClient.put(`/workflows/${workflowId}`, data),
  deleteWorkflow: (workflowId) => apiClient.delete(`/workflows/${workflowId}`),
  createStep: (workflowId, data) => apiClient.post(`/workflows/${workflowId}/steps`, data),
  updateStep: (stepId, data) => apiClient.put(`/workflows/steps/${stepId}`, data),
  deleteStep: (stepId) => apiClient.delete(`/workflows/steps/${stepId}`),
  getExecutions: (workflowId, limit = 20) =>
    apiClient.get(`/workflows/${workflowId}/executions`, { params: { limit } }),
  executeWorkflow: (workflowId, emailId = null) =>
    apiClient.post(`/workflows/${workflowId}/execute`, { email_id: emailId }),
}
