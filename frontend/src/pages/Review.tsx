import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { reviewApi } from '../api/review';
import { ideasApi } from '../api/ideas';
import { Icon } from '../components/Icons';
import { useAuth } from '../auth/AuthProvider';
import { REVIEW_ROLES } from '../constants/roles';
import { fmtDate } from '../utils/format';
import type { Role } from '../types/auth';
import type { Category } from '../types/idea';
import type { ReviewQueueItem } from '../types/review';

type Filter = '' | 'overdue' | 'unscored' | 'needsinfo' | 'unpicked';

export function ReviewPage() {
  const { user } = useAuth();
  const active = (user?.active_role ?? 'contributor') as Role;
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const f = (params.get('f') as Filter) || '';

  useEffect(() => {
    ideasApi.categories().then(setCategories).catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    if (!REVIEW_ROLES.includes(active)) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const queue = await reviewApi.queue();
        if (!cancelled) setItems(queue);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : 'Failed to load queue');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [active]);

  const catLabel = (id: string | null) =>
    categories.find((c) => c.id === id)?.label ?? '—';

  const filtered = useMemo(() => {
    let list = [...items];
    if (f === 'overdue')
      list = list.filter(
        (r) => r.days_until_due != null && r.days_until_due < 0,
      );
    else if (f === 'needsinfo')
      list = list.filter((r) => r.status === 'needs_info');
    else if (f === 'unpicked')
      list = list.filter(
        (r) => r.status === 'under_review' && !r.picked_up_at,
      );
    else if (f === 'unscored')
      list = list.filter(
        (r) => r.status === 'under_review' && !r.reviewer_id,
      );
    return list.sort((a, b) => {
      const ai = a.status === 'needs_info' ? 1 : 0;
      const bi = b.status === 'needs_info' ? 1 : 0;
      if (ai !== bi) return ai - bi;
      const ad = a.due_at ? new Date(a.due_at).getTime() : 0;
      const bd = b.due_at ? new Date(b.due_at).getTime() : 0;
      return ad - bd;
    });
  }, [items, f]);

  const counts = useMemo(() => {
    const base = items;
    return {
      all: base.length,
      overdue: base.filter(
        (r) => r.days_until_due != null && r.days_until_due < 0,
      ).length,
      unscored: base.filter(
        (r) => r.status === 'under_review' && !r.reviewer_id,
      ).length,
      unpicked: base.filter(
        (r) => r.status === 'under_review' && !r.picked_up_at,
      ).length,
      needsinfo: base.filter((r) => r.status === 'needs_info').length,
    };
  }, [items]);

  const setFilter = (next: Filter) => {
    const p = new URLSearchParams(params);
    if (next) p.set('f', next);
    else p.delete('f');
    setParams(p);
  };

  const pickup = async (ideaId: string) => {
    setBusyId(ideaId);
    setError(null);
    try {
      await reviewApi.pickup(ideaId);
      const queue = await reviewApi.queue();
      setItems(queue);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Pickup failed');
    } finally {
      setBusyId(null);
    }
  };

  if (!REVIEW_ROLES.includes(active)) {
    return (
      <div className="card" style={{ maxWidth: 640, margin: '48px auto' }}>
        <div className="empty">
          <Icon name="lock" size={36} />
          <h2>Review needs the Reviewer role</h2>
          <p className="muted">
            Switch to Reviewer or Administrator from the account menu if you hold
            that role.
          </p>
        </div>
      </div>
    );
  }

  const chips: Array<[Filter, string, number]> = [
    ['', 'All', counts.all],
    ['overdue', 'Overdue', counts.overdue],
    ['unscored', 'Unscored', counts.unscored],
    ['unpicked', 'Awaiting pickup', counts.unpicked],
    ['needsinfo', 'Needs info', counts.needsinfo],
  ];

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Review</div>
          <h1>Review queue</h1>
          <p>
            Sorted by time remaining. Every decision needs a written reason.
          </p>
        </div>
      </div>

      <div
        className="row"
        style={{ marginBottom: 'var(--space-4)' }}
        role="group"
        aria-label="Filter the queue"
      >
        {chips.map(([id, label, n]) => (
          <button
            key={id || 'all'}
            type="button"
            className="chip-link"
            aria-current={f === id ? 'true' : undefined}
            onClick={() => setFilter(id)}
          >
            {label}
            <span className="count">{n}</span>
          </button>
        ))}
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      {loading ? (
        <p className="muted">Loading queue…</p>
      ) : filtered.length === 0 ? (
        <div className="card">
          <div className="empty">
            <Icon name="checkcircle" size={32} />
            <h3>Nothing matches</h3>
            <p className="muted">
              No ideas match this filter. Clear the filter to see the whole
              queue.
            </p>
            {f ? (
              <button type="button" className="btn" onClick={() => setFilter('')}>
                Clear filters
              </button>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="card card--flush">
          <div className="table-wrap">
            <table className="table table--cards">
              <thead>
                <tr>
                  <th>Idea</th>
                  <th>Panel</th>
                  <th>Submitted</th>
                  <th>State</th>
                  <th>Time remaining</th>
                  <th>Reviewer</th>
                  <th>
                    <span className="sr-only">Action</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => {
                  const overdue =
                    row.days_until_due != null && row.days_until_due < 0;
                  const dueSoon =
                    row.days_until_due != null &&
                    row.days_until_due >= 0 &&
                    row.days_until_due <= 2;
                  const timeLabel =
                    row.days_until_due == null
                      ? '—'
                      : overdue
                        ? `${Math.abs(Math.round(row.days_until_due))}d overdue`
                        : `${Math.round(row.days_until_due)}d left`;
                  const tone = overdue
                    ? 'danger'
                    : dueSoon
                      ? 'warning'
                      : '';
                  return (
                    <tr key={row.idea_id}>
                      <td className="title-cell" data-label="Idea">
                        <Link to={`/review/${row.idea_id}`}>{row.title}</Link>
                      </td>
                      <td data-label="Panel">
                        <span className="tag">{catLabel(row.category_id)}</span>
                      </td>
                      <td data-label="Submitted">
                        {fmtDate(row.submitted_at)}
                      </td>
                      <td data-label="State">
                        {row.status === 'needs_info' ? (
                          <span className="pill pill--warning">Needs info</span>
                        ) : row.picked_up_at ? (
                          <span className="pill pill--brand">In review</span>
                        ) : (
                          <span className="pill pill--info">Awaiting pickup</span>
                        )}
                      </td>
                      <td data-label="Time">
                        <span
                          className={`pill${tone ? ` pill--${tone}` : ''}`}
                        >
                          <Icon
                            name={overdue ? 'alert' : 'clock'}
                            size={12}
                          />{' '}
                          {timeLabel}
                        </span>
                      </td>
                      <td data-label="Reviewer">
                        {row.reviewer_id ? (
                          <span className="mono small">
                            {row.reviewer_id.slice(0, 8)}…
                          </span>
                        ) : (
                          <span className="muted">Unassigned</span>
                        )}
                      </td>
                      <td data-label="">
                        {row.status === 'under_review' && !row.picked_up_at ? (
                          <button
                            type="button"
                            className="btn btn--sm"
                            disabled={busyId === row.idea_id}
                            onClick={() => pickup(row.idea_id)}
                          >
                            Pick up
                          </button>
                        ) : null}{' '}
                        <Link
                          className="btn btn--sm btn--primary"
                          to={`/review/${row.idea_id}`}
                        >
                          Review
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
