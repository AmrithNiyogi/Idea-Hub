import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PollBubble } from './PollBubble';
import type { GroupPoll } from '../../types/groups';

const poll: GroupPoll = {
  id: 'p1',
  group_id: 'g1',
  question: 'Lunch?',
  options: ['Pizza', 'Sushi'],
  created_by: 'u-other',
  closed_at: null,
  ends_at: null,
  created_at: '2026-01-01T10:00:00Z',
  multi_select: false,
  counts: [2, 1],
  total_votes: 3,
  my_votes: [0],
};

const base = {
  senderName: 'Sam',
  mine: false,
  createdAt: '2026-01-01T10:00:00Z',
  canVote: true,
  canClose: false,
  busy: false,
  onVote: vi.fn(),
  onClose: vi.fn(),
};

describe('PollBubble', () => {
  it('shows question, options and counts', () => {
    render(<PollBubble {...base} poll={poll} />);
    expect(screen.getByText('Lunch?')).toBeTruthy();
    expect(screen.getByText('Pizza')).toBeTruthy();
    expect(screen.getByText('2')).toBeTruthy();
    expect(screen.getByText(/Select one · 3 votes/)).toBeTruthy();
  });

  it('calls onVote with the option index when an option is clicked', async () => {
    const onVote = vi.fn();
    render(<PollBubble {...base} onVote={onVote} poll={poll} />);
    await userEvent.click(screen.getByRole('radio', { name: /Sushi/ }));
    expect(onVote).toHaveBeenCalledWith(1);
  });

  it('disables voting when the viewer cannot post', () => {
    render(<PollBubble {...base} canVote={false} poll={poll} />);
    expect(screen.getByRole('radio', { name: /Pizza/ }).hasAttribute('disabled')).toBe(true);
  });

  it('shows Close only to users allowed to close, and calls onClose', async () => {
    const onClose = vi.fn();
    const { rerender } = render(<PollBubble {...base} poll={poll} />);
    expect(screen.queryByRole('button', { name: 'Close' })).toBeNull();
    rerender(<PollBubble {...base} canClose onClose={onClose} poll={poll} />);
    await userEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('renders a placeholder when the poll is missing', () => {
    render(<PollBubble {...base} poll={undefined} />);
    expect(screen.getByText('Poll unavailable')).toBeTruthy();
  });

  it('marks multi-select polls as checkboxes', () => {
    render(<PollBubble {...base} poll={{ ...poll, multi_select: true }} />);
    expect(screen.getAllByRole('checkbox')).toHaveLength(2);
    expect(screen.getByText(/Select one or more/)).toBeTruthy();
  });
});
