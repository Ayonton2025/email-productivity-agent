import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PromptManager from '../components/prompts/PromptManager'
import { PromptContext } from '../context/PromptContext'
import { aiApi } from '../services/api'

vi.mock('../services/api', () => ({ aiApi: { assistWorkspace: vi.fn() } }))

describe('prompt manager', () => {
  const context = {
    prompts: [
      {
        id: '1',
        name: 'Reply Helper',
        description: 'Draft replies',
        template: 'Reply to {{email}}',
        category: 'reply_draft',
        is_system: false,
      },
    ],
    createPrompt: vi.fn().mockResolvedValue({}),
    updatePrompt: vi.fn().mockResolvedValue({}),
    deletePrompt: vi.fn().mockResolvedValue({}),
    testPrompt: vi.fn().mockResolvedValue({ output: 'Test output' }),
    loading: false,
  }
  it('filters prompts by search text', () => {
    render(
      <PromptContext.Provider value={context}>
        <PromptManager />
      </PromptContext.Provider>
    )
    expect(screen.getAllByText('Reply Helper').length).toBeGreaterThan(0)
    fireEvent.change(screen.getByPlaceholderText('Search prompts...'), { target: { value: 'missing' } })
    expect(screen.getByText('No prompts found')).toBeInTheDocument()
  })

  it('filters prompts by category', () => {
    render(
      <PromptContext.Provider value={context}>
        <PromptManager />
      </PromptContext.Provider>
    )
    fireEvent.change(screen.getByDisplayValue('All Categories'), { target: { value: 'summary' } })
    expect(screen.getByText('No prompts found')).toBeInTheDocument()
  })

  it('creates a prompt through the form', async () => {
    render(
      <PromptContext.Provider value={context}>
        <PromptManager />
      </PromptContext.Provider>
    )
    fireEvent.click(screen.getByRole('button', { name: 'New Prompt' }))
    fireEvent.change(screen.getByLabelText('Name *'), { target: { value: 'New prompt' } })
    fireEvent.change(screen.getByLabelText('Template *'), { target: { value: 'Summarize this' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Prompt' }))
    await waitFor(() =>
      expect(context.createPrompt).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'New prompt', template: 'Summarize this' })
      )
    )
  })

  it('updates, tests, and deletes a selected prompt', async () => {
    window.confirm = vi.fn(() => true)
    render(
      <PromptContext.Provider value={context}>
        <PromptManager />
      </PromptContext.Provider>
    )
    fireEvent.click(screen.getByRole('button', { name: 'Edit Prompt' }))
    fireEvent.change(screen.getByDisplayValue('Reply Helper'), { target: { value: 'Updated prompt' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save Prompt' }))
    await waitFor(() => expect(context.updatePrompt).toHaveBeenCalled())
    fireEvent.click(screen.getByRole('button', { name: 'Test' }))
    fireEvent.change(screen.getByPlaceholderText('Enter test email content...'), { target: { value: 'Test email' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run Test' }))
    await waitFor(() => expect(context.testPrompt).toHaveBeenCalledWith('1', 'Test email'))
    fireEvent.click(screen.getByRole('button', { name: 'Delete prompt' }))
    await waitFor(() => expect(context.deletePrompt).toHaveBeenCalledWith('1'))
  })

  it('shows an AI draft generation failure', async () => {
    aiApi.assistWorkspace.mockRejectedValueOnce({ response: { data: { detail: 'AI unavailable' } } })
    render(
      <PromptContext.Provider value={context}>
        <PromptManager />
      </PromptContext.Provider>
    )
    fireEvent.change(screen.getByPlaceholderText('Describe the prompt you want...'), {
      target: { value: 'Draft a reply' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Generate' }))
    expect(await screen.findByText('AI unavailable')).toBeInTheDocument()
  })
})
