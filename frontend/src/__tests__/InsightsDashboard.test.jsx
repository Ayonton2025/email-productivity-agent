import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InsightsDashboard from '../components/insights/InsightsDashboard'
import { insightsApi } from '../services/api'

vi.mock('../services/api', () => ({
  insightsApi: {
    getAnalytics: vi.fn(),
    getRisks: vi.fn(),
    getOpportunities: vi.fn(),
    getDeadlines: vi.fn(),
    getRelationships: vi.fn(),
  },
}))

const successfulResponses = () => {
  insightsApi.getAnalytics.mockResolvedValue({ data: {} })
  insightsApi.getRisks.mockResolvedValue({ data: [] })
  insightsApi.getOpportunities.mockResolvedValue({ data: [] })
  insightsApi.getDeadlines.mockResolvedValue({ data: [] })
  insightsApi.getRelationships.mockResolvedValue({ data: {} })
}

describe('insights dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    successfulResponses()
  })

  it('renders after all API data loads', async () => {
    render(
      <MemoryRouter>
        <InsightsDashboard />
      </MemoryRouter>
    )
    expect(await screen.findByRole('heading', { name: 'Insights Dashboard' })).toBeInTheDocument()
    expect(insightsApi.getAnalytics).toHaveBeenCalledWith(30)
  })

  it('changes dashboard tabs through user interaction', async () => {
    render(
      <MemoryRouter>
        <InsightsDashboard />
      </MemoryRouter>
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Risks' }))
    expect(screen.getByText(/risk/i, { selector: 'h2' })).toBeInTheDocument()
  })

  it('shows a friendly API error and supports retry', async () => {
    insightsApi.getAnalytics.mockRejectedValueOnce({ friendlyMessage: 'Insights are temporarily unavailable.' })
    render(
      <MemoryRouter>
        <InsightsDashboard />
      </MemoryRouter>
    )

    expect(await screen.findByRole('alert')).toHaveTextContent('Insights are temporarily unavailable.')
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))
    await waitFor(() => expect(insightsApi.getAnalytics).toHaveBeenCalledTimes(2))
  })
})
