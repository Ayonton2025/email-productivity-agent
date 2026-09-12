import { render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import BackgroundCanvas from '../components/landing/BackgroundCanvas'

describe('BackgroundCanvas', () => {
  afterEach(() => vi.restoreAllMocks())

  it('draws on mount and cancels animation on unmount', () => {
    const animationFrame = vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(1)
    const cancelAnimationFrame = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {})
    const context = {
      fillRect: vi.fn(),
      beginPath: vi.fn(),
      arc: vi.fn(),
      stroke: vi.fn(),
    }
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(context)

    const { unmount } = render(<BackgroundCanvas scrollY={12} />)

    expect(context.fillRect).toHaveBeenCalled()
    expect(animationFrame).toHaveBeenCalled()
    unmount()
    expect(cancelAnimationFrame).toHaveBeenCalledWith(1)
  })
})
