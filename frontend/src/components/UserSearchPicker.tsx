/**
 * Name / email search → pick a person. Used for group invites and DMs
 * (no UUID entry anywhere in the UI).
 */

import { useEffect, useId, useRef, useState } from 'react';
import { usersApi } from '../api/users';
import type { User } from '../types/auth';
import { Avatar, Icon } from './Icons';

export function UserSearchPicker({
  label,
  placeholder = 'Search by name or email…',
  excludeIds = [],
  actionIcon = 'plus',
  actionLabel,
  disabled = false,
  onPick,
}: {
  label: string;
  placeholder?: string;
  /** Users already in the group / self — hidden from results. */
  excludeIds?: string[];
  actionIcon?: string;
  actionLabel?: string;
  disabled?: boolean;
  onPick: (user: User) => void | Promise<void>;
}) {
  const inputId = useId();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<User[]>([]);
  const [searching, setSearching] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const seq = useRef(0);
  const exclude = excludeIds.join(',');

  useEffect(() => {
    const q = query.trim();
    if (q.length < 1) {
      setResults([]);
      setSearching(false);
      setFailed(null);
      return;
    }
    const ticket = ++seq.current;
    setSearching(true);
    const t = window.setTimeout(() => {
      usersApi
        .search(q, 12)
        .then((rows) => {
          if (ticket !== seq.current) return;
          const skip = new Set(exclude.split(',').filter(Boolean));
          setResults(rows.filter((u) => !skip.has(u.id)).slice(0, 8));
          setFailed(null);
        })
        .catch((e) => {
          if (ticket !== seq.current) return;
          setResults([]);
          setFailed(e instanceof Error ? e.message : 'Search failed');
        })
        .finally(() => {
          if (ticket === seq.current) setSearching(false);
        });
    }, 220);
    return () => window.clearTimeout(t);
  }, [query, exclude]);

  return (
    <div className="usp">
      <label className="muted small" htmlFor={inputId}>
        {label}
      </label>
      <input
        id={inputId}
        className="input"
        placeholder={placeholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        disabled={disabled}
        autoComplete="off"
      />
      {failed ? <div className="notice notice--danger" role="alert">{failed}</div> : null}
      {results.length ? (
        <div className="grp-list usp__results" role="listbox" aria-label={label}>
          {results.map((u) => (
            <button
              key={u.id}
              type="button"
              className="grp-row usp__row"
              role="option"
              aria-selected={false}
              disabled={disabled}
              onClick={() => {
                void Promise.resolve(onPick(u)).then(() => {
                  setQuery('');
                  setResults([]);
                });
              }}
            >
              <Avatar
                name={u.name}
                avatar={u.avatar}
                avatarUrl={u.avatar_url}
                size="sm"
              />
              <div className="grp-row__main">
                <div className="grp-row__title">{u.name}</div>
                <div className="muted small">{u.email}</div>
              </div>
              {actionLabel ? (
                <span className="btn btn--sm">{actionLabel}</span>
              ) : (
                <Icon name={actionIcon} size={16} />
              )}
            </button>
          ))}
        </div>
      ) : query.trim() && !searching && !failed ? (
        <p className="muted small">No people match that search.</p>
      ) : null}
    </div>
  );
}
