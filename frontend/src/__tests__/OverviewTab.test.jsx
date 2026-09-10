import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import OverviewTab from '../components/insights/tabs/OverviewTab'

const empty = { analytics: null, risks: [], opportunities: [], deadlines: [], relationships: null }
const count = (label) => screen.getByText(label).nextElementSibling

describe('OverviewTab', () => {
  it('renders totals, category counts and sentiments, limiting categories to three', () => {
    render(
      <OverviewTab
        {...empty}
        risks={[{ id: 1, title: 'Risk A' }]}
        opportunities={[{ id: 2, title: 'Opportunity A' }]}
        deadlines={[{ id: 3 }, { id: 4 }]}
        relationships={{ total_contacts: 9 }}
        analytics={{
          email_statistics: {
            total_emails: 36,
            by_category: { Sales: 11, Support: 12, Billing: 13, Hidden: 99 },
            by_sentiment: { positive: 21, negative: 15 },
          },
        }}
        navigate={vi.fn()}
      />
    )
    for (const [label, value] of [
      ['Active Risks', '1'],
      ['Opportunities', '1'],
      ['Upcoming Deadlines', '2'],
      ['Total Contacts', '9'],
      ['Total Emails', '36'],
    ])
      expect(count(label)).toHaveTextContent(value)
    for (const [label, value] of [
      ['Sales', '11'],
      ['Support', '12'],
      ['Billing', '13'],
      ['positive', '21'],
      ['negative', '15'],
    ])
      expect(screen.getByText(label).parentElement).toHaveTextContent(value)
    expect(screen.queryByText('Hidden')).not.toBeInTheDocument()
  })
  it('renders only five recent risks and opportunities with details and navigation', () => {
    const navigate = vi.fn()
    const risks = Array.from({ length: 6 }, (_, id) => ({
      id,
      title: `Risk ${id}`,
      description: `Risk description ${id}`,
      severity: id === 0 ? 'critical' : 'high',
      created_at: '2026-01-15T12:00:00',
    }))
    const opportunities = Array.from({ length: 6 }, (_, id) => ({
      id,
      title: `Opportunity ${id}`,
      description: `Opportunity description ${id}`,
      status: 'new',
      estimated_value: 2500,
      probability: 60,
    }))
    render(<OverviewTab {...empty} risks={risks} opportunities={opportunities} navigate={navigate} />)
    expect(screen.getByRole('heading', { name: 'Recent Risks' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Recent Opportunities' })).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(10)
    expect(screen.queryByText('Risk 5')).not.toBeInTheDocument()
    expect(screen.queryByText('Opportunity 5')).not.toBeInTheDocument()
    expect(screen.getByText('Risk description 0')).toBeInTheDocument()
    expect(screen.getByText('critical')).toHaveClass('bg-red-100')
    expect(screen.getAllByText('Jan 15, 2026')).toHaveLength(5)
    expect(screen.getAllByText('$2,500')).toHaveLength(5)
    expect(screen.getAllByText('60% probability')).toHaveLength(5)
    fireEvent.click(screen.getByText('Risk 4'))
    expect(navigate).toHaveBeenLastCalledWith('/risks/4')
    fireEvent.click(screen.getByText('Opportunity 4'))
    expect(navigate).toHaveBeenLastCalledWith('/opportunities/4')
  })
  it('handles absent analytics and relationships without showing empty recent sections', () => {
    const { rerender } = render(<OverviewTab {...empty} navigate={vi.fn()} />)
    for (const label of ['Active Risks', 'Opportunities', 'Upcoming Deadlines', 'Total Contacts'])
      expect(count(label)).toHaveTextContent('0')
    expect(screen.queryByText('Recent Risks')).not.toBeInTheDocument()
    expect(screen.queryByText('Recent Opportunities')).not.toBeInTheDocument()
    expect(screen.queryByText('Email Statistics (Last 30 Days)')).not.toBeInTheDocument()
    rerender(<OverviewTab {...empty} analytics={{}} navigate={vi.fn()} />)
    expect(count('Total Emails')).toHaveTextContent('0')
  })
})
