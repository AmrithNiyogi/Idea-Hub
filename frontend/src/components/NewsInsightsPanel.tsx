/** Side panel for the AI Newsletter: trending repos, weekly papers, recurring themes. */

import type { NewsInsights } from '../types/news';
import { Icon } from './Icons';

interface Props {
  insights: NewsInsights | null;
  failed: boolean;
}

function Unavailable({ what }: { what: string }) {
  return <p className="nws-side__empty">Couldn&apos;t load {what} right now.</p>;
}

export function NewsInsightsPanel({ insights, failed }: Props) {
  if (failed) {
    return (
      <aside className="nws-aside" aria-label="Insights">
        <div className="notice notice--danger" role="alert">
          <span>Couldn&apos;t load insights right now.</span>
        </div>
      </aside>
    );
  }
  if (!insights) {
    return (
      <aside className="nws-aside" aria-label="Insights" aria-busy="true">
        <div className="card card--tight skeleton">
          <i style={{ width: '60%' }} />
          <i style={{ width: '90%' }} />
          <i style={{ width: '75%' }} />
          <i style={{ width: '85%' }} />
        </div>
        <p className="nws-side__empty">
          Loading insights. The first load can take about 20 seconds.
        </p>
      </aside>
    );
  }

  const down = (key: string) => insights.unavailable.includes(key);

  return (
    <aside className="nws-aside" aria-label="Insights">
      <section className="card card--tight nws-side">
        <h2 className="nws-side__title">Trending repos this week</h2>
        <p className="nws-side__note">New open-source AI projects on GitHub.</p>
        {down('trending_repos') ? (
          <Unavailable what="trending repos" />
        ) : (
          <ol className="nws-side__list">
            {insights.trending_repos.map((r) => (
              <li key={r.url}>
                <a href={r.url} target="_blank" rel="noopener noreferrer">
                  {r.name}
                </a>
                <span className="nws-side__meta">
                  <Icon name="star" size={12} /> {r.stars.toLocaleString()}
                  {r.language ? ` · ${r.language}` : ''}
                </span>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="card card--tight nws-side">
        <h2 className="nws-side__title">New papers this week</h2>
        <p className="nws-side__note">
          arXiv submissions in the last 7 days. A paper can count in more than one area.
        </p>
        {down('paper_topics') ? (
          <Unavailable what="paper counts" />
        ) : (
          <ul className="nws-side__list">
            {insights.paper_topics.map((t) => (
              <li key={t.label}>
                <span>{t.label}</span>
                <span className="nws-side__meta">
                  {t.count.toLocaleString()}
                  {t.latest_url ? (
                    <>
                      {' · '}
                      <a
                        href={t.latest_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={t.latest_title}
                      >
                        latest
                      </a>
                    </>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card card--tight nws-side">
        <h2 className="nws-side__title">Recurring themes</h2>
        <p className="nws-side__note">Words that recur in story titles.</p>
        {insights.top_topics.length ? (
          <div className="chip-row">
            {insights.top_topics.map((t) => (
              <span key={t.topic} className="chip-link">
                {t.topic}
                <span className="count">{t.count}</span>
              </span>
            ))}
          </div>
        ) : (
          <p className="nws-side__empty">Not enough stories yet to find themes.</p>
        )}
      </section>
    </aside>
  );
}
