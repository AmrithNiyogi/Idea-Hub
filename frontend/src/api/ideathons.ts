/** Ideathons API — mirrors idea-hub.html `api.ideathons.*`. */

import { apiFetch } from './client';
import type {
  AgentRunResult,
  EntryScores,
  Handoff,
  IdeathonCreateBody,
  IdeathonUpdateBody,
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

  update: (id: string, body: IdeathonUpdateBody) =>
    apiFetch<{ id: string }>(`/ideathons/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  advance: (id: string) =>
    apiFetch<{ phase: string }>(`/ideathons/${id}/advance`, { method: 'POST' }),

  runRank: (id: string, weights: Record<string, number>) =>
    apiFetch<AgentRunResult>(`/ideathons/${id}/agents/rank`, {
      method: 'POST',
      body: JSON.stringify({ weights }),
    }),

  draftChallenges: (theme: string) =>
    apiFetch<{ success: boolean; names: string[]; challenges: string[] }>('/ideathons/agents/draft', {
      method: 'POST',
      body: JSON.stringify({ theme }),
    }),

  runPitch: (id: string, body: { stage: 'pitch' | 'handoff' | 'both' }) =>
    apiFetch<AgentRunResult>(`/ideathons/${id}/agents/pitch`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

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

  /** Saved AI rubric scores for every entry (reviewer / leadership / admin). */
  scores: (id: string) => apiFetch<EntryScores>(`/ideathons/${id}/scores`),

  /** Score every entry now and save the result (leadership / admin). */
  runScores: (id: string) =>
    apiFetch<EntryScores>(`/ideathons/${id}/scores/run`, { method: 'POST' }),

  complete: (id: string) =>
    apiFetch<{ ok: boolean }>(`/ideathons/${id}/complete`, { method: 'POST' }),
};
