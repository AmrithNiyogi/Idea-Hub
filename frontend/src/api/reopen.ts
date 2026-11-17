import { apiFetch } from './client';
import type { ReopenProposal, ReopenState } from '../types/phase456';

export const reopenApi = {
  state: (ideaId: string) => apiFetch<ReopenState>(`/reopen/${ideaId}`),

  proposals: () => apiFetch<ReopenProposal[]>('/reopen/proposals'),

  upsert: (body: Record<string, unknown>) =>
    apiFetch<ReopenState>('/reopen', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  approve: (ideaId: string, reason = '') =>
    apiFetch(`/reopen/${ideaId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  dismiss: (ideaId: string, reason = '', snooze_days = 7) =>
    apiFetch(`/reopen/${ideaId}/dismiss`, {
      method: 'POST',
      body: JSON.stringify({ reason, snooze_days }),
    }),

  markManual: (ideaId: string, cond_id: string, note = '') =>
    apiFetch<ReopenState>(`/reopen/${ideaId}/mark-manual`, {
      method: 'POST',
      body: JSON.stringify({ cond_id, note }),
    }),
};
