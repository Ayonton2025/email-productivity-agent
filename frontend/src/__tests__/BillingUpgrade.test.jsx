import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import BillingUpgrade from '../components/billing/BillingUpgrade';
import { useAuth } from '../context/AuthContext';
import { useSubscription } from '../hooks/useSubscription';
import { getAvailablePlans } from '../services/paymentService';

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }));
vi.mock('../hooks/useSubscription', () => ({ useSubscription: vi.fn() }));
vi.mock('../services/paymentService', () => ({
  initiateUpgrade: vi.fn(),
  getAvailablePaymentMethods: vi.fn(),
  getAvailablePlans: vi.fn(),
}));

// Basic render test and Paystack default behavior
describe('BillingUpgrade', () => {
  it('renders plan cards and starts hosted checkout flow without preselecting payment controls', async () => {
    useAuth.mockReturnValue({ user: { id: 'user-1' } });
    useSubscription.mockReturnValue({ userPlan: 'personal' });
    getAvailablePlans.mockRejectedValue(new Error('offline test'));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
    render(
      <MemoryRouter>
        <BillingUpgrade />
      </MemoryRouter>
    );

    // Expect plan price elements to render (e.g., $)
    const priceElems = await screen.findAllByText(/\$/i);
    expect(priceElems.length).toBeGreaterThan(0);

    // Checkout now defers payment method selection to hosted provider UI
    expect(screen.getByText(/opens hosted checkout with card as default/i)).toBeInTheDocument();
  });
});
