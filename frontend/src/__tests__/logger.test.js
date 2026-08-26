import { afterEach, describe, expect, it, vi } from 'vitest'
import { logger } from '../utils/logger'

describe('frontend logger', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('does not write directly to the console', () => {
    const consoleSpy = vi.spyOn(console, 'log')
    logger.info('diagnostic event')
    expect(consoleSpy).not.toHaveBeenCalled()
  })

  it('emits a structured development event', () => {
    const eventSpy = vi.fn()
    window.addEventListener('bylix:log', eventSpy)
    logger.error('request failed', { status: 503 })
    expect(eventSpy).toHaveBeenCalledOnce()
    expect(eventSpy.mock.calls[0][0].detail.level).toBe('error')
    window.removeEventListener('bylix:log', eventSpy)
  })
})
