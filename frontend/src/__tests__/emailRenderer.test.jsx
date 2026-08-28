import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EmailContentRenderer } from '../utils/emailParser';

describe('email content renderer', () => {
  it('sanitizes scripts and inline handlers', () => {
    const { container } = render(
      <EmailContentRenderer bodyHtml={'<script>bad()</script><p onclick="bad()">Safe</p>'} />
    );
    expect(screen.getByText('Safe')).toBeInTheDocument();
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('[onclick]')).toBeNull();
  });
});
