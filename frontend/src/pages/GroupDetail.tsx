/**
 * Group detail — Discord channel list + WhatsApp-like chat transcript.
 */

import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  Link,
  Navigate,
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router-dom';
import { groupsApi } from '../api/groups';
import { useAuth } from '../auth/AuthProvider';
import { GroupGlyph } from '../components/GroupGlyph';
import { Avatar, Icon } from '../components/Icons';
import { UserSearchPicker } from '../components/UserSearchPicker';
import { relTime } from '../utils/format';
import type { User } from '../types/auth';
import type {
  Group,
  GroupChannel,
  GroupMeeting,
  GroupMessage,
  GroupMcpConnection,
} from '../types/groups';
import { useDialog } from '../components/DialogProvider';

type SidePanel = 'none' | 'meeting' | 'mcp' | 'members';

export function GroupDetailPage({ dmRoute = false }: { dmRoute?: boolean }) {
  const dialog = useDialog();
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const [search, setSearch] = useSearchParams();
  const { user: me } = useAuth();
  const [group, setGroup] = useState<Group | null>(null);
  const [channelId, setChannelId] = useState<string | null>(
    search.get('channel'),
  );
  const [messages, setMessages] = useState<GroupMessage[]>([]);
  const [meetings, setMeetings] = useState<GroupMeeting[]>([]);
  const [mcpList, setMcpList] = useState<GroupMcpConnection[]>([]);
  const avatarInput = useRef<HTMLInputElement>(null);
  const [inviteRole, setInviteRole] = useState<'member' | 'admin'>('member');
  const [notice, setNotice] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [side, setSide] = useState<SidePanel>('none');
  const scroller = useRef<HTMLDivElement>(null);

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

  const memberMap = useMemo(() => {
    const m = new Map<string, Group['members'][number]>();
    group?.members.forEach((x) => m.set(x.user_id, x));
    return m;
  }, [group]);

  const activeChannel: GroupChannel | null = useMemo(() => {
    if (!group || !channelId) return null;
    return group.channels.find((c) => c.id === channelId) ?? null;
  }, [group, channelId]);

  const reloadGroup = useCallback(async () => {
    const g = await groupsApi.get(id);
    setGroup(g);
    setChannelId((prev) => {
      const fromUrl = search.get('channel');
      if (fromUrl && g.channels.some((c) => c.id === fromUrl)) return fromUrl;
      if (prev && g.channels.some((c) => c.id === prev)) return prev;
      return g.channels[0]?.id ?? null;
    });
  }, [id, search]);

  const reloadMessages = useCallback(
    async (cid: string) => {
      const rows = await groupsApi.messages(id, cid);
      setMessages(rows);
    },
    [id],
  );

  const reloadExtras = useCallback(async () => {
    const [m, mcp] = await Promise.all([
      groupsApi.meetings(id),
      groupsApi.listMcp(id),
    ]);
    setMeetings(m);
    setMcpList(mcp);
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(null);
      try {
        await Promise.all([reloadGroup(), reloadExtras()]);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load group');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, reloadGroup, reloadExtras]);

  useEffect(() => {
    if (!channelId) {
      setMessages([]);
      return;
    }
    const next = new URLSearchParams(search);
    if (next.get('channel') !== channelId) {
      next.set('channel', channelId);
      setSearch(next, { replace: true });
    }
    let cancelled = false;
    (async () => {
      try {
        await reloadMessages(channelId);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : 'Failed to load messages',
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [channelId, reloadMessages]); // eslint-disable-line react-hooks/exhaustive-deps

  // Light polling so chats feel live without websockets.
  useEffect(() => {
    if (!channelId) return;
    const t = window.setInterval(() => {
      if (document.visibilityState === 'visible') {
        void reloadMessages(channelId).catch(() => undefined);
      }
    }, 8000);
    return () => window.clearInterval(t);
  }, [channelId, reloadMessages]);

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, channelId]);

  async function onSend(e: FormEvent) {
    e.preventDefault();
    if (!channelId || !draft.trim() || !group?.can_post) return;
    setBusy(true);
    setError(null);
    try {
      await groupsApi.postMessage(id, channelId, draft.trim());
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
    if (!newChannelName.trim() || !group?.can_manage) return;
    setBusy(true);
    setError(null);
    try {
      const ch = await groupsApi.createChannel(id, {
        name: newChannelName.trim(),
      });
      setNewChannelName('');
      await reloadGroup();
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
      await groupsApi.scheduleMeeting(id, {
        title: meetTitle.trim(),
        starts_at: new Date(meetWhen).toISOString(),
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
    if (!group?.can_manage) return;
    setBusy(true);
    setError(null);
    try {
      await groupsApi.connectMcp(id, {
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

  async function onInvite(person: User) {
    if (!group?.can_manage) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await groupsApi.invite(id, { user_id: person.id, role: inviteRole });
      setNotice(
        `Invite sent to ${person.name}. They get a bell notification and an email, and join once they Accept.`,
      );
      await reloadGroup();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to invite');
    } finally {
      setBusy(false);
    }
  }

  async function onCancelInvite(inviteId: string) {
    setBusy(true);
    setError(null);
    try {
      await groupsApi.cancelInvite(id, inviteId);
      await reloadGroup();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel invite');
    } finally {
      setBusy(false);
    }
  }

  async function onRemoveMember(userId: string, name: string) {
    if (
      !(await dialog.confirm({
        title: `Remove ${name} from “${group?.name}”?`,
        confirmLabel: 'Remove',
        danger: true,
      }))
    )
      return;
    setBusy(true);
    setError(null);
    try {
      await groupsApi.removeMember(id, userId);
      await reloadGroup();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove member');
    } finally {
      setBusy(false);
    }
  }

  async function onLeave() {
    if (!me) return;
    if (
      !(await dialog.confirm({
        title: `Leave “${group?.name}”?`,
        confirmLabel: 'Leave',
        danger: true,
      }))
    )
      return;
    setBusy(true);
    setError(null);
    try {
      await groupsApi.removeMember(id, me.id);
      navigate('/groups');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to leave group');
      setBusy(false);
    }
  }

  async function onDeleteGroup() {
    if (
      !(await dialog.confirm({
        title: `Delete “${group?.name}”?`,
        message: 'It disappears for every member and pending invites are cancelled.',
        confirmLabel: 'Delete',
        danger: true,
      }))
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await groupsApi.softDelete(id);
      navigate('/groups');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete group');
      setBusy(false);
    }
  }

  async function onAvatarFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const g = await groupsApi.uploadAvatar(id, file);
      setGroup(g);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Avatar upload failed');
    } finally {
      setBusy(false);
      if (avatarInput.current) avatarInput.current.value = '';
    }
  }

  async function onClearAvatar() {
    setBusy(true);
    setError(null);
    try {
      setGroup(await groupsApi.update(id, { clear_avatar: true }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not remove avatar');
    } finally {
      setBusy(false);
    }
  }

  function nameOf(uid: string) {
    if (uid === me?.id) return 'You';
    return memberMap.get(uid)?.name || 'Former member';
  }

  if (error && !group) {
    return (
      <div className="card">
        <div className="empty" style={{ padding: 24 }}>
          <Icon name="alert" size={28} />
          <h3>Could not open group</h3>
          <p className="muted small">{error}</p>
          <Link className="btn btn--sm" to="/groups">
            Back to groups
          </Link>
        </div>
      </div>
    );
  }

  if (!group) {
    return (
      <div className="card">
        <p className="muted" style={{ padding: 16 }}>
          Loading group…
        </p>
      </div>
    );
  }

  const chatPane = (isDm: boolean) => (
    <section className="ts-pane" aria-label="Messages">
      {isDm ? null : (
        <div className="ts-pane__head">
          <div>
            <h2>
              <span className="muted">#</span> {activeChannel?.name ?? '…'}
            </h2>
            {activeChannel?.description ? (
              <p className="muted small" style={{ margin: 0 }}>
                {activeChannel.description}
              </p>
            ) : null}
          </div>
          <Link className="btn btn--sm btn--ghost" to="/integrations/teams">
            Teams webhook
          </Link>
        </div>
      )}

      {error ? (
        <div className="notice notice--danger" role="alert" style={{ margin: '8px 12px 0' }}>
          {error}
        </div>
      ) : null}

      <div className="ts-messages" ref={scroller}>
        {messages.length === 0 ? (
          <div className="empty" style={{ padding: 24 }}>
            <Icon name="message" size={28} />
            <h3>No messages yet</h3>
            <p className="muted small">Say hi — the composer is below.</p>
          </div>
        ) : (
          messages.map((msg) => {
            const mine = msg.author_id === me?.id;
            const system =
              msg.message_type === 'system' ||
              msg.message_type === 'meeting';
            const cls = system
              ? 'ts-bubble ts-bubble--system'
              : mine
                ? 'ts-bubble ts-bubble--mine'
                : 'ts-bubble ts-bubble--theirs';
            return (
              <div key={msg.id} className={cls}>
                {!system && !mine ? (
                  <div className="ts-bubble__sender">
                    {nameOf(msg.author_id)}
                  </div>
                ) : null}
                <div className="ts-bubble__text">{msg.body}</div>
                <div className="ts-bubble__time">
                  {relTime(msg.created_at)}
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
            group.can_post
              ? isDm
                ? `Message ${group.name}`
                : `Message #${activeChannel?.slug ?? 'channel'}`
              : 'Members only'
          }
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={!group.can_post || busy || !channelId}
          aria-label="Message"
        />
        <button
          type="submit"
          className="btn"
          disabled={
            !group.can_post || busy || !channelId || !draft.trim()
          }
          aria-label="Send"
        >
          <Icon name="send" size={16} />
        </button>
      </form>
    </section>
  );

  if (group.kind === 'dm' && !dmRoute) {
    return <Navigate to={`/dms/${group.id}`} replace />;
  }
  if (group.kind !== 'dm' && dmRoute) {
    return <Navigate to={`/groups/${group.id}`} replace />;
  }

  if (group.kind === 'dm') {
    const peer = group.peer_user_id;
    return (
      <div className="grp-page">
        <div className="row grp-head" style={{ gap: 12 }}>
          <Avatar
            name={group.name}
            avatar={group.peer_avatar}
            avatarUrl={group.peer_avatar_url}
          />
          <div className="grow" style={{ minWidth: 0 }}>
            <div className="crumbs">
              <Link to="/dms">Messages</Link>
              <span aria-hidden>/</span>
              <span aria-current="page">{group.name}</span>
            </div>
            <div className="muted small">Direct message</div>
          </div>
          {peer ? (
            <Link className="btn btn--sm btn--ghost" to={`/people/${peer}`}>
              View profile
            </Link>
          ) : null}
        </div>
        <div className="ts-shell ts-shell--dm">
          {chatPane(true)}
        </div>
      </div>
    );
  }

  return (
    <div className="grp-page">
      <div className="row grp-head" style={{ justifyContent: 'space-between', gap: 12 }}>
        <div className="row" style={{ gap: 12, minWidth: 0 }}>
          <GroupGlyph name={group.name} avatarUrl={group.avatar_url} size={48} />
          <div style={{ minWidth: 0 }}>
            <div className="crumbs">
              <Link to="/groups">Groups</Link>
              <span aria-hidden>/</span>
              <span aria-current="page">{group.name}</span>
            </div>
            {group.description ? (
              <p className="muted small" style={{ margin: '4px 0 0' }}>
                {group.description}
              </p>
            ) : null}
            {group.can_manage ? (
              <div className="row" style={{ gap: 6, marginTop: 6 }}>
                <input
                  ref={avatarInput}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  hidden
                  onChange={(e) => void onAvatarFile(e.target.files?.[0])}
                />
                <button
                  type="button"
                  className="btn btn--sm btn--ghost"
                  disabled={busy}
                  onClick={() => avatarInput.current?.click()}
                >
                  <Icon name="upload" size={14} />{' '}
                  {group.avatar_url ? 'Change avatar' : 'Set avatar'}
                </button>
                {group.avatar_url ? (
                  <button
                    type="button"
                    className="btn btn--sm btn--ghost"
                    disabled={busy}
                    onClick={() => void onClearAvatar()}
                  >
                    Remove
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
        <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
          {group.idea_id ? (
            <Link className="btn btn--sm btn--ghost" to={`/ideas/${group.idea_id}`}>
              Linked idea
            </Link>
          ) : (
            <span className="muted small">No idea linked yet</span>
          )}
          <button
            type="button"
            className="btn btn--sm btn--ghost"
            onClick={() => setSide(side === 'members' ? 'none' : 'members')}
          >
            <Icon name="users" size={14} /> Members
            {group.pending_invites.length ? (
              <span className="count">{group.pending_invites.length}</span>
            ) : null}
          </button>
          {group.can_manage ? (
            <button
              type="button"
              className="btn btn--sm btn--ghost grp-danger"
              disabled={busy}
              onClick={() => void onDeleteGroup()}
            >
              <Icon name="trash" size={14} /> Delete group
            </button>
          ) : (
            <button
              type="button"
              className="btn btn--sm btn--ghost"
              disabled={busy}
              onClick={() => void onLeave()}
            >
              Leave
            </button>
          )}
        </div>
      </div>

      {notice ? <div className="notice">{notice}</div> : null}

      <div className={`ts-shell${side !== 'none' ? ' ts-shell--drawer' : ''}`}>
        <aside className="ts-channels" aria-label="Channels">
          <div className="ts-channels__head">
            <h2>Channels</h2>
            <p className="muted small">{group.name}</p>
          </div>
          <div className="ts-channel-list" role="list">
            {group.channels.map((ch) => (
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
          {group.can_manage ? (
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
              disabled={!group.can_post}
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

        {chatPane(false)}

        {side === 'meeting' ? (
          <aside className="ts-drawer card" aria-label="Schedule meeting">
            <div className="ts-drawer__head">
              <h3>Schedule</h3>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setSide('none')}
              >
                <Icon name="x" size={14} />
              </button>
            </div>
            <p className="muted small">
              Announces in this channel. Optionally posts a MessageCard to your
              Teams webhook.
            </p>
            <form className="stack" onSubmit={onSchedule} style={{ gap: 8 }}>
              <input
                className="input"
                placeholder="Title"
                value={meetTitle}
                onChange={(e) => setMeetTitle(e.target.value)}
                required
              />
              <input
                className="input"
                type="datetime-local"
                value={meetWhen}
                onChange={(e) => setMeetWhen(e.target.value)}
                required
              />
              <input
                className="input"
                placeholder="Join URL (optional)"
                value={meetJoin}
                onChange={(e) => setMeetJoin(e.target.value)}
              />
              <textarea
                className="input"
                rows={3}
                placeholder="Notes"
                value={meetNotes}
                onChange={(e) => setMeetNotes(e.target.value)}
              />
              <label className="ts-check">
                <input
                  type="checkbox"
                  checked={meetTeams}
                  onChange={(e) => setMeetTeams(e.target.checked)}
                />
                <span>Notify Microsoft Teams</span>
              </label>
              <button type="submit" className="btn" disabled={busy}>
                Schedule
              </button>
            </form>
          </aside>
        ) : null}

        {side === 'mcp' ? (
          <aside className="ts-drawer card" aria-label="MCP">
            <div className="ts-drawer__head">
              <h3>MCP</h3>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setSide('none')}
              >
                <Icon name="x" size={14} />
              </button>
            </div>
            <div className="ts-mcp-list">
              {mcpList.map((m) => (
                <div key={m.id} className="ts-mcp-row">
                  <div>
                    <div className="strong">{m.label}</div>
                    <div className="muted small">{m.transport}</div>
                  </div>
                  {group.can_manage ? (
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      onClick={() =>
                        void groupsApi.deleteMcp(id, m.id).then(reloadExtras)
                      }
                    >
                      Remove
                    </button>
                  ) : null}
                </div>
              ))}
            </div>
            {group.can_manage ? (
              <form className="stack" onSubmit={onConnectMcp} style={{ gap: 8, marginTop: 12 }}>
                <input
                  className="input"
                  placeholder="Label"
                  value={mcpLabel}
                  onChange={(e) => setMcpLabel(e.target.value)}
                />
                <label className="ts-check">
                  <input
                    type="checkbox"
                    checked={mcpStub}
                    onChange={(e) => setMcpStub(e.target.checked)}
                  />
                  <span>Use stub transport</span>
                </label>
                {!mcpStub ? (
                  <>
                    <input
                      className="input"
                      placeholder="Endpoint URL"
                      value={mcpUrl}
                      onChange={(e) => setMcpUrl(e.target.value)}
                      required
                    />
                    <input
                      className="input"
                      placeholder="Auth header name"
                      value={mcpAuthName}
                      onChange={(e) => setMcpAuthName(e.target.value)}
                    />
                    <input
                      className="input"
                      placeholder="Auth header value"
                      value={mcpAuthValue}
                      onChange={(e) => setMcpAuthValue(e.target.value)}
                    />
                  </>
                ) : null}
                <button type="submit" className="btn" disabled={busy}>
                  Attach MCP
                </button>
              </form>
            ) : null}
          </aside>
        ) : null}

        {side === 'members' ? (
          <aside className="ts-drawer card" aria-label="Members">
            <div className="ts-drawer__head">
              <h3>Members</h3>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setSide('none')}
              >
                <Icon name="x" size={14} />
              </button>
            </div>
            <div className="grp-list grp-list--flush" role="list">
              {group.members.map((m) => {
                const mine = m.user_id === me?.id;
                const iAmOwner =
                  group.created_by === me?.id ||
                  memberMap.get(me?.id ?? '')?.role === 'owner';
                const canRemove =
                  group.can_manage &&
                  !mine &&
                  m.role !== 'owner' &&
                  (m.role !== 'admin' || iAmOwner);
                return (
                  <div key={m.user_id} className="grp-row" role="listitem">
                    <Avatar
                      name={m.name || '?'}
                      avatar={m.avatar}
                      avatarUrl={m.avatar_url}
                      size="sm"
                    />
                    <div className="grp-row__main">
                      <Link className="grp-row__title" to={`/people/${m.user_id}`}>
                        {mine ? `${m.name} (you)` : m.name}
                      </Link>
                      <div className="muted small">{m.role}</div>
                    </div>
                    {canRemove ? (
                      <button
                        type="button"
                        className="btn btn--sm btn--ghost grp-danger"
                        disabled={busy}
                        onClick={() => void onRemoveMember(m.user_id, m.name)}
                      >
                        Remove
                      </button>
                    ) : null}
                  </div>
                );
              })}
            </div>

            {group.can_manage ? (
              <>
                <h3 className="grp-sub">Pending invites</h3>
                {group.pending_invites.length === 0 ? (
                  <p className="muted small">No pending invites.</p>
                ) : (
                  <div className="grp-list grp-list--flush" role="list">
                    {group.pending_invites.map((inv) => (
                      <div key={inv.id} className="grp-row" role="listitem">
                        <Avatar
                          name={inv.invitee_name || '?'}
                          avatar={inv.invitee_avatar}
                          avatarUrl={inv.invitee_avatar_url}
                          size="sm"
                        />
                        <div className="grp-row__main">
                          <div className="grp-row__title">
                            {inv.invitee_name}
                          </div>
                          <div className="muted small">
                            Waiting to accept · {inv.role}
                          </div>
                        </div>
                        <button
                          type="button"
                          className="btn btn--sm btn--ghost"
                          disabled={busy}
                          onClick={() => void onCancelInvite(inv.id)}
                        >
                          Cancel
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <h3 className="grp-sub">Invite someone</h3>
                <div className="grp-chips" role="radiogroup" aria-label="Invite as">
                  {(['member', 'admin'] as const).map((r) => (
                    <button
                      key={r}
                      type="button"
                      role="radio"
                      aria-checked={inviteRole === r}
                      className={
                        inviteRole === r ? 'grp-chip grp-chip--on' : 'grp-chip'
                      }
                      onClick={() => setInviteRole(r)}
                    >
                      {r === 'admin' ? 'Admin' : 'Member'}
                    </button>
                  ))}
                </div>
                <UserSearchPicker
                  label="Search by name or email"
                  actionLabel="Invite"
                  disabled={busy}
                  excludeIds={[
                    ...group.members.map((m) => m.user_id),
                    ...group.pending_invites.map((i) => i.invitee_id),
                  ]}
                  onPick={onInvite}
                />
                <p className="muted small">
                  They get a bell notification and an email, and only join after
                  they Accept.
                </p>
              </>
            ) : null}
          </aside>
        ) : null}
      </div>
    </div>
  );
}

export default GroupDetailPage;
