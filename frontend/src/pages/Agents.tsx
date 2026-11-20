/** Agents hub — route `/agents`. Roster, run log, approvals, Kompass map. */

import { useEffect, useState } from 'react';
import { agentsApi } from '../api/agents';
import { reopenApi } from '../api/reopen';
import { Icon } from '../components/Icons';
import { relTime } from '../utils/format';
import type {
  AgentInfo,
  AgentRun,
  KompassMap,
  PendingProposal,
  ReopenProposal,
} from '../types/phase456';

type Tab = 'approvals' | 'runs' | 'roster' | 'kompass';

export function AgentsPage() {
  const [roster, setRoster] = useState<AgentInfo[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [pending, setPending] = useState<PendingProposal[]>([]);
  const [reopen, setReopen] = useState<ReopenProposal[]>([]);
  const [kompass, setKompass] = useState<KompassMap | null>(null);
  const [tab, setTab] = useState<Tab>('approvals');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = () =>
    Promise.all([
      agentsApi.roster(),
      agentsApi.runs({ limit: 40 }),
      agentsApi.proposals(),
      reopenApi.proposals(),
      agentsApi.kompass(),
    ])
      .then(([r, runs_, p, re, k]) => {
        setRoster(r);
        setRuns(runs_);
        setPending(p);
        setReopen(re);
        setKompass(k);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'));

  useEffect(() => {
    reload();
  }, []);

  const runStuck = async () => {
    setBusy(true);
    try {
      await agentsApi.run({
        agent_id: 'innovation-workflow',
        event: 'clock.tick',
        record: true,
      });
      await reload();
    } finally {
      setBusy(false);
    }
  };

  if (error) {
    return (
      <div className="notice notice--danger" role="alert">
        <Icon name="alert" size={18} />
        <span>{error}</span>
      </div>
    );
  }

  const pendingCount = pending.length + reopen.length;

  return (
    <div className="stack stack--lg page agents">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Agents</div>
          <h1>Agent hub</h1>
          <p>
            Every simulated agent run with its trace, the agent registry, and the
            Kompass integration design.
          </p>
        </div>
      </div>

      <div className="kmap-note" role="note">
        <Icon name="alert" size={20} />
        <div>
          <strong>Kompass seam:</strong> default is simulated (
          <code>SIMULATE_AGENTS=true</code>). When live env is set, chat and
          coding-agent-build call <code>POST /api/v2/runs/execute</code>. Agents
          still propose only — humans decide.
        </div>
      </div>

      <div className="tabs" role="tablist">
        {(
          [
            ['approvals', 'Pending approvals'],
            ['runs', 'Activity'],
            ['roster', 'Agents'],
            ['kompass', 'Kompass map'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
          >
            {label}
            {id === 'approvals' && pendingCount ? (
              <span className="count">{pendingCount}</span>
            ) : null}
          </button>
        ))}
      </div>

      {tab === 'approvals' ? (
        <div className="stack">
          <section className="card">
            <div className="card__head">
              <h2>Agent proposals waiting</h2>
              <button
                type="button"
                className="btn btn--sm"
                disabled={busy}
                onClick={runStuck}
              >
                Run stuck detection
              </button>
            </div>
            {pending.length === 0 && reopen.length === 0 ? (
              <div className="empty" style={{ padding: 24 }}>
                <Icon name="checkcircle" size={28} />
                <h3>No agent proposals are waiting</h3>
                <p className="muted small">
                  When an agent proposes a reminder or nomination, it will be
                  listed here.
                </p>
              </div>
            ) : (
              <>
                {pending.map((p) => (
                  <div key={p.proposal_key} className="attn" style={{ marginBottom: 8 }}>
                    <span className="attn__ic">
                      <Icon name="spark" size={16} />
                    </span>
                    <span className="grow">
                      <span className="sim-chip">Simulated</span>
                      <strong>{p.run.agent_id}</strong>: {p.run.summary}
                      <div className="row" style={{ marginTop: 8, gap: 6 }}>
                        <button
                          type="button"
                          className="btn btn--sm btn--primary"
                          onClick={async () => {
                            await agentsApi.decide(p.proposal_key, true);
                            reload();
                          }}
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          className="btn btn--sm"
                          onClick={async () => {
                            await agentsApi.decide(
                              p.proposal_key,
                              false,
                              'Dismissed',
                              7,
                            );
                            reload();
                          }}
                        >
                          Dismiss 7d
                        </button>
                      </div>
                    </span>
                  </div>
                ))}
                {reopen.map((r) => (
                  <div key={r.proposal_key} className="attn" style={{ marginBottom: 8 }}>
                    <span className="attn__ic">
                      <Icon name="refresh" size={16} />
                    </span>
                    <span className="grow">
                      <span className="sim-chip">Reopen</span> “{r.idea_title}” —{' '}
                      {r.evidence.join('; ') || 'conditions met'}
                      <div className="row" style={{ marginTop: 8, gap: 6 }}>
                        <button
                          type="button"
                          className="btn btn--sm btn--primary"
                          onClick={async () => {
                            await reopenApi.approve(r.idea_id, 'Conditions met');
                            reload();
                          }}
                        >
                          Reopen
                        </button>
                        <button
                          type="button"
                          className="btn btn--sm"
                          onClick={async () => {
                            await reopenApi.dismiss(r.idea_id);
                            reload();
                          }}
                        >
                          Dismiss
                        </button>
                      </div>
                    </span>
                  </div>
                ))}
              </>
            )}
          </section>
        </div>
      ) : null}

      {tab === 'runs' ? (
        <section className="card">
          <div className="card__head">
            <h2>Run log</h2>
            <span className="muted small">{runs.length} recorded</span>
          </div>
          <p className="muted small" style={{ marginBottom: 10 }}>
            Simulated — no language model was called. Newest first.
          </p>
          {runs.length === 0 ? (
            <p className="muted">No runs yet.</p>
          ) : (
            <div className="stack stack--sm">
              {runs.map((r) => (
                <details key={r.id} className="trace">
                  <summary>
                    <span className="agent__name">{r.agent_id}</span>
                    <span className="pill pill--agent">Simulated</span>
                    {r.approval_required ? (
                      <span
                        className={`pill${
                          r.approval_state === 'pending'
                            ? ' pill--warning'
                            : r.approval_state === 'approved'
                              ? ' pill--success'
                              : ''
                        }`}
                      >
                        {r.approval_state}
                      </span>
                    ) : null}
                    <span className="muted small">{r.summary}</span>
                    <span
                      className="muted small mono"
                      style={{ marginLeft: 'auto' }}
                    >
                      {relTime(r.created_at)}
                    </span>
                  </summary>
                  <div className="trace__steps">
                    <p className="small">
                      Event <span className="mono">{r.event}</span>, engine{' '}
                      <span className="mono">{r.engine}</span>
                      {r.idea_id ? `, idea ${r.idea_id}` : ''}.
                    </p>
                  </div>
                </details>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {tab === 'roster' ? (
        <div className="stack">
          <div className="notice" style={{ marginBottom: 0 }}>
            <Icon name="info" size={16} />
            <span>
              Simulated agents. “Computed” means a real calculation on the data.
              No agent here uses a language model.
            </span>
          </div>
          <div className="grid grid-2">
            {roster.map((a) => (
              <article key={a.id} className="card agent-card">
                <h3>
                  <Icon name="spark" size={18} /> {a.id}{' '}
                  {a.simulated ? (
                    <span className="pill pill--brand">Simulated</span>
                  ) : null}
                </h3>
                <p>{a.purpose}</p>
                <dl className="kv">
                  <dt>Form</dt>
                  <dd>{a.form}</dd>
                  <dt>Triggers</dt>
                  <dd>
                    {a.triggers.map((t) => (
                      <span
                        key={t}
                        className="mono small"
                        style={{ display: 'inline-block', marginRight: 8 }}
                      >
                        {t}
                      </span>
                    ))}
                  </dd>
                  {a.prompt_slug ? (
                    <>
                      <dt>Prompt</dt>
                      <dd className="mono small">{a.prompt_slug}</dd>
                    </>
                  ) : null}
                  <dt>May never</dt>
                  <dd>
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                      {a.never.map((n) => (
                        <li key={n}>{n}</li>
                      ))}
                    </ul>
                  </dd>
                </dl>
              </article>
            ))}
          </div>
        </div>
      ) : null}

      {tab === 'kompass' && kompass ? (
        <section className="card">
          <div className="card__head">
            <h2>Kompass integration map</h2>
          </div>
          <p role="status">
            <strong>{kompass.notice}</strong>
          </p>
          {kompass.questions.map((q) => (
            <div key={q.id} className="qrow" id={`kq-${q.id}`}>
              <div className="row" style={{ alignItems: 'flex-start', gap: 8 }}>
                <span className="pill mono">{q.id.toUpperCase()}</span>
                <div className="grow">
                  <div>{q.text}</div>
                  {q.answered ? (
                    <div
                      className="notice notice--ok"
                      style={{ marginTop: 8 }}
                    >
                      <Icon name="checkcircle" size={16} />
                      <span>
                        <strong>Answered</strong>
                        {q.note ? `: ${q.note}` : ''}
                      </span>
                    </div>
                  ) : (
                    <div className="muted small" style={{ marginTop: 4 }}>
                      Open. No answer recorded.
                    </div>
                  )}
                  <label className="check" style={{ marginTop: 8 }}>
                    <input
                      type="checkbox"
                      checked={q.answered}
                      onChange={async (e) => {
                        await agentsApi.answerQuestion(q.id, e.target.checked);
                        reload();
                      }}
                    />
                    <span>Mark as answered</span>
                  </label>
                </div>
              </div>
            </div>
          ))}
        </section>
      ) : null}
    </div>
  );
}
