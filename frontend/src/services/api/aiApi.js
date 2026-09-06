import apiClient, { LONG_AI_TIMEOUT_MS } from './client'

export const aiApi = {
  categorizeEmail: (emailId) =>
    apiClient.post('/agent/process', {
      email_id: emailId,
      prompt_type: 'categorization',
    }),
  summarizeEmail: (emailId) =>
    apiClient.post('/agent/process', {
      email_id: emailId,
      prompt_type: 'summary',
    }),
  generateReply: (emailId, options = {}) =>
    apiClient.post('/agent/process', {
      email_id: emailId,
      prompt_type: 'reply_draft',
      ...options,
    }),
  extractActions: (emailId) =>
    apiClient.post('/agent/process', {
      email_id: emailId,
      prompt_type: 'action_extraction',
    }),
  assistWorkspace: (payload, timeoutMs = LONG_AI_TIMEOUT_MS) =>
    apiClient.post('/ai/assistant/assist', payload, { timeout: timeoutMs }),
}
