import { act, renderHook, waitFor, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import React from 'react'
import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { useCampaignBuilder } from '../components/campaigns/useCampaignBuilder'
import { useEmailDetail } from '../components/inbox/useEmailDetail'
import { useSharedInbox } from '../components/shared-inbox/useSharedInbox'
import { campaignsApi, aiApi, emailApi, sharedInboxApi } from '../services/api'
import * as payment from '../services/paymentService'
import { notifications } from '../utils/notifications'

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'u1', email: 'owner@example.test', plan: 'professional' } }),
}))
const wrapper = ({ children }) => <MemoryRouter>{children}</MemoryRouter>
beforeEach(() => {
  vi.spyOn(campaignsApi, 'getRecommendedSender').mockResolvedValue({
    data: { success: true, recommended: { email: 'sender@example.test', from_name: 'Sender' } },
  })
  vi.spyOn(campaignsApi, 'getLeads').mockResolvedValue({ data: [] })
})
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  notifications.clear()
})

it('creates a campaign and associates sequences and leads with the returned ID', async () => {
  const create = vi.spyOn(campaignsApi, 'createCampaign').mockResolvedValue({ data: { id: 'saved-campaign' } })
  const sequence = vi.spyOn(campaignsApi, 'createSequence').mockResolvedValue({ data: { id: 's1' } })
  const leads = vi.spyOn(campaignsApi, 'bulkCreateLeads').mockResolvedValue({ data: {} })
  const onSave = vi.fn(),
    onClose = vi.fn()
  const { result } = renderHook(() => useCampaignBuilder({ onSave, onClose }))
  await waitFor(() => expect(result.current.recommendedSender).not.toBeNull())
  act(() => {
    result.current.applyRecommendedSender()
    result.current.handleInputChange('name', 'Outreach')
  })
  act(() => result.current.setNewSequence({ name: 'Intro', subject_template: 'Hello', body_template: 'Welcome' }))
  await act(() => result.current.addSequence())
  await act(() => result.current.handleBulkImport('email,first_name\nlead@example.test,Lee'))
  await act(() => result.current.handleSave())
  expect(create).toHaveBeenCalledWith(expect.objectContaining({ name: 'Outreach', from_email: 'sender@example.test' }))
  expect(sequence).toHaveBeenCalledWith('saved-campaign', expect.objectContaining({ name: 'Intro' }))
  expect(leads).toHaveBeenCalledWith('saved-campaign', [expect.objectContaining({ email: 'lead@example.test' })])
  expect(onSave).toHaveBeenCalledOnce()
  expect(onClose).toHaveBeenCalledOnce()
})
it('keeps an invalid campaign open and provides validation feedback', async () => {
  const create = vi.spyOn(campaignsApi, 'createCampaign')
  const onClose = vi.fn()
  const { result } = renderHook(() => useCampaignBuilder({ onSave: vi.fn(), onClose }))
  await act(() => result.current.handleSave())
  expect(create).not.toHaveBeenCalled()
  expect(onClose).not.toHaveBeenCalled()
  expect(notifications.getSnapshot()[0].message).toMatch(/required fields/)
})
it('applies an AI campaign draft and reports a later provider failure', async () => {
  const assist = vi.spyOn(aiApi, 'assistWorkspace').mockResolvedValue({
    data: {
      provider: 'test',
      model: 'test-model',
      draft: {
        campaign: { name: 'AI campaign' },
        sequences: [{ name: 'First' }],
        leads: [{ email: 'lead@example.test' }],
      },
    },
  })
  const { result } = renderHook(() => useCampaignBuilder({ onSave: vi.fn(), onClose: vi.fn() }))
  await act(() => result.current.handleGenerateAIDraft('Create outreach'))
  expect(result.current.formData.name).toBe('AI campaign')
  expect(result.current.sequences[0].step_order).toBe(1)
  expect(result.current.leads).toHaveLength(1)
  assist.mockRejectedValueOnce(new Error('Provider unavailable'))
  await act(() => result.current.handleGenerateAIDraft('Try again'))
  expect(result.current.aiError).toBe('Provider unavailable')
  expect(result.current.aiLoading).toBe(false)
})
it('generates and sends a reply with the original thread metadata', async () => {
  vi.spyOn(emailApi, 'generateReply').mockResolvedValue({ data: { reply: 'Thanks for writing', ai_generated: true } })
  const send = vi.spyOn(emailApi, 'sendEmail').mockResolvedValue({ data: {} })
  const email = {
    id: 'e1',
    subject: 'Re: Meeting',
    sender: 'sender@example.test',
    message_id: '<m1>',
    references: ['<m0>'],
    thread_id: 'thread1',
  }
  const { result } = renderHook(() => useEmailDetail({ email, accountId: 'a1' }), { wrapper })
  await act(() => result.current.generateReply())
  expect(result.current.reply).toBe('Thanks for writing')
  await act(() => result.current.sendReply())
  expect(send).toHaveBeenCalledWith(
    'a1',
    expect.objectContaining({
      to: email.sender,
      subject: 'Re: Meeting',
      body_text: 'Thanks for writing',
      in_reply_to: '<m1>',
      references: ['<m0>'],
      thread_id: 'thread1',
    })
  )
  expect(result.current.sendSuccess).toBe(true)
})
it('keeps reply text available after a send failure', async () => {
  vi.spyOn(emailApi, 'sendEmail').mockRejectedValue(new Error('Mailbox offline'))
  const { result } = renderHook(
    () => useEmailDetail({ email: { id: 'e1', sender: 'sender@example.test' }, accountId: 'a1' }),
    { wrapper }
  )
  act(() => result.current.setReply('Please keep this draft'))
  await act(() => result.current.sendReply())
  expect(result.current.error).toBe('Mailbox offline')
  expect(result.current.reply).toBe('Please keep this draft')
  expect(result.current.sending).toBe(false)
})
it('loads shared inbox members and enforces member-management permissions', async () => {
  vi.spyOn(payment, 'getSubscription').mockResolvedValue({ plan_id: 'team', team_members_limit: 5 })
  vi.spyOn(sharedInboxApi, 'list').mockResolvedValue({
    data: { items: [{ id: 'i1', name: 'Support', member_role: 'member' }] },
  })
  vi.spyOn(sharedInboxApi, 'listMembers').mockResolvedValue({
    data: { members: [{ user_id: 'u1', email: 'owner@example.test' }] },
  })
  vi.spyOn(sharedInboxApi, 'listEmails').mockResolvedValue({
    data: {
      items: [
        { id: 'e1', shared: { assigned_to_user_id: 'u1' } },
        { id: 'e2', shared: {} },
      ],
    },
  })
  const addMember = vi.spyOn(sharedInboxApi, 'addMember')
  const { result } = renderHook(() => useSharedInbox())
  await waitFor(() => expect(result.current.items).toHaveLength(2))
  act(() => {
    result.current.setAssignedToMeOnly(true)
    result.current.setMemberEmail('new@example.test')
  })
  expect(result.current.filteredItems.map((item) => item.id)).toEqual(['e1'])
  await act(() => result.current.addMember())
  expect(addMember).not.toHaveBeenCalled()
  expect(result.current.error).toMatch(/Only owner or admin/)
})
