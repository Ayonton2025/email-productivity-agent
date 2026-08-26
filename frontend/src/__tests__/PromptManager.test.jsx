import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PromptManager from '../components/prompts/PromptManager'
import { PromptContext } from '../context/PromptContext'

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
    createPrompt: vi.fn(),
    updatePrompt: vi.fn(),
    deletePrompt: vi.fn(),
    testPrompt: vi.fn(),
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
})
