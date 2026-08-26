import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import ProtectedRoute from '../components/ProtectedRoute'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

describe('protected routes', () => {
  it('renders children for authenticated users', () => {
    useAuth.mockReturnValue({ isAuthenticated: true, loading: false })
    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Private workspace</div>
        </ProtectedRoute>
      </MemoryRouter>
    )
    expect(screen.getByText('Private workspace')).toBeInTheDocument()
  })
  it('shows access denied while redirecting guests', () => {
    useAuth.mockReturnValue({ isAuthenticated: false, loading: false })
    render(
      <MemoryRouter initialEntries={['/private']}>
        <ProtectedRoute>
          <div>Private</div>
        </ProtectedRoute>
      </MemoryRouter>
    )
    expect(screen.getByText('Access Denied')).toBeInTheDocument()
  })
})
