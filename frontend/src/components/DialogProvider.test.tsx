import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { DialogProvider, useDialog } from './DialogProvider';

type Result = { value: unknown };

function Harness({ run, out }: { run: (d: ReturnType<typeof useDialog>) => Promise<unknown>; out: Result }) {
  const dialog = useDialog();
  return (
    <button type="button" onClick={() => void run(dialog).then((v) => (out.value = v))}>
      open
    </button>
  );
}

function setup(run: (d: ReturnType<typeof useDialog>) => Promise<unknown>) {
  const out: Result = { value: 'unset' };
  render(
    <DialogProvider>
      <Harness run={run} out={out} />
    </DialogProvider>,
  );
  return out;
}

describe('DialogProvider', () => {
  it('resolves true when confirmed', async () => {
    const user = userEvent.setup();
    const out = setup((d) => d.confirm({ title: 'Remove it?', confirmLabel: 'Remove' }));
    await user.click(screen.getByRole('button', { name: 'open' }));
    expect(screen.getByRole('dialog', { name: 'Remove it?' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Remove' }));
    await act(async () => {});
    expect(out.value).toBe(true);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('resolves false when cancelled', async () => {
    const user = userEvent.setup();
    const out = setup((d) => d.confirm({ title: 'Sure?' }));
    await user.click(screen.getByRole('button', { name: 'open' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    await act(async () => {});
    expect(out.value).toBe(false);
  });

  it('closes on Escape and resolves false', async () => {
    const user = userEvent.setup();
    const out = setup((d) => d.confirm({ title: 'Sure?' }));
    await user.click(screen.getByRole('button', { name: 'open' }));
    await user.keyboard('{Escape}');
    await act(async () => {});
    expect(out.value).toBe(false);
  });

  it('keeps confirm disabled until the required text matches', async () => {
    const user = userEvent.setup();
    const out = setup((d) =>
      d.confirm({ title: 'Delete?', requireText: 'dana@example.com', confirmLabel: 'Delete' }),
    );
    await user.click(screen.getByRole('button', { name: 'open' }));
    const confirmBtn = screen.getByRole('button', { name: 'Delete' });
    expect(confirmBtn).toBeDisabled();
    await user.type(screen.getByLabelText(/Type/i), 'DANA@example.com');
    expect(confirmBtn).toBeEnabled();
    await user.click(confirmBtn);
    await act(async () => {});
    expect(out.value).toBe(true);
  });

  it('returns the entered text from a prompt, after the minimum length is met', async () => {
    const user = userEvent.setup();
    const out = setup((d) =>
      d.prompt({ title: 'Decline', label: 'Reason', minLength: 10, confirmLabel: 'Send' }),
    );
    await user.click(screen.getByRole('button', { name: 'open' }));
    await user.type(screen.getByLabelText('Reason'), 'too short');
    await user.click(screen.getByRole('button', { name: 'Send' }));
    expect(screen.getByRole('alert')).toHaveTextContent('at least 10 characters');
    await user.clear(screen.getByLabelText('Reason'));
    await user.type(screen.getByLabelText('Reason'), 'long enough reason');
    await user.click(screen.getByRole('button', { name: 'Send' }));
    await act(async () => {});
    expect(out.value).toBe('long enough reason');
  });

  it('resolves null when a prompt is cancelled', async () => {
    const user = userEvent.setup();
    const out = setup((d) => d.prompt({ title: 'Note', label: 'Note' }));
    await user.click(screen.getByRole('button', { name: 'open' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    await act(async () => {});
    expect(out.value).toBeNull();
  });
});
