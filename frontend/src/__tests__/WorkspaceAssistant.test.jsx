import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import WorkspaceAssistant from '../components/assistant/WorkspaceAssistant'
import { aiApi } from '../services/api'

vi.mock('../services/api', () => ({ aiApi: { assistWorkspace: vi.fn() } }))

describe('AI assistant flow', () => {
  it('submits an objective and renders the response', async () => {
    aiApi.assistWorkspace.mockResolvedValue({
      data: { assistant_message: 'Draft ready', provider: 'mock', model: 'mock:test' },
    })
    render(<WorkspaceAssistant page="campaigns" />)
    fireEvent.click(screen.getByRole('button', { name: /workplace/i }))
    fireEvent.change(screen.getByPlaceholderText(/tell workplace/i), { target: { value: 'Create a campaign' } })
    fireEvent.click(screen.getByRole('button', { name: /run assistant/i }))
    await waitFor(() =>
      expect(aiApi.assistWorkspace).toHaveBeenCalledWith({
        page: 'campaigns',
        objective: 'Create a campaign',
        mode: 'draft',
      })
    )
    expect(await screen.findByText('Draft ready')).toBeInTheDocument()
  })
})
