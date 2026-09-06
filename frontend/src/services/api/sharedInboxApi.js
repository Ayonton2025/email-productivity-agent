import apiClient from './client'

export const sharedInboxApi = {
  list: () => apiClient.get('/shared-inboxes/'),
  create: (payload) => apiClient.post('/shared-inboxes/', payload),
  listMembers: (inboxId) => apiClient.get(`/shared-inboxes/${inboxId}/members`),
  addMember: (inboxId, payload) => apiClient.post(`/shared-inboxes/${inboxId}/members`, payload),
  listEmails: (inboxId, params = {}) => apiClient.get(`/shared-inboxes/${inboxId}/emails`, { params }),
  addEmail: (inboxId, emailId) => apiClient.post(`/shared-inboxes/${inboxId}/emails/${emailId}`),
  updateEmail: (inboxId, emailId, payload) => apiClient.patch(`/shared-inboxes/${inboxId}/emails/${emailId}`, payload),
}
