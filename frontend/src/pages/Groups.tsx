/**
 * Collaborate home — Groups, Direct messages, and pending invites.
 */

import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { groupsApi } from '../api/groups';
import { UserSearchPicker } from '../components/UserSearchPicker';
import { GroupGlyph } from '../components/GroupGlyph';
import { Avatar, Icon } from '../components/Icons';
import type { User } from '../types/auth';
import type { GroupInvite, GroupSummary } from '../types/groups';

type TabId = 'groups' | 'dms' | 'invites';

export function GroupsPage({ defaultTab = 'groups' }: { defaultTab?: TabId }) {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const tab: TabId = params.get('tab') === 'invites' ? 'invites' : defaultTab;

  const [groups, setGroups] = useState<GroupSummary[]>([]);
  const [dms, setDms] = useState<GroupSummary[]>([]);
  const [invites, setInvites] = useState<GroupInvite[]>([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const setTab = (next: TabId) => {
    navigate(
      next === 'dms' ? '/dms' : next === 'invites' ? '/groups?tab=invites' : '/groups',
    );
  };

  const reload = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [g, d, inv] = await Promise.all([
        groupsApi.list('group'),
        groupsApi.list('dm'),
        groupsApi.myInvites(),
      ]);
      setGroups(g);
      setDms(d);
      setInvites(inv);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const g = await groupsApi.create({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setName('');
      setDescription('');
      navigate(`/groups/${g.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create group');
      setBusy(false);
    }
  }

  async function onOpenDm(person: User) {
    setBusy(true);
    setError(null);
    try {
      const g = await groupsApi.openDm(person.id);
      navigate(`/dms/${g.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not open DM');
      setBusy(false);
    }
  }

  async function onAccept(inviteId: string) {
    setBusy(true);
    setError(null);
    try {
      const g = await groupsApi.acceptInvite(inviteId);
      await reload();
      navigate(`/groups/${g.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not accept');
      setBusy(false);
    }
  }

  async function onDecline(inviteId: string) {
    setBusy(true);
    setError(null);
    try {
      await groupsApi.declineInvite(inviteId);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not decline');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grp-page">
      <div>
        <div className="eyebrow eyebrow--plain">Collaborate</div>
        <h1 style={{ margin: '4px 0 6px' }}>
          {tab === 'dms' ? 'Messages' : tab === 'invites' ? 'Invites' : 'Groups'}
        </h1>
        <p className="muted" style={{ margin: 0, maxWidth: 560 }}>
          {tab === 'dms'
            ? 'One-to-one chats with anyone in KonnektIdea.'
            : tab === 'invites'
              ? 'Accept or decline invitations to join a group.'
              : 'Groups you belong to. Invite teammates by name — they must accept before joining.'}
        </p>
      </div>

      <div className="tabs" role="tablist" aria-label="Collaborate">
        <button
          type="button"
          role="tab"
                    aria-selected={tab === 'groups'}
          onClick={() => setTab('groups')}
        >
          Groups
          {groups.length ? (
            <span className="count">{groups.length}</span>
          ) : null}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'dms'}
          onClick={() => setTab('dms')}
        >
          Messages
          {dms.length ? <span className="count">{dms.length}</span> : null}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'invites'}
          onClick={() => setTab('invites')}
        >
          Invites
          {invites.length ? (
            <span className="count">{invites.length}</span>
          ) : null}
        </button>
      </div>

      {error ? <div className="notice notice--danger" role="alert">{error}</div> : null}

      {tab === 'groups' ? (
        <>
          <form className="card card--tight grp-create" onSubmit={onCreate}>
            <div style={{ flex: '1 1 220px' }}>
              <label className="muted small" htmlFor="grp-name">
                New group
              </label>
              <input
                id="grp-name"
                className="input"
                placeholder="e.g. Parking lot ideas"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={busy}
                required
              />
            </div>
            <div style={{ flex: '2 1 280px' }}>
              <label className="muted small" htmlFor="grp-desc">
                Description (optional)
              </label>
              <input
                id="grp-desc"
                className="input"
                placeholder="What is this space for?"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={busy}
              />
            </div>
            <button
              type="submit"
              className="btn"
              disabled={busy || !name.trim()}
            >
              <Icon name="plus" size={16} /> Create group
            </button>
          </form>

          {loading ? (
            <p className="muted">Loading groups…</p>
          ) : groups.length === 0 ? (
            <div className="card">
              <div className="empty" style={{ padding: 28 }}>
                <Icon name="users" size={28} />
                <h3>No groups yet</h3>
                <p className="muted small">
                  Create a group above, or wait for an invite.
                </p>
              </div>
            </div>
          ) : (
            <div className="grp-list" role="list">
              {groups.map((g) => (
                <Link
                  key={g.id}
                  to={`/groups/${g.id}`}
                  className="grp-row"
                  role="listitem"
                >
                  <GroupGlyph name={g.name} avatarUrl={g.avatar_url} />
                  <div className="grp-row__main">
                    <div className="grp-row__title">{g.name}</div>
                    <div className="muted small grp-row__meta">
                      {g.member_count}{' '}
                      {g.member_count === 1 ? 'member' : 'members'}
                      {g.idea_id ? ' · Linked to an idea' : ' · No idea linked'}
                      {g.my_role ? ` · ${g.my_role}` : ''}
                    </div>
                  </div>
                  <Icon name="chevronR" size={18} />
                </Link>
              ))}
            </div>
          )}
        </>
      ) : null}

      {tab === 'dms' ? (
        <>
          <div className="card card--tight">
            <UserSearchPicker
              label="Message someone"
              actionIcon="message"
              disabled={busy}
              onPick={onOpenDm}
            />
          </div>

          {loading ? (
            <p className="muted">Loading messages…</p>
          ) : dms.length === 0 ? (
            <div className="card">
              <div className="empty" style={{ padding: 28 }}>
                <Icon name="message" size={28} />
                <h3>No conversations yet</h3>
                <p className="muted small">
                  Search above to start a 1:1 chat.
                </p>
              </div>
            </div>
          ) : (
            <div className="grp-list" role="list">
              {dms.map((g) => (
                <Link
                  key={g.id}
                  to={`/dms/${g.id}`}
                  className="grp-row"
                  role="listitem"
                >
                  <Avatar
                    name={g.name}
                    avatar={g.peer_avatar}
                    avatarUrl={g.peer_avatar_url}
                  />
                  <div className="grp-row__main">
                    <div className="grp-row__title">{g.name}</div>
                    <div className="muted small grp-row__meta">
                      Direct message
                    </div>
                  </div>
                  <Icon name="chevronR" size={18} />
                </Link>
              ))}
            </div>
          )}
        </>
      ) : null}

      {tab === 'invites' ? (
        loading ? (
          <p className="muted">Loading invites…</p>
        ) : invites.length === 0 ? (
          <div className="card">
            <div className="empty" style={{ padding: 28 }}>
              <Icon name="users" size={28} />
              <h3>No pending invites</h3>
              <p className="muted small">
                When someone invites you to a group, it shows up here and in
                your notification bell.
              </p>
            </div>
          </div>
        ) : (
          <div className="grp-list" role="list">
            {invites.map((inv) => {
              return (
                <div key={inv.id} className="grp-row" role="listitem">
                  <GroupGlyph name={inv.group_name} />
                  <div className="grp-row__main">
                    <div className="grp-row__title">{inv.group_name}</div>
                    <div className="muted small grp-row__meta">
                      Invited by {inv.invited_by_name || 'someone'} · role {inv.role}
                    </div>
                  </div>
                  <div className="row" style={{ gap: 6 }}>
                    <button
                      type="button"
                      className="btn btn--sm"
                      disabled={busy}
                      onClick={() => void onAccept(inv.id)}
                    >
                      Accept
                    </button>
                    <button
                      type="button"
                      className="btn btn--sm btn--ghost"
                      disabled={busy}
                      onClick={() => void onDecline(inv.id)}
                    >
                      Decline
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )
      ) : null}
    </div>
  );
}

export default GroupsPage;
