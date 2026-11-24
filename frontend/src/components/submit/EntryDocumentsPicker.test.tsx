import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { EntryDocumentsPicker } from './EntryDocumentsPicker';
import { EventKindChips } from '../ideathon/EventKindChips';

function pick(input: HTMLElement, files: File[]) {
  fireEvent.change(input, { target: { files } });
}

describe('EntryDocumentsPicker', () => {
  it('adds valid files and marks the field required for hackathons', () => {
    const onChange = vi.fn();
    render(<EntryDocumentsPicker files={[]} onChange={onChange} required />);
    expect(screen.getByText(/required for hackathons/)).toBeInTheDocument();
    const f = new File(['# hi'], 'readme.md');
    pick(screen.getByLabelText(/Documentation/), [f]);
    expect(onChange).toHaveBeenCalledWith([f]);
  });

  it('rejects an unsupported file with a clear message', () => {
    const onChange = vi.fn();
    render(<EntryDocumentsPicker files={[]} onChange={onChange} />);
    pick(screen.getByLabelText(/Documentation/), [new File(['x'], 'app.zip')]);
    expect(screen.getByRole('alert')).toHaveTextContent('app.zip: use PDF, Markdown, TXT or DOCX.');
    expect(onChange).not.toHaveBeenCalled();
  });

  it('removes a picked file', async () => {
    const onChange = vi.fn();
    const a = new File(['a'], 'a.pdf');
    const b = new File(['b'], 'b.txt');
    render(<EntryDocumentsPicker files={[a, b]} onChange={onChange} />);
    await userEvent.click(screen.getByRole('button', { name: 'Remove a.pdf' }));
    expect(onChange).toHaveBeenCalledWith([b]);
  });
});

describe('EventKindChips', () => {
  it('switches between ideathon and hackathon', async () => {
    const onChange = vi.fn();
    render(<EventKindChips value="ideathon" onChange={onChange} />);
    expect(screen.getByRole('button', { name: 'Ideathon' })).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(screen.getByRole('button', { name: 'Hackathon' }));
    expect(onChange).toHaveBeenCalledWith('hackathon');
  });
});
