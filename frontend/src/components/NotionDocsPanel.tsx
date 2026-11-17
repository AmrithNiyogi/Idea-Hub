/**
 * Delivery / docs panel: create or link a Notion page for an accepted idea.
 * Credentials live under Integrations → Notion (personal or org default).
 */

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { integrationsApi } from '../api/integrations';
import { trackersApi } from '../api/trackers';
import { IntegrationLogo } from './integrations/IntegrationLogo';
import { Icon } from './Icons';
import type { Idea } from '../types/idea';
import type {
  EffectiveConnection,
  IdeaTrackerLink,
} from '../types/trackers';

const LINKABLE = new Set(['accepted', 'prototype', 'implemented']);
const CREATABLE = new Set(['accepted', 'prototype']);
const PROVIDER_ID = 'notion';

type Props = {
  idea: Idea;
  canManage: boolean;
};

export function NotionDocsPanel({ idea, canManage }: Props) {
  const [effective, setEffective] = useState<EffectiveConnection | null>(null);
  const [links, setLinks] = useState<IdeaTrackerLink[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<'create' | 'link'>('create');
  const [externalRef, setExternalRef] = useState('');

  const connection = effective?.connection ?? null;
  const connected = effective?.source !== 'none' && connection != null;

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [effList, allLinks] = await Promise.all([
        integrationsApi.listEffective('docs').catch(() => [] as EffectiveConnection[]),
        trackersApi.listLinks(idea.id).catch(() => [] as IdeaTrackerLink[]),
      ]);
      setEffective(
        effList.find((x) => x.provider_id === PROVIDER_ID) ?? null,
      );
      setLinks(allLinks.filter((l) => l.provider_id === PROVIDER_ID));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load Notion');
    }
  }, [idea.id]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const eligible = LINKABLE.has(idea.status);
  const canCreate = CREATABLE.has(idea.status);

  const sourceLabel = useMemo(() => {
    if (!effective || effective.source === 'none') return '';
    return effective.source === 'user' ? 'my connection' : 'org default';
  }, [effective]);

  async function onCreateOrLink(e: FormEvent) {
    e.preventDefault();
    if (!canManage || !connection) return;
    if (mode === 'link' && !externalRef.trim()) {
      setError('Paste a Notion page id or URL to link.');
      return;
    }
    if (mode === 'create' && !canCreate) {
      setError('New Notion pages can be created while accepted or in prototype.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await trackersApi.createOrLink(idea.id, {
        connection_id: connection.id,
        provider_id: PROVIDER_ID,
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
    if (!window.confirm('Remove this Notion link? The page is not deleted.')) {
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
    links.length > 0 ? (
      <ul className="integ-doc-list" role="list">
        {links.map((link) => (
          <li key={link.id} className="integ-doc-row" role="listitem">
            <IntegrationLogo providerId={PROVIDER_ID} size={24} />
            <div className="integ-doc-row__main">
              <div className="integ-doc-row__title-row">
                <strong>{link.title || idea.title}</strong>
                <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
                  {link.external_url ? (
                    <a
                      className="btn btn--sm"
                      href={link.external_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open in Notion
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
              <span className="muted small mono">
                {link.external_key || link.external_id}
              </span>
            </div>
          </li>
        ))}
      </ul>
    ) : (
      <p className="muted small" style={{ margin: '0 0 4px' }}>
        No Notion pages linked yet.
      </p>
    );

  const head = (
    <div className="integ-doc-panel__head">
      <div>
        <h2>Notion docs</h2>
        <p className="muted small">
          Create a page (or database row) from this idea, or link an existing
          Notion page. Connect once under{' '}
          <Link to="/integrations/notion">Integrations → Notion</Link>.
        </p>
      </div>
      {eligible ? (
        <Link className="btn btn--sm" to="/integrations/notion">
          Notion settings
        </Link>
      ) : null}
    </div>
  );

  if (!eligible) {
    return (
      <div className="card card--tight integ-doc-panel">
        {head}
        {links.length > 0 ? linkList : null}
        <div className="notice">
          <Icon name="lock" size={16} />
          <span>
            {links.length
              ? 'New Notion links can be added after the idea is accepted.'
              : 'Notion pages can be created or linked after the idea is accepted.'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="card card--tight integ-doc-panel">
      {head}

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={16} />
          <span>{error}</span>
        </div>
      ) : null}

      {linkList}

      {canManage ? (
        connected ? (
          <form
            className="integ-doc-form"
            onSubmit={(e) => void onCreateOrLink(e)}
          >
            <p className="muted small" style={{ margin: 0 }}>
              Using {connection?.display_label || 'Notion'} ({sourceLabel}).
            </p>
            <div className="segmented" role="group" aria-label="Notion mode">
              <label>
                <input
                  type="radio"
                  name="notion-mode"
                  checked={mode === 'create'}
                  disabled={!canCreate}
                  onChange={() => setMode('create')}
                />
                <span>Create page</span>
              </label>
              <label>
                <input
                  type="radio"
                  name="notion-mode"
                  checked={mode === 'link'}
                  onChange={() => setMode('link')}
                />
                <span>Link existing</span>
              </label>
            </div>
            {mode === 'link' ? (
              <label className="field">
                <span className="field__label">Notion page id or URL</span>
                <input
                  className="input"
                  value={externalRef}
                  onChange={(e) => setExternalRef(e.target.value)}
                  placeholder="https://www.notion.so/…"
                  required
                />
              </label>
            ) : null}
            <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
              <button
                type="submit"
                className="btn btn--sm btn--primary"
                disabled={busy}
              >
                {mode === 'create' ? 'Create in Notion' : 'Link to idea'}
              </button>
            </div>
          </form>
        ) : (
          <div className="notice" style={{ marginTop: 8 }}>
            <Icon name="layers" size={16} />
            <span>
              Notion is not connected yet.{' '}
              <Link to="/integrations/notion">Connect Notion</Link>
              {' '}(or ask an admin to set an org default).
            </span>
          </div>
        )
      ) : (
        <div className="notice" style={{ marginTop: 8 }}>
          <Icon name="lock" size={16} />
          <span>
            Only the owner, authors, a team lead or an administrator can
            manage Notion links.
          </span>
        </div>
      )}
    </div>
  );
}
