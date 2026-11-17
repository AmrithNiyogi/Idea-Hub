import { apiFetch } from './client';
import type {
  AgentInfo,
  AgentRun,
  KompassMap,
  PendingProposal,
} from '../types/phase456';

export const agentsApi = {
  roster: () => apiFetch<AgentInfo[]>('/agents/roster'),

  run: (body: {
    agent_id: string;
    event: string;
    idea_id?: string;
    context?: Record<string, unknown>;
    record?: boolean;
  }) =>
    apiFetch<AgentRun>('/agents/run', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  runs: (opts?: { limit?: number; agent_id?: string; pending_only?: boolean }) => {
    const q = new URLSearchParams();
    if (opts?.limit) q.set('limit', String(opts.limit));
    if (opts?.agent_id) q.set('agent_id', opts.agent_id);
    if (opts?.pending_only) q.set('pending_only', 'true');
    const qs = q.toString();
    return apiFetch<AgentRun[]>(`/agents/runs${qs ? `?${qs}` : ''}`);
  },

  proposals: () => apiFetch<PendingProposal[]>('/agents/proposals'),

  decide: (proposal_key: string, approve: boolean, reason = '', snooze_days = 0) =>
    apiFetch('/agents/proposals/decide', {
      method: 'POST',
      body: JSON.stringify({ proposal_key, approve, reason, snooze_days }),
    }),

  kompass: () => apiFetch<KompassMap>('/agents/kompass'),

  answerQuestion: (id: string, answered: boolean, note = '') =>
    apiFetch<KompassMap>(`/agents/kompass/questions/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ answered, note }),
    }),
};
