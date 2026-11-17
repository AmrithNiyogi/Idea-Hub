/**
 * Idea team collaboration space — Discord-ish channels + messages,
 * meeting schedule (Teams webhook), and custom MCP connections.
 * Styled with Idea Hub tokens / list-row patterns (`.ts-*`).
 */

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { teamSpaceApi } from '../api/teamSpace';
import { usersApi } from '../api/users';
import { useAuth } from '../auth/AuthProvider';
import { Avatar, Icon } from './Icons';
import { relTime } from '../utils/format';
import type { Idea } from '../types/idea';
import type { User } from '../types/auth';
import type {
  IdeaMcpConnection,
  TeamChannel,
  TeamMeeting,
  TeamMessage,
  TeamSpace,
} from '../types/teamSpace';

type Props = { idea: Idea };

type SidePanel = 'none' | 'meeting' | 'mcp';

export function TeamSpacePanel({ idea }: Props) {
  const { user: me } = useAuth();
  const [space, setSpace] = useState<TeamSpace | null>(null);
  const [channelId, setChannelId] = useState<string | null>(null);
  const [messages, setMessages] = useState<TeamMessage[]>([]);
  const [meetings, setMeetings] = useState<TeamMeeting[]>([]);
  const [mcpList, setMcpList] = useState<IdeaMcpConnection[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [side, setSide] = useState<SidePanel>('none');

  const [meetTitle, setMeetTitle] = useState('');
  const [meetWhen, setMeetWhen] = useState('');
  const [meetJoin, setMeetJoin] = useState('');
  const [meetNotes, setMeetNotes] = useState('');
  const [meetTeams, setMeetTeams] = useState(true);

  const [mcpLabel, setMcpLabel] = useState('default');
  const [mcpUrl, setMcpUrl] = useState('');
  const [mcpAuthName, setMcpAuthName] = useState('Authorization');
  const [mcpAuthValue, setMcpAuthValue] = useState('');
  const [mcpStub, setMcpStub] = useState(true);

  const [newChannelName, setNewChannelName] = useState('');

  const userMap = useMemo(() => {
    const m = new Map<string, User>();
    users.forEach((u) => m.set(u.id, u));
    return m;
  }, [users]);

  const activeChannel: TeamChannel | null = useMemo(() => {
    if (!space || !channelId) return null;
    return space.channels.find((c) => c.id === channelId) ?? null;
  }, [space, channelId]);

  const reloadSpace = useCallback(async () => {
    const s = await teamSpaceApi.get(idea.id);
    setSpace(s);
    setChannelId((prev) => {
      if (prev && s.channels.some((c) => c.id === prev)) return prev;
      return s.channels[0]?.id ?? null;
    });
  }, [idea.id]);

  const reloadMessages = useCallback(async (cid: string) => {
    const rows = await teamSpaceApi.messages(idea.id, cid);
    setMessages(rows);
  }, [idea.id]);

  const reloadExtras = useCallback(async () => {
    const [m, mcp] = await Promise.all([
      teamSpaceApi.meetings(idea.id),
      teamSpaceApi.listMcp(idea.id),
    ]);
    setMeetings(m);
    setMcpList(mcp);
  }, [idea.id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(null);
      try {
        const [u] = await Promise.all([usersApi.list(), reloadSpace(), reloadExtras()]);
        if (!cancelled) setUsers(u);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load team space');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [idea.id, reloadSpace, reloadExtras]);

  useEffect(() => {
    if (!channelId) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        await reloadMessages(channelId);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load messages');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [channelId, reloadMessages]);

  async function onSend(e: FormEvent) {
    e.preventDefault();
    if (!channelId || !draft.trim() || !space?.can_post) return;
    setBusy(true);
    setError(null);
    try {
      await teamSpaceApi.postMessage(idea.id, channelId, draft.trim());
      setDraft('');
      await reloadMessages(channelId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to post');
    } finally {
      setBusy(false);
    }
  }

  async function onCreateChannel(e: FormEvent) {
    e.preventDefault();
    if (!newChannelName.trim() || !space?.can_manage) return;
    setBusy(true);
    setError(null);
    try {
      const ch = await teamSpaceApi.createChannel(idea.id, {
        name: newChannelName.trim(),
      });
      setNewChannelName('');
      await reloadSpace();
      setChannelId(ch.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create channel');
    } finally {
      setBusy(false);
    }
  }

  async function onSchedule(e: FormEvent) {
    e.preventDefault();
    if (!meetTitle.trim() || !meetWhen) return;
    setBusy(true);
    setError(null);
    try {
      const starts = new Date(meetWhen);
      await teamSpaceApi.scheduleMeeting(idea.id, {
        title: meetTitle.trim(),
        starts_at: starts.toISOString(),
        description: meetNotes.trim(),
        join_url: meetJoin.trim(),
        channel_id: channelId ?? undefined,
        notify_teams: meetTeams,
        announce_in_channel: true,
      });
      setMeetTitle('');
      setMeetWhen('');
      setMeetJoin('');
      setMeetNotes('');
      setSide('none');
      await Promise.all([
        reloadExtras(),
        channelId ? reloadMessages(channelId) : Promise.resolve(),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to schedule');
    } finally {
      setBusy(false);
    }
  }

  async function onConnectMcp(e: FormEvent) {
    e.preventDefault();
    if (!space?.can_manage) return;
    setBusy(true);
    setError(null);
    try {
      await teamSpaceApi.connectMcp(idea.id, {
        label: mcpLabel.trim() || 'default',
        endpoint_url: mcpStub ? 'stub://local' : mcpUrl.trim(),
        auth_header_name: mcpAuthName.trim() || 'Authorization',
        auth_header_value: mcpAuthValue,
        transport: mcpStub ? 'stub' : 'http_jsonrpc',
        seed_stub_tools: mcpStub,
      });
      setMcpUrl('');
      setMcpAuthValue('');
      setSide('none');
      await reloadExtras();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect MCP');
    } finally {
      setBusy(false);
    }
  }

  function nameOf(uid: string) {
    if (uid === me?.id) return 'You';
    return userMap.get(uid)?.name || 'Someone';
  }

  if (error && !space) {
    return (
      <div className="card">
        <div className="empty" style={{ padding: 24 }}>
          <Icon name="alert" size={28} />
          <h3>Could not open team space</h3>
          <p className="muted small">{error}</p>
        </div>
      </div>
    );
  }

  if (!space) {
    return (
      <div className="card">
        <p className="muted" style={{ padding: 16 }}>
          Loading team space…
        </p>
      </div>
    );
  }

  return (
    <div className="ts-shell">
      <aside className="ts-channels" aria-label="Channels">
        <div className="ts-channels__head">
          <h2>Channels</h2>
          <p className="muted small">{space.title}</p>
        </div>
        <div className="ts-channel-list" role="list">
          {space.channels.map((ch) => (
            <button
              key={ch.id}
              type="button"
              role="listitem"
              className={
                ch.id === channelId
                  ? 'ts-channel-row ts-channel-row--active'
                  : 'ts-channel-row'
              }
              onClick={() => setChannelId(ch.id)}
            >
              <span className="ts-channel-row__hash">#</span>
              <span className="ts-channel-row__name">{ch.name}</span>
            </button>
          ))}
        </div>
        {space.can_manage ? (
          <form className="ts-channel-add" onSubmit={onCreateChannel}>
            <input
              className="input"
              placeholder="New channel"
              value={newChannelName}
              onChange={(e) => setNewChannelName(e.target.value)}
              disabled={busy}
            />
            <button
              type="submit"
              className="btn btn--sm"
              disabled={busy || !newChannelName.trim()}
            >
              Add
            </button>
          </form>
        ) : null}
        <div className="ts-side-actions">
          <button
            type="button"
            className="btn btn--sm"
            onClick={() => setSide(side === 'meeting' ? 'none' : 'meeting')}
            disabled={!space.can_post}
          >
            <Icon name="calendar" size={14} /> Schedule
          </button>
          <button
            type="button"
            className="btn btn--sm btn--ghost"
            onClick={() => setSide(side === 'mcp' ? 'none' : 'mcp')}
          >
            <Icon name="spark" size={14} /> MCP
          </button>
        </div>
        {meetings.length ? (
          <div className="ts-meetings">
            <h3 className="ts-meetings__title">Upcoming</h3>
            {meetings.slice(0, 4).map((m) => (
              <div key={m.id} className="ts-meeting-row">
                <div className="ts-meeting-row__title">{m.title}</div>
                <div className="muted small">
                  {new Date(m.starts_at).toLocaleString()}
                  {m.notify_via === 'teams_webhook'
                    ? ` · Teams ${m.notify_status}`
                    : ''}
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </aside>

      <section className="ts-pane" aria-label="Messages">
        <div className="ts-pane__head">
          <div>
            <h2>
              <span className="muted">#</span> {activeChannel?.name ?? '…'}
            </h2>
            {activeChannel?.description ? (
              <p className="muted small">{activeChannel.description}</p>
            ) : null}
          </div>
          <Link className="btn btn--sm btn--ghost" to="/integrations/teams">
            Teams webhook
          </Link>
        </div>

        {error ? (
          <div className="error" style={{ margin: '0 16px 8px' }}>
            {error}
          </div>
        ) : null}

        <div className="ts-messages">
          {messages.length === 0 ? (
            <div className="empty" style={{ padding: 24 }}>
              <Icon name="message" size={28} />
              <h3>No messages yet</h3>
              <p className="muted small">
                Start the conversation for this channel.
              </p>
            </div>
          ) : (
            messages.map((msg) => {
              const system = msg.message_type !== 'user';
              return (
                <div
                  key={msg.id}
                  className={
                    system ? 'ts-msg ts-msg--system' : 'ts-msg'
                  }
                >
                  {!system ? (
                    <Avatar
                      name={nameOf(msg.author_id)}
                      avatar={userMap.get(msg.author_id)?.avatar ?? 1}
                    />
                  ) : (
                    <span className="ts-msg__sysicon">
                      <Icon
                        name={msg.message_type === 'meeting' ? 'calendar' : 'info'}
                        size={14}
                      />
                    </span>
                  )}
                  <div className="ts-msg__body">
                    <div className="ts-msg__meta">
                      <span className="strong">
                        {system
                          ? msg.message_type === 'meeting'
                            ? 'Meeting'
                            : 'System'
                          : nameOf(msg.author_id)}
                      </span>
                      <span className="muted small">
                        {relTime(msg.created_at)}
                      </span>
                    </div>
                    <div className="ts-msg__text">{msg.body}</div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        <form className="ts-composer" onSubmit={onSend}>
          <input
            className="input"
            placeholder={
              space.can_post
                ? `Message #${activeChannel?.slug ?? 'channel'}`
                : 'View only — join the idea team to post'
            }
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={!space.can_post || busy || !channelId}
          />
          <button
            type="submit"
            className="btn btn--primary"
            disabled={!space.can_post || busy || !draft.trim()}
          >
            Send
          </button>
        </form>
      </section>

      {side === 'meeting' ? (
        <aside className="ts-drawer card card--tight">
          <div className="ts-drawer__head">
            <h3>Schedule meeting</h3>
            <button
              type="button"
              className="btn btn--sm btn--ghost"
              onClick={() => setSide('none')}
            >
              Close
            </button>
          </div>
          <p className="muted small" style={{ marginBottom: 10 }}>
            Announces in this channel. Optionally posts a MessageCard to your
            Teams Incoming Webhook (
            <Link to="/integrations/teams">connect</Link>).
          </p>
          <form className="stack" onSubmit={onSchedule}>
            <label className="field">
              <span>Title</span>
              <input
                className="input"
                value={meetTitle}
                onChange={(e) => setMeetTitle(e.target.value)}
                required
              />
            </label>
            <label className="field">
              <span>Starts</span>
              <input
                className="input"
                type="datetime-local"
                value={meetWhen}
                onChange={(e) => setMeetWhen(e.target.value)}
                required
              />
            </label>
            <label className="field">
              <span>Join URL</span>
              <input
                className="input"
                value={meetJoin}
                onChange={(e) => setMeetJoin(e.target.value)}
                placeholder="https://teams.microsoft.com/l/meetup-join/…"
              />
            </label>
            <label className="field">
              <span>Notes</span>
              <textarea
                className="input"
                rows={3}
                value={meetNotes}
                onChange={(e) => setMeetNotes(e.target.value)}
              />
            </label>
            <label className="ts-check">
              <input
                type="checkbox"
                checked={meetTeams}
                onChange={(e) => setMeetTeams(e.target.checked)}
              />
              <span>Notify Microsoft Teams</span>
            </label>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={busy || !meetTitle.trim() || !meetWhen}
            >
              Schedule
            </button>
          </form>
        </aside>
      ) : null}

      {side === 'mcp' ? (
        <aside className="ts-drawer card card--tight">
          <div className="ts-drawer__head">
            <h3>Custom MCP</h3>
            <button
              type="button"
              className="btn btn--sm btn--ghost"
              onClick={() => setSide('none')}
            >
              Close
            </button>
          </div>
          <p className="muted small" style={{ marginBottom: 10 }}>
            Attach a team MCP endpoint (HTTP JSON-RPC) or a local stub that
            exposes <code>schedule_meeting</code>. See docs/TEAM_SPACE.md.
          </p>
          {mcpList.length ? (
            <div className="ts-mcp-list">
              {mcpList.map((m) => (
                <div key={m.id} className="ts-mcp-row">
                  <div className="listrow__main">
                    <div className="strong">{m.label}</div>
                    <div className="muted small">
                      {m.transport} · {(m.tools_cache || []).length} tools
                    </div>
                  </div>
                  {space.can_manage ? (
                    <div className="row" style={{ gap: 6 }}>
                      <button
                        type="button"
                        className="btn btn--sm"
                        disabled={busy}
                        onClick={() =>
                          void teamSpaceApi
                            .discoverMcp(idea.id, m.id)
                            .then(reloadExtras)
                            .catch((err) =>
                              setError(
                                err instanceof Error
                                  ? err.message
                                  : 'Discover failed',
                              ),
                            )
                        }
                      >
                        Discover
                      </button>
                      <button
                        type="button"
                        className="btn btn--sm btn--ghost"
                        disabled={busy}
                        onClick={() =>
                          void teamSpaceApi
                            .deleteMcp(idea.id, m.id)
                            .then(reloadExtras)
                            .catch((err) =>
                              setError(
                                err instanceof Error
                                  ? err.message
                                  : 'Delete failed',
                              ),
                            )
                        }
                      >
                        Remove
                      </button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="muted small">No MCP connections yet.</p>
          )}
          {space.can_manage ? (
            <form className="stack" onSubmit={onConnectMcp} style={{ marginTop: 12 }}>
              <label className="ts-check">
                <input
                  type="checkbox"
                  checked={mcpStub}
                  onChange={(e) => setMcpStub(e.target.checked)}
                />
                <span>Use stub catalog (schedule_meeting locally)</span>
              </label>
              <label className="field">
                <span>Label</span>
                <input
                  className="input"
                  value={mcpLabel}
                  onChange={(e) => setMcpLabel(e.target.value)}
                />
              </label>
              {!mcpStub ? (
                <>
                  <label className="field">
                    <span>Endpoint URL</span>
                    <input
                      className="input"
                      value={mcpUrl}
                      onChange={(e) => setMcpUrl(e.target.value)}
                      placeholder="https://mcp.example.com/rpc"
                      required
                    />
                  </label>
                  <label className="field">
                    <span>Auth header</span>
                    <input
                      className="input"
                      value={mcpAuthName}
                      onChange={(e) => setMcpAuthName(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>Auth value</span>
                    <input
                      className="input"
                      type="password"
                      value={mcpAuthValue}
                      onChange={(e) => setMcpAuthValue(e.target.value)}
                      autoComplete="off"
                    />
                  </label>
                </>
              ) : null}
              <button type="submit" className="btn btn--primary" disabled={busy}>
                Attach MCP
              </button>
            </form>
          ) : (
            <p className="muted small" style={{ marginTop: 8 }}>
              Only owners / authors / leads can attach MCP endpoints.
            </p>
          )}
        </aside>
      ) : null}
    </div>
  );
}

export default TeamSpacePanel;
