/** Problem detail — route `/problems/:key`. HTML layout clone. */

import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { problemsApi } from '../api/problems';
import { useAuth } from '../auth/AuthProvider';
import { Icon } from '../components/Icons';
import { StatusPill } from '../components/StatusPill';
import { CAN_SUBMIT } from '../constants/roles';
import { fmtDate } from '../utils/format';
import type { Role } from '../types/auth';
import type { Problem } from '../types/phase456';

export function ProblemDetailPage() {
  const { key = '' } = useParams();
  const { user } = useAuth();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [label, setLabel] = useState('');
  const [error, setError] = useState<string | null>(null);
  const canLead =
    user?.active_role === 'leadership' || user?.active_role === 'admin';
  const canSubmit = CAN_SUBMIT.includes(
    (user?.active_role ?? 'contributor') as Role,
  );

  const reload = () =>
    problemsApi
      .get(key)
      .then((p) => {
        setProblem(p);
        setLabel(p.custom_label || p.label);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'));

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  if (error) {
    return (
      <div className="card" style={{ maxWidth: 640, margin: '48px auto' }}>
        <div className="empty">
          <Icon name="target" size={36} />
          <h2>That problem is not on the radar</h2>
          <p className="muted">{error}</p>
          <Link className="btn btn--primary" to="/problems">
            Open the problem radar
          </Link>
        </div>
      </div>
    );
  }
  if (!problem) return <p className="muted">Loading…</p>;

  const stateTone =
    problem.state === 'solved'
      ? 'pill--success'
      : problem.state === 'in_progress'
        ? 'pill--brand'
        : 'pill--warning';

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">
            <Link to="/problems">Problem radar</Link>
          </div>
          <h1>{problem.label}</h1>
          <p>
            {problem.custom_label
              ? `Renamed. Computed label may differ.`
              : 'Label computed from shared terms in the problem statements. Leadership can rename it.'}
          </p>
        </div>
      </div>

      <div className="card">
        <div className="row" style={{ gap: 6 }}>
          <span className={`pill ${stateTone}`}>
            {problem.state.replace(/_/g, ' ')}
          </span>
          {problem.acknowledged_at ? (
            <span className="pill pill--success">
              <Icon name="check" size={12} /> Acknowledged
            </span>
          ) : null}
        </div>

        <div
          className="grid kpi-row kpi-row--4"
          style={{ marginTop: 'var(--space-4)' }}
        >
          <div className="kpi">
            <span className="kpi__label">Times raised</span>
            <span className="kpi__value">{problem.idea_count}</span>
            <span className="kpi__sub">ideas on this problem</span>
          </div>
          <div className="kpi">
            <span className="kpi__label">Teams</span>
            <span className="kpi__value">{problem.team_count}</span>
            <span className="kpi__sub">named contributors</span>
          </div>
          <div className="kpi">
            <span className="kpi__label">“I have this too”</span>
            <span className="kpi__value">{problem.me_too_count}</span>
            <span className="kpi__sub">never earns points</span>
          </div>
          <div className="kpi">
            <span className="kpi__label">State</span>
            <span className="kpi__value" style={{ fontSize: 18 }}>
              {problem.state.replace(/_/g, ' ')}
            </span>
          </div>
        </div>

        <div className="chip-row" style={{ marginTop: 12 }}>
          {problem.terms.map((t) => (
            <span key={t} className="tag">
              {t}
            </span>
          ))}
        </div>

        {problem.acknowledged_at ? (
          <div className="notice notice--ok" style={{ marginTop: 12 }}>
            <Icon name="check" size={16} />
            <span>
              Acknowledged {fmtDate(problem.acknowledged_at, true)}
              {problem.note ? `: ${problem.note}` : ''}
            </span>
          </div>
        ) : null}

        <div className="row" style={{ marginTop: 'var(--space-4)', gap: 8 }}>
          <button
            type="button"
            className={`btn${problem.me_too_mine ? ' btn--primary' : ''}`}
            aria-pressed={problem.me_too_mine}
            onClick={async () => {
              if (problem.me_too_mine) await problemsApi.unMeToo(key);
              else await problemsApi.meToo(key);
              reload();
            }}
          >
            <Icon name="hand" size={16} />{' '}
            {problem.me_too_mine
              ? 'You have this problem too'
              : 'I have this problem too'}{' '}
            <span className="count">{problem.me_too_count}</span>
          </button>
          {canSubmit ? (
            <Link
              className="btn btn--primary"
              to={`/submit?problem=${encodeURIComponent(key)}`}
            >
              <Icon name="plus" size={16} /> Submit an idea for this problem
            </Link>
          ) : null}
        </div>
      </div>

      <div className="layout-rail layout-rail--wide">
        <div className="stack">
          <div className="card">
            <div className="card__head">
              <h2>Every time it was raised</h2>
              <span className="muted small">
                {problem.ideas.length} idea
                {problem.ideas.length === 1 ? '' : 's'}
              </span>
            </div>
            <div className="timeline">
              {problem.ideas.map((i) => (
                <div key={i.id} className="timeline__item">
                  <span className="timeline__dot">
                    <Icon name="list" size={14} />
                  </span>
                  <div>
                    <div className="row" style={{ gap: 6 }}>
                      <StatusPill status={i.status} />
                      <Link className="strong" to={`/ideas/${i.id}`}>
                        {i.title}
                      </Link>
                    </div>
                    <div className="muted small" style={{ marginTop: 2 }}>
                      Raised {fmtDate(i.submitted_at, true)}
                      {i.anonymous ? ' · anonymous' : ''}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <aside className="stack">
          {canLead ? (
            <div className="card">
              <div className="card__head">
                <h2>Leadership</h2>
              </div>
              <div className="field">
                <label htmlFor="pr-rename">Rename</label>
                <input
                  id="pr-rename"
                  className="input"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                />
              </div>
              <div className="row" style={{ marginTop: 10, gap: 8 }}>
                <button
                  type="button"
                  className="btn btn--sm"
                  onClick={async () => {
                    await problemsApi.updateMeta(key, { custom_label: label });
                    reload();
                  }}
                >
                  <Icon name="edit" size={14} /> Save name
                </button>
                <button
                  type="button"
                  className="btn btn--sm"
                  onClick={async () => {
                    await problemsApi.updateMeta(key, { acknowledge: true });
                    reload();
                  }}
                >
                  <Icon name="check" size={14} /> Acknowledge
                </button>
              </div>
            </div>
          ) : (
            <div className="card card--tight">
              <p className="muted small">
                Renaming and acknowledging are for leadership and
                administrators. “I have this problem too” is a signal of demand
                and never earns points.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
