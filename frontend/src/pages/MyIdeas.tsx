import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ideasApi } from '../api/ideas';
import { Icon } from '../components/Icons';
import { StatusPill } from '../components/StatusPill';
import { useAuth } from '../auth/AuthProvider';
import { nextStep, relTime } from '../utils/format';
import type { Category, Idea } from '../types/idea';

type Tab = 'submitted' | 'following' | 'drafts';

export function MyIdeasPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>('submitted');
  const [items, setItems] = useState<Idea[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ideasApi.categories().then(setCategories).catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        let res;
        if (tab === 'following') {
          res = await ideasApi.list({ following: true, limit: 50 });
        } else if (tab === 'drafts') {
          res = await ideasApi.list({
            author_id: user.id,
            include_drafts: true,
            status: 'draft',
            limit: 50,
          });
        } else {
          res = await ideasApi.list({
            author_id: user.id,
            limit: 50,
          });
        }
        if (!cancelled) {
          setItems(
            tab === 'drafts'
              ? res.items
              : res.items.filter((i) => i.status !== 'draft'),
          );
        }
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user, tab]);

  const catLabel = (id: string | null) =>
    categories.find((c) => c.id === id)?.label ?? 'Uncategorised';

  const draftCount = tab === 'drafts' ? items.length : undefined;

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Your work</div>
          <h1>My ideas</h1>
          <p>
            Every idea you wrote, helped with or follow, with its status and the
            next step.
          </p>
        </div>
        <div className="row">
          {draftCount ? (
            <button
              type="button"
              className="btn"
              onClick={() => setTab('drafts')}
            >
              {draftCount} draft{draftCount === 1 ? '' : 's'}
            </button>
          ) : null}
          <Link className="btn btn--primary" to="/submit">
            <Icon name="plus" size={16} /> Submit an idea
          </Link>
        </div>
      </div>

      <div className="tabs" role="tablist">
        {(
          [
            ['submitted', 'Submitted'],
            ['following', 'Following'],
            ['drafts', 'Drafts'],
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
            {tab === id && items.length ? (
              <span className="count">{items.length}</span>
            ) : null}
          </button>
        ))}
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="card">
        {loading ? (
          <p className="muted">Loading…</p>
        ) : items.length === 0 ? (
          <div className="empty">
            <Icon
              name={
                tab === 'following' ? 'eye' : tab === 'drafts' ? 'edit' : 'plus'
              }
              size={32}
            />
            <h3>
              {tab === 'following'
                ? 'You are not following any ideas'
                : tab === 'drafts'
                  ? 'No drafts'
                  : 'You have not submitted an idea yet'}
            </h3>
            <p className="muted">
              {tab === 'following'
                ? 'Follow ideas in Explore to get updates — decisions, questions and delivery milestones land in your notifications.'
                : tab === 'drafts'
                  ? 'Save a draft from the submit page and it will appear here.'
                  : 'Share the first one. It takes about five minutes.'}
            </p>
            {tab === 'following' ? (
              <Link className="btn" to="/explore">
                Explore ideas
              </Link>
            ) : (
              <Link className="btn btn--primary" to="/submit">
                {tab === 'drafts' ? 'Start an idea' : 'Submit an idea'}
              </Link>
            )}
          </div>
        ) : tab === 'drafts' ? (
          items.map((i) => (
            <div key={i.id} className="listrow">
              <div className="listrow__main">
                <Link className="listrow__title" to={`/submit?draft=${i.id}`}>
                  {i.title || 'Untitled draft'}
                </Link>
                <div className="muted small">
                  {catLabel(i.category_id)} · saved {relTime(i.updated_at)}
                </div>
              </div>
              <Link className="btn btn--sm btn--primary" to={`/submit?draft=${i.id}`}>
                Resume
              </Link>
            </div>
          ))
        ) : (
          items.map((i) => {
            const ns = nextStep(i);
            return (
              <div key={i.id} className="listrow">
                <div className="listrow__main">
                  <Link className="listrow__title" to={`/ideas/${i.id}`}>
                    {i.title}
                  </Link>
                  <div className="muted small">
                    <span className="tag" style={{ marginRight: 6 }}>
                      {catLabel(i.category_id)}
                    </span>
                    {ns.text}
                  </div>
                </div>
                <div
                  className="stack stack--sm"
                  style={{ alignItems: 'flex-end' }}
                >
                  <StatusPill status={i.status} />
                  <span className="muted small">{relTime(i.updated_at)}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
