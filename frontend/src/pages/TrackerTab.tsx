/**
 * Idea detail → Tracker tab: live remote tasks (ClickUp / Jira / custom)
 * with status / priority / due date / assignee write-back.
 * Create/link stays on Delivery.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { trackersApi } from '../api/trackers';
import { IntegrationLogo } from '../components/integrations/IntegrationLogo';
import { Icon } from '../components/Icons';
import { TrackerRemoteControls } from '../components/TrackerRemoteControls';
import type { Idea } from '../types/idea';
import type {
  IdeaTrackerLink,
  IdeaTrackerRemoteUpdateBody,
  LiveTrackerTask,
  TrackerProvider,
} from '../types/trackers';

type Props = {
  idea: Idea;
  onOpenDelivery: () => void;
};

const PROVIDER_FALLBACK: Record<string, string> = {
  clickup: 'ClickUp',
  jira: 'Jira',
  custom_webhook: 'Custom tracker',
};

const LINKABLE = new Set(['accepted', 'prototype', 'implemented']);

/** Map stored links to task rows when the live endpoint fails entirely. */
function cachedFromLinks(
  links: IdeaTrackerLink[],
  error: string,
): LiveTrackerTask[] {
  return links.map((link) => ({
    link_id: link.id,
    provider_id: link.provider_id,
    external_id: link.external_id,
    external_key: link.external_key,
    external_url: link.external_url,
    stored_title: link.title,
    title: link.title,
    status: '',
    status_id: '',
    status_color: '',
    status_type: '',
    priority: '',
    priority_id: '',
    priority_color: '',
    due_date: '',
    url: link.external_url,
    assignees: [],
    assignable: [],
    status_options: [],
    priority_options: [],
    editable_fields: [],
    live: false,
    error,
    can_update_status: false,
    can_update: false,
  }));
}

export function TrackerTab({ idea, onOpenDelivery }: Props) {
  const [tasks, setTasks] = useState<LiveTrackerTask[]>([]);
  const [providers, setProviders] = useState<TrackerProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const providerName = useCallback(
    (id: string) =>
      providers.find((p) => p.id === id)?.display_name ??
      PROVIDER_FALLBACK[id] ??
      id,
    [providers],
  );

  const reload = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [live, prov] = await Promise.all([
        trackersApi.listLiveTasks(idea.id),
        trackersApi.listProviders().catch(() => [] as TrackerProvider[]),
      ]);
      const trackerIds = new Set(prov.map((p) => p.id));
      // Docs adapters (e.g. Notion) share idea links; keep Tracker tab tracker-only.
      setTasks(
        trackerIds.size
          ? live.filter((t) => trackerIds.has(t.provider_id))
          : live.filter((t) => t.provider_id !== 'notion'),
      );
      setProviders(prov);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to load tracker tasks';
      try {
        const [links, prov] = await Promise.all([
          trackersApi.listLinks(idea.id),
          trackersApi.listProviders().catch(() => [] as TrackerProvider[]),
        ]);
        setProviders(prov);
        const trackerIds = new Set(prov.map((p) => p.id));
        const trackerLinks = trackerIds.size
          ? links.filter((l) => trackerIds.has(l.provider_id))
          : links.filter((l) => l.provider_id !== 'notion');
        if (trackerLinks.length > 0) {
          setTasks(cachedFromLinks(trackerLinks, message));
          setError(message);
        } else {
          setTasks([]);
          setError(message);
        }
      } catch {
        setTasks([]);
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }, [idea.id]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onPatch(
    task: LiveTrackerTask,
    patch: IdeaTrackerRemoteUpdateBody,
  ) {
    if (!(task.can_update ?? task.can_update_status)) return;
    setBusyId(task.link_id);
    setError(null);
    try {
      const updated = await trackersApi.updateRemote(
        idea.id,
        task.link_id,
        patch,
      );
      setTasks((list) =>
        list.map((t) => (t.link_id === updated.link_id ? updated : t)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setBusyId(null);
    }
  }

  async function onRefreshOne(linkId: string) {
    setBusyId(linkId);
    setError(null);
    try {
      const updated = await trackersApi.getLiveTask(idea.id, linkId);
      setTasks((list) =>
        list.map((t) => (t.link_id === updated.link_id ? updated : t)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Refresh failed');
    } finally {
      setBusyId(null);
    }
  }

  const canLink = LINKABLE.has(idea.status);
  const showEmpty = !loading && tasks.length === 0 && !error;
  const showLoadFailed = !loading && tasks.length === 0 && !!error;

  return (
    <div className="card card--tight trk-panel">
      <div className="trk-panel__head">
        <div className="trk-panel__titles">
          <h2>Tracker</h2>
          <p className="muted small">
            Live tasks for this idea. Change status, priority, due date, or
            assignees here — writes go back to ClickUp / Jira. Create or link
            on Delivery.
          </p>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <button
            type="button"
            className="btn btn--sm"
            disabled={loading || busyId != null}
            onClick={() => void reload()}
          >
            <Icon name="refresh" size={14} /> Refresh
          </button>
          <button type="button" className="btn btn--sm" onClick={onOpenDelivery}>
            Delivery
          </button>
        </div>
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={16} />
          <span>{error}</span>
        </div>
      ) : null}

      {loading ? (
        <p className="muted" style={{ margin: '4px 0 0' }}>
          Loading linked tasks…
        </p>
      ) : showLoadFailed ? (
        <div className="empty" style={{ padding: 20 }}>
          <Icon name="alert" size={28} />
          <h3>Couldn’t load tracker tasks</h3>
          <p className="muted small">
            The live tracker request failed. Retry, or open Delivery to manage
            links.
          </p>
          <div className="row" style={{ gap: 8, justifyContent: 'center' }}>
            <button
              type="button"
              className="btn btn--primary btn--sm"
              onClick={() => void reload()}
            >
              Retry
            </button>
            <button
              type="button"
              className="btn btn--sm"
              onClick={onOpenDelivery}
            >
              Go to Delivery
            </button>
          </div>
        </div>
      ) : showEmpty ? (
        <div className="empty" style={{ padding: 20 }}>
          <Icon name="layers" size={28} />
          <h3>No linked tracker tasks</h3>
          <p className="muted small">
            {canLink ? (
              <>
                Create or link a ClickUp / Jira task from Delivery. Credentials
                live under Integrations.
              </>
            ) : (
              <>
                This idea is still{' '}
                <strong>{idea.status.replace(/_/g, ' ')}</strong>. After
                acceptance, create or link a task from Delivery.
              </>
            )}
          </p>
          <div className="row" style={{ gap: 8, justifyContent: 'center' }}>
            <button
              type="button"
              className="btn btn--primary btn--sm"
              onClick={onOpenDelivery}
            >
              Go to Delivery
            </button>
            <Link className="btn btn--sm" to="/integrations">
              Integrations
            </Link>
          </div>
        </div>
      ) : (
        <ul className="trk-list">
          {tasks.map((task) => {
            const openUrl = task.url || task.external_url;
            const label =
              task.title ||
              task.stored_title ||
              task.external_key ||
              task.external_id;
            const busy = busyId === task.link_id;
            return (
              <li key={task.link_id} className="trk-task">
                <div className="trk-task__top">
                  <IntegrationLogo providerId={task.provider_id} size={28} />
                  <div className="trk-task__main">
                    <div className="trk-task__title-row">
                      <strong className="trk-task__title">{label}</strong>
                      <div className="trk-task__actions">
                        <button
                          type="button"
                          className="btn btn--sm btn--icon"
                          disabled={busy}
                          onClick={() => void onRefreshOne(task.link_id)}
                          title="Refresh from tracker"
                          aria-label="Refresh from tracker"
                        >
                          <Icon name="refresh" size={14} />
                        </button>
                        {openUrl ? (
                          <a
                            className="btn btn--sm btn--primary"
                            href={openUrl}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open
                          </a>
                        ) : null}
                      </div>
                    </div>
                    <div className="trk-task__meta">
                      <span>{providerName(task.provider_id)}</span>
                      {task.external_key || task.external_id ? (
                        <>
                          <span className="trk-task__dot" aria-hidden>
                            ·
                          </span>
                          <span className="mono small">
                            {task.external_key || task.external_id}
                          </span>
                        </>
                      ) : null}
                      {task.live ? (
                        <span className="pill pill--success">Live</span>
                      ) : (
                        <span className="pill pill--warning">Cached</span>
                      )}
                    </div>
                    {task.error ? (
                      <div
                        className="muted small"
                        style={{ marginTop: 4, color: 'var(--danger)' }}
                      >
                        {task.error}
                      </div>
                    ) : null}
                  </div>
                </div>
                <TrackerRemoteControls
                  task={task}
                  busy={busy}
                  onPatch={(patch) => onPatch(task, patch)}
                />
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
