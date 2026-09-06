import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import apiClient, * as api from '../services/api'
import transport from '../services/api/client'
let requests
const originalAdapter = apiClient.defaults.adapter
beforeEach(() => {
  requests = []
  localStorage.clear()
  apiClient.defaults.adapter = async (config) => {
    requests.push(config)
    return { data: { ok: true }, status: 200, statusText: 'OK', headers: {}, config }
  }
})
afterEach(() => {
  apiClient.defaults.adapter = originalAdapter
  vi.restoreAllMocks()
})
it('retains one shared transport behind the public facade', () => expect(apiClient).toBe(transport))
it.each([
  ['promptApi', 'getPrompts', [], 'get', '/prompts'],
  ['promptApi', 'createPrompt', [{ name: 'Summary', template: 'Summarize' }], 'post', '/prompts'],
  ['promptApi', 'updatePrompt', ['p1', { name: 'Updated' }], 'put', '/prompts/p1'],
  ['promptApi', 'deletePrompt', ['p1'], 'delete', '/prompts/p1'],
  ['draftApi', 'getDrafts', [], 'get', '/drafts'],
  ['draftApi', 'createDraft', [{ subject: 'Hello' }], 'post', '/drafts'],
  ['draftApi', 'updateDraft', ['d1', { subject: 'Revised' }], 'put', '/drafts/d1'],
  ['draftApi', 'deleteDraft', ['d1'], 'delete', '/drafts/d1'],
  ['sharedInboxApi', 'list', [], 'get', '/shared-inboxes/'],
  ['sharedInboxApi', 'create', [{ name: 'Support' }], 'post', '/shared-inboxes/'],
  ['sharedInboxApi', 'listMembers', ['i1'], 'get', '/shared-inboxes/i1/members'],
  ['sharedInboxApi', 'addEmail', ['i1', 'e1'], 'post', '/shared-inboxes/i1/emails/e1'],
  ['sharedInboxApi', 'updateEmail', ['i1', 'e1', { status: 'resolved' }], 'patch', '/shared-inboxes/i1/emails/e1'],
  ['workflowsApi', 'getWorkflows', [], 'get', '/workflows/'],
  ['workflowsApi', 'createWorkflow', [{ name: 'Invoices' }], 'post', '/workflows/'],
  ['workflowsApi', 'updateWorkflow', ['w1', { name: 'Updated' }], 'put', '/workflows/w1'],
  ['workflowsApi', 'deleteWorkflow', ['w1'], 'delete', '/workflows/w1'],
  ['agentsApi', 'getAgents', [], 'get', '/agents/'],
  ['agentsApi', 'getAgent', ['a1'], 'get', '/agents/a1'],
  ['agentsApi', 'createAgent', [{ name: 'Support' }], 'post', '/agents/'],
  ['campaignsApi', 'getCampaigns', [], 'get', '/campaigns/'],
  ['campaignsApi', 'createCampaign', [{ name: 'Outreach' }], 'post', '/campaigns/'],
  ['campaignsApi', 'getRecommendedSender', [], 'get', '/campaigns/recommended-sender'],
  ['campaignsApi', 'startCampaign', ['c1'], 'post', '/campaigns/c1/start'],
  ['campaignsApi', 'pauseCampaign', ['c1'], 'post', '/campaigns/c1/pause'],
  ['briefingsApi', 'getToday', [], 'get', '/briefings/today'],
  ['briefingsApi', 'regenerateToday', [], 'post', '/briefings/regenerate'],
  ['followupsApi', 'getPolicy', [], 'get', '/followups/policy'],
  ['followupsApi', 'processDue', [], 'post', '/followups/process-due'],
  ['hostedEmailApi', 'getLimits', [], 'get', '/hosted-email/limits'],
  ['deliverabilityApi', 'getScore', [7], 'get', '/deliverability/score'],
  ['executiveApi', 'getSummary', [], 'get', '/executive/summary'],
  ['insightsApi', 'getRisks', ['high'], 'get', '/insights/risks'],
  ['analyticsApi', 'getStats', [], 'get', '/analytics/stats'],
  ['healthApi', 'checkAPI', [], 'get', '/health'],
])('%s.%s preserves its HTTP contract', async (domain, method, args, verb, url) => {
  localStorage.setItem('auth_token', 'test-session')
  const response = await api[domain][method](...args)
  expect(response.data).toEqual({ ok: true })
  expect(requests).toHaveLength(1)
  expect(requests[0]).toMatchObject({ method: verb, url })
  expect(requests[0].headers.Authorization).toBe('Bearer test-session')
})
it('uses the AI timeout and forwards the assistant request unchanged', async () => {
  const payload = { page: 'prompts', mode: 'draft', objective: 'Summarize' }
  await api.aiApi.assistWorkspace(payload)
  expect(requests[0].timeout).toBe(300000)
  expect(JSON.parse(requests[0].data)).toEqual(payload)
})
it('clears invalid authentication on a public page without navigating', async () => {
  localStorage.setItem('auth_token', 'expired-session')
  localStorage.setItem('user', '{}')
  const handler = apiClient.interceptors.response.handlers[0].rejected
  const error = { response: { status: 401 }, config: { url: '/me' }, message: 'Unauthorized' }
  await expect(handler(error)).rejects.toBe(error)
  expect(localStorage.getItem('auth_token')).toBeNull()
  expect(localStorage.getItem('user')).toBeNull()
})
it('stores and removes session tokens through the compatible utilities', () => {
  api.tokenUtils.setToken('session')
  expect(api.tokenUtils.isValid()).toBe(true)
  expect(api.tokenUtils.getToken()).toBe('session')
  api.tokenUtils.removeToken()
  expect(api.tokenUtils.isValid()).toBe(false)
})
