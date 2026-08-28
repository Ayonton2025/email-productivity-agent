import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PromptManager from '../components/prompts/PromptManager';
import { PromptContext } from '../context/PromptContext';

vi.mock('../services/api', () => ({ aiApi: { assistWorkspace: vi.fn() } }));

describe('prompt manager', () => {
  let context;

  beforeEach(() => {
    vi.clearAllMocks();
    window.confirm = vi.fn(() => true);
    context = {
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
    };
  });
  it('filters prompts by search text', () => {
    render(
      <PromptContext.Provider value={context}>
        <PromptManager />
      </PromptContext.Provider>
    );
    expect(screen.getAllByText('Reply Helper').length).toBeGreaterThan(0);
    fireEvent.change(screen.getByPlaceholderText('Search prompts...'), {
      target: { value: 'missing' },
    });
    expect(screen.getByText('No prompts found')).toBeInTheDocument();
  });

  it('renders a loading state supplied by the API context', () => {
    context.loading = true;
    context.prompts = [];
    render(
      <PromptContext.Provider value={context}>
        <PromptManager />
      </PromptContext.Provider>
    );
    expect(screen.getByText(/loading prompts/i)).toBeInTheDocument();
  });

  it('deletes a selected prompt after confirmation', async () => {
    context.deletePrompt.mockResolvedValue(undefined);
    render(
      <PromptContext.Provider value={context}>
        <PromptManager />
      </PromptContext.Provider>
    );
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    await waitFor(() => expect(context.deletePrompt).toHaveBeenCalledWith('1'));
  });

  it('shows a friendly error when deleting fails', async () => {
    context.deletePrompt.mockRejectedValue(new Error('API unavailable'));
    render(
      <PromptContext.Provider value={context}>
        <PromptManager />
      </PromptContext.Provider>
    );
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    expect(await screen.findByText('Failed to delete prompt: API unavailable')).toBeInTheDocument();
  });
});
