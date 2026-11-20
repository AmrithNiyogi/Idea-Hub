/**
 * Idea → Agent Build Loop CTA + run status on idea detail.
 *
 * Shown for Accepted ideas (and when a prior build run exists). Launching
 * creates a real AgentRun with a human gate before Prototype — status never
 * auto-flips.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { agentsApi } from '../api/agents';
import type { AgentRun } from '../types/phase456';
import { Icon } from './Icons';
import { relTime } from '../utils/format';

type TimelineStep = {
  id?: string;
  label?: string;
  status?: string;
  detail?: string;
};

type Props = {
  ideaId: string;
  ideaStatus: string;
  canLaunch: boolean;
  canDecide: boolean;
};

function asTimeline(output: Record<string, unknown> | undefined): TimelineStep[] {
  const raw = output?.timeline;
  if (!Array.isArray(raw)) return [];
  return raw.filter((s): s is TimelineStep => !!s && typeof s === 'object');
}

function gateMessage(output: Record<string, unknown> | undefined): string | null {
  const gate = output?.prototype_gate;
  if (!gate || typeof gate !== 'object') return null;
  const msg = (gate as { message?: unknown }).message;
  return typeof msg === 'string' ? msg : null;
}

function planItems(output: Record<string, unknown> | undefined): string[] {
  const plan = output?.plan;
  if (!plan || typeof plan !== 'object') return [];
  const items = (plan as { items?: unknown }).items;
  if (!Array.isArray(items)) return [];
  return items.filter((x): x is string => typeof x === 'string');
}

export function AgentBuildPanel({
  ideaId,
  ideaStatus,
  canLaunch,
  canDecide,
}: Props) {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    return agentsApi
      .runs({ idea_id: ideaId, agent_id: 'coding-agent-build', limit: 5 })
      .then(setRuns)
      .catch((e) =>
        setError(e instanceof Error ? e.message : 'Failed to load builds'),
      );
  }, [ideaId]);

  useEffect(() => {
    setError(null);
    reload();
  }, [reload]);

  const latest = runs[0] ?? null;
  const show =
    ideaStatus === 'accepted' ||
    (latest != null && ideaStatus !== 'draft');

  if (!show) return null;

  const timeline = asTimeline(latest?.output);
  const items = planItems(latest?.output);
  const gate = gateMessage(latest?.output);
  const pending = latest?.approval_state === 'pending';
  const approved = latest?.approval_state === 'approved';

  const launch = async () => {
    setBusy(true);
    setError(null);
    try {
      const run = await agentsApi.launchBuild(ideaId);
      setRuns((prev) => [run, ...prev.filter((r) => r.id !== run.id)]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Launch failed');
    } finally {
      setBusy(false);
    }
  };

  const decide = async (approve: boolean) => {
    if (!latest?.proposal_key) return;
    setBusy(true);
    setError(null);
    try {
      await agentsApi.decide(
        latest.proposal_key,
        approve,
        approve ? 'Build accepted for delivery path' : 'Build rejected',
      );
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Decision failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="agent agent-build" aria-label="Agent build">
      <div className="agent__head">
        <Icon name="spark" size={16} />
        <span className="agent__name">Agent build</span>
        <span className="pill pill--agent">
          {latest && !latest.simulated ? 'Live' : 'Simulated'}
        </span>
        <span className="agent__kind">Idea → coding loop</span>
      </div>

      <div className="agent__body">
        <p className="muted small" style={{ margin: 0 }}>
          Generate the handoff pack, kick a Kompass-shaped coding run (or a
          persisted simulation), then approve before Prototype. Status never
          auto-flips.
        </p>

        {error ? (
          <div className="notice notice--danger" role="alert">
            <Icon name="alert" size={16} />
            <span>{error}</span>
          </div>
        ) : null}

        {!latest ? (
          <p className="muted small" style={{ margin: 0 }}>
            No agent build run yet for this idea.
          </p>
        ) : (
          <div className="agent-build__status">
            <div className="agent-build__meta">
              <span className="pill">
                {latest.approval_state === 'pending'
                  ? 'Awaiting approval'
                  : latest.approval_state === 'approved'
                    ? 'Build approved'
                    : latest.approval_state === 'rejected'
                      ? 'Rejected'
                      : latest.approval_state}
              </span>
              <span className="muted small">{relTime(latest.created_at)}</span>
              <Link
                className="muted small"
                to="/agents?tab=runs"
                title={latest.id}
              >
                Open run log
              </Link>
            </div>
            <p style={{ margin: 0 }}>{latest.summary}</p>
            {timeline.length ? (
              <ol className="agent-build__timeline">
                {timeline.map((step, i) => (
                  <li key={step.id ?? `${i}`} data-status={step.status ?? ''}>
                    <strong>{step.label ?? step.id}</strong>
                    {step.detail ? (
                      <span className="muted small"> — {step.detail}</span>
                    ) : null}
                  </li>
                ))}
              </ol>
            ) : null}
            {items.length ? (
              <ul className="bullets">
                {items.slice(0, 5).map((it) => (
                  <li key={it}>{it}</li>
                ))}
              </ul>
            ) : null}
            {gate ? <p className="muted small">{gate}</p> : null}
          </div>
        )}

        <div className="agent-build__actions">
          {ideaStatus === 'accepted' && canLaunch ? (
            <button
              type="button"
              className="btn btn--primary"
              disabled={busy}
              onClick={launch}
            >
              <Icon name="spark" size={16} /> Launch agent build
            </button>
          ) : null}
          {pending && canDecide && latest?.proposal_key ? (
            <>
              <button
                type="button"
                className="btn"
                disabled={busy}
                onClick={() => decide(true)}
              >
                <Icon name="checkcircle" size={16} /> Approve build
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                disabled={busy}
                onClick={() => decide(false)}
              >
                Reject
              </button>
            </>
          ) : null}
          {approved ? (
            <Link className="btn" to={`/ideas/${ideaId}?tab=delivery`}>
              Request hours → Prototype
            </Link>
          ) : null}
        </div>
      </div>

      <div className="agent__foot">
        Uses agent-context + skill pack. Live when{' '}
        <code>SIMULATE_AGENTS=false</code> and{' '}
        <code>AISTUDIO_AGENT_CODING_BUILD</code> is set; otherwise a simulated
        timeline is still written to AgentRun.
      </div>
    </aside>
  );
}
