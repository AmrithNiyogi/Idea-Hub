/**
 * Delivery panel: create/link remote tasks using already-connected integrations.
 * Credentials live under Integrations (personal or org default) — not re-entered here.
 */

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { trackersApi } from '../api/trackers';
import { IntegrationLogo } from './integrations/IntegrationLogo';
import { Icon } from './Icons';
import type { Idea } from '../types/idea';
import type {
  EffectiveConnection,
  IdeaTrackerLink,
  TrackerProvider,
} from '../types/trackers';

const LINKABLE = new Set(['accepted', 'prototype', 'implemented']);
const CREATABLE = new Set(['accepted', 'prototype']);

type Props = {
  idea: Idea;
  canManage: boolean;
};

export function ExternalTrackersPanel({ idea, canManage }: Props) {
  const [providers, setProviders] = useState<TrackerProvider[]>([]);
  const [effective, setEffective] = useState<EffectiveConnection[]>([]);
  const [links, setLinks] = useState<IdeaTrackerLink[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [connectionId, setConnectionId] = useState('');
  const [mode, setMode] = useState<'create' | 'link'>('create');
  const [externalRef, setExternalRef] = useState('');

  const providerMap = useMemo(() => {
    const m = new Map<string, TrackerProvider>();
    providers.forEach((p) => m.set(p.id, p));
    return m;
  }, [providers]);

  const trackerIds = useMemo(
    () => new Set(providers.map((p) => p.id)),
    [providers],
  );

  const usable = useMemo(
    () =>
      effective.filter(
        (e) =>
          e.source !== 'none' &&
          e.connection != null &&
          trackerIds.has(e.connection.provider_id),
      ),
    [effective, trackerIds],
  );

  const trackerLinks = useMemo(
    () => links.filter((l) => trackerIds.has(l.provider_id)),
    [links, trackerIds],
  );

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [p, e, l] = await Promise.all([
        trackersApi.listProviders(),
        trackersApi.listEffective().catch(() => [] as EffectiveConnection[]),
        trackersApi.listLinks(idea.id).catch(() => [] as IdeaTrackerLink[]),
      ]);
      setProviders(p);
      setEffective(e);
      setLinks(l);
      const first = e.find((x) => x.connection)?.connection?.id;
      setConnectionId((prev) => {
        if (prev && e.some((x) => x.connection?.id === prev)) return prev;
        return first ?? '';
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trackers');
    }
  }, [idea.id]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const eligible = LINKABLE.has(idea.status);
  const canCreate = CREATABLE.has(idea.status);

  async function onCreateOrLink(e: FormEvent) {
    e.preventDefault();
    if (!canManage || !connectionId) return;
    if (mode === 'link' && !externalRef.trim()) {
      setError('Paste a remote id or URL to link.');
      return;
    }
    if (mode === 'create' && !canCreate) {
      setError('New remote tasks can be created while accepted or in prototype.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await trackersApi.createOrLink(idea.id, {
        connection_id: connectionId,
        mode,
        title: idea.title,
        external_id_or_url: mode === 'link' ? externalRef.trim() : undefined,
      });
      setExternalRef('');
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create/link failed');
    } finally {
      setBusy(false);
    }
  }

  async function onUnlink(linkId: string) {
    if (!canManage) return;
    if (!window.confirm('Remove this link? The remote task is not deleted.')) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await trackersApi.unlink(idea.id, linkId);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unlink failed');
    } finally {
      setBusy(false);
    }
  }

  const linkList =
    trackerLinks.length > 0 ? (
      <ul className="trk-list trk-list--compact">
        {trackerLinks.map((link) => {
          const pname =
            providerMap.get(link.provider_id)?.display_name ?? link.provider_id;
          return (
            <li key={link.id} className="trk-task trk-task--compact">
              <div className="trk-task__top">
                <IntegrationLogo providerId={link.provider_id} size={24} />
                <div className="trk-task__main">
                  <div className="trk-task__title-row">
                    <strong className="trk-task__title">
                      {link.title || idea.title}
                    </strong>
                    <div className="trk-task__actions">
                      {link.external_url ? (
                        <a
                          className="btn btn--sm"
                          href={link.external_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Open
                        </a>
                      ) : null}
                      {canManage && eligible ? (
                        <button
                          type="button"
                          className="btn btn--sm"
                          disabled={busy}
                          onClick={() => void onUnlink(link.id)}
                        >
                          Unlink
                        </button>
                      ) : null}
                    </div>
                  </div>
                  <div className="trk-task__meta">
                    <span>{pname}</span>
                    <span className="trk-task__dot" aria-hidden>
                      ·
                    </span>
                    <span className="mono small">
                      {link.external_key || link.external_id}
                    </span>
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    ) : (
      <p className="muted small" style={{ margin: '0 0 4px' }}>
        No remote links yet.
      </p>
    );

  const head = (
    <div className="trk-panel__head">
      <div className="trk-panel__titles">
        <h2>External trackers</h2>
        <p className="muted small">
          Create or link a remote work item. Live status, priority, due date,
          and assignees are edited on the{' '}
          <Link to={`/ideas/${idea.id}?tab=tracker`}>Tracker</Link> tab.
        </p>
      </div>
      {eligible ? (
        <Link className="btn btn--sm" to="/integrations">
          Browse integrations
        </Link>
      ) : null}
    </div>
  );

  if (!eligible) {
    return (
      <div className="card card--tight trk-panel">
        {head}
        {trackerLinks.length > 0 ? linkList : null}
        <div className="notice">
          <Icon name="lock" size={16} />
          <span>
            {trackerLinks.length
              ? 'New links can be added after the idea is accepted. Existing links stay visible on the Tracker tab.'
              : 'Connect ClickUp, Jira, or a custom tracker after the idea is accepted and ready for development.'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="card card--tight trk-panel">
      {head}

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={16} />
          <span>{error}</span>
        </div>
      ) : null}

      {linkList}

      {canManage ? (
        usable.length > 0 ? (
          <form
            className="trk-link-form"
            onSubmit={(e) => void onCreateOrLink(e)}
          >
            <label className="field">
              <span className="field__label">Use connection</span>
              <select
                className="select"
                value={connectionId}
                onChange={(e) => setConnectionId(e.target.value)}
              >
                {usable.map((e) => {
                  const c = e.connection!;
                  const pname =
                    providerMap.get(c.provider_id)?.display_name ??
                    c.provider_id;
                  const src =
                    e.source === 'user' ? 'my connection' : 'org default';
                  return (
                    <option key={c.id} value={c.id}>
                      {pname} — {c.display_label || c.label} ({src})
                    </option>
                  );
                })}
              </select>
            </label>
            <div className="segmented" role="group" aria-label="Link mode">
              <label>
                <input
                  type="radio"
                  name="trk-mode"
                  checked={mode === 'create'}
                  disabled={!canCreate}
                  onChange={() => setMode('create')}
                />
                <span>Create task</span>
              </label>
              <label>
                <input
                  type="radio"
                  name="trk-mode"
                  checked={mode === 'link'}
                  onChange={() => setMode('link')}
                />
                <span>Link existing</span>
              </label>
            </div>
            {mode === 'link' ? (
              <label className="field">
                <span className="field__label">Remote id or URL</span>
                <input
                  className="input"
                  value={externalRef}
                  onChange={(e) => setExternalRef(e.target.value)}
                  placeholder="ENG-42 or https://…"
                  required
                />
              </label>
            ) : null}
            <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
              <button
                type="submit"
                className="btn btn--sm btn--primary"
                disabled={busy || !connectionId}
              >
                {mode === 'create' ? 'Create in tracker' : 'Link to idea'}
              </button>
            </div>
          </form>
        ) : (
          <div className="notice" style={{ marginTop: 8 }}>
            <Icon name="layers" size={16} />
            <span>
              No tracker connected yet. Connect{' '}
              <Link to="/integrations/clickup">ClickUp</Link>,{' '}
              <Link to="/integrations/jira">Jira</Link>, or a{' '}
              <Link to="/integrations/custom_webhook">custom webhook</Link>
              {' '}(or ask an admin to set an org default).
            </span>
          </div>
        )
      ) : (
        <div className="notice" style={{ marginTop: 8 }}>
          <Icon name="lock" size={16} />
          <span>
            Only the owner, authors, a team lead or an administrator can
            create tracker links.
          </span>
        </div>
      )}
    </div>
  );
}
