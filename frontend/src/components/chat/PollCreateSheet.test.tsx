import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PollCreateSheet } from './PollCreateSheet';

function setup(onSubmit = vi.fn(), onClose = vi.fn()) {
  render(<PollCreateSheet open busy={false} onClose={onClose} onSubmit={onSubmit} />);
  return { onSubmit, onClose };
}

describe('PollCreateSheet', () => {
  it('renders nothing when closed', () => {
    const { container } = render(
      <PollCreateSheet open={false} busy={false} onClose={vi.fn()} onSubmit={vi.fn()} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('keeps Send disabled until question and two options are filled', async () => {
    setup();
    const send = screen.getByRole('button', { name: 'Send' });
    expect(send.hasAttribute('disabled')).toBe(true);
    await userEvent.type(screen.getByPlaceholderText('Ask a question'), 'Lunch?');
    expect(send.hasAttribute('disabled')).toBe(true);
    await userEvent.type(screen.getByPlaceholderText('Option 1'), 'Pizza');
    await userEvent.type(screen.getByPlaceholderText('Option 2'), 'Sushi');
    expect(send.hasAttribute('disabled')).toBe(false);
  });

  it('submits a trimmed draft with multi-select off by default', async () => {
    const { onSubmit } = setup();
    await userEvent.type(screen.getByPlaceholderText('Ask a question'), '  Lunch?  ');
    await userEvent.type(screen.getByPlaceholderText('Option 1'), ' Pizza ');
    await userEvent.type(screen.getByPlaceholderText('Option 2'), 'Sushi');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));
    expect(onSubmit).toHaveBeenCalledWith({
      question: 'Lunch?',
      options: ['Pizza', 'Sushi'],
      multi: false,
      endsAt: null,
    });
  });

  it('adds and removes options', async () => {
    setup();
    await userEvent.click(screen.getByRole('button', { name: '+ Add option' }));
    expect(screen.getByPlaceholderText('Option 3')).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: 'Remove option 3' }));
    expect(screen.queryByPlaceholderText('Option 3')).toBeNull();
  });

  it('turns on multi-select and sends it', async () => {
    const { onSubmit } = setup();
    await userEvent.type(screen.getByPlaceholderText('Ask a question'), 'Days?');
    await userEvent.type(screen.getByPlaceholderText('Option 1'), 'Mon');
    await userEvent.type(screen.getByPlaceholderText('Option 2'), 'Tue');
    await userEvent.click(screen.getByRole('switch', { name: 'Allow multiple answers' }));
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));
    expect(onSubmit.mock.calls[0][0]).toMatchObject({ multi: true });
  });

  it('closes on Cancel and on Escape', async () => {
    const { onClose } = setup();
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onClose).toHaveBeenCalledTimes(1);
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
