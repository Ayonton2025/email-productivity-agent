import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import Login from '../components/auth/Login'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

describe('login flow', () => {
  it('submits entered credentials', async () => {
    const login = vi.fn().mockResolvedValue({ success: true })
    useAuth.mockReturnValue({ login, isAuthenticated: false })
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    )
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'user@example.test' } })
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'password' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(login).toHaveBeenCalledWith('user@example.test', 'password'))
  })
  it('shows authentication failures', async () => {
    useAuth.mockReturnValue({
      login: vi.fn().mockResolvedValue({ success: false, error: 'Invalid credentials' }),
      isAuthenticated: false,
    })
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    )
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'user@example.test' } })
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    expect(await screen.findByText('Invalid credentials')).toBeInTheDocument()
  })
})
