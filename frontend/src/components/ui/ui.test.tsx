import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AgentBlock } from './AgentBlock';
import { DimBar, DimLegend } from './DimBar';
import { EmptyState } from './EmptyState';
import { Kpi } from './Kpi';
import { Pill } from './Pill';
import { TabsNav } from './TabsNav';

describe('UI primitives', () => {
  it('EmptyState / Kpi / Pill / AgentBlock', () => {
    render(
      <>
        <EmptyState title="Nothing" body="Try again" action={<button>Go</button>} />
        <EmptyState title="Bare" />
        <Kpi label="Ideas" value={12} sub="live" tone="success" />
        <Kpi label="X" value="—" />
        <Kpi label="Y" value={1} tone="unknown" />
        <Pill variant="brand" icon="spark" title="tip">
          Brand
        </Pill>
        <Pill>Plain</Pill>
        <AgentBlock agent="Scout" kind="hint" how="heuristic">
          Hello
        </AgentBlock>
      </>,
    );
    expect(screen.getByText('Nothing')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('Brand')).toBeInTheDocument();
    expect(screen.getByText('Scout')).toBeInTheDocument();
  });

  it('DimBar / DimLegend', () => {
    const { rerender } = render(<DimBar dims={{ quality: 2, collab: 1, delivery: 1, impact: 0 }} />);
    expect(screen.getByRole('img')).toHaveAttribute('aria-label', expect.stringContaining('Quality 2'));
    rerender(<DimBar dims={null} />);
    expect(screen.getByRole('img')).toBeInTheDocument();
    render(<DimLegend />);
    expect(screen.getByLabelText(/Breakdown colours/i)).toBeInTheDocument();
  });

  it('TabsNav link and button modes', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <MemoryRouter>
        <TabsNav
          tabs={[
            { id: 'a', label: 'A', href: '/a', count: 2 },
            { id: 'b', label: 'B', count: 0 },
          ]}
          active="a"
          onSelect={onSelect}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole('tab', { name: /A/i })).toHaveAttribute('href', '/a');
    await user.click(screen.getByRole('tab', { name: 'B' }));
    expect(onSelect).toHaveBeenCalledWith('b');
  });
});
