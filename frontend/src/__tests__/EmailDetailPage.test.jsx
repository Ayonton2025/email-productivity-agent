import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import EmailDetailPage from '../components/inbox/EmailDetailPage';
import { emailApi } from '../services/api';

vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: { plan: 'professional' } }) }));
vi.mock('../services/api', () => ({
  emailApi: { generateReply: vi.fn(), sendEmail: vi.fn() },
  agentApi: { processEmail: vi.fn() },
}));
vi.mock('../components/inbox/AttachmentsSection', () => ({
  default: () => <div>Attachments</div>,
}));

const email = {
  id: 'email-1',
  sender: 'customer@example.com',
  subject: 'Need help',
  body: 'Could you help with my account?',
  timestamp: '2026-08-27T10:00:00Z',
  priority: 'high',
};

const renderPage = () =>
  render(
    <MemoryRouter>
      <EmailDetailPage email={email} accountId="account-1" onBack={vi.fn()} />
    </MemoryRouter>
  );

describe('email reply composer flow', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the email and composer action', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: 'Need help' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Generate AI Reply' })).toBeEnabled();
  });

  it('shows loading, then renders a generated reply', async () => {
    let resolveRequest;
    emailApi.generateReply.mockReturnValue(new Promise((resolve) => (resolveRequest = resolve)));
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Generate AI Reply' }));
    expect(screen.getByRole('button', { name: 'Generating…' })).toBeDisabled();
    resolveRequest({ data: { reply: 'Happy to help with your account.', ai_generated: true } });

    expect(await screen.findByText('Happy to help with your account.')).toBeInTheDocument();
  });

  it('renders a safe fallback and error when generation fails', async () => {
    emailApi.generateReply.mockRejectedValue(new Error('Provider unavailable'));
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Generate AI Reply' }));

    expect(await screen.findByText('Provider unavailable')).toBeInTheDocument();
    expect(screen.getByText(/Thank you for your email regarding/)).toBeInTheDocument();
  });

  it('sends the generated reply with thread metadata', async () => {
    emailApi.generateReply.mockResolvedValue({ data: { reply: 'Reply body', ai_generated: true } });
    emailApi.sendEmail.mockResolvedValue({ data: { success: true } });
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: 'Generate AI Reply' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Send reply' }));

    await waitFor(() =>
      expect(emailApi.sendEmail).toHaveBeenCalledWith(
        'account-1',
        expect.objectContaining({
          to: 'customer@example.com',
          subject: 'Re: Need help',
          body_text: 'Reply body',
        })
      )
    );
    expect(await screen.findByText('Reply sent successfully.')).toBeInTheDocument();
  });
});
