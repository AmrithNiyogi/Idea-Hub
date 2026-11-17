import { apiFetch } from './client';
import type { CollabRequest, Tracker } from '../types/phase456';

export const collabApi = {
  mine: () => apiFetch<CollabRequest[]>('/collab/mine'),

  incoming: () => apiFetch<CollabRequest[]>('/collab/incoming'),

  forIdea: (ideaId: string) =>
    apiFetch<CollabRequest[]>(`/ideas/${ideaId}/collab`),

  create: (body: {
    idea_id: string;
    type: 'coauthor' | 'build';
    message?: string;
    role?: string;
    hours?: number;
    source?: string;
  }) =>
    apiFetch<CollabRequest>('/collab', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  withdraw: (id: string) =>
    apiFetch<CollabRequest>(`/collab/${id}/withdraw`, { method: 'POST' }),

  decide: (id: string, accept: boolean, note = '') =>
    apiFetch<CollabRequest>(`/collab/${id}/decide`, {
      method: 'POST',
      body: JSON.stringify({ accept, note }),
    }),

  tracker: (ideaId: string) =>
    apiFetch<Tracker>(`/ideas/${ideaId}/tracker`),

  addMilestone: (
    ideaId: string,
    body: { title: string; owner_id?: string; due_at?: string },
  ) =>
    apiFetch(`/ideas/${ideaId}/tracker/milestones`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  updateMilestone: (
    id: string,
    body: Partial<{ title: string; status: string; blocker: string }>,
  ) =>
    apiFetch(`/tracker/milestones/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  addCheckin: (
    ideaId: string,
    body: { body: string; percent_complete?: number },
  ) =>
    apiFetch(`/ideas/${ideaId}/tracker/checkins`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};
