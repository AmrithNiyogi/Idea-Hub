/** Problem radar — route `/problems`. HTML layout clone. */

import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { problemsApi } from '../api/problems';
import { Icon } from '../components/Icons';
import type { Problem } from '../types/phase456';

const STATE_OPTS = [
  ['', 'Any state'],
  ['unsolved', 'Unsolved'],
  ['in_progress', 'In progress'],
  ['solved', 'Solved'],
] as const;

const SORT_OPTS = [
  ['raised', 'Most raised'],
  ['growing', 'Fastest growing'],
  ['teams', 'Most teams'],
  ['recent', 'Most recent'],
] as const;

export function ProblemsPage() {
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<Problem[]>([]);
  const [headline, setHeadline] = useState<{
    recurring: number;
    unsolved: number;
    again_30: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const state = params.get('state') ?? '';
  const sort = params.get('sort') ?? 'raised';

  useEffect(() => {
    setLoading(true);
    Promise.all([problemsApi.list(), problemsApi.headline()])
      .then(([list, h]) => {
        setItems(list);
        setHeadline(h);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'))
      .finally(() => setLoading(false));
  }, []);

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value && !(key === 'sort' && value === 'raised')) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };

  const lastRaised = (p: Problem) => {
    const times = p.ideas
      .map((i) => (i.submitted_at ? Date.parse(i.submitted_at) : 0))
      .filter((n) => Number.isFinite(n));
    return times.length ? Math.max(...times) : 0;
  };

  const filtered = items
    .filter((p) => !state || p.state === state)
    .slice()
    .sort((a, b) => {
      if (sort === 'teams') return b.team_count - a.team_count;
      if (sort === 'growing') return b.me_too_count - a.me_too_count;
      if (sort === 'recent') return lastRaised(b) - lastRaised(a);
      return b.idea_count - a.idea_count;
    });

  if (error) {
    return (
      <div className="notice notice--danger" role="alert">
        <Icon name="alert" size={18} />
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div className="stack stack--lg page problems">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Insight</div>
          <h1>Problem radar</h1>
          <p>
            Ideas come and go; problems stay. The radar groups ideas that
            describe the same underlying problem, so a declined idea can still
            count as evidence that the problem is live.
          </p>
        </div>
      </div>

      {headline ? (
        <div className="grid grid-3 kpi-row" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="kpi">
            <span className="kpi__label">Recurring problems</span>
            <span className="kpi__value">{headline.recurring}</span>
            <span className="kpi__sub">raised by two or more ideas</span>
          </div>
          <Link className="kpi" to="/problems?state=unsolved">
            <span className="kpi__label">Unsolved and recurring</span>
            <span className="kpi__value">{headline.unsolved}</span>
            <span className="kpi__sub">
              every attempt so far was declined or parked
            </span>
          </Link>
          <div className="kpi">
            <span className="kpi__label">Raised again in 30 days</span>
            <span className="kpi__value">{headline.again_30}</span>
            <span className="kpi__sub">
              a new idea joined an existing problem
            </span>
          </div>
        </div>
      ) : null}

      <div className="agent" style={{ marginBottom: 'var(--space-4)' }}>
        <div className="agent__head">
          <span className="agent__name">Innovation Analytics</span>
          <span className="agent__kind">Computed</span>
        </div>
        <div className="agent__body">
          <p className="muted small">
            Clusters are built from problem-statement similarity (shared terms
            and tags). Metoo earns no points.
          </p>
        </div>
      </div>

      <div className="filters">
        <div className="field">
          <label htmlFor="pr-state">State</label>
          <select
            className="select"
            id="pr-state"
            value={state}
            onChange={(e) => update('state', e.target.value)}
          >
            {STATE_OPTS.map(([v, lab]) => (
              <option key={v || 'any'} value={v}>
                {lab}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="pr-sort">Sort by</label>
          <select
            className="select"
            id="pr-sort"
            value={sort}
            onChange={(e) => update('sort', e.target.value)}
          >
            {SORT_OPTS.map(([v, lab]) => (
              <option key={v} value={v}>
                {lab}
              </option>
            ))}
          </select>
        </div>
        {state || sort !== 'raised' ? (
          <div className="field">
            <span className="label">&nbsp;</span>
            <Link className="btn btn--ghost" to="/problems">
              Clear
            </Link>
          </div>
        ) : null}
      </div>

      {loading ? (
        <p className="muted">Loading problems…</p>
      ) : !filtered.length ? (
        <div className="card">
          <div className="empty">
            <Icon name="target" size={32} />
            <h3>No problems match</h3>
            <p className="muted">
              No recurring problem fits these filters (need ≥2 similar ideas).
            </p>
            <Link className="btn" to="/problems">
              Clear filters
            </Link>
          </div>
        </div>
      ) : (
        <div className="stack">
          {filtered.map((p) => (
            <article key={p.cluster_key} className="card">
              <div className="row" style={{ gap: 6 }}>
                <span
                  className={`pill${
                    p.state === 'solved'
                      ? ' pill--success'
                      : p.state === 'in_progress'
                        ? ' pill--brand'
                        : ' pill--warning'
                  }`}
                >
                  {p.state.replace(/_/g, ' ')}
                </span>
              </div>
              <h3 style={{ marginTop: 8 }}>
                <Link to={`/problems/${p.cluster_key}`}>{p.label}</Link>
              </h3>
              <div className="muted small" style={{ marginTop: 4 }}>
                {p.idea_count} ideas · {p.me_too_count} metoo · {p.team_count}{' '}
                teams
              </div>
              <div className="chip-row" style={{ marginTop: 8 }}>
                {p.terms.slice(0, 6).map((t) => (
                  <span key={t} className="tag">
                    {t}
                  </span>
                ))}
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <Link
                  className="btn btn--sm btn--primary"
                  to={`/problems/${p.cluster_key}`}
                >
                  Open
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
