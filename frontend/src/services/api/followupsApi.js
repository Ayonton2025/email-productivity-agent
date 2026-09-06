import apiClient from './client'

export const followupsApi = {
  getPolicy: () => apiClient.get('/followups/policy'),
  updatePolicy: (data) => apiClient.put('/followups/policy', data),
  schedule: (emailId, delayHours = null) =>
    apiClient.post(`/followups/${emailId}/schedule`, { delay_hours: delayHours }),
  disable: (emailId) => apiClient.post(`/followups/${emailId}/disable`),
  getQueue: (status = 'pending_approval', limit = 50) =>
    apiClient.get('/followups/queue', { params: { status, limit } }),
  approveQueueItem: (executionId) => apiClient.post(`/followups/queue/${executionId}/approve`),
  processDue: () => apiClient.post('/followups/process-due'),
}
