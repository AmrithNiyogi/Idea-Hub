/** Author Idea Optimizer — simulated post-submit chat (not Review Intelligence). */

import { FormEvent, useEffect, useRef, useState } from 'react';
import { agentsApi, type IdeaOptimizeTurn } from '../api/agents';
import type { Effort, Idea } from '../types/idea';
import { Icon } from './Icons';

type Msg = { role: 'user' | 'assistant'; text: string };

type Staged = {
  title?: string;
  problem?: string;
  solution?: string;
  beneficiaries?: string;
  success_metrics?: string;
  tags?: string[];
  effort?: Effort;
};

function ideaPayload(idea: Idea, staged: Staged): Record<string, unknown> {
  return {
    id: idea.id,
    title: staged.title ?? idea.title,
    problem: staged.problem ?? idea.problem,
    solution: staged.solution ?? idea.solution,
    beneficiaries: staged.beneficiaries ?? idea.beneficiaries,
    success_metrics: staged.success_metrics ?? idea.success_metrics,
    tags: staged.tags ?? idea.tags,
    effort: staged.effort ?? idea.effort,
    category_id: idea.category_id,
    status: idea.status,
  };
}

const STARTERS = [
  'Optimize all',
  'Sharpen the problem',
  'Add a measurable metric',
  'Suggest better tags',
];

type Props = {
  idea: Idea;
  /** Called when the author applies patches (local preview / optional persist). */
  onApplyPatches: (patches: Staged) => void | Promise<void>;
};

export function IdeaOptimizePanel({ idea, onApplyPatches }: Props) {
  const [open, setOpen] = useState(true);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [pending, setPending] = useState<Record<string, unknown>>({});
  const [staged, setStaged] = useState<Staged>({});
  const [note, setNote] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Scroll the chat log itself. scrollIntoView would also scroll the page to the panel.
    const log = endRef.current?.closest<HTMLElement>('.sf-chat__log');
    log?.scrollTo({ top: log.scrollHeight, behavior: 'smooth' });
  }, [msgs, pending, busy]);

  useEffect(() => {
    let cancelled = false;
    setMsgs([]);
    setPending({});
    setStaged({});
    setNote(null);
    setConversationId(null);
    setBusy(true);
    agentsApi
      .ideaOptimize({
        idea_id: idea.id,
        idea: ideaPayload(idea, {}),
        message: '',
      })
      .then((turn) => {
        if (cancelled) return;
        setMsgs([{ role: 'assistant', text: turn.reply }]);
        if (turn.conversation_id) setConversationId(turn.conversation_id);
      })
      .catch((e) => {
        if (cancelled) return;
        setMsgs([
          {
            role: 'assistant',
            text:
              e instanceof Error
                ? e.message
                : 'Optimizer unavailable. You can still edit via Discussion.',
          },
        ]);
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
    // Open once per idea id; field text updates flow through later turns.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional idea.id key
  }, [idea.id]);

  const ask = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    setInput('');
    setMsgs((m) => [...m, { role: 'user', text: q }]);
    setBusy(true);
    setNote(null);
    try {
      const turn: IdeaOptimizeTurn = await agentsApi.ideaOptimize({
        idea_id: idea.id,
        idea: ideaPayload(idea, staged),
        message: q,
        conversation_id: conversationId,
      });
      setMsgs((m) => [...m, { role: 'assistant', text: turn.reply }]);
      setPending(turn.field_patches || {});
      if (turn.conversation_id) setConversationId(turn.conversation_id);
    } catch (e) {
      setMsgs((m) => [
        ...m,
        {
          role: 'assistant',
          text:
            e instanceof Error ? e.message : 'Could not reach the optimizer.',
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const applyKey = async (key: string) => {
    const val = pending[key];
    if (val === undefined) return;
    const next: Staged = { ...staged };
    if (key === 'tags' && Array.isArray(val)) {
      next.tags = val.map(String).slice(0, 8);
    } else if (
      key === 'effort' &&
      typeof val === 'string' &&
      ['S', 'M', 'L', 'XL'].includes(val)
    ) {
      next.effort = val as Effort;
    } else if (typeof val === 'string') {
      (next as Record<string, string>)[key] = val;
    } else {
      return;
    }
    setStaged(next);
    const rest = { ...pending };
    delete rest[key];
    setPending(rest);
    try {
      await onApplyPatches(next);
      setNote(`Applied ${key.replace(/_/g, ' ')} (preview).`);
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Apply failed');
    }
  };

  const applyAll = async () => {
    const keys = Object.keys(pending);
    if (!keys.length) return;
    let next: Staged = { ...staged };
    for (const key of keys) {
      const val = pending[key];
      if (key === 'tags' && Array.isArray(val)) {
        next = { ...next, tags: val.map(String).slice(0, 8) };
      } else if (
        key === 'effort' &&
        typeof val === 'string' &&
        ['S', 'M', 'L', 'XL'].includes(val)
      ) {
        next = { ...next, effort: val as Effort };
      } else if (typeof val === 'string') {
        next = { ...next, [key]: val };
      }
    }
    setStaged(next);
    setPending({});
    try {
      await onApplyPatches(next);
      setNote('Applied all proposed patches (preview).');
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Apply failed');
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void ask(input);
  };

  if (!open) {
    return (
      <div className="card card--tight">
        <button
          type="button"
          className="btn btn--sm"
          onClick={() => setOpen(true)}
        >
          <Icon name="spark" size={14} /> Optimize with agent (Simulated)
        </button>
      </div>
    );
  }

  const patchKeys = Object.keys(pending);

  return (
    <div className="card card--tight agent">
      <div className="agent__head">
        <Icon name="spark" size={16} />
        <span className="agent__name">Idea Optimizer</span>
        <span className="pill pill--agent">Simulated — Kompass soon</span>
        <button
          type="button"
          className="btn btn--sm btn--ghost"
          style={{ marginLeft: 'auto' }}
          onClick={() => setOpen(false)}
          aria-label="Collapse optimizer"
        >
          <Icon name="x" size={14} />
        </button>
      </div>
      <div className="agent__body">
        <p className="muted small" style={{ margin: 0 }}>
          Author co-pilot — improves clarity and metrics. Not Review
          Intelligence (no scores or decisions).
        </p>
        <div className="sf-chat__log" role="log" aria-live="polite">
          {msgs.map((m, i) => (
            <div
              key={i}
              className={`sf-chat__bubble sf-chat__bubble--${m.role}`}
            >
              <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{m.text}</p>
            </div>
          ))}
          {busy ? <p className="muted small">Thinking…</p> : null}
          <div ref={endRef} />
        </div>
        {patchKeys.length ? (
          <div className="stack" style={{ gap: 8 }}>
            <div className="eyebrow eyebrow--plain">Proposed patches</div>
            <div className="chip-row">
              {patchKeys.map((k) => (
                <button
                  key={k}
                  type="button"
                  className="btn btn--sm"
                  onClick={() => void applyKey(k)}
                >
                  Apply {k.replace(/_/g, ' ')}
                </button>
              ))}
              <button
                type="button"
                className="btn btn--sm btn--primary"
                onClick={() => void applyAll()}
              >
                Apply all
              </button>
            </div>
            <ul className="muted small" style={{ margin: 0, paddingLeft: 18 }}>
              {patchKeys.map((k) => (
                <li key={k}>
                  <strong>{k.replace(/_/g, ' ')}:</strong>{' '}
                  {Array.isArray(pending[k])
                    ? (pending[k] as string[]).join(', ')
                    : String(pending[k]).slice(0, 160)}
                  {String(pending[k]).length > 160 ? '…' : ''}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {Object.keys(staged).length ? (
          <div className="notice notice--brand" style={{ margin: 0 }}>
            <Icon name="spark" size={14} />
            <span className="small">
              Staged edits are a local preview on this page. Submitted ideas are
              not rewritten in-place — copy improved text into Discussion or a
              needs_info answer when you want it on the record.
            </span>
          </div>
        ) : null}
        {note ? <p className="muted small">{note}</p> : null}
        <div className="chip-row">
          {STARTERS.map((s) => (
            <button
              key={s}
              type="button"
              className="btn btn--sm"
              disabled={busy}
              onClick={() => void ask(s)}
            >
              {s}
            </button>
          ))}
        </div>
        <form className="sf-chat__compose" onSubmit={onSubmit}>
          <input
            className="input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask to optimize…"
            disabled={busy}
            aria-label="Message the idea optimizer"
          />
          <button
            type="submit"
            className="btn btn--primary btn--sm"
            disabled={busy || !input.trim()}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
