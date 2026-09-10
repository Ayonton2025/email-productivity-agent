import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import RisksTab from '../components/insights/tabs/RisksTab'

describe('RisksTab', () => {
  it('renders the empty state', () => {
    render(<RisksTab risks={[]} navigate={vi.fn()} />)
    expect(screen.getByText('No risks identified')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 3 })).not.toBeInTheDocument()
  })
  it('renders list details and navigates to the selected risk', () => {
    const navigate = vi.fn()
    render(
      <RisksTab
        risks={[
          {
            id: 1,
            title: 'Late payment',
            description: 'Invoice is pending',
            risk_type: 'financial',
            potential_impact: 'Cash flow delay',
            urgency_score: 85,
            created_at: '2026-01-15T12:00:00',
          },
          { id: 2, title: 'Missing date' },
        ]}
        navigate={navigate}
      />
    )
    for (const text of [
      'Late payment',
      'Invoice is pending',
      'financial',
      'Created: Jan 15, 2026',
      'Urgency: 85/100',
      'Created: No date',
    ])
      expect(screen.getByText(text)).toBeInTheDocument()
    expect(screen.getByText(/Cash flow delay/)).toBeInTheDocument()
    expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(2)
    fireEvent.click(screen.getByText('Missing date'))
    expect(navigate).toHaveBeenCalledExactlyOnceWith('/risks/2')
  })
  it.each([
    ['critical', 'bg-red-100'],
    ['HIGH', 'bg-orange-100'],
    ['medium', 'bg-yellow-100'],
    ['low', 'bg-blue-100'],
    ['unknown', 'bg-gray-100'],
  ])('renders %s severity', (severity, color) => {
    render(<RisksTab risks={[{ id: 1, title: 'Risk', severity }]} navigate={vi.fn()} />)
    expect(screen.getByText(severity)).toHaveClass(color)
  })
})
