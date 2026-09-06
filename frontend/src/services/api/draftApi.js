import apiClient from './client'

export const draftApi = {
  getDrafts: () => apiClient.get('/drafts'),
  createDraft: (draftData) => apiClient.post('/drafts', draftData),
  updateDraft: (draftId, draftData) => apiClient.put(`/drafts/${draftId}`, draftData),
  deleteDraft: (draftId) => apiClient.delete(`/drafts/${draftId}`),
}
