import { usePromptManager } from '../hooks/usePromptManager'
import { PromptContext } from '../context/PromptContext'
import React from 'react'
import { act, cleanup, fireEvent, render, renderHook, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import ToastProvider from '../components/shared/ToastProvider'
import { notifications, notify } from '../utils/notifications'
afterEach(() => {
  cleanup()
  notifications.clear()
  vi.unstubAllGlobals()
})
it('announces success and errors, keeps children, and supports dismissal', () => {
  render(
    <ToastProvider>
      <p>Workspace</p>
    </ToastProvider>
  )
  act(() => {
    notify('Saved', 'success')
    notify('Could not save', 'error')
  })
  expect(screen.getByRole('status')).toHaveTextContent('Saved')
  expect(screen.getByRole('alert')).toHaveTextContent('Could not save')
  fireEvent.click(screen.getAllByRole('button', { name: 'Dismiss notification' })[0])
  expect(screen.queryByText('Saved')).not.toBeInTheDocument()
  expect(screen.getByText('Workspace')).toBeInTheDocument()
})
it('bounds the visible queue to the latest five notices', () => {
  render(<ToastProvider />)
  act(() => {
    for (let i = 0; i < 7; i++) notify('Notice ' + i)
  })
  expect(screen.getAllByRole('status')).toHaveLength(5)
  expect(screen.queryByText('Notice 0')).not.toBeInTheDocument()
  expect(screen.getByText('Notice 6')).toBeInTheDocument()
})

it.each(['unavailable', 'denied'])('reports clipboard failure when access is %s', async (mode) => {
  const context = {
    prompts: [],
    createPrompt: vi.fn(),
    updatePrompt: vi.fn(),
    deletePrompt: vi.fn(),
    testPrompt: vi.fn(),
    loading: false,
  }
  const wrapper = ({ children }) => <PromptContext.Provider value={context}>{children}</PromptContext.Provider>
  const { result } = renderHook(() => usePromptManager(), { wrapper })
  vi.stubGlobal('navigator', {
    clipboard:
      mode === 'unavailable' ? undefined : { writeText: vi.fn().mockRejectedValue(new Error('Permission denied')) },
  })
  await act(() => result.current.copyToClipboard('Template'))
  expect(notifications.getSnapshot()).toEqual([
    expect.objectContaining({ type: 'error', message: 'Could not copy the prompt. Please copy it manually.' }),
  ])
})
