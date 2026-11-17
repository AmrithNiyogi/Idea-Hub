/**
 * Topbar global search — ideas, people, ideathons, problems.
 * Uses existing list APIs; Enter jumps to Explore when no idea hit.
 */

import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Avatar, Icon } from '../Icons';
import { ideathonsApi } from '../../api/ideathons';
import { ideasApi } from '../../api/ideas';
import { problemsApi } from '../../api/problems';
import { usersApi } from '../../api/users';
import { STATUS_META } from '../../constants/status';
import type { User } from '../../types/auth';
import type { Idea } from '../../types/idea';
import type { IdeathonSummary } from '../../types/ideathon';
import type { Problem } from '../../types/phase456';

interface SearchHits {
  ideas: Idea[];
  people: User[];
  ideathons: IdeathonSummary[];
  problems: Problem[];
}

const EMPTY: SearchHits = {
  ideas: [],
  people: [],
  ideathons: [],
  problems: [],
};

function trunc(s: string, n: number): string {
  return s.length <= n ? s : `${s.slice(0, n - 1)}…`;
}

export function GlobalSearch({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<SearchHits>(EMPTY);
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    if (open) {
      document.body.classList.add('search-open');
      inputRef.current?.focus();
    } else {
      document.body.classList.remove('search-open');
    }
    return () => document.body.classList.remove('search-open');
  }, [open]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (
        e.key === '/' &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement)
      ) {
        e.preventDefault();
        onOpenChange(true);
        inputRef.current?.focus();
      }
      if (e.key === 'Escape') {
        setShowResults(false);
        onOpenChange(false);
        setQuery('');
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onOpenChange]);

  useEffect(() => {
    const v = query.trim();
    if (v.length < 2) {
      setHits(EMPTY);
      setShowResults(false);
      return;
    }
    let cancelled = false;
    const t = window.setTimeout(async () => {
      try {
        const [ideasRes, users, ideathons, problems] = await Promise.all([
          ideasApi.list({ q: v, limit: 6 }),
          usersApi.list().catch(() => [] as User[]),
          ideathonsApi.list().catch(() => [] as IdeathonSummary[]),
          problemsApi.list().catch(() => [] as Problem[]),
        ]);
        if (cancelled) return;
        const q = v.toLowerCase();
        setHits({
          ideas: ideasRes.items,
          people: users
            .filter(
              (u) =>
                u.name.toLowerCase().includes(q) ||
                u.email.toLowerCase().includes(q) ||
                (u.title || '').toLowerCase().includes(q),
            )
            .slice(0, 5),
          ideathons: ideathons
            .filter(
              (it) =>
                it.title.toLowerCase().includes(q) ||
                (it.theme || '').toLowerCase().includes(q),
            )
            .slice(0, 5),
          problems: problems
            .filter((p) => {
              const label = (
                p.custom_label ||
                p.label ||
                p.cluster_key ||
                ''
              ).toLowerCase();
              return (
                label.includes(q) || p.cluster_key.toLowerCase().includes(q)
              );
            })
            .slice(0, 5),
        });
        setShowResults(true);
      } catch {
        if (!cancelled) {
          setHits(EMPTY);
          setShowResults(true);
        }
      }
    }, 220);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [query]);

  const close = () => {
    setQuery('');
    setShowResults(false);
    setHits(EMPTY);
    onOpenChange(false);
  };

  const goExplore = () => {
    const v = query.trim();
    close();
    if (v) navigate(`/explore?q=${encodeURIComponent(v)}`);
  };

  const onEnter = () => {
    const v = query.trim();
    if (!v) return;
    if (hits.ideas[0]) {
      const id = hits.ideas[0].id;
      close();
      navigate(`/ideas/${id}`);
      return;
    }
    goExplore();
  };

  const empty =
    !hits.ideas.length &&
    !hits.people.length &&
    !hits.ideathons.length &&
    !hits.problems.length;

  return (
    <div className="search" id="search-wrap" role="search" ref={wrapRef}>
      <div className="search__field">
        <span className="search__icon" id="search-icon">
          <Icon name="search" size={16} />
        </span>
        <input
          ref={inputRef}
          className="search__input"
          id="global-search"
          type="search"
          placeholder="Search ideas, teams, people"
          aria-label="Search ideas, ideathons, teams and people"
          autoComplete="off"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (query.trim().length >= 2) setShowResults(true);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              onEnter();
            }
          }}
        />
        <span className="search__kbd" aria-hidden="true">
          /
        </span>
      </div>
      <button
        className="btn btn--ghost btn--sm search__close"
        type="button"
        onClick={close}
      >
        Cancel
      </button>
      {showResults ? (
        <div className="search__results" id="search-results">
          {empty ? (
            <>
              <div className="search__group">No results</div>
              <div className="muted small" style={{ padding: '4px 8px 8px' }}>
                Nothing matches “{query.trim()}”.{' '}
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={goExplore}
                >
                  Search all ideas in Explore
                </button>
              </div>
            </>
          ) : (
            <>
              {hits.ideas.length ? (
                <>
                  <div className="search__group">Ideas</div>
                  {hits.ideas.map((i) => (
                    <Link
                      key={i.id}
                      className="search__item"
                      to={`/ideas/${i.id}`}
                      onClick={close}
                    >
                      <Icon name="compass" size={16} />
                      <span className="grow">
                        <span className="strong">{trunc(i.title, 60)}</span>
                        <br />
                        <span className="muted small">
                          {STATUS_META[i.status]?.label ?? i.status}
                        </span>
                      </span>
                    </Link>
                  ))}
                </>
              ) : null}
              {hits.people.length ? (
                <>
                  <div className="search__group">People</div>
                  {hits.people.map((u) => (
                    <Link
                      key={u.id}
                      className="search__item"
                      to={`/people/${u.id}`}
                      onClick={close}
                    >
                      <Avatar name={u.name} avatar={u.avatar} />
                      <span className="grow">
                        <span className="strong">{u.name}</span>
                        <br />
                        <span className="muted small">{u.title}</span>
                      </span>
                    </Link>
                  ))}
                </>
              ) : null}
              {hits.problems.length ? (
                <>
                  <div className="search__group">Recurring problems</div>
                  {hits.problems.map((p) => (
                    <Link
                      key={p.cluster_key}
                      className="search__item"
                      to={`/problems/${p.cluster_key}`}
                      onClick={close}
                    >
                      <Icon name="flag" size={16} />
                      <span className="grow">
                        <span className="strong">
                          {trunc(
                            p.custom_label || p.label || p.cluster_key,
                            60,
                          )}
                        </span>
                      </span>
                    </Link>
                  ))}
                </>
              ) : null}
              {hits.ideathons.length ? (
                <>
                  <div className="search__group">Ideathons</div>
                  {hits.ideathons.map((it) => (
                    <Link
                      key={it.id}
                      className="search__item"
                      to={`/ideathons/${it.id}`}
                      onClick={close}
                    >
                      <Icon name="flag" size={16} />
                      <span className="grow">
                        <span className="strong">{trunc(it.title, 60)}</span>
                        <br />
                        <span className="muted small">Theme: {it.theme}</span>
                      </span>
                    </Link>
                  ))}
                </>
              ) : null}
              <div className="search__group">All results</div>
              <button
                type="button"
                className="search__item"
                style={{
                  width: '100%',
                  border: 0,
                  background: 'transparent',
                  cursor: 'pointer',
                  textAlign: 'left',
                  font: 'inherit',
                }}
                onClick={goExplore}
              >
                <Icon name="search" size={16} />
                <span>Search every idea for “{query.trim()}”</span>
              </button>
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
