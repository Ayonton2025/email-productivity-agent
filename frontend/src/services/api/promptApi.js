import apiClient from './client'

export const promptApi = {
  getPrompts: () => apiClient.get('/prompts'),
  getUserPrompts: () => apiClient.get('/prompts/my'),
  createPrompt: (promptData) => apiClient.post('/prompts', promptData),
  updatePrompt: (promptId, promptData) => apiClient.put(`/prompts/${promptId}`, promptData),
  deletePrompt: (promptId) => apiClient.delete(`/prompts/${promptId}`),
}
