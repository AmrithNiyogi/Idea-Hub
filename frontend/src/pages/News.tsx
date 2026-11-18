/** AI Newsletter — route `/news`. */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { newsApi } from '../api/news';
import { useAuth } from '../auth/AuthProvider';
import { Icon } from '../components/Icons';
import { NewsInsightsPanel } from '../components/NewsInsightsPanel';
import type { NewsCategory, NewsFeed, NewsInsights } from '../types/news';

const SOURCE_NOTE: Record<NewsFeed['source'], string> = {
  sample: 'Open a story to read the full source.',
  arxiv:
    'Live from arXiv, newest first. Papers are not ranked by importance or peer reviewed.',
  github:
    'Live from GitHub: new AI repositories from the last 7 days, ranked by stars. Stars show interest, not quality.',
};

const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

export function timeAgo(iso: string | null, now = Date.now()): string {
  if (!iso) return '';
  const diff = Math.max(0, now - Date.parse(iso));
  if (diff < MINUTE_MS) return 'just now';
  if (diff < HOUR_MS) return `${Math.floor(diff / MINUTE_MS)} min ago`;
  if (diff < DAY_MS) return `${Math.floor(diff / HOUR_MS)} h ago`;
  return `${Math.floor(diff / DAY_MS)} d ago`;
}

export function NewsPage() {
  const { user } = useAuth();
  const isAdmin = (user?.roles ?? []).includes('admin');
  const [params, setParams] = useSearchParams();
  const [categories, setCategories] = useState<NewsCategory[]>([]);
  const [feed, setFeed] = useState<NewsFeed | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [insights, setInsights] = useState<NewsInsights | null>(null);
  const [insightsFailed, setInsightsFailed] = useState(false);
  const requestId = useRef(0);
  const autoRefreshed = useRef(new Set<string>());

  const selected = params.get('c') ?? categories[0]?.slug ?? '';

  const run = useCallback(async (call: () => Promise<NewsFeed>, silent: boolean) => {
    const id = ++requestId.current;
    if (silent) setRefreshing(true);
    else setLoading(true);
    try {
      const next = await call();
      if (id === requestId.current) {
        setFeed(next);
        setError(null);
      }
    } catch (e) {
      if (id === requestId.current)
        setError(e instanceof Error ? e.message : "Couldn't load the newsletter");
    } finally {
      if (id === requestId.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    newsApi
      .categories()
      .then(setCategories)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Couldn't load categories"),
      );
  }, []);

  useEffect(() => {
    newsApi
      .insights()
      .then(setInsights)
      .catch(() => setInsightsFailed(true));
  }, []);

  useEffect(() => {
    if (selected) void run(() => newsApi.feed(selected), false);
  }, [selected, run]);

  // Stored results older than the refresh window: show them, then refresh once.
  useEffect(() => {
    if (
      feed?.stale &&
      feed.category === selected &&
      !autoRefreshed.current.has(selected)
    ) {
      autoRefreshed.current.add(selected);
      void run(() => newsApi.refresh(selected), true);
    }
  }, [feed, selected, run]);

  const select = (slug: string) => {
    const next = new URLSearchParams(params);
    if (slug === categories[0]?.slug) next.delete('c');
    else next.set('c', slug);
    setParams(next);
  };

  if (error && !feed) {
    return (
      <div className="notice notice--danger" role="alert">
        <Icon name="alert" size={18} />
        <span>{error}</span>
      </div>
    );
  }

  const notice = error ?? feed?.error ?? null;

  return (
    <div className="stack stack--lg page nws">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Insight</div>
          <h1>AI Newsletter</h1>
          <p>
            {feed?.refreshed_at
              ? `Updated ${timeAgo(feed.refreshed_at)} · ${feed.items.length} stories`
              : 'The latest AI news, by topic.'}
          </p>
        </div>
        {isAdmin ? (
          <button
            type="button"
            className="btn"
            disabled={refreshing || loading || !selected}
            onClick={() => void run(() => newsApi.refresh(selected, true), true)}
          >
            <Icon name="refresh" size={16} />
            Refresh
          </button>
        ) : null}
      </div>

      <div className="chip-row nws-cats" role="group" aria-label="Category">
        {categories.map((c) => (
          <button
            key={c.slug}
            type="button"
            className="chip-link"
            aria-current={c.slug === selected ? 'true' : undefined}
            onClick={() => select(c.slug)}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="nws-layout">
        <div className="nws-main stack stack--lg">
          {feed?.source === 'sample' ? (
            <div className="notice" role="note">
              <Icon name="info" size={18} />
              <span>
                Sample data: these stories are fictional placeholders until the live news
                agent is connected.
              </span>
            </div>
          ) : null}
          {refreshing ? (
            <div className="notice" role="status">
              <Icon name="clock" size={18} />
              <span>Updating…</span>
            </div>
          ) : null}
          {notice ? (
            <div className="notice notice--danger" role="alert">
              <Icon name="alert" size={18} />
              <span>
                {notice}
                {feed?.items.length ? ' Showing the last good results.' : ''}
              </span>
            </div>
          ) : null}

          {loading && !feed ? (
            <div className="skeleton nws-skeleton" aria-busy="true">
              <i style={{ width: '90%' }} />
              <i style={{ width: '70%' }} />
              <i style={{ width: '85%' }} />
              <i style={{ width: '45%' }} />
            </div>
          ) : feed && feed.category === selected ? (
            <>
              {feed.brief ? (
                <div className="nws-brief">
                  <span className="eyebrow eyebrow--plain">
                    <Icon name="spark" size={14} /> Today&apos;s brief
                  </span>
                  <p>{feed.brief}</p>
                </div>
              ) : null}

              {feed.items.length ? (
                <div className="nws-rows card card--flush">
                  {feed.items.map((item, i) => (
                    <article
                      key={item.id}
                      className={i === 0 ? 'nws-row nws-row--feat' : 'nws-row'}
                    >
                      <time className="nws-time" dateTime={item.published_at}>
                        {timeAgo(item.published_at)}
                      </time>
                      <div className="nws-body">
                        <h2>
                          <a href={item.url} target="_blank" rel="noopener noreferrer">
                            {item.title}
                          </a>
                        </h2>
                        {item.summary ? <p>{item.summary}</p> : null}
                        {item.why_it_matters ? (
                          <p className="nws-why">{item.why_it_matters}</p>
                        ) : null}
                        <div className="nws-meta">
                          {item.source_name ? (
                            <span className="chip-link">{item.source_name}</span>
                          ) : null}
                          <span>{feed.label}</span>
                        </div>
                      </div>
                      <a
                        className="nws-open"
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`Open source: ${item.title}`}
                      >
                        <Icon name="external" size={16} />
                      </a>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="empty card">
                  <Icon name="inbox" size={28} />
                  <h3>No recent AI stories in {feed.label}</h3>
                  <p>Try another category, or check back later.</p>
                </div>
              )}
              <p className="nws-foot">{SOURCE_NOTE[feed.source]}</p>
            </>
          ) : null}
        </div>
        <NewsInsightsPanel insights={insights} failed={insightsFailed} />
      </div>
    </div>
  );
}
