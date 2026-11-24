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
  lazy,
  Suspense,
} from 'react';
import { EmojiStyle, Theme, type EmojiClickData } from 'emoji-picker-react';

// Loaded only when the emoji menu is opened, so the chat page stays light.
const EmojiPicker = lazy(() => import('emoji-picker-react'));
import {
  Link,
  Navigate,
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router-dom';
import { groupsApi } from '../api/groups';
import { integrationsApi } from '../api/integrations';
import { useAuth } from '../auth/AuthProvider';
import { renderInline } from '../components/ChatReply';
import { PollBubble } from '../components/chat/PollBubble';
import { PollCreateSheet, type PollDraft } from '../components/chat/PollCreateSheet';
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
  GroupPoll,
} from '../types/groups';
import type { TrackerConnection } from '../types/trackers';
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
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [side, setSide] = useState<SidePanel>('none');
  const [headOpen, setHeadOpen] = useState(true);
  const [polls, setPolls] = useState<GroupPoll[]>([]);
  const [pollOpen, setPollOpen] = useState(false);
  const pollById = useMemo(() => new Map(polls.map((p) => [p.id, p])), [polls]);


  async function onCreatePoll(draft: PollDraft) {
    if (!channelId) return;
    setBusy(true);
    try {
      const p = await groupsApi.createPoll(id, {
        question: draft.question,
        options: draft.options,
        multi_select: draft.multi,
        channel_id: channelId,
        ends_at: draft.endsAt ?? undefined,
      });
      setPolls((prev) => [p, ...prev]);
      setPollOpen(false);
      await reloadMessages(channelId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create poll');
    } finally {
      setBusy(false);
    }
  }

  async function onVote(pollId: string, optionIndex: number) {
    try {
      const p = await groupsApi.votePoll(id, pollId, optionIndex);
      setPolls((prev) => prev.map((x) => (x.id === p.id ? p : x)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not vote');
    }
  }

  async function onClosePoll(pollId: string) {
    try {
      const p = await groupsApi.closePoll(id, pollId);
      setPolls((prev) => prev.map((x) => (x.id === p.id ? p : x)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not close poll');
    }
  }
  const scroller = useRef<HTMLDivElement>(null);

  const [meetTitle, setMeetTitle] = useState('');
  const [meetWhen, setMeetWhen] = useState('');
  const [meetJoin, setMeetJoin] = useState('');
  const [meetNotes, setMeetNotes] = useState('');
  const [meetTeams, setMeetTeams] = useState(true);

  const [mcpMine, setMcpMine] = useState<TrackerConnection[]>([]);
  const [mcpPick, setMcpPick] = useState('');

  useEffect(() => {
    if (side !== 'mcp') return;
    let cancelled = false;
    integrationsApi.listMine().then((rows) => {
      const mcp = rows.filter((c) => c.provider_id === 'mcp_server');
      if (!cancelled) setMcpMine(mcp);
    }).catch(() => {
      if (!cancelled) setMcpMine([]);
    });
    return () => {
      cancelled = true;
    };
  }, [side]);
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
    const [m, mcp, pl] = await Promise.all([
      groupsApi.meetings(id),
      groupsApi.listMcp(id),
      groupsApi.polls(id),
    ]);
    setMeetings(m);
    setMcpList(mcp);
    setPolls(pl);
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

  // Light polling so chats feel live without websockets. Background refresh
  // failures are logged rather than hidden, so a stalled chat is visible in the console.
  useEffect(() => {
    if (!channelId) return;
    const refresh = () => {
      if (document.visibilityState !== 'visible') return;
      reloadMessages(channelId).catch((err: unknown) => {
        console.warn('Chat refresh failed', err);
      });
      groupsApi.polls(id).then(setPolls).catch(() => undefined);
    };
    const t = window.setInterval(refresh, 8000);
    // Browsers throttle timers in background tabs, so catch up as soon as the tab is back.
    document.addEventListener('visibilitychange', refresh);
    window.addEventListener('focus', refresh);
    return () => {
      window.clearInterval(t);
      document.removeEventListener('visibilitychange', refresh);
      window.removeEventListener('focus', refresh);
    };
  }, [id, channelId, reloadMessages]);

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

  async function onAttachMcp(e: FormEvent) {
    e.preventDefault();
    const conn = mcpMine.find((c) => c.id === mcpPick);
    if (!group?.can_manage || !conn) return;
    setBusy(true);
    setError(null);
    try {
      await groupsApi.connectMcp(id, { connection_id: conn.id, label: conn.label });
      setMcpPick('');
      await reloadExtras();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to attach MCP');
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
            if (msg.message_type === 'poll') {
              const poll = pollById.get(String(msg.meta?.poll_id ?? ''));
              return (
                <PollBubble
                  key={msg.id}
                  poll={poll}
                  senderName={mine ? 'You' : nameOf(msg.author_id)}
                  mine={mine}
                  createdAt={msg.created_at}
                  canVote={group.can_post}
                  canClose={!!poll && (poll.created_by === me?.id || !!group.can_manage)}
                  busy={busy}
                  onVote={(i) => poll && void onVote(poll.id, i)}
                  onClose={() => poll && void onClosePoll(poll.id)}
                />
              );
            }
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
                <div className="ts-bubble__text">
                  {system ? renderInline(msg.body) : msg.body}
                </div>
                <div className="ts-bubble__time">
                  {relTime(msg.created_at)}
                </div>
              </div>
            );
          })
        )}
      </div>

      <PollCreateSheet
        open={pollOpen}
        busy={busy}
        onClose={() => setPollOpen(false)}
        onSubmit={onCreatePoll}
      />
      <form className="ts-composer" onSubmit={onSend}>
        <div className="ts-emoji">
          <button
            type="button"
            className="btn ts-emoji__toggle"
            aria-label="Insert emoji"
            aria-expanded={emojiOpen}
            disabled={!group.can_post || busy || !channelId}
            onClick={() => setEmojiOpen((open) => !open)}
          >
            <span aria-hidden>😊</span>
          </button>
          {emojiOpen ? (
            <div
              className="ts-emoji__popover"
              onKeyDown={(e) => {
                if (e.key === 'Escape') setEmojiOpen(false);
              }}
            >
              <Suspense fallback={<p className="muted small">Loading emoji…</p>}>
                <EmojiPicker
                  emojiStyle={EmojiStyle.NATIVE}
                  theme={Theme.AUTO}
                  width={320}
                  height={380}
                  previewConfig={{ showPreview: false }}
                  onEmojiClick={(data: EmojiClickData) => {
                    setDraft((d) => `${d}${data.emoji}`);
                    setEmojiOpen(false);
                  }}
                />
              </Suspense>
            </div>
          ) : null}
        </div>
        <button
          type="button"
          className="btn ts-poll-btn"
          aria-label="Create poll"
          aria-expanded={pollOpen}
          title="Create poll"
          disabled={!group.can_post || busy || !channelId}
          onClick={() => setPollOpen((o) => !o)}
        >
          <Icon name="list" size={16} />
        </button>
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
      <div className="dm-screen">
        <div className="row dm-screen__head">
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
    <div className="dm-screen grp-screen">
      <div className="row dm-screen__head" style={{ justifyContent: 'space-between', gap: 12 }}>
        <div className="row" style={{ gap: 12, minWidth: 0 }}>
          <GroupGlyph name={group.name} avatarUrl={group.avatar_url} size={48} />
          <div style={{ minWidth: 0 }}>
            <div className="crumbs">
              <Link to="/groups">Groups</Link>
              <span aria-hidden>/</span>
              <span aria-current="page">{group.name}</span>
            </div>
            {headOpen && group.description ? (
              <p className="muted small" style={{ margin: '4px 0 0' }}>
                {group.description}
              </p>
            ) : null}
            {headOpen && group.can_manage ? (
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
        <div className="row" style={{ gap: 6, marginLeft: 'auto', alignItems: 'center' }}>
        {headOpen ? (
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
        ) : null}
        <button
          type="button"
          className="btn btn--sm btn--ghost grp-head-toggle"
          aria-expanded={headOpen}
          aria-label={headOpen ? 'Collapse header' : 'Expand header'}
          onClick={() => setHeadOpen((open) => !open)}
        >
          <Icon name="chevronD" size={16} />
        </button>
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
            <form className="meet-form" onSubmit={onSchedule}>
              <label className="field">
                <span className="label">Title</span>
                <input
                  className="input"
                  placeholder="e.g. Sprint review"
                  value={meetTitle}
                  onChange={(e) => setMeetTitle(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span className="label">Starts</span>
                <input
                  className="input"
                  type="datetime-local"
                  value={meetWhen}
                  onChange={(e) => setMeetWhen(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span className="label">Join link (optional)</span>
                <input
                  className="input"
                  type="url"
                  placeholder="https://"
                  value={meetJoin}
                  onChange={(e) => setMeetJoin(e.target.value)}
                />
              </label>
              <label className="field">
                <span className="label">Notes (optional)</span>
                <textarea
                  className="input"
                  rows={3}
                  placeholder="Agenda, prep, anything the group should know"
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
                <span>Also notify Microsoft Teams</span>
              </label>
              <button type="submit" className="btn btn--primary" disabled={busy}>
                Schedule meeting
              </button>
            </form>
          </aside>
        ) : null}

        {side === 'mcp' ? (
          <aside className="ts-drawer card" aria-label="MCP">
            <div className="ts-drawer__head">
              <h3>MCP servers</h3>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setSide('none')}
              >
                <Icon name="x" size={14} />
              </button>
            </div>
            <p className="muted small" style={{ marginTop: 0 }}>
              Attached servers give this group&apos;s channels access to their tools.
            </p>

            {mcpList.length === 0 ? (
              <p className="muted small">No MCP servers attached yet.</p>
            ) : (
              <div className="ts-mcp-list">
                {mcpList.map((m) => (
                  <div key={m.id} className="ts-mcp-row">
                    <div style={{ minWidth: 0 }}>
                      <div className="strong truncate">{m.label}</div>
                      <div className="muted small">
                        {m.tools_cache.length} tool{m.tools_cache.length === 1 ? '' : 's'}
                      </div>
                    </div>
                    {group.can_manage ? (
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        disabled={busy}
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
            )}

            {group.can_manage ? (
              mcpMine.length === 0 ? (
                <div className="mcp-empty">
                  <p className="muted small" style={{ margin: 0 }}>
                    You have no MCP servers yet. Add one under Integrations, then
                    attach it here.
                  </p>
                  <Link className="btn btn--sm" to="/integrations/mcp_server">
                    Open Integrations
                  </Link>
                </div>
              ) : (
                <form className="mcp-attach" onSubmit={onAttachMcp}>
                  <label className="field">
                    <span className="label">Server</span>
                    <select
                      className="input"
                      value={mcpPick}
                      onChange={(e) => setMcpPick(e.target.value)}
                      required
                    >
                      <option value="" disabled>
                        Choose a connection
                      </option>
                      {mcpMine.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.label}
                          {c.display_label ? ` — ${c.display_label}` : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button type="submit" className="btn" disabled={busy || !mcpPick}>
                    Attach to group
                  </button>
                </form>
              )
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

        <aside className="ts-rail" aria-label="Group tools">
          <button
            type="button"
            className={`ts-rail__btn${side === 'meeting' ? ' is-on' : ''}`}
            aria-label="Schedule"
            title="Schedule"
            aria-pressed={side === 'meeting'}
            disabled={!group.can_post}
            onClick={() => setSide(side === 'meeting' ? 'none' : 'meeting')}
          >
            <Icon name="calendar" size={16} />
          </button>
          <button
            type="button"
            className={`ts-rail__btn${side === 'mcp' ? ' is-on' : ''}`}
            aria-label="MCP"
            title="MCP"
            aria-pressed={side === 'mcp'}
            onClick={() => setSide(side === 'mcp' ? 'none' : 'mcp')}
          >
            <Icon name="spark" size={16} />
          </button>
        </aside>
      </div>
    </div>
  );
}

export default GroupDetailPage;
