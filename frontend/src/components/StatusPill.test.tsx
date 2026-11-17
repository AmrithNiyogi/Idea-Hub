import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusPill } from './StatusPill';

describe('StatusPill', () => {
  it('uses STATUS_META labels and falls back for unknown', () => {
    const { rerender } = render(<StatusPill status="accepted" />);
    expect(screen.getByText('Accepted')).toBeInTheDocument();
    rerender(<StatusPill status="custom_stage" />);
    expect(screen.getByText('custom_stage')).toBeInTheDocument();
  });
});
