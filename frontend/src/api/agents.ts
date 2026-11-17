import { apiFetch } from './client';
import type {
  AgentInfo,
  AgentRun,
  KompassMap,
  PendingProposal,
} from '../types/phase456';

export type SubmitAssistTurn = {
  simulated: boolean;
  engine: string;
  mode: string;
  reply: string;
  patches: Record<string, unknown>;
  awaiting_field: string | null;
  field_prompt: string | null;
  done: boolean;
  notice: string;
  conversation_id?: string | null;
};

export type HelpTurn = {
  simulated: boolean;
  engine: string;
  mode: string;
  topic: string;
  reply: string;
  links: Array<{ label: string; href: string }>;
  notice: string;
  conversation_id?: string | null;
};

export type IdeaOptimizeTurn = {
  simulated: boolean;
  engine: string;
  mode: string;
  reply: string;
  field_patches: Record<string, unknown>;
  focus_fields: string[];
  notice: string;
  conversation_id?: string | null;
};

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

  submitAssist: (body: {
    draft: Record<string, unknown>;
    message?: string;
    awaiting_field?: string | null;
    conversation_id?: string | null;
  }) =>
    apiFetch<SubmitAssistTurn>('/agents/simulate/submit-assist', {
      method: 'POST',
      body: JSON.stringify({
        draft: body.draft,
        message: body.message ?? '',
        awaiting_field: body.awaiting_field ?? null,
        conversation_id: body.conversation_id ?? null,
      }),
    }),

  help: (message: string, conversation_id?: string | null) =>
    apiFetch<HelpTurn>('/agents/simulate/help', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_id: conversation_id ?? null,
      }),
    }),

  ideaOptimize: (body: {
    idea_id?: string;
    idea: Record<string, unknown>;
    message?: string;
    messages?: Array<Record<string, unknown>>;
    conversation_id?: string | null;
  }) =>
    apiFetch<IdeaOptimizeTurn>('/agents/simulate/idea-optimize', {
      method: 'POST',
      body: JSON.stringify({
        idea_id: body.idea_id ?? null,
        idea: body.idea,
        message: body.message ?? '',
        messages: body.messages ?? [],
        conversation_id: body.conversation_id ?? null,
      }),
    }),
};
