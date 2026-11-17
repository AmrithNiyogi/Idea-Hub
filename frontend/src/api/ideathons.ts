/** Ideathons API — mirrors idea-hub.html `api.ideathons.*`. */

import { apiFetch } from './client';
import type {
  Handoff,
  IdeathonCreateBody,
  IdeathonDetail,
  IdeathonSummary,
  TallyRow,
} from '../types/ideathon';

export const ideathonsApi = {
  list: () => apiFetch<IdeathonSummary[]>('/ideathons'),

  get: (id: string) => apiFetch<IdeathonDetail>(`/ideathons/${id}`),

  create: (body: IdeathonCreateBody) =>
    apiFetch<{ id: string }>('/ideathons', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  advance: (id: string) =>
    apiFetch<{ phase: string }>(`/ideathons/${id}/advance`, { method: 'POST' }),

  link: (id: string, ideaId: string) =>
    apiFetch<{ title: string }>(`/ideathons/${id}/link`, {
      method: 'POST',
      body: JSON.stringify({ idea_id: ideaId }),
    }),

  unlink: (id: string, ideaId: string) =>
    apiFetch(`/ideathons/${id}/entries/${ideaId}`, { method: 'DELETE' }),

  approveShortlist: (id: string, ideaIds: string[]) =>
    apiFetch<{ count: number }>(`/ideathons/${id}/shortlist`, {
      method: 'POST',
      body: JSON.stringify({ idea_ids: ideaIds }),
    }),

  move: (id: string, ideaId: string, direction: 'up' | 'down') =>
    apiFetch(`/ideathons/${id}/pitch/move`, {
      method: 'POST',
      body: JSON.stringify({ idea_id: ideaId, direction }),
    }),

  score: (id: string, ideaId: string, score: number) =>
    apiFetch<{ score: number }>(`/ideathons/${id}/pitch/score`, {
      method: 'POST',
      body: JSON.stringify({ idea_id: ideaId, score }),
    }),

  vote: (id: string, ideaId: string) =>
    apiFetch<{ voted: boolean; changed?: boolean }>(
      `/ideathons/${id}/pitch/vote`,
      {
        method: 'POST',
        body: JSON.stringify({ idea_id: ideaId }),
      },
    ),

  closeVoting: (id: string) =>
    apiFetch<{ panel: number; audience: number }>(
      `/ideathons/${id}/pitch/close`,
      { method: 'POST' },
    ),

  tally: (id: string) => apiFetch<TallyRow[]>(`/ideathons/${id}/tally`),

  confirmWinners: (id: string, ideaIds: string[]) =>
    apiFetch<{ winners: number; finalists: number }>(
      `/ideathons/${id}/winners`,
      {
        method: 'POST',
        body: JSON.stringify({ idea_ids: ideaIds }),
      },
    ),

  handoffs: (id: string) =>
    apiFetch<Handoff[]>(`/ideathons/${id}/handoffs`),

  sendHandoff: (
    id: string,
    ideaId: string,
    statement: string,
    edited = false,
  ) =>
    apiFetch<Handoff>(`/ideathons/${id}/handoff`, {
      method: 'POST',
      body: JSON.stringify({ idea_id: ideaId, statement, edited }),
    }),

  complete: (id: string) =>
    apiFetch<{ ok: boolean }>(`/ideathons/${id}/complete`, { method: 'POST' }),
};
