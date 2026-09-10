import React from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InsightsDashboard from '../components/insights/InsightsDashboard'
import { insightsApi } from '../services/api'

const { navigate } = vi.hoisted(() => ({ navigate: vi.fn() }))
vi.mock('react-router-dom', () => ({ useNavigate: () => navigate }))
vi.mock('../utils/logger.js', () => ({ logger: { error: vi.fn() } }))
vi.mock('../services/api', () => ({
  insightsApi: {
    getAnalytics: vi.fn(),
    getRisks: vi.fn(),
    getOpportunities: vi.fn(),
    getDeadlines: vi.fn(),
    getRelationships: vi.fn(),
  },
}))

beforeEach(() => {
  vi.resetAllMocks()
  insightsApi.getAnalytics.mockResolvedValue({ data: { email_statistics: { total_emails: 42 } } })
  insightsApi.getRisks.mockResolvedValue({ data: [{ id: 11, title: 'Contract risk', severity: 'critical' }] })
  insightsApi.getOpportunities.mockResolvedValue({
    data: [{ id: 22, title: 'Renewal opportunity', status: 'qualified', estimated_value: 1200, probability: 75 }],
  })
  insightsApi.getDeadlines.mockResolvedValue({
    data: [{ id: 33, title: 'Deliver report', deadline: '2000-01-01T12:00:00Z', priority: 'high' }],
  })
  insightsApi.getRelationships.mockResolvedValue({
    data: {
      total_contacts: 1,
      companies: [{ id: 44, name: 'Example Company', relationship_status: 'active' }],
      top_contacts: [
        { id: 55, display_name: 'Sample Contact', email: 'sample@example.test', relationship_score: 78.6 },
      ],
    },
  })
})

describe('Insights Dashboard', () => {
  it('loads overview data and renders each extracted tab with working detail navigation', async () => {
    render(<InsightsDashboard />)
    expect(screen.getByRole('status', { name: 'Loading insights' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Insights Dashboard' })).toBeInTheDocument()
    for (const name of ['Overview', 'Risks', 'Opportunities', 'Deadlines', 'Relationships']) {
      expect(screen.getByRole('button', { name })).toBeInTheDocument()
    }
    expect(insightsApi.getAnalytics).toHaveBeenCalledWith(30)
    expect(insightsApi.getDeadlines).toHaveBeenCalledWith(7)
    expect(screen.getByText('42')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Contract risk'))
    expect(navigate).toHaveBeenLastCalledWith('/risks/11')
    fireEvent.click(screen.getByText('Renewal opportunity'))
    expect(navigate).toHaveBeenLastCalledWith('/opportunities/22')

    fireEvent.click(screen.getByRole('button', { name: 'Risks' }))
    expect(screen.getByRole('heading', { name: 'All Risks' })).toBeInTheDocument()
    expect(screen.getByText('critical')).toHaveClass('bg-red-100')
    fireEvent.click(screen.getByText('Contract risk'))
    expect(navigate).toHaveBeenLastCalledWith('/risks/11')

    fireEvent.click(screen.getByRole('button', { name: 'Opportunities' }))
    expect(screen.getByRole('heading', { name: 'All Opportunities' })).toBeInTheDocument()
    expect(screen.getByText('$1,200')).toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Renewal opportunity'))
    expect(navigate).toHaveBeenLastCalledWith('/opportunities/22')

    fireEvent.click(screen.getByRole('button', { name: 'Deadlines' }))
    expect(screen.getByText('Deliver report')).toBeInTheDocument()
    expect(screen.getByText('Overdue')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Relationships' }))
    fireEvent.click(screen.getByText('Example Company'))
    expect(navigate).toHaveBeenLastCalledWith('/companies/44')
    fireEvent.click(screen.getByText('Sample Contact'))
    expect(navigate).toHaveBeenLastCalledWith('/contacts/55')
    expect(screen.getByText('Score: 79')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Overview' }))
    expect(screen.getByText('Recent Risks')).toBeInTheDocument()
  })

  it('refreshes all data while retaining the selected tab', async () => {
    render(<InsightsDashboard />)
    await screen.findByText('Recent Risks')
    fireEvent.click(screen.getByRole('button', { name: 'Risks' }))
    let resolveRisks
    insightsApi.getRisks.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRisks = resolve
      })
    )
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))
    expect(screen.getByRole('status')).toBeInTheDocument()
    await act(async () => resolveRisks({ data: [{ id: 66, title: 'Updated risk' }] }))
    expect(await screen.findByText('Updated risk')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'All Risks' })).toBeInTheDocument()
    expect(screen.queryByText('Contract risk')).not.toBeInTheDocument()
    for (const method of Object.values(insightsApi)) expect(method).toHaveBeenCalledTimes(2)
  })

  it('shows a safe load failure and recovers on refresh', async () => {
    insightsApi.getAnalytics.mockRejectedValueOnce(new Error('internal server details'))
    render(<InsightsDashboard />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load insights')
    expect(screen.queryByText('internal server details')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))
    await screen.findByText('Recent Risks')
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  })

  it('preserves empty states across the extracted list tabs', async () => {
    insightsApi.getRisks.mockResolvedValue({ data: null })
    insightsApi.getOpportunities.mockResolvedValue({ data: [] })
    insightsApi.getDeadlines.mockResolvedValue({ data: [] })
    insightsApi.getRelationships.mockResolvedValue({ data: { companies: [], top_contacts: [] } })
    render(<InsightsDashboard />)
    await screen.findByRole('heading', { name: 'Insights Dashboard' })
    for (const [tab, empty] of [
      ['Risks', 'No risks identified'],
      ['Opportunities', 'No opportunities identified'],
      ['Deadlines', 'No upcoming deadlines'],
      ['Relationships', 'No companies found'],
    ]) {
      fireEvent.click(screen.getByRole('button', { name: tab }))
      expect(screen.getByText(empty)).toBeInTheDocument()
    }
    expect(screen.getByText('No contacts found')).toBeInTheDocument()
  })
  it.each(['getAnalytics', 'getRisks', 'getOpportunities', 'getDeadlines', 'getRelationships'])(
    'retains the last successful data and selected tab when %s fails during refresh',
    async (method) => {
      render(<InsightsDashboard />)
      await screen.findByText('Recent Risks')
      fireEvent.click(screen.getByRole('button', { name: 'Risks' }))
      insightsApi[method].mockRejectedValueOnce(new Error('private failure details'))
      fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))
      expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load insights')
      expect(screen.getByRole('heading', { name: 'All Risks' })).toBeInTheDocument()
      expect(screen.getByText('Contract risk')).toBeInTheDocument()
      expect(screen.queryByText('private failure details')).not.toBeInTheDocument()
      fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))
      await screen.findByRole('heading', { name: 'All Risks' })
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    }
  )
})
