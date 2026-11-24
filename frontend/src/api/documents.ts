/** Entry documents attached to an idea (hackathon / ideathon submissions). */

import { ApiError, API_BASE_URL, apiFetch } from './client';
import type { EntryDocument } from '../types/idea';

export const documentsApi = {
  list: (ideaId: string) =>
    apiFetch<EntryDocument[]>(`/ideas/${ideaId}/documents`),

  upload: async (ideaId: string, file: File): Promise<EntryDocument> => {
    const form = new FormData();
    form.append('file', file);
    // Use fetch so the browser sets the multipart boundary.
    const res = await fetch(`${API_BASE_URL}/ideas/${ideaId}/documents`, {
      method: 'POST',
      credentials: 'include',
      body: form,
    });
    if (!res.ok) {
      let detail = `Could not upload ${file.name}`;
      try {
        const body = (await res.json()) as { detail?: unknown };
        if (typeof body.detail === 'string') detail = body.detail;
      } catch {
        /* keep default message */
      }
      throw new ApiError(res.status, detail);
    }
    return (await res.json()) as EntryDocument;
  },

  /** Direct link; the browser sends the session cookie. */
  downloadUrl: (ideaId: string, docId: string) =>
    `${API_BASE_URL}/ideas/${ideaId}/documents/${docId}/download`,

  remove: (ideaId: string, docId: string) =>
    apiFetch<{ ok: boolean }>(`/ideas/${ideaId}/documents/${docId}`, {
      method: 'DELETE',
    }),
};
