import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { PremiumPrompt } from '../components/premium/PremiumPrompt';
import { useAuth } from '../context/AuthContext';

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }));

describe('premium prompt', () => {
  it('shows credit usage and supports dismissal', () => {
    useAuth.mockReturnValue({ user: { id: 'user' } });
    const onClose = vi.fn();
    render(
      <MemoryRouter>
        <PremiumPrompt
          isOpen
          limitType="credits"
          currentUsage={90}
          monthlyLimit={100}
          onClose={onClose}
        />
      </MemoryRouter>
    );
    expect(screen.getByText(/90% of your AI credits used/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));
    expect(onClose).toHaveBeenCalledWith('credits', true);
  });
});
