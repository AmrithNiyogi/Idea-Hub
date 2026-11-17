/**
 * Delivery tab for Idea Detail — matches idea-hub.html `ideaDelivery` density:
 * hours pool/request/approve, team, tasks, updates feed, impact/outcome.
 */

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { deliveryApi } from '../api/delivery';
import { usersApi } from '../api/users';
import { useAuth } from '../auth/AuthProvider';
import { Avatar, Icon } from '../components/Icons';
import { fmtDate, relTime } from '../utils/format';
import type { DeliveryDetail } from '../types/delivery';
import type { Idea } from '../types/idea';
import type { User } from '../types/auth';

const CONTRIB_ROLES = [
  'Builder',
  'Reviewer',
  'Tester',
  'Designer',
  'Advisor',
];

const IMPACT_LABELS: Record<string, string> = {
  hours_saved: 'Hours saved per month',
  revenue: 'Revenue influenced per month',
  cost_avoided: 'Cost avoided per month',
  other: 'Other measured impact',
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

function fmtNum(n: number) {
  return (Math.round(n * 100) / 100).toLocaleString('en-US');
}

function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function plural(n: number, one: string, many?: string) {
  return `${n} ${n === 1 ? one : many ?? `${one}s`}`;
}

type Props = { idea: Idea };

export function DeliveryTab({ idea }: Props) {
  const { user: me } = useAuth();
  const [data, setData] = useState<DeliveryDetail | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [hours, setHours] = useState(
    String(idea.hours_recommended ?? 40),
  );
  const [justification, setJustification] = useState('');
  const [logHours, setLogHours] = useState('');
  const [logDate, setLogDate] = useState(todayStr());
  const [logNote, setLogNote] = useState('');
  const [updateBody, setUpdateBody] = useState('');
  const [addUserId, setAddUserId] = useState('');
  const [addRole, setAddRole] = useState(CONTRIB_ROLES[0]);

  const userMap = useMemo(() => {
    const m = new Map<string, User>();
    users.forEach((u) => m.set(u.id, u));
    return m;
  }, [users]);

  const nameOf = useCallback(
    (id: string | null | undefined) => {
      if (!id) return 'Someone';
      if (me && id === me.id) return 'You';
      return userMap.get(id)?.name ?? id.slice(0, 8);
    },
    [me, userMap],
  );

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [d, u] = await Promise.all([
        deliveryApi.get(idea.id),
        usersApi.list().catch(() => [] as User[]),
      ]);
      setData(d);
      setUsers(u);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load delivery');
    }
  }, [idea.id]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const isOwner = me?.id === idea.owner_id;
  const isLeadOrAdmin = ['lead', 'admin', 'leadership'].includes(
    me?.active_role ?? '',
  );
  const canReq = (isOwner || isLeadOrAdmin) && idea.status === 'accepted';
  const canDecideHours = isLeadOrAdmin;
  const canEdit =
    !!data?.project_id &&
    (isOwner ||
      isLeadOrAdmin ||
      data.contributors.some((c) => c.user_id === me?.id));
  const canManage = isOwner || isLeadOrAdmin;

  async function onRequestHours(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await deliveryApi.requestHours(idea.id, {
        hours: Number(hours),
        justification: justification.trim(),
      });
      setJustification('');
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  }

  async function decide(approve: boolean) {
    if (!data?.pending_request) return;
    let reason = '';
    if (!approve) {
      reason =
        window.prompt('Reason for declining (min 10 chars)') || '';
      if (reason.trim().length < 10) {
        setError('A reason of at least 10 characters is required.');
        return;
      }
    }
    setBusy(true);
    try {
      await deliveryApi.decideHours(data.pending_request.id, {
        approve,
        reason,
        hours: data.pending_request.hours,
      });
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Decision failed');
    } finally {
      setBusy(false);
    }
  }

  async function onLogHours(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await deliveryApi.logHours(idea.id, {
        hours: Number(logHours),
        work_date: logDate,
        note: logNote.trim(),
      });
      setLogHours('');
      setLogNote('');
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Log failed');
    } finally {
      setBusy(false);
    }
  }

  async function onToggleTask(taskId: string, status: string) {
    const next = status === 'done' ? 'not_started' : 'done';
    setBusy(true);
    try {
      await deliveryApi.setTaskStatus(taskId, { status: next });
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Task update failed');
    } finally {
      setBusy(false);
    }
  }

  async function onPostUpdate(e: FormEvent) {
    e.preventDefault();
    if (updateBody.trim().length < 3) return;
    setBusy(true);
    try {
      await deliveryApi.postUpdate(idea.id, updateBody.trim());
      setUpdateBody('');
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setBusy(false);
    }
  }

  async function onAddContributor(e: FormEvent) {
    e.preventDefault();
    if (!addUserId) return;
    setBusy(true);
    try {
      await deliveryApi.addContributor(idea.id, addUserId, addRole);
      setAddUserId('');
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Add failed');
    } finally {
      setBusy(false);
    }
  }

  async function onRemoveContributor(userId: string) {
    if (!window.confirm('Remove this contributor from the delivery team?'))
      return;
    setBusy(true);
    try {
      await deliveryApi.removeContributor(idea.id, userId);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Remove failed');
    } finally {
      setBusy(false);
    }
  }

  async function onVerify(entryId: string) {
    const note =
      window.prompt('What did you check? (min 10 characters)') || '';
    if (note.trim().length < 10) return;
    setBusy(true);
    try {
      await deliveryApi.verifyImpact(idea.id, entryId, note.trim());
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verify failed');
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <p className="muted">{error}</p>;
  if (!data) return <p className="muted">Loading delivery…</p>;

  const owner = idea.owner_id ? userMap.get(idea.owner_id) : null;
  const pool = data.pool;
  const pend = data.pending_request;

  /* Pre-project: accepted / not yet granted hours */
  if (!data.project_id) {
    if (idea.status !== 'accepted' && idea.status !== 'prototype') {
      return (
        <div className="card">
          {error ? (
            <div className="notice notice--danger" role="alert">
              <Icon name="alert" size={16} />
              <span>{error}</span>
            </div>
          ) : null}
          <div className="empty" style={{ padding: 24 }}>
            <Icon name="layers" size={28} />
            <h3>Delivery starts after acceptance</h3>
            <p className="muted">
              Delivery begins once the idea is accepted, has an owner and
              leadership grants innovation hours. Until then there is nothing
              to track here.
            </p>
          </div>
        </div>
      );
    }

    const headPill = pend
      ? { label: 'Waiting for leadership', tone: 'warning' }
      : { label: 'Not requested', tone: '' };

    return (
      <div className="card">
        {error ? (
          <div className="notice notice--danger" role="alert">
            <Icon name="alert" size={16} />
            <span>{error}</span>
          </div>
        ) : null}
        <div className="card__head">
          <h2>Innovation hours</h2>
          <Pill label={headPill.label} tone={headPill.tone} />
        </div>
        <p>
          {owner
            ? `${owner.name} owns this idea.`
            : 'This idea has no owner yet. An owner must be assigned before hours can be requested.'}{' '}
          The reviewers recommended{' '}
          <strong>
            {idea.hours_recommended
              ? `${idea.hours_recommended} hours`
              : 'no specific number of hours'}
          </strong>
          . When leadership approves, the idea moves to Prototype and delivery
          tracking opens here.
        </p>

        {pend ? (
          <div className="dv-row" style={{ marginTop: 8 }}>
            <div className="dv-row__main">
              <div className="muted small">
                {nameOf(pend.requested_by)} requested{' '}
                <span className="mono strong" style={{ color: 'var(--text)' }}>
                  {pend.hours} h
                </span>
                {idea.hours_recommended
                  ? ` (panel recommended ${idea.hours_recommended})`
                  : ''}{' '}
                · {relTime(pend.created_at)}
              </div>
              <div className="quote" style={{ marginTop: 6 }}>
                {pend.justification}
              </div>
            </div>
            {canDecideHours && pend.requested_by !== me?.id ? (
              <div className="dv-row__act row" style={{ gap: 6 }}>
                <button
                  type="button"
                  className="btn btn--sm btn--primary"
                  disabled={busy}
                  onClick={() => void decide(true)}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="btn btn--sm"
                  disabled={busy}
                  onClick={() => void decide(false)}
                >
                  Decline
                </button>
              </div>
            ) : null}
          </div>
        ) : null}

        {canReq && !pend ? (
          <form className="stack" style={{ marginTop: 12 }} onSubmit={onRequestHours}>
            <div className="inline-form" style={{ marginTop: 0 }}>
              <div className="field" style={{ flex: '0 0 120px' }}>
                <label htmlFor="del-hours">Hours</label>
                <input
                  id="del-hours"
                  className="input"
                  type="number"
                  min={1}
                  max={400}
                  value={hours}
                  onChange={(e) => setHours(e.target.value)}
                  required
                />
              </div>
              <div className="field" style={{ flex: '1 1 220px' }}>
                <label htmlFor="del-just">Justification</label>
                <textarea
                  id="del-just"
                  className="textarea"
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  minLength={10}
                  required
                  placeholder="What the hours buy, who works on it and by when"
                  rows={2}
                />
              </div>
            </div>
            <div className="row">
              <button
                type="submit"
                className="btn btn--primary"
                disabled={busy}
              >
                <Icon name="clock" size={16} /> Request innovation hours
              </button>
            </div>
          </form>
        ) : !pend && owner && !canReq ? (
          <p className="muted small" style={{ marginTop: 8 }}>
            Only {owner.name}, a team lead or an administrator can request
            hours.
          </p>
        ) : null}

        {canDecideHours && pool ? (
          <div className="pool" style={{ marginTop: 16 }}>
            <div className="row row--between">
              <strong>Innovation pool</strong>
              <span className="muted small">
                {pool.budget_hours} hours this quarter
              </span>
            </div>
            <div
              className={`meter${pool.remaining < 0 ? ' meter--over' : pool.remaining < pool.budget_hours * 0.15 ? ' meter--warn' : ''}`}
              role="progressbar"
              style={{ margin: '8px 0' }}
            >
              <i
                style={{
                  width: `${Math.min(100, Math.round((100 * pool.granted_hours) / Math.max(1, pool.budget_hours)))}%`,
                }}
              />
            </div>
            <div className="mini-kpis">
              <div>
                <div className="kpi__label">Granted</div>
                <div className="kpi__value kpi__value--sm">
                  {pool.granted_hours}
                </div>
              </div>
              <div>
                <div className="kpi__label">Remaining</div>
                <div className="kpi__value kpi__value--sm">
                  {pool.remaining}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  /* Active delivery project */
  const granted = data.hours_granted ?? 0;
  const logged = data.hours_logged;
  const over = logged > granted;
  const pct = Math.min(
    100,
    Math.round((100 * logged) / Math.max(1, granted)),
  );
  const tasksDone = data.tasks.filter((t) => t.status === 'done').length;
  const lastUpdate = data.updates[0]?.created_at;
  const peopleForAdd = users.filter(
    (u) =>
      u.id !== idea.owner_id &&
      !data.contributors.some((c) => c.user_id === u.id),
  );

  return (
    <div className="stack">
      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={16} />
          <span>{error}</span>
        </div>
      ) : null}

      {!canEdit && idea.status === 'prototype' ? (
        <div className="notice">
          <Icon name="lock" size={16} />
          <span>
            You are viewing this delivery record read-only. Accepted team
            members, team leads and administrators can edit it.
          </span>
        </div>
      ) : null}

      {idea.status === 'implemented' ? (
        <>
          <div className="card">
            <div className="card__head">
              <h2>Outcome</h2>
              <Pill
                label={`Implemented ${fmtDate(data.implemented_at, true)}`}
                tone="success"
                icon="check"
              />
            </div>
            <p style={{ overflowWrap: 'anywhere' }}>
              {data.outcome || '—'}
            </p>
          </div>
          <div className="card">
            <div className="card__head">
              <h2>Measured impact</h2>
              <span className="muted small">
                {plural(
                  data.impact.filter((e) => e.verified_at).length,
                  'entry',
                  'entries',
                )}{' '}
                verified of {data.impact.length}
              </span>
            </div>
            {data.impact.length === 0 ? (
              <p className="muted small">No impact entries recorded.</p>
            ) : (
              data.impact.map((e) => (
                <div key={e.id} className="dv-row">
                  <div className="dv-row__main">
                    <div className="row" style={{ gap: 6 }}>
                      <strong>
                        {IMPACT_LABELS[e.impact_type] ?? e.impact_type}
                      </strong>
                      {e.verified_at ? (
                        <Pill label="Verified" tone="success" icon="check" />
                      ) : (
                        <Pill label="Not yet verified" tone="warning" />
                      )}
                      <Pill label={`${e.confidence} confidence`} />
                    </div>
                    <div style={{ marginTop: 4 }}>
                      <span className="mono strong">
                        {fmtNum(e.value)}
                        {e.unit ? ` ${e.unit}` : ''}
                      </span>{' '}
                      <span className="muted small">
                        against a baseline of {fmtNum(e.baseline)}
                      </span>
                    </div>
                    <div className="muted small" style={{ marginTop: 4 }}>
                      Evidence: {e.evidence}
                    </div>
                    {e.verified_at ? (
                      <div className="small" style={{ marginTop: 4 }}>
                        <strong>
                          Verified by {nameOf(e.verified_by)}
                        </strong>{' '}
                        on {fmtDate(e.verified_at, true)}
                        {e.verify_note ? `: ${e.verify_note}` : ''}
                      </div>
                    ) : null}
                  </div>
                  {!e.verified_at && canDecideHours ? (
                    <div className="dv-row__act">
                      <button
                        type="button"
                        className="btn btn--sm"
                        disabled={busy}
                        onClick={() => void onVerify(e.id)}
                      >
                        <Icon name="check" size={14} /> Verify
                      </button>
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </div>
          {data.shares.length ? (
            <div className="card">
              <div className="card__head">
                <h2>Who is credited</h2>
                <span className="muted small">
                  Shares add up to{' '}
                  {Math.round(
                    data.shares.reduce((a, x) => a + x.pct, 0),
                  )}
                  %
                </span>
              </div>
              {data.shares.map((x) => {
                const u = userMap.get(x.user_id);
                return (
                  <div key={x.user_id} className="dv-row">
                    <Avatar
                      name={nameOf(x.user_id)}
                      avatar={u?.avatar ?? 1}
                    />
                    <div className="dv-row__main">
                      <strong>{nameOf(x.user_id)}</strong>
                      <div className="muted small">
                        {x.roles.join(', ')}
                      </div>
                    </div>
                    <span className="mono strong">{x.pct}%</span>
                  </div>
                );
              })}
            </div>
          ) : null}
        </>
      ) : null}

      <div className="dv-grid">
        <div className="card">
          <div className="card__head">
            <h2>Innovation hours</h2>
            {over ? (
              <Pill
                label={`Over budget by ${fmtNum(logged - granted)} h`}
                tone="danger"
                icon="alert"
              />
            ) : (
              <Pill
                label={`${fmtNum(granted - logged)} h left`}
                tone="success"
              />
            )}
          </div>
          <div className="row row--between">
            <span>
              <span className="kpi__value kpi__value--sm">
                {fmtNum(logged)}
              </span>{' '}
              <span className="muted">logged of {granted} granted</span>
            </span>
          </div>
          <div
            className={`meter${over ? ' meter--over' : pct >= 90 ? ' meter--warn' : ''}`}
            role="progressbar"
            style={{ margin: '8px 0 4px' }}
          >
            <i style={{ width: `${pct}%` }} />
          </div>
          <p className="muted small">
            Going over is flagged, not blocked.
          </p>
          {canEdit ? (
            <form onSubmit={onLogHours} style={{ marginTop: 12 }}>
              <div className="inline-form" style={{ marginTop: 0 }}>
                <div className="field" style={{ flex: '0 0 90px' }}>
                  <label htmlFor="dl-hours">Hours</label>
                  <input
                    className="input"
                    id="dl-hours"
                    type="number"
                    step={0.25}
                    min={0.25}
                    max={80}
                    value={logHours}
                    onChange={(e) => setLogHours(e.target.value)}
                    placeholder="2.5"
                    required
                  />
                </div>
                <div className="field" style={{ flex: '0 0 150px' }}>
                  <label htmlFor="dl-date">Date</label>
                  <input
                    className="input"
                    id="dl-date"
                    type="date"
                    value={logDate}
                    max={todayStr()}
                    onChange={(e) => setLogDate(e.target.value)}
                    required
                  />
                </div>
                <div className="field" style={{ flex: '1 1 160px' }}>
                  <label htmlFor="dl-note">What was it spent on?</label>
                  <input
                    className="input"
                    id="dl-note"
                    type="text"
                    maxLength={200}
                    value={logNote}
                    onChange={(e) => setLogNote(e.target.value)}
                    placeholder="Wrote the sync job"
                    required
                  />
                </div>
              </div>
              <div className="row" style={{ marginTop: 8 }}>
                <button
                  type="submit"
                  className="btn btn--primary btn--sm"
                  disabled={busy}
                >
                  <Icon name="plus" size={14} /> Log hours
                </button>
              </div>
            </form>
          ) : null}
          {data.hour_logs.length ? (
            <div style={{ marginTop: 12 }}>
              {data.hour_logs.slice(0, 6).map((h) => (
                <div key={h.id} className="dv-row">
                  <div className="dv-row__main">
                    <span className="mono strong">{fmtNum(h.hours)} h</span>{' '}
                    <span className="muted small">
                      {fmtDate(h.work_date)} · {nameOf(h.user_id)}
                    </span>
                    <div className="small">{h.note}</div>
                  </div>
                </div>
              ))}
              {data.hour_logs.length > 6 ? (
                <p className="muted small">
                  and {data.hour_logs.length - 6} earlier entries
                </p>
              ) : null}
            </div>
          ) : (
            <p className="muted small" style={{ marginTop: 12 }}>
              No hours logged yet.
            </p>
          )}
        </div>

        <div className="card">
          <div className="card__head">
            <h2>Team</h2>
            <span className="muted small">
              {plural(data.contributors.length + (idea.owner_id ? 1 : 0), 'person', 'people')}
            </span>
          </div>
          {idea.owner_id ? (
            <div className="dv-row">
              <Avatar
                name={nameOf(idea.owner_id)}
                avatar={owner?.avatar ?? 1}
              />
              <div className="dv-row__main">
                <strong>{nameOf(idea.owner_id)}</strong>
                <div className="muted small">Owner</div>
              </div>
            </div>
          ) : null}
          {data.contributors.map((c) => {
            const u = userMap.get(c.user_id);
            return (
              <div key={c.user_id} className="dv-row">
                <Avatar name={nameOf(c.user_id)} avatar={u?.avatar ?? 1} />
                <div className="dv-row__main">
                  <strong>{nameOf(c.user_id)}</strong>
                  <div className="muted small">
                    {c.role} · added {fmtDate(c.added_at)}
                  </div>
                </div>
                {canManage ? (
                  <div className="dv-row__act">
                    <button
                      type="button"
                      className="btn btn--sm btn--ghost"
                      disabled={busy}
                      aria-label={`Remove ${nameOf(c.user_id)}`}
                      onClick={() => void onRemoveContributor(c.user_id)}
                    >
                      <Icon name="x" size={14} /> Remove
                    </button>
                  </div>
                ) : null}
              </div>
            );
          })}
          <p className="small" style={{ marginTop: 12 }}>
            <Icon name="users" size={14} /> Manage collaboration requests on the{' '}
            <Link to={`/ideas/${idea.id}?tab=team`}>Team and progress</Link>{' '}
            tab.
          </p>
          {canManage ? (
            <form
              onSubmit={onAddContributor}
              style={{ marginTop: 12 }}
            >
              <div className="inline-form" style={{ marginTop: 0 }}>
                <div className="field" style={{ flex: '1 1 150px' }}>
                  <label htmlFor="dl-cuser">Add a contributor</label>
                  <select
                    className="select"
                    id="dl-cuser"
                    value={addUserId}
                    onChange={(e) => setAddUserId(e.target.value)}
                    required
                  >
                    <option value="">Choose a person</option>
                    {peopleForAdd.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field" style={{ flex: '0 0 120px' }}>
                  <label htmlFor="dl-crole">Role</label>
                  <select
                    className="select"
                    id="dl-crole"
                    value={addRole}
                    onChange={(e) => setAddRole(e.target.value)}
                  >
                    {CONTRIB_ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="row" style={{ marginTop: 8 }}>
                <button
                  type="submit"
                  className="btn btn--sm btn--primary"
                  disabled={busy}
                >
                  <Icon name="plus" size={14} /> Add
                </button>
              </div>
            </form>
          ) : null}
        </div>
      </div>

      <div className="card dv-section">
        <div className="card__head">
          <h2>Tasks and milestones</h2>
          <span className="muted small">
            {tasksDone} of {data.tasks.length} done ·{' '}
            <Link to={`/ideas/${idea.id}?tab=team`}>Team and progress</Link>
          </span>
        </div>
        <p className="muted small" style={{ marginBottom: 8 }}>
          Delivery tasks for this prototype. Tracker milestones live on the Team
          and progress tab.
        </p>
        {data.tasks.length === 0 ? (
          <p className="muted small">No tasks yet.</p>
        ) : (
          data.tasks.map((t) => (
            <div key={t.id} className={`ms ms--${t.status}`}>
              <div className="ms__main">
                <div className="row" style={{ gap: 6 }}>
                  <strong className="ms__title">{t.title}</strong>
                  <Pill
                    label={
                      t.status === 'done'
                        ? 'Done'
                        : t.status === 'blocked'
                          ? 'Blocked'
                          : t.status === 'in_progress'
                            ? 'In progress'
                            : 'Not started'
                    }
                    tone={
                      t.status === 'done'
                        ? 'success'
                        : t.status === 'blocked'
                          ? 'danger'
                          : t.status === 'in_progress'
                            ? 'brand'
                            : ''
                    }
                  />
                </div>
                {t.status === 'blocked' && t.blocker ? (
                  <div className="ms__blocker small">
                    <Icon name="alert" size={14} />
                    <span>{t.blocker}</span>
                  </div>
                ) : null}
                <div className="meta-row small">
                  <span className="muted">Assigned to</span>
                  {t.assignee_id ? (
                    <span className="person">
                      {nameOf(t.assignee_id)}
                    </span>
                  ) : (
                    <span className="muted">Unassigned</span>
                  )}
                </div>
              </div>
              <div className="ms__act">
                {canEdit ? (
                  <button
                    type="button"
                    className={`btn btn--sm${t.status !== 'done' ? ' btn--primary' : ''}`}
                    disabled={busy}
                    onClick={() => void onToggleTask(t.id, t.status)}
                  >
                    <Icon
                      name={t.status === 'done' ? 'refresh' : 'check'}
                      size={14}
                    />{' '}
                    {t.status === 'done' ? 'Reopen' : 'Mark done'}
                  </button>
                ) : null}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="card dv-section">
        <div className="card__head">
          <h2>Implementation updates</h2>
          {lastUpdate ? (
            <Pill label={`Last update ${relTime(lastUpdate)}`} />
          ) : (
            <Pill label="No updates yet" tone="warning" icon="clock" />
          )}
        </div>
        {canEdit ? (
          <form onSubmit={onPostUpdate}>
            <div className="field">
              <label htmlFor="dp-text">Post a check-in</label>
              <textarea
                className="textarea"
                id="dp-text"
                value={updateBody}
                onChange={(e) => setUpdateBody(e.target.value)}
                maxLength={600}
                placeholder="What moved, what is blocked, what comes next"
                required
                minLength={3}
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
        {data.updates.length ? (
          <div style={{ marginTop: 12 }}>
            {data.updates.map((u) => (
              <div key={u.id} className="dv-row">
                <div className="dv-row__main upd">
                  <div className="muted small">
                    <strong>{nameOf(u.user_id)}</strong> ·{' '}
                    {new Date(u.created_at).toLocaleString()}
                  </div>
                  <div>{u.body}</div>
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

export default DeliveryTab;
