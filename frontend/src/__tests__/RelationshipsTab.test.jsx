import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import RelationshipsTab from '../components/insights/tabs/RelationshipsTab'

describe('RelationshipsTab', () => {
  it('renders independent empty company and contact states', () => {
    render(<RelationshipsTab relationships={{ companies: [], top_contacts: [] }} navigate={vi.fn()} />)
    expect(screen.getByText('No companies found')).toBeInTheDocument()
    expect(screen.getByText('No contacts found')).toBeInTheDocument()
  })
  it('renders company details and named/email-only contacts with score fallbacks and navigation', () => {
    const navigate = vi.fn()
    render(
      <RelationshipsTab
        relationships={{
          companies: [{ id: 10, name: 'Example Ltd', domain: 'example.test', total_contacts: 2 }],
          top_contacts: [
            {
              id: 20,
              first_name: 'Alice',
              display_name: 'Alice Sample',
              email: 'alice@example.test',
              relationship_score: 81.6,
            },
            { id: 21, email: 'bob@example.test' },
          ],
        }}
        navigate={navigate}
      />
    )
    for (const text of ['example.test', '2 contacts', 'A', 'B', 'Score: 82', 'Score: 0'])
      expect(screen.getByText(text)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('heading', { name: 'Example Ltd' }))
    expect(navigate).toHaveBeenLastCalledWith('/companies/10')
    fireEvent.click(screen.getByRole('heading', { name: 'Alice Sample' }))
    expect(navigate).toHaveBeenLastCalledWith('/contacts/20')
    fireEvent.click(screen.getByRole('heading', { name: 'bob@example.test' }))
    expect(navigate).toHaveBeenLastCalledWith('/contacts/21')
  })
  it.each([
    ['active', 'bg-green-100'],
    ['warming', 'bg-yellow-100'],
    ['inactive', 'bg-gray-100'],
  ])('renders %s company and contact status', (relationship_status, color) => {
    render(
      <RelationshipsTab
        relationships={{
          companies: [{ id: 1, name: 'Company', relationship_status }],
          top_contacts: [{ id: 2, email: 'sample@example.test', relationship_status }],
        }}
        navigate={vi.fn()}
      />
    )
    expect(screen.getAllByText(relationship_status)).toHaveLength(2)
    for (const badge of screen.getAllByText(relationship_status)) expect(badge).toHaveClass(color)
  })
})
