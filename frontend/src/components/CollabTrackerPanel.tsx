/**
 * Team & progress tab — matches idea-hub.html `ideaTeam` / milestone / check-in markup.
 * Roster, pending collab requests, milestones with status chips, check-in feed.
 */

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { collabApi } from '../api/collab';
import { usersApi } from '../api/users';
import { useAuth } from '../auth/AuthProvider';
import { STATUS_META } from '../constants/status';
import { Avatar, Icon } from './Icons';
import { fmtDate, relTime } from '../utils/format';
import type { Idea } from '../types/idea';
import type { User } from '../types/auth';
import type { CollabRequest, Tracker } from '../types/phase456';
import { useDialog } from './DialogProvider';

const MS_TRACKABLE = [
  'submitted',
  'under_review',
  'needs_info',
  'accepted',
  'prototype',
  'parked',
];
const COLLAB_OPEN = [
  'submitted',
  'under_review',
  'needs_info',
  'accepted',
  'prototype',
];
const COLLAB_COAUTHOR_OPEN = ['submitted', 'under_review', 'needs_info'];

const MS_STATUS: Record<string, { label: string; tone: string }> = {
  not_started: { label: 'Not started', tone: '' },
  in_progress: { label: 'In progress', tone: 'brand' },
  blocked: { label: 'Blocked', tone: 'danger' },
  done: { label: 'Done', tone: 'success' },
};

const COLLAB_TYPE_LABEL: Record<string, { label: string; tone: string }> = {
  coauthor: { label: 'Co-author', tone: 'brand' },
  build: { label: 'Help build', tone: '' },
};

const COLLAB_STATUS_TONE: Record<string, string> = {
  pending: 'warning',
  accepted: 'success',
  declined: 'danger',
  withdrawn: '',
  left: '',
  removed: 'danger',
};

const QUICK: Record<string, [string, string, string]> = {
  not_started: ['in_progress', 'Start', 'play'],
  in_progress: ['done', 'Mark done', 'check'],
  blocked: ['in_progress', 'Unblock', 'refresh'],
  done: ['in_progress', 'Reopen', 'refresh'],
};

function Pill({
  label,
  tone = '',
  icon,
}: {
  label: string;
  tone?: string;
  icon?: string;
}) {
  const cls = tone ? `pill pill--${tone}` : 'pill';
  return (
    <span className={cls}>
      {icon ? <Icon name={icon} size={12} /> : null} {label}
    </span>
  );
}

function plural(n: number, one: string, many?: string) {
  return `${n} ${n === 1 ? one : many ?? `${one}s`}`;
}

function isOverdue(dueAt: string | null | undefined, status: string) {
  if (!dueAt || status === 'done') return false;
  return new Date(dueAt).getTime() < Date.now();
}

type Props = { idea: Idea };

export function CollabTrackerPanel({ idea }: Props) {
  const dialog = useDialog();
  const { user: me } = useAuth();
  const [reqs, setReqs] = useState<CollabRequest[]>([]);
  const [tracker, setTracker] = useState<Tracker | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [looking, setLooking] = useState(false);
  const [skillsWanted, setSkillsWanted] = useState('');

  const [askOpen, setAskOpen] = useState(false);
  const [askType, setAskType] = useState<'coauthor' | 'build'>('build');
  const [askMessage, setAskMessage] = useState('');
  const [askRole, setAskRole] = useState('');
  const [askHours, setAskHours] = useState('');

  const [msTitle, setMsTitle] = useState('');
  const [msWho, setMsWho] = useState('');
  const [msDue, setMsDue] = useState('');
  const [checkinBody, setCheckinBody] = useState('');

  const userMap = useMemo(() => {
    const m = new Map<string, User>();
    users.forEach((u) => m.set(u.id, u));
    return m;
  }, [users]);

  const nameOf = useCallback(
    (id: string | null | undefined) => {
      if (!id) return 'Someone';
      if (me && id === me.id) return 'You';
      return userMap.get(id)?.name ?? 'Unknown user';
    },
    [me, userMap],
  );

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [r, t, u] = await Promise.all([
        collabApi.forIdea(idea.id),
        collabApi.tracker(idea.id),
        usersApi.list().catch(() => [] as User[]),
      ]);
      setReqs(r);
      setTracker(t);
      setUsers(u);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load team');
    }
  }, [idea.id]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (me && !msWho) setMsWho(me.id);
  }, [me, msWho]);

  const trackable = MS_TRACKABLE.includes(idea.status);
  const open = COLLAB_OPEN.includes(idea.status);
  const canCo = COLLAB_COAUTHOR_OPEN.includes(idea.status);
  const isAuthor = me?.id === idea.author_id;
  const isOwner = me?.id === idea.owner_id;
  const isCoAuthor = idea.co_author_ids.includes(me?.id ?? '');
  const accepted = reqs.filter(
    (r) => r.status === 'accepted' && r.from_user_id === me?.id,
  );
  const isMember =
    isAuthor ||
    isOwner ||
    isCoAuthor ||
    accepted.length > 0;
  const isLeadOrAdmin = ['lead', 'admin', 'leadership'].includes(
    me?.active_role ?? '',
  );
  const canDecide =
    isAuthor || isOwner || isCoAuthor || isLeadOrAdmin;
  const canWork = trackable && (isMember || isLeadOrAdmin);
  const mgr = isAuthor || isOwner || isLeadOrAdmin;
  const seesReqs = canDecide;

  const mine = useMemo(() => {
    if (!me) return null;
    const mineList = reqs
      .filter((r) => r.from_user_id === me.id)
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
    return mineList[0] ?? null;
  }, [reqs, me]);

  const pending = reqs.filter((r) => r.status === 'pending');
  const history = reqs
    .filter((r) => r.status !== 'pending')
    .slice()
    .reverse();

  const roster = useMemo(() => {
    const rows: Array<{ userId: string; label: string }> = [
      { userId: idea.author_id, label: 'Author' },
    ];
    idea.co_author_ids.forEach((u) =>
      rows.push({ userId: u, label: 'Co-author' }),
    );
    if (idea.owner_id) {
      const existing = rows.find((r) => r.userId === idea.owner_id);
      if (existing) existing.label += ' and owner';
      else rows.push({ userId: idea.owner_id, label: 'Owner' });
    }
    reqs
      .filter((r) => r.status === 'accepted')
      .forEach((r) => {
        if (!rows.some((x) => x.userId === r.from_user_id)) {
          rows.push({ userId: r.from_user_id, label: 'Collaborator' });
        }
      });
    return rows;
  }, [idea, reqs]);

  const milestones = tracker?.milestones ?? [];
  const checkins = tracker?.checkins ?? [];
  const done = milestones.filter((m) => m.status === 'done').length;
  const inProg = milestones.filter((m) => m.status === 'in_progress').length;
  const notStarted = milestones.filter((m) => m.status === 'not_started').length;
  const blocked = tracker?.blocked_count ?? 0;
  const overdue = tracker?.overdue_count ?? 0;
  const pct = milestones.length
    ? Math.round((100 * done) / milestones.length)
    : 0;
  const myMs = milestones.filter((m) => m.owner_id === me?.id);

  const statusLabel =
    STATUS_META[idea.status as keyof typeof STATUS_META]?.label ?? idea.status;

  const askKind: 'member' | 'pending' | 'can' | 'none' = (() => {
    if (isMember) return 'member';
    if (mine?.status === 'pending') return 'pending';
    if (open && me && !isAuthor) return 'can';
    return 'none';
  })();

  async function sendRequest(e: FormEvent) {
    e.preventDefault();
    if (askMessage.trim().length < 10) {
      setError('Write at least 10 characters about what you can contribute.');
      return;
    }
    setBusy(true);
    try {
      await collabApi.create({
        idea_id: idea.id,
        type: askType,
        message: askMessage.trim(),
        role: askRole.trim() || undefined,
        hours: askHours ? Number(askHours) : undefined,
      });
      setAskMessage('');
      setAskRole('');
      setAskHours('');
      setAskOpen(false);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  }

  async function decide(id: string, accept: boolean) {
    let note = '';
    if (!accept) {
      note =
        (await dialog.prompt({
          title: 'Decline request',
          label: 'Note for the requester (min 10 characters)',
          minLength: 10,
          multiline: true,
          confirmLabel: 'Decline',
          danger: true,
        })) ?? '';
      if (note.trim().length < 10) {
        setError('A note of at least 10 characters is required to decline.');
        return;
      }
    } else {
      const welcome = await dialog.prompt({
        title: 'Accept request',
        label: 'A word of welcome (optional)',
        multiline: true,
        confirmLabel: 'Accept',
      });
      // Cancelling the dialog keeps the request pending.
      if (welcome === null) return;
      note = welcome;
    }
    setBusy(true);
    try {
      await collabApi.decide(id, accept, note);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Decision failed');
    } finally {
      setBusy(false);
    }
  }

  async function withdraw(id: string) {
    setBusy(true);
    try {
      await collabApi.withdraw(id);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Withdraw failed');
    } finally {
      setBusy(false);
    }
  }

  async function setMsStatus(id: string, to: string) {
    let blocker = '';
    if (to === 'blocked') {
      const entered = await dialog.prompt({
        title: 'Mark as blocked',
        label: 'What is blocking this? (min 5 characters)',
        minLength: 5,
        multiline: true,
        confirmLabel: 'Mark blocked',
      });
      if (entered === null) return;
      blocker = entered;
    }
    setBusy(true);
    try {
      await collabApi.updateMilestone(id, { status: to, blocker });
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setBusy(false);
    }
  }

  async function addMilestone(e: FormEvent) {
    e.preventDefault();
    if (msTitle.trim().length < 2) return;
    setBusy(true);
    try {
      await collabApi.addMilestone(idea.id, {
        title: msTitle.trim(),
        owner_id: msWho || undefined,
        due_at: msDue ? new Date(msDue).toISOString() : undefined,
      });
      setMsTitle('');
      setMsDue('');
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add milestone');
    } finally {
      setBusy(false);
    }
  }

  async function postCheckin(e: FormEvent) {
    e.preventDefault();
    if (checkinBody.trim().length < 2) return;
    setBusy(true);
    try {
      await collabApi.addCheckin(idea.id, { body: checkinBody.trim() });
      setCheckinBody('');
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Check-in failed');
    } finally {
      setBusy(false);
    }
  }

  function requestControl() {
    if (askKind === 'member' && !isAuthor) {
      return (
        <span className="btn" aria-disabled="true">
          <Icon name="users" size={16} /> You are on the team
        </span>
      );
    }
    if (askKind === 'pending' && mine) {
      return (
        <>
          <span className="btn" aria-disabled="true">
            <Icon name="clock" size={16} /> Request sent: pending
          </span>
          <button
            type="button"
            className="btn btn--ghost"
            disabled={busy}
            onClick={() => void withdraw(mine.id)}
          >
            Withdraw
          </button>
        </>
      );
    }
    if (askKind !== 'can') return null;
    const again = mine?.status === 'declined';
    return (
      <>
        {again ? (
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setAskOpen(true)}
          >
            <Icon name="message" size={16} /> Read the answer
          </button>
        ) : null}
        <button
          type="button"
          className="btn"
          onClick={() => {
            setAskType('build');
            setAskOpen(true);
          }}
        >
          <Icon name="hand" size={16} />{' '}
          {again ? 'Ask again to help build' : 'I want to help build this'}
        </button>
        {canCo ? (
          <button
            type="button"
            className="btn"
            onClick={() => {
              setAskType('coauthor');
              setAskOpen(true);
            }}
          >
            <Icon name="edit" size={16} />{' '}
            {again ? 'Ask again as co-author' : 'Join as co-author'}
          </button>
        ) : null}
      </>
    );
  }

  function msRow(
    m: Tracker['milestones'][number],
    compact = false,
  ) {
    const s = MS_STATUS[m.status] ?? MS_STATUS.not_started;
    const over = isOverdue(m.due_at, m.status);
    const quick = QUICK[m.status] ?? QUICK.not_started;
    const canStatus = canWork;
    return (
      <div key={m.id} className={`ms ms--${m.status}`}>
        <div className="ms__main">
          <div className="row" style={{ gap: 6 }}>
            <strong className="ms__title">{m.title}</strong>
            <Pill
              label={s.label}
              tone={s.tone}
              icon={
                m.status === 'done'
                  ? 'check'
                  : m.status === 'blocked'
                    ? 'alert'
                    : undefined
              }
            />
            {over ? <Pill label="Overdue" tone="warning" icon="clock" /> : null}
          </div>
          {m.status === 'blocked' && m.blocker ? (
            <div className="ms__blocker small">
              <Icon name="alert" size={14} />
              <span>
                <strong>Blocked:</strong> {m.blocker}
              </span>
            </div>
          ) : null}
          <div className="meta-row small">
            <span className="muted">Assigned to</span>
            {m.owner_id ? (
              <span className="person">
                <Avatar
                  name={nameOf(m.owner_id)}
                  avatar={userMap.get(m.owner_id)?.avatar ?? 1}
                  size="sm"
                />
                {nameOf(m.owner_id)}
              </span>
            ) : (
              <span className="muted">Unassigned</span>
            )}
            {m.due_at ? (
              <span className={over ? 'ms__due--over' : 'muted'}>
                Due {fmtDate(m.due_at)}
              </span>
            ) : (
              <span className="muted">No due date</span>
            )}
          </div>
        </div>
        <div className="ms__act">
          {canStatus && !compact ? (
            <>
              <button
                type="button"
                className={`btn btn--sm${m.status === 'in_progress' ? ' btn--primary' : ''}`}
                disabled={busy}
                onClick={() => void setMsStatus(m.id, quick[0])}
              >
                <Icon name={quick[2]} size={14} /> {quick[1]}
              </button>
              <label className="sr-only" htmlFor={`mss-${m.id}`}>
                Change status of {m.title}
              </label>
              <select
                className="select select--sm"
                id={`mss-${m.id}`}
                value={m.status}
                disabled={busy}
                onChange={(e) => void setMsStatus(m.id, e.target.value)}
              >
                {Object.entries(MS_STATUS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v.label}
                  </option>
                ))}
              </select>
            </>
          ) : null}
        </div>
      </div>
    );
  }

  if (!tracker && !error) {
    return <p className="muted">Loading team and progress…</p>;
  }

  return (
    <div className="stack">
      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={16} />
          <span>{error}</span>
        </div>
      ) : null}

      {/* Your request / want to join */}
      {mine && askKind !== 'member' ? (
        <div
          className="card"
          style={
            mine.status === 'declined'
              ? { borderColor: 'var(--warning)' }
              : undefined
          }
        >
          <div className="row row--between">
            <h3>Your request</h3>
            <Pill
              label={mine.status}
              tone={COLLAB_STATUS_TONE[mine.status] ?? ''}
            />
          </div>
          <p className="small" style={{ marginTop: 6 }}>
            <Pill
              label={COLLAB_TYPE_LABEL[mine.type]?.label ?? mine.type}
              tone={COLLAB_TYPE_LABEL[mine.type]?.tone ?? ''}
            />{' '}
            <span className="muted">sent {relTime(mine.created_at)}:</span>{' '}
            {mine.message}
          </p>
          {mine.status === 'pending' ? (
            <>
              <p className="muted small">
                Waiting for the author
                {idea.owner_id ? ' or owner' : ''}. You can follow along here;
                editing the tracker opens up once you are accepted.
              </p>
              <div className="row">
                <button
                  type="button"
                  className="btn btn--sm"
                  disabled={busy}
                  onClick={() => void withdraw(mine.id)}
                >
                  Withdraw request
                </button>
              </div>
            </>
          ) : null}
          {['declined', 'removed', 'left'].includes(mine.status) ? (
            <>
              <div className="quote" style={{ margin: '8px 0' }}>
                {mine.status === 'left'
                  ? 'You left this team.'
                  : mine.note || 'No note was left.'}
                <cite>
                  {mine.decided_at
                    ? fmtDate(mine.decided_at, true)
                    : relTime(mine.created_at)}
                </cite>
              </div>
              {askKind === 'can' ? (
                <div className="row">{requestControl()}</div>
              ) : null}
            </>
          ) : null}
        </div>
      ) : askKind === 'can' && !askOpen ? (
        <div className="card">
          <div className="card__head">
            <h3>Want to work on this?</h3>
          </div>
          <p className="muted small">
            Requests go to the author
            {idea.owner_id ? ' and owner' : ''}. Once accepted you can use the
            tracker, post check-ins and be credited if the idea is implemented.
          </p>
          <div className="row" style={{ marginTop: 8 }}>
            {requestControl()}
          </div>
        </div>
      ) : null}

      {askOpen && askKind === 'can' ? (
        <div className="card">
          <div className="card__head">
            <h3>Ask to join</h3>
          </div>
          <form className="stack" onSubmit={sendRequest}>
            <div className="field">
              <label htmlFor="ask-type">What would you like to do?</label>
              <select
                id="ask-type"
                className="select"
                value={askType}
                onChange={(e) =>
                  setAskType(e.target.value as 'coauthor' | 'build')
                }
              >
                <option value="build">Help build: help deliver it</option>
                {canCo ? (
                  <option value="coauthor">
                    Co-author: shape the idea with the author
                  </option>
                ) : null}
              </select>
            </div>
            <div className="field">
              <label htmlFor="ask-msg">What can you contribute?</label>
              <textarea
                id="ask-msg"
                className="textarea"
                value={askMessage}
                onChange={(e) => setAskMessage(e.target.value)}
                rows={3}
                required
                minLength={10}
                placeholder={
                  askType === 'coauthor'
                    ? 'For example: I run this process today and can sharpen the problem statement.'
                    : 'For example: I can build the first prototype and review the design.'
                }
              />
            </div>
            <div className="inline-form" style={{ marginTop: 0 }}>
              <div className="field" style={{ flex: '1 1 160px' }}>
                <label htmlFor="ask-role">Your skills or role (optional)</label>
                <input
                  id="ask-role"
                  className="input"
                  value={askRole}
                  onChange={(e) => setAskRole(e.target.value)}
                  placeholder="For example: data analyst"
                />
              </div>
              <div className="field" style={{ flex: '0 0 140px' }}>
                <label htmlFor="ask-hours">Hours / week (optional)</label>
                <input
                  id="ask-hours"
                  className="input"
                  type="number"
                  min={1}
                  max={40}
                  value={askHours}
                  onChange={(e) => setAskHours(e.target.value)}
                />
              </div>
            </div>
            <div className="row">
              <button
                type="submit"
                className="btn btn--primary"
                disabled={busy}
              >
                <Icon name="send" size={16} /> Send request
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setAskOpen(false)}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {/* Team roster */}
      <div className="card">
        <div className="card__head">
          <h2>Team</h2>
          <span className="muted small">
            {plural(roster.length, 'person', 'people')}
          </span>
        </div>
        {roster.map((row) => {
          const u = userMap.get(row.userId);
          const mem = reqs.find(
            (r) =>
              r.from_user_id === row.userId && r.status === 'accepted',
          );
          const detail = mem
            ? [mem.role, mem.hours ? `${mem.hours} h per week` : '']
                .filter(Boolean)
                .join(' · ')
            : '';
          const label =
            me?.id === row.userId ? `${nameOf(row.userId)} (you)` : nameOf(row.userId);
          return (
            <div key={row.userId} className="dv-row">
              <Avatar name={label} avatar={u?.avatar ?? 1} />
              <div className="dv-row__main">
                <strong>{label}</strong>
                <div className="muted small">
                  {row.label}
                  {detail ? ` · ${detail}` : ''}
                  {mem
                    ? ` · joined ${fmtDate(mem.decided_at || mem.created_at)}`
                    : ''}
                </div>
              </div>
            </div>
          );
        })}
        <p className="muted small" style={{ marginTop: 10 }}>
          {open
            ? `Requests go to the author${idea.owner_id ? '. The author can see them too' : ''}. A team lead or administrator can also answer.`
            : `This idea is ${statusLabel.toLowerCase()} and is not taking new collaborators.`}
        </p>
        {mgr && open ? (
          <div className="row" style={{ marginTop: 8 }}>
            <label className="switch">
              <input
                type="checkbox"
                checked={looking}
                onChange={async (e) => {
                  const on = e.target.checked;
                  if (on) {
                    const skills = await dialog.prompt({
                      title: 'Skills wanted',
                      label: 'Skills wanted (optional)',
                      defaultValue: skillsWanted,
                    });
                    if (skills !== null) setSkillsWanted(skills);
                  }
                  setLooking(on);
                }}
              />
              <span className="switch__track" />
              <span>
                <strong>Looking for collaborators</strong>
                <br />
                <span className="muted small">
                  {looking
                    ? skillsWanted
                      ? `Skills wanted: ${skillsWanted}`
                      : 'No skills listed.'
                    : 'Show a chip on the idea and in Explore.'}
                </span>
              </span>
            </label>
          </div>
        ) : looking && open ? (
          <p className="small" style={{ marginTop: 8 }}>
            <Pill label="Looking for collaborators" tone="brand" icon="users" />{' '}
            {skillsWanted ? `Skills wanted: ${skillsWanted}` : ''}
          </p>
        ) : null}
      </div>

      {/* Collaboration requests */}
      {open && (pending.length > 0 || history.length > 0) ? (
        <div className="card">
          <div className="card__head">
            <h2>Collaboration requests</h2>
            <span className="muted small">
              {seesReqs
                ? plural(pending.length, 'pending request')
                : `${plural(pending.length, 'request')} waiting`}
            </span>
          </div>
          {seesReqs ? (
            pending.length ? (
              pending.map((r) => {
                const u = userMap.get(r.from_user_id);
                const canAct = canDecide && r.from_user_id !== me?.id;
                return (
                  <div key={r.id} className="req">
                    <div
                      className="row"
                      style={{ gap: 10, alignItems: 'flex-start' }}
                    >
                      <Avatar
                        name={u?.name ?? nameOf(r.from_user_id)}
                        avatar={u?.avatar ?? 1}
                      />
                      <div className="grow" style={{ minWidth: 0 }}>
                        <div className="row" style={{ gap: 6 }}>
                          <strong>{nameOf(r.from_user_id)}</strong>
                          <Pill
                            label={
                              COLLAB_TYPE_LABEL[r.type]?.label ?? r.type
                            }
                            tone={COLLAB_TYPE_LABEL[r.type]?.tone ?? ''}
                            icon={r.type === 'coauthor' ? 'edit' : 'hand'}
                          />
                          {r.hours ? (
                            <Pill
                              label={`${r.hours} h per week`}
                              icon="clock"
                            />
                          ) : null}
                          <span className="muted small">
                            {relTime(r.created_at)}
                          </span>
                        </div>
                        <div className="muted small">
                          {u?.title ?? ''}
                          {r.role ? ` · ${r.role}` : ''}
                        </div>
                        <div className="req__msg">{r.message}</div>
                      </div>
                    </div>
                    {canAct ? (
                      <div className="row" style={{ marginTop: 8 }}>
                        <button
                          type="button"
                          className="btn btn--sm btn--primary"
                          disabled={busy}
                          onClick={() => void decide(r.id, true)}
                        >
                          <Icon name="check" size={14} /> Accept
                        </button>
                        <button
                          type="button"
                          className="btn btn--sm"
                          disabled={busy}
                          onClick={() => void decide(r.id, false)}
                        >
                          Decline
                        </button>
                      </div>
                    ) : null}
                  </div>
                );
              })
            ) : (
              <p className="muted small">No requests are waiting.</p>
            )
          ) : (
            <p className="muted small">
              {plural(pending.length, 'request')} waiting for the author
              {idea.owner_id ? ' or owner' : ''}.
            </p>
          )}
          {seesReqs && !canDecide && pending.length ? (
            <p className="muted small">
              Only the author, a team lead or an administrator can answer.
            </p>
          ) : null}
          {seesReqs && history.length ? (
            <details style={{ marginTop: 12 }}>
              <summary className="small strong">
                Earlier requests ({history.length})
              </summary>
              {history.map((r) => (
                <div key={r.id} className="dv-row">
                  <div className="dv-row__main">
                    <div className="small">
                      <strong>{nameOf(r.from_user_id)}</strong>{' '}
                      <Pill
                        label={COLLAB_TYPE_LABEL[r.type]?.label ?? r.type}
                        tone={COLLAB_TYPE_LABEL[r.type]?.tone ?? ''}
                      />{' '}
                      <Pill
                        label={r.status}
                        tone={COLLAB_STATUS_TONE[r.status] ?? ''}
                      />{' '}
                      <span className="muted">
                        {fmtDate(r.decided_at || r.created_at)}
                      </span>
                    </div>
                    {r.note ? (
                      <div className="muted small">“{r.note}”</div>
                    ) : null}
                  </div>
                </div>
              ))}
            </details>
          ) : null}
        </div>
      ) : null}

      {/* Progress / milestones */}
      <div className="card">
        <div className="card__head">
          <h2>Progress</h2>
          {milestones.length ? (
            <Pill
              label={`${pct}% done`}
              tone={pct === 100 ? 'success' : 'brand'}
            />
          ) : null}
        </div>
        {!trackable ? (
          <div className="notice" style={{ marginBottom: 10 }}>
            <Icon name="lock" size={16} />
            <span>
              The tracker is read-only because this idea is{' '}
              {statusLabel.toLowerCase()}. Everything stays visible for the
              record.
            </span>
          </div>
        ) : !canWork ? (
          <div className="notice" style={{ marginBottom: 10 }}>
            <Icon name="lock" size={16} />
            <span>
              You can read the tracker. Only accepted team members can change
              it
              {askKind === 'can' ? '. Send a request above to join' : ''}.
            </span>
          </div>
        ) : null}

        {milestones.length ? (
          <>
            <div
              className="meter"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={pct}
              style={{ marginBottom: 8 }}
            >
              <i style={{ width: `${pct}%` }} />
            </div>
            <div
              className="row small"
              style={{ gap: 6, marginBottom: 8 }}
            >
              <Pill label={`${done} done`} tone="success" />
              <Pill label={`${inProg} in progress`} tone="brand" />
              <Pill label={`${notStarted} not started`} />
              {blocked ? (
                <Pill label={`${blocked} blocked`} tone="danger" icon="alert" />
              ) : null}
              {overdue ? (
                <Pill
                  label={`${overdue} overdue`}
                  tone="warning"
                  icon="clock"
                />
              ) : null}
            </div>
          </>
        ) : null}

        {canWork && myMs.length ? (
          <>
            <div className="myw">
              <div
                className="eyebrow eyebrow--plain"
                style={{ marginBottom: 6 }}
              >
                My work on this idea
              </div>
              {myMs.map((m) => msRow(m, true))}
            </div>
            <h3 style={{ margin: '14px 0 6px' }}>All milestones</h3>
          </>
        ) : null}

        {milestones.length ? (
          milestones.map((m) => msRow(m))
        ) : (
          <p className="muted small">
            {canWork
              ? 'No milestones yet. Add the first step below.'
              : 'No milestones yet. Accepted team members add them here.'}
          </p>
        )}

        {canWork && trackable ? (
          <form
            className="inline-form"
            style={{ marginTop: 12 }}
            onSubmit={addMilestone}
          >
            <div className="field" style={{ flex: '2 1 220px' }}>
              <label htmlFor="tm-title">Add a milestone</label>
              <input
                className="input"
                id="tm-title"
                value={msTitle}
                onChange={(e) => setMsTitle(e.target.value)}
                maxLength={160}
                placeholder="For example: Collect one piece of evidence"
                required
              />
            </div>
            <div className="field" style={{ flex: '1 1 150px' }}>
              <label htmlFor="tm-who">Assigned to</label>
              <select
                className="select"
                id="tm-who"
                value={msWho}
                onChange={(e) => setMsWho(e.target.value)}
              >
                {roster.map((r) => (
                  <option key={r.userId} value={r.userId}>
                    {me?.id === r.userId
                      ? `${nameOf(r.userId)} (you)`
                      : nameOf(r.userId)}
                  </option>
                ))}
              </select>
            </div>
            <div className="field" style={{ flex: '0 1 150px' }}>
              <label htmlFor="tm-due">Due (optional)</label>
              <input
                className="input"
                id="tm-due"
                type="date"
                value={msDue}
                onChange={(e) => setMsDue(e.target.value)}
              />
            </div>
            <button
              type="submit"
              className="btn btn--primary btn--sm"
              disabled={busy}
            >
              <Icon name="plus" size={14} /> Add
            </button>
          </form>
        ) : null}
      </div>

      {/* Check-ins */}
      <div className="card">
        <div className="card__head">
          <h2>Check-ins</h2>
          <span className="muted small">
            {plural(checkins.length, 'note')}
          </span>
        </div>
        {canWork && trackable ? (
          <form onSubmit={postCheckin}>
            <div className="field">
              <label htmlFor="tc-text">Post a check-in</label>
              <textarea
                className="textarea"
                id="tc-text"
                value={checkinBody}
                onChange={(e) => setCheckinBody(e.target.value)}
                maxLength={600}
                placeholder="What moved, what is blocked, what comes next"
                required
              />
            </div>
            <div className="inline-form">
              <button
                type="submit"
                className="btn btn--primary btn--sm"
                disabled={busy}
              >
                <Icon name="send" size={14} /> Post check-in
              </button>
            </div>
          </form>
        ) : null}
        {checkins.length ? (
          <div style={{ marginTop: 12 }}>
            {checkins.map((c) => (
              <div key={c.id} className="dv-row">
                <div className="dv-row__main upd">
                  <div className="muted small">
                    <strong>{nameOf(c.author_id)}</strong> ·{' '}
                    {new Date(c.created_at).toLocaleString()}
                    {c.percent_complete != null
                      ? ` · ${c.percent_complete}%`
                      : ''}
                  </div>
                  <div>{c.body}</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted small" style={{ marginTop: 12 }}>
            No check-ins yet.
          </p>
        )}
      </div>

    </div>
  );
}
