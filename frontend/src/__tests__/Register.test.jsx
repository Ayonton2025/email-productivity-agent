import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import Register from '../components/auth/Register'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

describe('signup flow', () => {
  it('rejects mismatched passwords before calling the API', async () => {
    const register = vi.fn()
    useAuth.mockReturnValue({ register, registerHosted: vi.fn(), isAuthenticated: false })
    render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    )
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Test User' } })
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'user@example.test' } })
    fireEvent.change(screen.getByLabelText(/^password \*/i), { target: { value: 'password1' } })
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'password2' } })
    fireEvent.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByText('Passwords do not match')).toBeInTheDocument()
    expect(register).not.toHaveBeenCalled()
  })
})
