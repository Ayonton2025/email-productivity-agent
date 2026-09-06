import apiClient from './client'

export const autoReplyApi = {
  getRules: () => apiClient.get('/auto-reply/'),
  createRule: (data) => apiClient.post('/auto-reply/', data),
  updateRule: (ruleId, data) => apiClient.put(`/auto-reply/${ruleId}`, data),
  deleteRule: (ruleId) => apiClient.delete(`/auto-reply/${ruleId}`),
  getAwayMode: () => apiClient.get('/auto-reply/away'),
  setAwayMode: (data) => apiClient.put('/auto-reply/away', data),
  getApprovalQueue: () => apiClient.get('/auto-reply/approval-queue'),
  approveDraft: (draftId) => apiClient.post(`/auto-reply/approval-queue/${draftId}/approve`),
  rejectDraft: (draftId) => apiClient.post(`/auto-reply/approval-queue/${draftId}/reject`),
}
