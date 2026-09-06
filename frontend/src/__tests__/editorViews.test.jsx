import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import CampaignBuilder from '../components/campaigns/CampaignBuilder'
import EmailDetailPage from '../components/inbox/EmailDetailPage'
import ProviderList from '../components/admin/ProviderList'
import { campaignsApi, emailApi } from '../services/api'
import attachmentService from '../services/attachmentService'
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1', plan: 'professional' } }) }))
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})
it('keeps form state while switching campaign tabs and adding a sequence', async () => {
  vi.spyOn(campaignsApi, 'getRecommendedSender').mockResolvedValue({ data: {} })
  render(<CampaignBuilder onSave={vi.fn()} onClose={vi.fn()} />)
  fireEvent.change(screen.getByPlaceholderText('e.g., Q1 Sales Outreach'), { target: { value: 'Customer outreach' } })
  fireEvent.click(screen.getByRole('button', { name: /^sequences$/i }))
  fireEvent.click(screen.getByRole('button', { name: /add sequence/i }))
  fireEvent.change(screen.getByPlaceholderText('e.g., Initial Outreach'), { target: { value: 'Introduction' } })
  fireEvent.change(screen.getByPlaceholderText('e.g., Quick question about {company}'), { target: { value: 'Hello' } })
  fireEvent.change(screen.getByPlaceholderText('Hi {name}, ...'), { target: { value: 'Welcome aboard' } })
  fireEvent.click(screen.getAllByRole('button', { name: /add sequence/i }).at(-1))
  await waitFor(() => expect(screen.getByText('Introduction')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: /^leads$/i }))
  expect(screen.getByRole('heading', { name: 'Leads (0)' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /^basic$/i }))
  expect(screen.getByDisplayValue('Customer outreach')).toBeInTheDocument()
})
it('renders a message, generates a reply, and preserves reply sending behavior', async () => {
  vi.spyOn(attachmentService, 'getEmailAttachments').mockResolvedValue({ success: true, data: { attachments: [] } })
  vi.spyOn(emailApi, 'generateReply').mockResolvedValue({
    data: { reply: 'Thank you for the update.', ai_generated: true },
  })
  const send = vi.spyOn(emailApi, 'sendEmail').mockResolvedValue({ data: {} })
  const email = {
    id: 'e1',
    subject: 'Project update',
    sender: 'sender@example.test',
    received_at: '2026-01-01T10:00:00Z',
    body_text: 'Read the project update at https://example.test/project',
    ai_summary: 'The project is on schedule.',
    ai_category: 'Important',
    priority: 'high',
  }
  render(
    <MemoryRouter>
      <EmailDetailPage email={email} accountId="account-1" onBack={vi.fn()} />
    </MemoryRouter>
  )
  expect(screen.getByRole('heading', { name: 'Project update' })).toBeInTheDocument()
  expect(screen.getByText('The project is on schedule.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /generate.*reply/i }))
  await screen.findByText('Thank you for the update.')
  fireEvent.click(screen.getByRole('button', { name: /send reply/i }))
  await waitFor(() =>
    expect(send).toHaveBeenCalledWith('account-1', expect.objectContaining({ body_text: 'Thank you for the update.' }))
  )
})
it('shows masked provider keys and wires management actions to the selected provider', () => {
  const rotateKey = vi.fn(),
    check = vi.fn(),
    test = vi.fn(),
    confirmDelete = vi.fn()
  render(
    <ProviderList
      llmProviders={[
        {
          provider: 'provider-one',
          display_name: 'Test Provider',
          is_healthy: true,
          is_enabled: true,
          key_count: 1,
          masked_keys: ['masked-key'],
          priority: 1,
        },
      ]}
      patchProvider={vi.fn()}
      setLlmProviders={vi.fn()}
      setConfirmDelete={confirmDelete}
      newKeys={{}}
      setNewKeys={vi.fn()}
      rotateKey={rotateKey}
      runSingleProviderHealthCheck={check}
      providerChecks={{}}
      runSingleProviderTest={test}
      saveState={{}}
      setProviderChecks={vi.fn()}
    />
  )
  expect(screen.getByText('Test Provider')).toBeInTheDocument()
  expect(screen.getByText('masked-key')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Add/Rotate Key' }))
  fireEvent.click(screen.getByRole('button', { name: 'Check' }))
  fireEvent.click(screen.getByRole('button', { name: 'Test' }))
  fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
  expect(rotateKey).toHaveBeenCalledWith('provider-one')
  expect(check).toHaveBeenCalledWith('provider-one')
  expect(test).toHaveBeenCalledWith('provider-one')
  expect(confirmDelete).toHaveBeenCalledWith({ provider: 'provider-one', keyIndex: 0, maskedKey: 'masked-key' })
})
