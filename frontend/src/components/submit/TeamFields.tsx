/** Team section of the idea form: teammates (co-authors), team name, and GitHub repo link. */

import { useEffect, useState } from 'react';
import { usersApi } from '../../api/users';
import { GITHUB_REPO_PATTERN } from '../../constants/github';
import type { User } from '../../types/auth';
import { Icon } from '../Icons';

export interface TeamFieldsProps {
  currentUserId: string | null;
  /** Teammates selected so far, by user id. Each is added as a co-author. */
  coAuthorIds: string[];
  /** Optional team name, stored on the idea. */
  teamName: string;
  githubUrl: string;
  demoUrl: string;
  onCoAuthorsChange: (ids: string[]) => void;
  onTeamNameChange: (value: string) => void;
  onGithubUrlChange: (value: string) => void;
  onDemoUrlChange: (value: string) => void;
  /** Hackathon entries must link a repository. */
  githubRequired?: boolean;
}

export function TeamFields({
  currentUserId,
  coAuthorIds,
  teamName,
  githubUrl,
  demoUrl,
  onCoAuthorsChange,
  onTeamNameChange,
  onGithubUrlChange,
  onDemoUrlChange,
  githubRequired = false,
}: TeamFieldsProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<User[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  // Keep names for selected teammates so chips still read correctly after a new search.
  const [known, setKnown] = useState<Record<string, User>>({});

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) return;
    let alive = true;
    const timer = window.setTimeout(() => {
      usersApi
        .search(q, 8)
        .then((users) => {
          if (!alive) return;
          setSearchError(null);
          setResults(users.filter((u) => u.id !== currentUserId));
          setKnown((k) => {
            const next = { ...k };
            users.forEach((u) => {
              next[u.id] = u;
            });
            return next;
          });
        })
        .catch(() => {
          if (!alive) return;
          setResults([]);
          setSearchError('Could not search people right now.');
        });
    }, 250);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [query, currentUserId]);

  // Saved drafts come back with ids only; look up names so chips read correctly.
  useEffect(() => {
    const missing = coAuthorIds.filter((id) => !known[id]);
    if (!missing.length) return;
    let alive = true;
    Promise.all(
      missing.map((id) =>
        usersApi
          .get(id)
          .then((u) => [id, u] as const)
          .catch(() => null),
      ),
    ).then((pairs) => {
      if (!alive) return;
      setKnown((k) => {
        const next = { ...k };
        pairs.forEach((p) => {
          if (p) next[p[0]] = p[1];
        });
        return next;
      });
    });
    return () => {
      alive = false;
    };
    // known is read but not a dependency: we only fetch ids we have not seen.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [coAuthorIds]);

  // Hide stale results when the query is too short, without setting state in the effect.
  const searching = query.trim().length >= 2;
  const shownResults = searching ? results : [];
  const shownError = searching ? searchError : null;

  const addMate = (u: User) => {
    if (coAuthorIds.includes(u.id) || u.id === currentUserId) return;
    setKnown((k) => ({ ...k, [u.id]: u }));
    onCoAuthorsChange([...coAuthorIds, u.id]);
    setQuery('');
    setResults([]);
  };

  const removeMate = (id: string) => {
    onCoAuthorsChange(coAuthorIds.filter((x) => x !== id));
  };

  const githubTrimmed = githubUrl.trim();
  const githubInvalid =
    githubTrimmed.length > 0 && !GITHUB_REPO_PATTERN.test(githubTrimmed);
  const demoTrimmed = demoUrl.trim();
  const demoInvalid = demoTrimmed.length > 0 && !/^https:\/\/[^\s/]+\.\S+$/.test(demoTrimmed);

  return (
    <div className="stack">
      <div className="field">
        <span className="label">Teammates</span>
        <div className="hint">
          Pick everyone who worked on this with you. They are added as
          co-authors straight away.
        </div>
        {coAuthorIds.length ? (
          <div className="chip-row" style={{ margin: '8px 0' }}>
            {coAuthorIds.map((id) => {
              const u = known[id];
              const label = u ? u.name : `Teammate ${id.slice(0, 8)}`;
              return (
                <span key={id} className="tag tag--removable">
                  {label}
                  <button
                    type="button"
                    aria-label={`Remove ${label}`}
                    onClick={() => removeMate(id)}
                  >
                    ×
                  </button>
                </span>
              );
            })}
          </div>
        ) : null}
        <input
          className="input"
          id="sf-teammate-search"
          aria-label="Search people by name or email"
          type="search"
          placeholder="Search by name or email (at least 2 letters)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoComplete="off"
        />
        {shownError ? (
          <div className="notice notice--danger" role="alert" style={{ marginTop: 8 }}>
            <Icon name="alert" size={16} />
            <span>{shownError}</span>
          </div>
        ) : null}
        {shownResults.length ? (
          <ul className="listrow" aria-label="People matching your search" style={{ marginTop: 8 }}>
            {shownResults.map((u) => {
              const picked = coAuthorIds.includes(u.id);
              return (
                <li key={u.id}>
                  <button
                    type="button"
                    className="listrow__title"
                    disabled={picked}
                    onClick={() => addMate(u)}
                  >
                    {u.name}
                    {u.title ? <span className="muted small"> · {u.title}</span> : null}
                    {picked ? <span className="muted small"> · added</span> : null}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : null}
      </div>

      <div className="field">
        <label htmlFor="sf-team-name">Team name (optional)</label>
        <input
          className="input"
          id="sf-team-name"
          maxLength={120}
          value={teamName}
          onChange={(e) => onTeamNameChange(e.target.value)}
          placeholder="For example: Night Owls"
        />
      </div>

      <div className="field">
        <label htmlFor="sf-demo">Live project link (optional)</label>
        <input
          className="input"
          id="sf-demo"
          type="url"
          maxLength={300}
          value={demoUrl}
          onChange={(e) => onDemoUrlChange(e.target.value)}
          placeholder="https://your-prototype.example.com"
          aria-invalid={demoInvalid}
        />
        {demoInvalid ? (
          <div className="hint" role="alert">
            Use a secure link that starts with https://.
          </div>
        ) : (
          <div className="hint">Where people can see the working prototype.</div>
        )}
      </div>

      <div className="field">
        <label htmlFor="sf-github">
          GitHub repository {githubRequired ? '(required for hackathons)' : '(optional)'}
        </label>
        <input
          className="input"
          id="sf-github"
          type="url"
          maxLength={300}
          value={githubUrl}
          onChange={(e) => onGithubUrlChange(e.target.value)}
          placeholder="https://github.com/owner/repo"
          aria-invalid={githubInvalid}
          aria-required={githubRequired}
        />
        {githubInvalid ? (
          <div className="hint" role="alert">
            Use a link to one repository, like https://github.com/owner/repo.
          </div>
        ) : (
          <div className="hint">
            {githubRequired
              ? 'One repository per entry. The AI reviewer reads its README and structure.'
              : 'One repository per idea.'}
          </div>
        )}
      </div>
    </div>
  );
}

export default TeamFields;
