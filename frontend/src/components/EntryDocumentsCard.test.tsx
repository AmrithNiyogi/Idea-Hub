import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { EntryDocumentsCard } from './EntryDocumentsCard';
import { documentsApi } from '../api/documents';
import type { EntryDocument } from '../types/idea';

vi.mock('../api/documents', () => ({
  documentsApi: {
    list: vi.fn(),
    upload: vi.fn(),
    remove: vi.fn(),
    downloadUrl: (ideaId: string, docId: string) => `/dl/${ideaId}/${docId}`,
  },
}));

const doc: EntryDocument = {
  id: 'd1',
  idea_id: 'i1',
  filename: 'design.pdf',
  content_type: 'application/pdf',
  size_bytes: 2048,
  text_chars: 0,
  created_at: '2026-11-24T10:00:00Z',
};

describe('EntryDocumentsCard', () => {
  beforeEach(() => {
    vi.mocked(documentsApi.list).mockReset();
    vi.mocked(documentsApi.upload).mockReset();
    vi.mocked(documentsApi.remove).mockReset();
  });

  it('lists documents with a download link and an unreadable note', async () => {
    vi.mocked(documentsApi.list).mockResolvedValue([doc]);
    render(<EntryDocumentsCard ideaId="i1" canEdit={false} />);
    const link = await screen.findByRole('link', { name: 'design.pdf' });
    expect(link).toHaveAttribute('href', '/dl/i1/d1');
    expect(screen.getByText(/AI could not read it/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Add documentation/)).not.toBeInTheDocument();
  });

  it('hides itself for viewers when there are no documents', async () => {
    vi.mocked(documentsApi.list).mockResolvedValue([]);
    const { container } = render(<EntryDocumentsCard ideaId="i1" canEdit={false} />);
    await waitFor(() => expect(documentsApi.list).toHaveBeenCalled());
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it('lets the author upload and remove documents', async () => {
    vi.mocked(documentsApi.list).mockResolvedValue([doc]);
    vi.mocked(documentsApi.upload).mockResolvedValue({ ...doc, id: 'd2', filename: 'notes.md', text_chars: 40 });
    vi.mocked(documentsApi.remove).mockResolvedValue({ ok: true });
    render(<EntryDocumentsCard ideaId="i1" canEdit />);
    await screen.findByText('design.pdf');
    fireEvent.change(screen.getByLabelText(/Add documentation/), {
      target: { files: [new File(['# x'], 'notes.md')] },
    });
    expect(await screen.findByText('notes.md')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Remove design.pdf' }));
    await waitFor(() => expect(screen.queryByText('design.pdf')).not.toBeInTheDocument());
    expect(documentsApi.remove).toHaveBeenCalledWith('i1', 'd1');
  });

  it('shows validation and upload errors', async () => {
    vi.mocked(documentsApi.list).mockResolvedValue([]);
    vi.mocked(documentsApi.upload).mockRejectedValue(new Error('Too big'));
    render(<EntryDocumentsCard ideaId="i1" canEdit />);
    const input = await screen.findByLabelText(/Add documentation/);
    fireEvent.change(input, { target: { files: [new File(['x'], 'a.zip')] } });
    expect(await screen.findByRole('alert')).toHaveTextContent('a.zip');
    fireEvent.change(input, { target: { files: [new File(['x'], 'a.pdf')] } });
    expect(await screen.findByText('Too big')).toBeInTheDocument();
  });
});
