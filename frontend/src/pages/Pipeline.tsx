/**
 * Pipeline board — `/pipeline`.
 * Five read-only stage columns; status changes only via review/delivery actions.
 */

import { type CSSProperties, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ideasApi } from '../api/ideas';
import { Icon } from '../components/Icons';
import { StatusPill } from '../components/StatusPill';
import { STAGE_LABELS, STATUS_META } from '../constants/status';
import type { Category, Idea } from '../types/idea';

const STAGE_INFO = [
  'Awaiting pickup by a reviewer',
  'Picked up or waiting on the author',
  'Accepted, parked, merged or declined',
  'Building with innovation hours',
  'Delivered',
] as const;

function stageOf(status: string): number {
  if (status === 'submitted') return 0;
  if (status === 'under_review' || status === 'needs_info') return 1;
  if (['accepted', 'parked', 'merged', 'declined'].includes(status)) return 2;
  if (status === 'prototype') return 3;
  if (status === 'implemented') return 4;
  return -1;
}

function stuckReason(idea: Idea): string | null {
  const now = Date.now();
  if (
    (idea.status === 'submitted' || idea.status === 'under_review') &&
    idea.due_at &&
    new Date(idea.due_at).getTime() < now
  ) {
    return 'Decision overdue';
  }
  if (idea.status === 'accepted' && !idea.owner_id) {
    return 'Awaiting owner';
  }
  if (idea.status === 'accepted' && idea.awaiting_owner) {
    return 'Awaiting owner';
  }
  if (idea.status === 'prototype' && idea.stage_entered_at) {
    const days =
      (now - new Date(idea.stage_entered_at).getTime()) / (1000 * 60 * 60 * 24);
    if (days > 14) return `Stale ${Math.floor(days)}d`;
  }
  return null;
}

function daysInStage(idea: Idea): number {
  const start = idea.stage_entered_at || idea.created_at;
  return Math.max(
    0,
    Math.floor((Date.now() - new Date(start).getTime()) / (1000 * 60 * 60 * 24)),
  );
}

function subState(idea: Idea): string {
  if (idea.status === 'needs_info') return 'Waiting on author';
  if (idea.status === 'submitted') return 'In queue';
  if (idea.status === 'under_review') return 'With reviewer';
  return STATUS_META[idea.status]?.label ?? idea.status;
}

export function PipelinePage() {
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<Idea[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const categoryId = params.get('category_id') ?? '';
  const stuckOnly = params.get('stuck') === '1';

  const catMap = useMemo(() => {
    const m = new Map<string, Category>();
    categories.forEach((c) => m.set(c.id, c));
    return m;
  }, [categories]);

  useEffect(() => {
    ideasApi.categories().then(setCategories).catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await ideasApi.list({
          category_id: categoryId || undefined,
          limit: 100,
        });
        if (!cancelled) setItems(res.items);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : 'Failed to load pipeline');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [categoryId]);

  const live = useMemo(
    () =>
      items.filter(
        (i) => !i.is_draft && i.status !== 'draft' && i.status !== 'withdrawn',
      ),
    [items],
  );

  const filtered = useMemo(() => {
    let list = live;
    if (stuckOnly) list = list.filter((i) => stuckReason(i));
    return list;
  }, [live, stuckOnly]);

  const cols = useMemo(() => {
    const out: Idea[][] = [[], [], [], [], []];
    for (const idea of filtered) {
      const s = stageOf(idea.status);
      if (s >= 0) out[s].push(idea);
    }
    for (const col of out) {
      col.sort((a, b) => {
        const sa = stuckReason(a) ? 0 : 1;
        const sb = stuckReason(b) ? 0 : 1;
        if (sa !== sb) return sa - sb;
        const ta = new Date(a.stage_entered_at || a.created_at).getTime();
        const tb = new Date(b.stage_entered_at || b.created_at).getTime();
        return ta - tb;
      });
    }
    return out;
  }, [filtered]);

  const counts = cols.map((c) => c.length);
  const total = counts.reduce((a, b) => a + b, 0);
  const maxCount = Math.max(1, ...counts);

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };

  const toggleStuck = () => {
    const next = new URLSearchParams(params);
    if (stuckOnly) next.delete('stuck');
    else next.set('stuck', '1');
    setParams(next);
  };

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Pipeline</div>
          <h1>Idea pipeline</h1>
          <p>
            Where every idea sits in the five stages, and which ones are stuck.
            Stages change only through reviewer decisions and owner actions on
            the idea, never by dragging cards.
          </p>
        </div>
      </div>

      <div className="card card--tight">
        <div className="stagebar" aria-hidden="true">
          {counts.map((n, i) => (
            <span
              key={STAGE_LABELS[i]}
              style={{ flex: Math.max(0.08, n / maxCount) }}
            />
          ))}
        </div>
        <ul className="stagebar__legend">
          {STAGE_LABELS.map((label, i) => (
            <li key={label}>
              <i aria-hidden="true" />
              <span className="stagebar__lab">{label}</span>
              <span className="mono">{counts[i]}</span>
            </li>
          ))}
        </ul>
        <p className="muted small" style={{ marginTop: 8 }}>
          {total} ideas on the board
          {stuckOnly ? ' (stuck only)' : ''}
        </p>
      </div>

      <div className="filters">
        <div className="field">
          <label htmlFor="pl-cat">Category</label>
          <select
            id="pl-cat"
            className="select"
            value={categoryId}
            onChange={(e) => setFilter('category_id', e.target.value)}
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <span className="label">&nbsp;</span>
          <button
            type="button"
            className="btn"
            aria-pressed={stuckOnly}
            onClick={toggleStuck}
          >
            <Icon name="alert" size={16} /> Stuck only
          </button>
        </div>
        {categoryId || stuckOnly ? (
          <div className="field">
            <span className="label">&nbsp;</span>
            <Link className="btn btn--ghost" to="/pipeline">
              Clear filters
            </Link>
          </div>
        ) : null}
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      {loading ? (
        <p className="muted">Loading pipeline…</p>
      ) : (
        <>
          <p className="board-cue muted" id="board-cue">
            <Icon name="chevronR" size={14} /> All five stages sit side by side
            on wide screens. Scroll sideways to see the rest.
          </p>
          <div className="board" role="list">
            {STAGE_LABELS.map((label, n) => (
              <section
                key={label}
                className="board__col"
                role="listitem"
                aria-label={label}
              >
                <div className="board__head">
                  <span>{label}</span>
                  <span className="pill">{cols[n].length}</span>
                </div>
                <div className="muted small" style={{ padding: '0 6px 8px' }}>
                  {STAGE_INFO[n]}
                </div>
                <div className="board__list">
                  {cols[n].length === 0 ? (
                    <p className="muted small" style={{ padding: '8px 6px' }}>
                      Nothing here{stuckOnly ? ' is stuck' : ''}.
                    </p>
                  ) : (
                    cols[n].map((idea) => {
                      const stuck = stuckReason(idea);
                      const muted = ['declined', 'merged'].includes(idea.status);
                      const cat = idea.category_id
                        ? catMap.get(idea.category_id)
                        : null;
                      return (
                        <Link
                          key={idea.id}
                          className={`pcard${stuck ? ' pcard--stuck' : ''}${
                            muted ? ' pcard--muted' : ''
                          }`}
                          to={`/ideas/${idea.id}`}
                        >
                          <span className="pcard__title">{idea.title}</span>
                          <span className="row" style={{ gap: 6 }}>
                            {cat ? (
                              <span
                                className="tag tag--cat"
                                style={
                                  cat.color
                                    ? ({
                                        ['--cat-color']: cat.color,
                                      } as CSSProperties)
                                    : undefined
                                }
                              >
                                <i className="dot" aria-hidden="true" />
                                {cat.label}
                              </span>
                            ) : null}
                            <StatusPill status={idea.status} />
                          </span>
                          <span className="muted small">{subState(idea)}</span>
                          {stuck ? (
                            <span
                              className="small"
                              style={{
                                color: 'var(--danger)',
                                fontWeight: 600,
                              }}
                            >
                              {stuck}
                            </span>
                          ) : null}
                          <span
                            className="row small muted"
                            style={{
                              gap: 8,
                              justifyContent: 'space-between',
                            }}
                          >
                            <span />
                            <span className="mono">{daysInStage(idea)}d in stage</span>
                          </span>
                        </Link>
                      );
                    })
                  )}
                </div>
              </section>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
