import apiClient from './client'

export const insightsApi = {
  getRisks: (severity) => apiClient.get('/insights/risks', { params: { severity } }),
  getOpportunities: (status) => apiClient.get('/insights/opportunities', { params: { status } }),
  getDeadlines: (daysAhead = 7) => apiClient.get('/insights/deadlines', { params: { days_ahead: daysAhead } }),
  getRelationships: (status) => apiClient.get('/insights/relationships', { params: { status } }),
  getAnalytics: (days = 30) => apiClient.get('/insights/analytics', { params: { days } }),
  getContactDetails: (contactId) => apiClient.get(`/insights/contacts/${contactId}`),
  getCompanyDetails: (companyId) => apiClient.get(`/insights/companies/${companyId}`),
}
