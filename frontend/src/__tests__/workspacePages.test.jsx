import React from 'react'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppContent } from '../App'
import apiClient from '../services/api'
import { EmailProvider } from '../context/EmailContext'
import { PromptProvider } from '../context/PromptContext'
import { EmailAccountsProvider } from '../context/EmailAccountsContext'

vi.mock('../context/AuthContext', () => ({
  AuthProvider: ({ children }) => children,
  useAuth: () => ({
    user: {
      id: 'viewer',
      email: 'viewer@example.test',
      full_name: 'Workspace Reviewer',
      plan: 'enterprise',
      is_super_admin: true,
    },
    isAuthenticated: true,
    loading: false,
    logout: vi.fn(),
  }),
}))

let requests
const originalAdapter = apiClient.defaults.adapter
function responseFor(url) {
  if (/\/(workflows|agents|campaigns|drafts|prompts)(\/my)?\/?$/.test(url)) return []
  if (url.includes('shared-inboxes')) return { items: [] }
  if (url.includes('email-accounts')) return { accounts: [] }
  if (url.includes('subscription')) return { plan_id: 'enterprise', status: 'active' }
  if (url.includes('providers')) return { providers: [] }
  if (url.includes('transactions')) return { transactions: [] }
  if (url.includes('revenue')) return { report: [] }
  if (url.includes('overview')) return { metrics: { total_users: 1 } }
  if (url.includes('risks')) return []
  if (url.includes('opportunities')) return []
  if (url.includes('deadlines')) return []
  if (url.includes('relationships')) return { contacts: [], companies: [] }
  if (url.includes('followups')) return { items: [], policy: { enabled: false } }
  if (url.includes('briefings'))
    return { briefing: null, preferences: { timezone: 'UTC', send_hour: 6, enabled: true } }
  if (url.includes('auto-reply')) return { rules: [], items: [] }
  return {}
}
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
  requests = []
  apiClient.defaults.adapter = async (config) => {
    requests.push(config.url)
    return { data: responseFor(config.url), status: 200, statusText: 'OK', headers: {}, config }
  }
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }))
})
afterEach(() => {
  cleanup()
  apiClient.defaults.adapter = originalAdapter
  vi.unstubAllGlobals()
})

describe('workspace navigation with an empty account', () => {
  it.each([
    ['inbox', /Inbox/i],
    ['insights', /Insights/i],
    ['relationships', /Relationships/i],
    ['workflows', /Workflows/i],
    ['agents', /Agents/i],
    ['campaigns', /Campaigns/i],
    ['briefings', /Briefing/i],
    ['followups', /Follow/i],
    ['hosted-email', /Hosted/i],
    ['shared-inbox', /Shared Inbox/i],
    ['deliverability', /Deliverability/i],
    ['executive', /Executive/i],
    ['agent', /Agent/i],
    ['drafts', /Draft/i],
    ['auto-reply', /Auto.Reply/i],
    ['email-accounts', /Email Accounts/i],
    ['prompts', /Prompt/i],
    ['admin-dashboard', /Admin Dashboard/i],
    ['admin-llm', /LLM/i],
  ])('opens %s and renders its page', async (tab, heading) => {
    render(
      <MemoryRouter initialEntries={['/inbox#' + tab]}>
        <EmailAccountsProvider>
          <EmailProvider>
            <PromptProvider>
              <AppContent />
            </PromptProvider>
          </EmailProvider>
        </EmailAccountsProvider>
      </MemoryRouter>
    )
    await waitFor(() =>
      expect(screen.getAllByRole('heading').some((element) => heading.test(element.textContent))).toBe(true)
    )
    await waitFor(() => expect(requests.length).toBeGreaterThan(0))
    expect(document.title).toContain('Bylix Email')
  })
})
