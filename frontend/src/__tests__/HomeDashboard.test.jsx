import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Home } from '../components/Home'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../App', () => ({ AppContent: () => <div>Authenticated dashboard</div> }))
vi.mock('../components/landing/LandingPage', () => ({ default: () => <div>Public landing page</div> }))

describe('dashboard routing', () => {
  it('renders the dashboard for an authenticated user', () => {
    useAuth.mockReturnValue({ isAuthenticated: true, loading: false })
    render(<Home />)
    expect(screen.getByText('Authenticated dashboard')).toBeInTheDocument()
  })
  it('renders a loading state before auth resolves', () => {
    useAuth.mockReturnValue({ isAuthenticated: false, loading: true })
    render(<Home />)
    expect(screen.getByText('Loading your workspace...')).toBeInTheDocument()
  })
})
