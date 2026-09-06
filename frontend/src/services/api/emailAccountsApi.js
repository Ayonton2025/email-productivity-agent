import apiClient from './client'

export const emailAccountsApi = {
  connectGmail: (authData) => apiClient.post('/email-accounts/gmail', authData),
  connectOutlook: (authData) => apiClient.post('/email-accounts/outlook', authData),
  getEmailAccounts: () => apiClient.get('/email-accounts'),
  disconnectAccount: (accountId) => apiClient.delete(`/email-accounts/${accountId}`),
  syncAccount: (accountId) => apiClient.post(`/email-accounts/${accountId}/sync`),
  getAccount: (accountId) => apiClient.get(`/email-accounts/${accountId}`),
}
