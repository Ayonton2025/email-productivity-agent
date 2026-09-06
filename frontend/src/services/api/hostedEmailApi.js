import apiClient from './client'

export const hostedEmailApi = {
  checkAvailability: (localPart) => apiClient.get('/hosted-email/availability', { params: { local_part: localPart } }),
  provision: (payload) => apiClient.post('/hosted-email/provision', payload),
  signup: (payload) => apiClient.post('/hosted-email/signup', payload),
  getLimits: () => apiClient.get('/hosted-email/limits'),
}
