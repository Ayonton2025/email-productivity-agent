import { DEFAULT_REQUEST_TIMEOUT_MS } from './client'
import apiClient, { LONG_AI_TIMEOUT_MS } from './client'

export const healthApi = {
  checkAPI: () => apiClient.get('/health'),
  checkDatabase: () => apiClient.get('/health/db'),
  checkAI: () => apiClient.get('/health/ai'),
  checkAIProviders: (checkLive = false) =>
    apiClient.get(`/ai/health?check_live=${checkLive ? 'true' : 'false'}`, {
      timeout: checkLive ? LONG_AI_TIMEOUT_MS : DEFAULT_REQUEST_TIMEOUT_MS,
    }),
}
