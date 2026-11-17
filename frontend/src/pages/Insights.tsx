/** Insights — route `/insights`. Computed aggregates from DB. HTML layout clone. */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { insightsApi } from '../api/insights';
import { Icon } from '../components/Icons';
import type { InsightsDashboard } from '../types/phase456';

export function InsightsPage() {
  const [days, setDays] = useState(90);
  const [data, setData] = useState<InsightsDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    insightsApi
      .dashboard(days)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'));
  }, [days]);

  if (error) {
    return (
      <div className="notice notice--danger" role="alert">
        <Icon name="alert" size={18} />
        <span>{error}</span>
      </div>
    );
  }
  if (!data) return <p className="muted">Loading insights…</p>;

  const hoursPeriod = data.impact.period.hours as
    | { v?: number; u?: number }
    | undefined;
  const maxFunnel = Math.max(1, ...data.funnel.counts);
  const maxTeam = Math.max(
    1,
    ...data.participation.by_team.map((t) => t.pct),
  );
  const maxTag = Math.max(1, ...data.themes.tags.map((t) => t.cur), 1);

  return (
    <div className="stack stack--lg page insights">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Leadership</div>
          <h1>Insights</h1>
          <p>
            Participation, conversion, review speed, impact and recognition —
            computed from live data. Narrative cards are Simulated.
          </p>
        </div>
      </div>

      <div className="ins-toolbar">
        <nav className="row" style={{ gap: 6 }} aria-label="Period">
          {[30, 90, 180].map((d) => (
            <button
              key={d}
              type="button"
              className="chip-link"
              aria-current={d === days ? 'true' : undefined}
              onClick={() => setDays(d)}
            >
              Last {d} days
            </button>
          ))}
        </nav>
        <span className="muted small">Period filter applies to every section.</span>
      </div>

      {data.cards.length ? (
        <div className="agent" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="agent__head">
            <span className="agent__name">Innovation Analytics</span>
            <span className="pill pill--agent">Simulated</span>
            <span className="agent__kind">Templated</span>
          </div>
          <div className="agent__body">
            {data.cards.map((c) => (
              <div key={c.id} className="ins-item" style={{ marginBottom: 12 }}>
                <span className="sim-chip">Simulated</span>
                <p>{c.text}</p>
                {c.link ? (
                  <Link to={c.link} className="btn btn--sm">
                    Open
                  </Link>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="ins-grid">
        <section className="card chart-card">
          <div className="chart-card__head">
            <div>
              <h2>Participation</h2>
              <p className="chart-card__blurb">
                Share of each team active in the last {days} days.
              </p>
            </div>
            <div className="kpi__value">{data.participation.pct}%</div>
          </div>
          <p className="muted small">
            {data.participation.active} of {data.participation.total} people
            active.
          </p>
          {data.participation.by_team.slice(0, 6).map((t) => (
            <div key={t.team_id} className="hbar">
              <span className="truncate">{t.team_name}</span>
              <div className="meter" aria-hidden="true">
                <i style={{ width: `${Math.round((100 * t.pct) / maxTeam)}%` }} />
              </div>
              <span className="mono">
                {t.active}/{t.size}
              </span>
            </div>
          ))}
        </section>

        <section className="card chart-card">
          <div className="chart-card__head">
            <div>
              <h2>Funnel and conversion</h2>
              <p className="chart-card__blurb">
                Ideas at the furthest stage they have reached.
              </p>
            </div>
          </div>
          <div className="funnel">
            {data.funnel.stages.map((s, i) => (
              <div key={s} className="funnel__row">
                <span className="funnel__lab">{s}</span>
                <span className="funnel__track">
                  <i
                    style={{
                      width: `${Math.round((data.funnel.counts[i] / maxFunnel) * 100)}%`,
                    }}
                  />
                </span>
                <span className="funnel__val mono">{data.funnel.counts[i]}</span>
              </div>
            ))}
          </div>
          <ul
            className="bullets"
            style={{
              listStyle: 'none',
              padding: 0,
              margin: '12px 0 0',
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
            }}
          >
            {data.funnel.conversions.map((c) => (
              <li
                key={`${c.from}-${c.to}`}
                className="row row--between"
                style={{ fontSize: 13 }}
              >
                <span>
                  {c.from} to {c.to}
                </span>
                <span className="mono">
                  {c.pct == null
                    ? 'no ideas yet'
                    : `${c.pct}% (${c.n} of ${c.of})`}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="card chart-card">
          <div className="chart-card__head">
            <div>
              <h2>Review performance</h2>
              <p className="chart-card__blurb">
                Overdue decisions and SLA of {data.review.timeline_days} working
                days.
              </p>
            </div>
          </div>
          <div className="mini-kpis">
            <div>
              <div className="kpi__label">Overdue</div>
              <div className="kpi__value">{data.review.overdue_total}</div>
            </div>
            <div>
              <div className="kpi__label">SLA</div>
              <div className="kpi__value">{data.review.timeline_days}d</div>
            </div>
          </div>
          <ul style={{ marginTop: 12 }}>
            {data.review.rows.map((r) => (
              <li key={String(r.panel_id)} className="listrow">
                <div className="listrow__main">
                  <span className="strong">{String(r.label)}</span>
                  <div className="muted small">
                    median {String(r.median ?? '—')}d · on-time{' '}
                    {String(r.on_time ?? '—')}% · overdue {String(r.overdue)}
                  </div>
                </div>
              </li>
            ))}
          </ul>
          <div className="row" style={{ marginTop: 8 }}>
            <Link className="btn btn--sm" to="/pipeline?stuck=1">
              <Icon name="alert" size={14} /> Stuck ideas
            </Link>
          </div>
        </section>

        <section className="card chart-card">
          <div className="chart-card__head">
            <div>
              <h2>Emerging themes</h2>
              <p className="chart-card__blurb">
                Tags ranked by growth against the previous {days} days.
              </p>
            </div>
          </div>
          {data.themes.tags.length ? (
            data.themes.tags.slice(0, 8).map((t) => (
              <div key={t.tag} className="hbar">
                <Link
                  className="truncate"
                  to={`/explore?tag=${encodeURIComponent(t.tag)}`}
                >
                  {t.tag}
                </Link>
                <div className="meter" aria-hidden="true">
                  <i
                    style={{
                      width: `${Math.round((100 * t.cur) / maxTag)}%`,
                    }}
                  />
                </div>
                <span className="mono">
                  {t.cur}
                  {t.growth > 0
                    ? ` (+${t.growth})`
                    : t.growth < 0
                      ? ` (${t.growth})`
                      : ''}
                </span>
              </div>
            ))
          ) : (
            <p className="muted">No ideas were submitted in this period.</p>
          )}
          <h3 style={{ margin: '16px 0 4px' }}>Strategic themes</h3>
          <ul>
            {data.themes.themes.slice(0, 6).map((t) => (
              <li key={t.id} className="muted small">
                {t.label}: {t.cur} (Δ{t.growth})
              </li>
            ))}
          </ul>
        </section>

        <section className="card chart-card">
          <div className="chart-card__head">
            <div>
              <h2>Business impact & hours</h2>
              <p className="chart-card__blurb">
                Verified hours saved and innovation pool remaining.
              </p>
            </div>
          </div>
          <div className="mini-kpis">
            <div>
              <div className="kpi__label">Verified hours</div>
              <div className="kpi__value">{hoursPeriod?.v ?? 0}</div>
              <div className="muted small">this period</div>
            </div>
            <div>
              <div className="kpi__label">Pool remaining</div>
              <div className="kpi__value">{data.hours.remaining}</div>
              <div className="muted small">
                of {data.hours.quarterly_hours} h
              </div>
            </div>
            <div>
              <div className="kpi__label">Granted</div>
              <div className="kpi__value">{data.hours.granted}</div>
            </div>
          </div>
        </section>

        <section className="card chart-card">
          <div className="chart-card__head">
            <div>
              <h2>Recognition</h2>
              <p className="chart-card__blurb">
                Points awarded in the last {days} days by dimension.
              </p>
            </div>
          </div>
          <p>
            <strong>{data.recognition.total}</strong> points across{' '}
            {data.recognition.rows} ledger rows.
          </p>
          {Object.entries(data.recognition.dims).map(([k, v]) => (
            <div key={k} className="hbar">
              <span>{k}</span>
              <div className="meter" aria-hidden="true">
                <i
                  style={{
                    width: `${Math.min(100, Math.round((100 * v) / Math.max(1, data.recognition.total)))}%`,
                  }}
                />
              </div>
              <span className="mono">{v}</span>
            </div>
          ))}
          <div className="row" style={{ marginTop: 10 }}>
            <Link className="btn btn--sm" to="/problems">
              Problem radar
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
