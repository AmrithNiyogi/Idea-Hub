import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { documentsApi } from './documents';
import { ideathonsApi } from './ideathons';
import { ApiError } from './http';

function stub(payload: unknown, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({ ok, status, statusText: 'x', json: async () => payload, text: async () => '' });
}

describe('documents and scores api', () => {
  let fetchMock: ReturnType<typeof stub>;
  const lastUrl = () => String(fetchMock.mock.calls.at(-1)?.[0]);
  const lastInit = () => (fetchMock.mock.calls.at(-1)?.[1] ?? {}) as RequestInit;

  beforeEach(() => {
    fetchMock = stub({ ok: true });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('lists, uploads, links and deletes documents', async () => {
    await documentsApi.list('i1');
    expect(lastUrl()).toContain('/ideas/i1/documents');

    const f = new File(['hello'], 'notes.md', { type: 'text/markdown' });
    await documentsApi.upload('i1', f);
    expect(lastUrl()).toContain('/ideas/i1/documents');
    expect(lastInit().method).toBe('POST');
    expect(lastInit().body).toBeInstanceOf(FormData);
    expect(lastInit().credentials).toBe('include');

    expect(documentsApi.downloadUrl('i1', 'd1')).toContain('/ideas/i1/documents/d1/download');

    await documentsApi.remove('i1', 'd1');
    expect(lastUrl()).toContain('/ideas/i1/documents/d1');
    expect(lastInit().method).toBe('DELETE');
  });

  it('surfaces the backend message when an upload fails', async () => {
    vi.stubGlobal('fetch', stub({ detail: 'Too many documents' }, false, 400));
    const f = new File(['x'], 'a.pdf');
    await expect(documentsApi.upload('i1', f)).rejects.toMatchObject({
      status: 400,
      message: 'Too many documents',
    });
  });

  it('falls back to a generic upload message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => { throw new Error('no json'); } }),
    );
    const err = await documentsApi.upload('i1', new File(['x'], 'a.pdf')).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toContain('a.pdf');
  });

  it('gets and runs entry scores', async () => {
    await ideathonsApi.scores('t1');
    expect(lastUrl()).toContain('/ideathons/t1/scores');
    await ideathonsApi.runScores('t1');
    expect(lastUrl()).toContain('/ideathons/t1/scores/run');
    expect(lastInit().method).toBe('POST');
  });
});
