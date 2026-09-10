import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import DeadlinesTab from '../components/insights/tabs/DeadlinesTab'

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-01-15T12:00:00Z'))
})
afterEach(() => vi.useRealTimers())
describe('DeadlinesTab', () => {
  it('renders the empty state', () => {
    render(<DeadlinesTab deadlines={[]} />)
    expect(screen.getByText('No upcoming deadlines')).toBeInTheDocument()
  })
  it('renders commitment details, due date and owner', () => {
    render(
      <DeadlinesTab
        deadlines={[
          {
            id: 1,
            title: 'Send report',
            description: 'Quarterly summary',
            deadline: '2026-01-16T12:00:00',
            commitment_type: 'delivery',
            committed_by: 'Alex',
            priority: 'high',
          },
        ]}
      />
    )
    for (const text of ['Send report', 'Quarterly summary', 'Due: Jan 16, 2026', 'Type: delivery', 'By: Alex'])
      expect(screen.getByText(text)).toBeInTheDocument()
  })
  it.each([
    ['past', '2026-01-15T11:59:59Z', true],
    ['now', '2026-01-15T12:00:00Z', false],
    ['future', '2026-01-15T12:00:01Z', false],
    ['missing', null, false],
  ])('marks only past deadlines overdue: %s', (_label, deadline, overdue) => {
    render(<DeadlinesTab deadlines={[{ id: 1, title: 'Task', deadline }]} />)
    if (overdue) expect(screen.getByText('Overdue')).toBeInTheDocument()
    else expect(screen.queryByText('Overdue')).not.toBeInTheDocument()
    if (!deadline) expect(screen.getByText('Due: No date')).toBeInTheDocument()
    expect(screen.queryByText(/By:/)).not.toBeInTheDocument()
  })
  it.each([
    ['high', 'bg-red-100'],
    ['medium', 'bg-yellow-100'],
    ['low', 'bg-blue-100'],
  ])('renders %s priority', (priority, color) => {
    render(<DeadlinesTab deadlines={[{ id: 1, title: 'Task', priority }]} />)
    expect(screen.getByText(priority)).toHaveClass(color)
  })
})
