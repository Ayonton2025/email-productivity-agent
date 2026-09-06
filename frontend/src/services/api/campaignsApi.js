import apiClient from './client'

export const campaignsApi = {
  getCampaigns: (status = null) => apiClient.get('/campaigns/', { params: status ? { status } : {} }),
  getCampaign: (campaignId) => apiClient.get(`/campaigns/${campaignId}`),
  createCampaign: (data) => apiClient.post('/campaigns/', data),
  updateCampaign: (campaignId, data) => apiClient.put(`/campaigns/${campaignId}`, data),
  deleteCampaign: (campaignId) => apiClient.delete(`/campaigns/${campaignId}`),
  getRecommendedSender: () => apiClient.get('/campaigns/recommended-sender'),
  createSequence: (campaignId, data) => apiClient.post(`/campaigns/${campaignId}/sequences`, data),
  bulkCreateLeads: (campaignId, leads) => {
    const normalizedLeads = Array.isArray(leads) ? leads : leads?.leads || []
    return apiClient.post(`/campaigns/${campaignId}/leads/bulk`, { leads: normalizedLeads })
  },
  getLeads: (campaignId, status = null, limit = 100, offset = 0) =>
    apiClient.get(`/campaigns/${campaignId}/leads`, {
      params: { status, limit, offset },
    }),
  startCampaign: (campaignId) => apiClient.post(`/campaigns/${campaignId}/start`),
  pauseCampaign: (campaignId) => apiClient.post(`/campaigns/${campaignId}/pause`),
}
