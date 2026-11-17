import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ideasApi } from '../api/ideas';
import { Icon } from '../components/Icons';
import { StatusPill } from '../components/StatusPill';
import { STAGE_KEYS, STAGE_LABELS, STATUS_META } from '../constants/status';
import { useAuth } from '../auth/AuthProvider';
import { CAN_SUBMIT, ROLE_BLURBS, roleLabel } from '../constants/roles';
import { firstName, greeting, nextStep, relTime } from '../utils/format';
import type { HomeAggregates, Idea } from '../types/idea';
import type { Role } from '../types/auth';

export function HomePage() {
  const { user } = useAuth();
  const [data, setData] = useState<HomeAggregates | null>(null);
  const [mine, setMine] = useState<Idea[]>([]);
  const [queue, setQueue] = useState<Idea[]>([]);
  const [recent, setRecent] = useState<Idea[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const home = await ideasApi.home();
        if (!cancelled) setData(home);
        const [mineRes, recentRes] = await Promise.all([
          user
            ? ideasApi.list({ author_id: user.id, limit: 4 }).catch(() => ({
                items: [] as Idea[],
                total: 0,
              }))
            : Promise.resolve({ items: [] as Idea[], total: 0 }),
          ideasApi.list({ limit: 9 }).catch(() => ({ items: [] as Idea[], total: 0 })),
        ]);
        if (cancelled) return;
        setMine(mineRes.items.filter((i) => i.status !== 'draft'));
        setRecent(recentRes.items.filter((i) => i.status !== 'draft'));
        if (
          user &&
          (user.active_role === 'reviewer' || user.active_role === 'admin')
        ) {
          const q = await ideasApi
            .list({ status: 'under_review', limit: 4 })
            .catch(() => ({ items: [] as Idea[], total: 0 }));
          if (!cancelled) setQueue(q.items);
        }
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : 'Failed to load home');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  const active = (user?.active_role ?? 'contributor') as Role;
  const canSubmit = CAN_SUBMIT.includes(active);

  if (loading) {
    return (
      <div className="empty">
        <p className="muted">Loading home…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="notice notice--danger" role="alert">
        <Icon name="alert" size={18} />
        <span>{error}</span>
      </div>
    );
  }

  const counts = data?.status_counts ?? {};
  const awaiting =
    (counts.submitted ?? 0) +
    (counts.under_review ?? 0) +
    (counts.needs_info ?? 0);
  const acceptedOnly = counts.accepted ?? 0;
  const delivery = counts.prototype ?? 0;
  const implemented = counts.implemented ?? 0;
  const total = data?.total_live ?? 0;

  const tiles: Array<[string, number, string, string, string]> = [
    [
      'Total ideas',
      total,
      'submitted, excluding drafts and withdrawn',
      '/explore',
      'kpi--accent',
    ],
    [
      'Awaiting review',
      awaiting,
      'submitted, in review or waiting on the author',
      '/explore?status=under_review',
      'kpi--warning',
    ],
    [
      'Accepted',
      acceptedOnly,
      'accepted, not yet in prototype',
      '/explore?status=accepted',
      'kpi--success',
    ],
    [
      'In delivery',
      delivery,
      'in prototype',
      '/explore?status=prototype',
      'kpi--info',
    ],
    [
      'Implemented',
      implemented,
      'delivered',
      '/explore?status=implemented',
      'kpi--gold',
    ],
  ];

  const also: Array<[string, number, string]> = [
    ['parked', counts.parked ?? 0, 'parked'],
    ['declined', counts.declined ?? 0, 'declined'],
    ['merged', counts.merged ?? 0, 'merged'],
    ['withdrawn', counts.withdrawn ?? 0, 'withdrawn'],
  ];

  const stageValues = STAGE_KEYS.map((k) => {
    if (k === 'accepted') {
      return (
        (counts.accepted ?? 0) +
        (counts.parked ?? 0) +
        (counts.merged ?? 0) +
        (counts.declined ?? 0)
      );
    }
    if (k === 'under_review') {
      return (counts.under_review ?? 0) + (counts.needs_info ?? 0);
    }
    if (k === 'submitted') return counts.submitted ?? 0;
    return counts[k] ?? 0;
  });
  const maxStage = Math.max(1, ...stageValues);
  const attention = data?.needs_attention ?? [];
  const maxBar = Math.max(1, ...stageValues);

  let band: ReactNode;
  if (active === 'reviewer' || active === 'admin') {
    band = (
      <div className="card">
        <div className="card__head">
          <h2>
            {active === 'admin' ? 'Review queue across panels' : 'Your review queue'}
          </h2>
          <Link className="btn btn--sm" to="/review">
            Open queue
          </Link>
        </div>
        {queue.length ? (
          queue.map((i) => (
            <div key={i.id} className="listrow">
              <div className="listrow__main">
                <Link className="listrow__title" to={`/review/${i.id}`}>
                  {i.title}
                </Link>
                <div className="muted small">
                  {i.picked_up_at ? 'in review' : 'awaiting pickup'}
                  {i.due_at ? ` · due ${relTime(i.due_at)}` : ''}
                </div>
              </div>
              <StatusPill status={i.status} />
            </div>
          ))
        ) : (
          <div className="empty" style={{ padding: 24 }}>
            <Icon name="checkcircle" size={28} />
            <h3>Queue clear</h3>
            <p className="muted small">No ideas are waiting for a decision.</p>
          </div>
        )}
      </div>
    );
  } else if (active === 'lead') {
    const owned = mine.filter((i) =>
      ['accepted', 'prototype'].includes(i.status),
    );
    band = (
      <div className="card">
        <div className="card__head">
          <h2>My delivery items</h2>
          <Link className="btn btn--sm" to="/pipeline">
            Open pipeline
          </Link>
        </div>
        {owned.length ? (
          owned.map((i) => (
            <div key={i.id} className="listrow">
              <div className="listrow__main">
                <Link
                  className="listrow__title"
                  to={`/ideas/${i.id}?tab=delivery`}
                >
                  {i.title}
                </Link>
                <div className="muted small">{nextStep(i).text}</div>
              </div>
              <StatusPill status={i.status} />
            </div>
          ))
        ) : (
          <div className="empty" style={{ padding: 24 }}>
            <Icon name="layers" size={28} />
            <h3>Nothing assigned</h3>
            <p className="muted small">
              Accepted ideas without an owner appear under attention.
            </p>
          </div>
        )}
      </div>
    );
  } else if (active === 'leadership') {
    band = (
      <div className="card">
        <div className="card__head">
          <h2>Where ideas are waiting</h2>
          <Link className="btn btn--sm" to="/pipeline?stuck=1">
            See stuck ideas
          </Link>
        </div>
        <p className="muted small">
          Open Approvals for innovation-hour requests. Use Insights for pipeline
          health.
        </p>
        <div className="row" style={{ marginTop: 12, gap: 8 }}>
          <Link className="btn btn--sm btn--primary" to="/approvals">
            Open approvals
          </Link>
          <Link className="btn btn--sm" to="/insights">
            Insights
          </Link>
          <Link className="btn btn--sm" to="/problems">
            Problem radar
          </Link>
        </div>
      </div>
    );
  } else {
    band = (
      <div className="card">
        <div className="card__head">
          <h2>Your ideas</h2>
          <Link className="btn btn--sm" to="/my">
            All my ideas
          </Link>
        </div>
        {mine.length ? (
          mine.slice(0, 4).map((i) => (
            <div key={i.id} className="listrow">
              <div className="listrow__main">
                <Link className="listrow__title" to={`/ideas/${i.id}`}>
                  {i.title}
                </Link>
                <div className="muted small">{nextStep(i).text}</div>
              </div>
              <StatusPill status={i.status} />
            </div>
          ))
        ) : (
          <div className="empty" style={{ padding: 24 }}>
            <Icon name="plus" size={28} />
            <h3>No ideas yet</h3>
            <p className="muted small">
              Use New idea in the top bar — it takes about five minutes.
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">{greeting()}</div>
          <h1>Welcome back, {firstName(user?.name)}</h1>
          <p>{ROLE_BLURBS[active] ?? roleLabel(active)}</p>
        </div>
      </div>

      <div className="grid grid-5 kpi-row">
        {tiles.map(([label, value, sub, href, tone]) => (
          <Link key={label} className={`kpi ${tone}`} to={href}>
            <span className="kpi__label">{label}</span>
            <span className="kpi__value">{value}</span>
            <span className="kpi__sub">{sub}</span>
          </Link>
        ))}
      </div>
      <p className="muted small kpi-also">
        Also:{' '}
        {also.map(([status, n, lab], idx) => (
          <span key={status}>
            {idx ? ' · ' : ''}
            <Link to={`/explore?status=${status}`}>
              {n} {lab}
            </Link>
          </span>
        ))}
        . The four tiles after Total plus parked, declined and merged add up to
        the {total} total. Withdrawn ideas are not in the total.
      </p>

      <div className="layout-rail layout-rail--wide" style={{ marginTop: 'var(--space-5)' }}>
        <div className="stack">
          {band}

          <div className="card">
            <div className="card__head">
              <h2>Needs your attention</h2>
              <span className="muted small">
                {attention.length
                  ? `${attention.length} item${attention.length === 1 ? '' : 's'}`
                  : ''}
              </span>
            </div>
            {attention.length === 0 ? (
              <div className="empty" style={{ padding: 24 }}>
                <Icon name="checkcircle" size={28} />
                <h3>You are all caught up</h3>
                <p className="muted small">Nothing needs your action right now.</p>
              </div>
            ) : (
              <div className="stack stack--sm">
                {attention.slice(0, 8).map((item, idx) => {
                  const href =
                    typeof item.href === 'string' ? item.href : '/my';
                  const to = href.startsWith('#')
                    ? href.replace(/^#/, '') || '/'
                    : href;
                  const sev = Math.min(Number(item.priority) || 1, 2);
                  return (
                    <Link
                      key={idx}
                      className={`attn attn--${sev}`}
                      to={to.startsWith('/') ? to : `/${to}`}
                    >
                      <span className="attn__ic">
                        <Icon name="inbox" size={16} />
                      </span>
                      <span className="grow">{String(item.text ?? 'Open item')}</span>
                      <Icon name="chevronR" size={16} />
                    </Link>
                  );
                })}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card__head">
              <h2>Recent activity</h2>
            </div>
            {recent.length === 0 ? (
              <p className="muted small">No recent ideas yet.</p>
            ) : (
              <ul className="feed">
                {recent.map((i) => (
                  <li key={i.id}>
                    <span className="grow">
                      <Link to={`/ideas/${i.id}`}>{i.title}</Link>{' '}
                      <span className="muted">
                        · {STATUS_META[i.status]?.label ?? i.status}
                      </span>
                    </span>
                    <span className="when muted small">
                      {relTime(i.updated_at || i.submitted_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="stack">
          <div className="card">
            <div className="card__head">
              <h2>Lifecycle funnel</h2>
            </div>
            <div className="funnel">
              {STAGE_LABELS.map((label, i) => (
                <div key={label} className="funnel__row">
                  <span className="funnel__lab">{label}</span>
                  <span className="funnel__track">
                    <i
                      style={{
                        width: `${Math.round((stageValues[i] / maxStage) * 100)}%`,
                      }}
                    />
                  </span>
                  <span className="funnel__val mono">{stageValues[i]}</span>
                </div>
              ))}
            </div>
            <p className="muted small">
              Ideas that have reached each stage. Rejected and parked ideas count
              as reaching Decision.
            </p>
          </div>

          <div className="card">
            <div className="card__head">
              <h2>Where ideas are now</h2>
            </div>
            <div className="stagebar" aria-hidden="true">
              {stageValues.map((n, i) => (
                <span
                  key={STAGE_LABELS[i]}
                  style={{ flex: Math.max(0.08, n / maxBar) }}
                />
              ))}
            </div>
            <ul className="stagebar__legend">
              {STAGE_LABELS.map((label, i) => (
                <li key={label}>
                  <i aria-hidden="true" />
                  <span className="stagebar__lab">{label}</span>
                  <span className="mono">{stageValues[i]}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card">
            <div className="card__head">
              <h2>Quick links</h2>
            </div>
            <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
              <Link className="btn btn--sm" to="/pipeline">
                Pipeline board
              </Link>
              <Link className="btn btn--sm" to="/explore">
                Explore
              </Link>
              {canSubmit ? (
                <Link className="btn btn--sm" to="/my">
                  My ideas
                </Link>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
