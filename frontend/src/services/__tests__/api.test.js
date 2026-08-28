import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getFriendlyApiError, handleApiError, handleApiSuccess } from '../api'

describe('API response handling', () => {
  beforeEach(() => {
    localStorage.clear()
    window.history.replaceState({}, '', '/inbox')
  })

  it('removes stale authentication and schedules a login redirect after a 401', async () => {
    localStorage.setItem('auth_token', 'expired-token')
    localStorage.setItem('user', JSON.stringify({ id: 'user-1' }))
    const scheduleRedirect = vi.fn()
    const error = { response: { status: 401, data: { detail: 'Session expired' } }, message: 'Unauthorized' }

    await expect(handleApiError(error, scheduleRedirect)).rejects.toBe(error)

    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
    expect(scheduleRedirect).toHaveBeenCalledOnce()
    expect(scheduleRedirect.mock.calls[0][0]).toEqual(expect.any(Function))
  })

  it('returns a successful response unchanged', () => {
    const response = { status: 200, data: { emails: [] } }
    expect(handleApiSuccess(response)).toBe(response)
  })

  it('adds a friendly message to server failures while preserving diagnostics', async () => {
    const error = { response: { status: 503, data: {} }, message: 'Request failed with status code 503' }

    await expect(handleApiError(error)).rejects.toBe(error)

    expect(error.friendlyMessage).toBe('The server encountered a problem. Please try again shortly.')
    expect(getFriendlyApiError(error)).not.toContain('503')
  })

  it('does not redirect when a public page receives a 401', async () => {
    window.history.replaceState({}, '', '/register')
    localStorage.setItem('auth_token', 'expired-token')
    const scheduleRedirect = vi.fn()

    await expect(
      handleApiError({ response: { status: 401, data: {} }, message: 'Unauthorized' }, scheduleRedirect)
    ).rejects.toBeDefined()

    expect(scheduleRedirect).not.toHaveBeenCalled()
  })
})
