import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import OpportunitiesTab from '../components/insights/tabs/OpportunitiesTab'

describe('OpportunitiesTab', () => {
  it('renders the empty state', () => {
    render(<OpportunitiesTab opportunities={[]} navigate={vi.fn()} />)
    expect(screen.getByText('No opportunities identified')).toBeInTheDocument()
  })
  it('renders value, probability, close date and details and navigates to the chosen opportunity', () => {
    const navigate = vi.fn()
    render(
      <OpportunitiesTab
        opportunities={[
          {
            id: 7,
            title: 'Renewal',
            description: 'Annual contract',
            opportunity_type: 'upsell',
            estimated_value: 12500,
            probability: 80,
            expected_close_date: '2026-01-15T12:00:00',
          },
          { id: 8, title: 'New lead' },
        ]}
        navigate={navigate}
      />
    )
    for (const text of ['Annual contract', 'upsell', '$12,500', '80%', 'Close: Jan 15, 2026'])
      expect(screen.getByText(text)).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(2)
    fireEvent.click(screen.getByText('New lead'))
    expect(navigate).toHaveBeenCalledExactlyOnceWith('/opportunities/8')
  })
  it('omits unknown financial details and close date', () => {
    render(
      <OpportunitiesTab
        opportunities={[{ id: 1, title: 'Unqualified lead', estimated_value: null, probability: null }]}
        navigate={vi.fn()}
      />
    )
    expect(screen.queryByText(/probability/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Close:/)).not.toBeInTheDocument()
    expect(screen.queryByText(/\$/)).not.toBeInTheDocument()
  })
  it.each([
    ['new', 'bg-blue-100'],
    ['qualified', 'bg-purple-100'],
    ['in_progress', 'bg-yellow-100'],
    ['won', 'bg-green-100'],
    ['lost', 'bg-red-100'],
    ['unknown', 'bg-gray-100'],
  ])('renders %s status', (status, color) => {
    render(<OpportunitiesTab opportunities={[{ id: 1, title: 'Lead', status }]} navigate={vi.fn()} />)
    expect(screen.getByText(status)).toHaveClass(color)
  })
  it.each([
    ['hot', 'bg-red-100'],
    ['warm', 'bg-orange-100'],
    ['cold', 'bg-blue-100'],
  ])('renders %s lead temperature', (lead_temperature, color) => {
    render(<OpportunitiesTab opportunities={[{ id: 1, title: 'Lead', lead_temperature }]} navigate={vi.fn()} />)
    expect(screen.getByText(lead_temperature)).toHaveClass(color)
  })
})
