import { apiFetch } from './client';
import type { Problem } from '../types/phase456';

export const problemsApi = {
  list: (opts?: { state?: string; sort?: string }) => {
    const q = new URLSearchParams();
    if (opts?.state) q.set('state', opts.state);
    if (opts?.sort) q.set('sort', opts.sort);
    const qs = q.toString();
    return apiFetch<Problem[]>(`/problems${qs ? `?${qs}` : ''}`);
  },

  headline: () =>
    apiFetch<{ recurring: number; unsolved: number; again_30: number }>(
      '/problems/headline',
    ),

  get: (key: string) => apiFetch<Problem>(`/problems/${key}`),

  byIdea: (ideaId: string) =>
    apiFetch<Problem | null>(`/problems/by-idea/${ideaId}`),

  meToo: (key: string) =>
    apiFetch(`/problems/${key}/me-too`, { method: 'POST' }),

  unMeToo: (key: string) =>
    apiFetch(`/problems/${key}/me-too`, { method: 'DELETE' }),

  updateMeta: (
    key: string,
    body: {
      custom_label?: string;
      sponsor_id?: string;
      acknowledge?: boolean;
      note?: string;
    },
  ) =>
    apiFetch<Problem>(`/problems/${key}/meta`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
};
