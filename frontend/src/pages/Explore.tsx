import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ideasApi } from '../api/ideas';
import { IdeaCard } from '../components/IdeaCard';
import { Icon } from '../components/Icons';
import type { Category, Idea } from '../types/idea';

const STATUS_OPTS: Array<[string, string]> = [
  ['', 'Any status'],
  ['submitted', 'Submitted'],
  ['under_review', 'Submitted or in review'],
  ['needs_info', 'Needs info only'],
  ['accepted', 'Accepted'],
  ['parked', 'Parked'],
  ['merged', 'Merged'],
  ['declined', 'Declined'],
  ['prototype', 'In prototype'],
  ['implemented', 'Implemented'],
  ['withdrawn', 'Withdrawn'],
];

const SORT_OPTS: Array<[string, string]> = [
  ['newest', 'Newest'],
  ['votes', 'Most upvoted'],
  ['discussed', 'Most discussed'],
];

export function ExplorePage() {
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<Idea[]>([]);
  const [total, setTotal] = useState(0);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const q = params.get('q') ?? '';
  const status = params.get('status') ?? '';
  const categoryId = params.get('category_id') ?? params.get('cat') ?? '';
  const tag = params.get('tag') ?? '';
  const sort = params.get('sort') ?? 'newest';
  const following = params.get('following') === '1';

  const catMap = useMemo(() => {
    const m = new Map<string, Category>();
    categories.forEach((c) => m.set(c.id, c));
    return m;
  }, [categories]);

  const allTags = useMemo(() => {
    const set = new Set<string>();
    items.forEach((i) => i.tags.forEach((t) => set.add(t)));
    return Array.from(set).sort();
  }, [items]);

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
          q: q || undefined,
          status: status || undefined,
          category_id: categoryId || undefined,
          tag: tag || undefined,
          following: following || undefined,
          limit: 50,
        });
        if (cancelled) return;
        const list = [...res.items];
        if (sort === 'votes') {
          list.sort((a, b) => b.vote_count - a.vote_count);
        } else if (sort === 'discussed') {
          list.sort((a, b) => b.comment_count - a.comment_count);
        } else {
          list.sort(
            (a, b) =>
              new Date(b.submitted_at || b.created_at).getTime() -
              new Date(a.submitted_at || a.created_at).getTime(),
          );
        }
        setItems(list);
        setTotal(res.total);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : 'Failed to load ideas');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [q, status, categoryId, tag, following, sort]);

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key === 'sort' && value === 'newest') next.delete('sort');
    setParams(next);
  };

  const toggleFollowing = () => {
    const next = new URLSearchParams(params);
    if (following) next.delete('following');
    else next.set('following', '1');
    setParams(next);
  };

  const clearFilters = () => setParams({});

  const [qDraft, setQDraft] = useState(q);
  useEffect(() => {
    setQDraft(q);
  }, [q]);
  useEffect(() => {
    const t = window.setTimeout(() => {
      if (qDraft !== q) update('q', qDraft);
    }, 280);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce q only
  }, [qDraft]);

  const active =
    Boolean(q) ||
    Boolean(status) ||
    Boolean(categoryId) ||
    Boolean(tag) ||
    following ||
    (sort && sort !== 'newest');

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Discover</div>
          <h1>Explore ideas</h1>
          <p>
            Search every idea in the company, upvote the ones you want to see
            happen, and offer to help build them.
          </p>
        </div>
      </div>

      <div className="card card--tight" style={{ marginBottom: 'var(--space-4)' }}>
        <div className="filters" role="search">
          <div className="field field--q">
            <label htmlFor="ex-q">Search</label>
            <input
              className="input"
              id="ex-q"
              type="search"
              value={qDraft}
              onChange={(e) => setQDraft(e.target.value)}
              placeholder="Title, problem, tag or author"
              autoComplete="off"
            />
          </div>
          <div className="field">
            <label htmlFor="ex-cat">Category</label>
            <select
              className="select"
              id="ex-cat"
              value={categoryId}
              onChange={(e) => update('category_id', e.target.value)}
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
            <label htmlFor="ex-status">Status</label>
            <select
              className="select"
              id="ex-status"
              value={status}
              onChange={(e) => update('status', e.target.value)}
            >
              {STATUS_OPTS.map(([v, lab]) => (
                <option key={v || 'any'} value={v}>
                  {lab}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="ex-tag">Tag</label>
            <select
              className="select"
              id="ex-tag"
              value={tag}
              onChange={(e) => update('tag', e.target.value)}
            >
              <option value="">Any tag</option>
              {allTags.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
              {/* Allow typed tags not yet in current result set */}
              {tag && !allTags.includes(tag) ? (
                <option value={tag}>{tag}</option>
              ) : null}
            </select>
          </div>
          <div className="field">
            <label htmlFor="ex-sort">Sort by</label>
            <select
              className="select"
              id="ex-sort"
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
          <div className="field">
            <span className="label">&nbsp;</span>
            <button
              type="button"
              className="btn"
              data-pressed={following ? 'true' : 'false'}
              aria-pressed={following}
              onClick={toggleFollowing}
            >
              <Icon name="eye" size={16} /> Following
            </button>
          </div>
        </div>
        <div className="row row--between">
          <span aria-live="polite" className="muted">
            <strong className="mono" style={{ color: 'var(--text)' }}>
              {loading ? '…' : items.length}
            </strong>{' '}
            {items.length === 1 ? 'idea' : 'ideas'}
            {active ? ' match your filters' : ''}
            {!loading && total > items.length ? ` (of ${total})` : ''}
          </span>
          {active ? (
            <button
              type="button"
              className="btn btn--sm btn--ghost"
              onClick={clearFilters}
            >
              <Icon name="x" size={14} /> Clear filters
            </button>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      {loading ? (
        <p className="muted">Loading ideas…</p>
      ) : items.length === 0 ? (
        <div className="card">
          <div className="empty">
            <Icon name="search" size={32} />
            <h3>No ideas match</h3>
            <p className="muted">
              Try removing a filter or searching for a shorter word.
            </p>
            {active ? (
              <button type="button" className="btn" onClick={clearFilters}>
                Clear filters
              </button>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="cards">
          {items.map((idea) => (
            <IdeaCard
              key={idea.id}
              idea={idea}
              category={
                idea.category_id ? catMap.get(idea.category_id) : null
              }
            />
          ))}
        </div>
      )}

    </div>
  );
}
