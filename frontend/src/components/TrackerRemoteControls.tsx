/**
 * Polished remote-field controls for live tracker tasks:
 * status pill menu, priority chips, due date, multi-assignee picker.
 */

import {
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
} from 'react';
import { Icon } from './Icons';
import type {
  LiveTrackerTask,
  RemoteAssignee,
  RemotePriorityOption,
  RemoteStatusOption,
} from '../types/trackers';

type Patch = {
  status?: string;
  priority?: string;
  due_date?: string;
  assignee_ids?: string[];
};

type Props = {
  task: LiveTrackerTask;
  busy?: boolean;
  onPatch: (patch: Patch) => void | Promise<void>;
};

function titleCase(s: string) {
  if (!s) return s;
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}

function statusStyle(color?: string): CSSProperties | undefined {
  if (!color) return undefined;
  return {
    ['--trk-accent' as string]: color,
    background: `color-mix(in srgb, ${color} 18%, var(--surface))`,
    color: 'var(--text)',
    borderColor: `color-mix(in srgb, ${color} 45%, var(--border))`,
  };
}

function priorityStyle(opt?: RemotePriorityOption | null): CSSProperties | undefined {
  if (!opt?.color) return undefined;
  const c = opt.color;
  // Skip non-color values (Jira sometimes returns icon URLs).
  if (c.startsWith('http')) return undefined;
  return {
    background: `color-mix(in srgb, ${c} 16%, var(--surface))`,
    borderColor: `color-mix(in srgb, ${c} 40%, var(--border))`,
    color: 'var(--text)',
  };
}

function AssigneeAvatar({ person, size = 22 }: { person: RemoteAssignee; size?: number }) {
  const initials = (person.name || person.email || '?')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('');
  if (person.avatar_url) {
    return (
      <img
        className="trk-avatar"
        src={person.avatar_url}
        alt=""
        width={size}
        height={size}
        style={{ width: size, height: size }}
      />
    );
  }
  return (
    <span
      className="trk-avatar trk-avatar--fallback"
      style={{ width: size, height: size, fontSize: size > 20 ? 10 : 9 }}
      aria-hidden
    >
      {initials || '?'}
    </span>
  );
}

function StatusMenu({
  status,
  color,
  options,
  disabled,
  onPick,
}: {
  status: string;
  color?: string;
  options: RemoteStatusOption[];
  disabled?: boolean;
  onPick: (name: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (!options.length && !status) return null;

  return (
    <div className="trk-menu" ref={rootRef}>
      <button
        type="button"
        className="trk-chip trk-chip--status"
        style={statusStyle(color)}
        disabled={disabled || !options.length}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((v) => !v)}
      >
        <i
          className="dot"
          style={color ? { background: color } : undefined}
          aria-hidden
        />
        <span>{status ? titleCase(status) : 'Status'}</span>
        {options.length ? <Icon name="chevronD" size={12} /> : null}
      </button>
      {open ? (
        <ul className="trk-menu__list" id={menuId} role="listbox">
          {options.map((o) => {
            const selected = o.name.toLowerCase() === status.toLowerCase();
            return (
              <li key={`${o.id}-${o.name}`} role="option" aria-selected={selected}>
                <button
                  type="button"
                  className={`trk-menu__opt${selected ? ' is-selected' : ''}`}
                  onClick={() => {
                    setOpen(false);
                    if (!selected) onPick(o.name);
                  }}
                >
                  <i
                    className="dot"
                    style={o.color ? { background: o.color } : undefined}
                    aria-hidden
                  />
                  {titleCase(o.name)}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

function AssigneePicker({
  selected,
  options,
  multi,
  disabled,
  onChange,
}: {
  selected: RemoteAssignee[];
  options: RemoteAssignee[];
  multi: boolean;
  disabled?: boolean;
  onChange: (ids: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const rootRef = useRef<HTMLDivElement>(null);
  const selectedIds = new Set(selected.map((a) => a.id));

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const filtered = options.filter((o) => {
    const hay = `${o.name} ${o.email}`.toLowerCase();
    return !q.trim() || hay.includes(q.trim().toLowerCase());
  });

  function toggle(id: string) {
    if (multi) {
      const next = new Set(selectedIds);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      onChange([...next]);
    } else {
      // Single-assignee (Jira): tap same id to unassign.
      onChange(selectedIds.has(id) ? [] : [id]);
      setOpen(false);
    }
  }

  return (
    <div className="trk-menu trk-assignees" ref={rootRef}>
      <button
        type="button"
        className="trk-chip trk-chip--assignees"
        disabled={disabled || (!options.length && !selected.length)}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {selected.length === 0 ? (
          <span className="muted">Unassigned</span>
        ) : (
          <span className="trk-assignees__stack">
            {selected.slice(0, 3).map((a) => (
              <AssigneeAvatar key={a.id} person={a} />
            ))}
            {selected.length > 3 ? (
              <span className="trk-avatar trk-avatar--more">+{selected.length - 3}</span>
            ) : null}
            <span className="trk-assignees__names">
              {selected
                .slice(0, 2)
                .map((a) => a.name || a.email)
                .join(', ')}
              {selected.length > 2 ? ` +${selected.length - 2}` : ''}
            </span>
          </span>
        )}
        <Icon name="chevronD" size={12} />
      </button>
      {open ? (
        <div className="trk-menu__panel">
          <input
            className="input trk-menu__search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search people…"
            autoFocus
          />
          <ul className="trk-menu__list trk-menu__list--scroll" role="listbox">
            {filtered.length === 0 ? (
              <li className="muted small" style={{ padding: '8px 10px' }}>
                No matches
              </li>
            ) : (
              filtered.map((o) => {
                const on = selectedIds.has(o.id);
                return (
                  <li key={o.id} role="option" aria-selected={on}>
                    <button
                      type="button"
                      className={`trk-menu__opt trk-menu__opt--person${on ? ' is-selected' : ''}`}
                      onClick={() => toggle(o.id)}
                    >
                      <AssigneeAvatar person={o} size={24} />
                      <span className="trk-menu__person">
                        <strong>{o.name || o.email || o.id}</strong>
                        {o.email ? (
                          <span className="muted small">{o.email}</span>
                        ) : null}
                        {o.idea_hub_user_id ? (
                          <span className="pill pill--brand" style={{ minHeight: 18, fontSize: 10 }}>
                            IdeaKonnekt
                          </span>
                        ) : null}
                      </span>
                      {on ? <Icon name="checkcircle" size={14} /> : null}
                    </button>
                  </li>
                );
              })
            )}
          </ul>
          {multi && selected.length > 0 ? (
            <button
              type="button"
              className="btn btn--sm btn--ghost trk-menu__clear"
              onClick={() => onChange([])}
            >
              Clear assignees
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function TrackerRemoteControls({ task, busy, onPatch }: Props) {
  const canEdit = Boolean(task.can_update ?? task.can_update_status) && task.live;
  const fields = new Set(task.editable_fields?.length ? task.editable_fields : ['status']);
  const showStatus =
    fields.has('status') &&
    (task.can_update_status
      ? task.status_options.length > 0 || !!task.status
      : !!task.status);
  const showPriority =
    fields.has('priority') &&
    (task.priority_options?.length > 0 || !!task.priority);
  const showDue = fields.has('due_date');
  const showAssignees =
    fields.has('assignees') &&
    ((task.assignable?.length ?? 0) > 0 || task.assignees.length > 0);

  const multiAssignees = task.provider_id !== 'jira';

  if (!showStatus && !showPriority && !showDue && !showAssignees) {
    return null;
  }

  return (
    <div className="trk-controls">
      {showStatus ? (
        <div className="trk-controls__group">
          <span className="trk-controls__label">Status</span>
          {canEdit && task.status_options.length > 0 ? (
            <StatusMenu
              status={task.status}
              color={task.status_color}
              options={task.status_options}
              disabled={busy}
              onPick={(name) => void onPatch({ status: name })}
            />
          ) : task.status ? (
            <span className="trk-chip trk-chip--status" style={statusStyle(task.status_color)}>
              <i
                className="dot"
                style={
                  task.status_color ? { background: task.status_color } : undefined
                }
                aria-hidden
              />
              {titleCase(task.status)}
            </span>
          ) : (
            <span className="muted small">—</span>
          )}
        </div>
      ) : null}

      {showPriority ? (
        <div className="trk-controls__group">
          <span className="trk-controls__label">Priority</span>
          {canEdit && (task.priority_options?.length ?? 0) > 0 ? (
            <div className="trk-priority-row" role="group" aria-label="Priority">
              {(task.priority_options ?? []).map((o) => {
                const active =
                  o.name.toLowerCase() === (task.priority || '').toLowerCase() ||
                  o.id === task.priority_id;
                return (
                  <button
                    key={`${o.id}-${o.name}`}
                    type="button"
                    className={`trk-chip trk-chip--priority${active ? ' is-active' : ''}`}
                    style={priorityStyle(o)}
                    disabled={busy}
                    aria-pressed={active}
                    onClick={() => {
                      if (active && task.provider_id === 'clickup') {
                        void onPatch({ priority: '' });
                      } else if (!active) {
                        void onPatch({ priority: o.name });
                      }
                    }}
                  >
                    <i
                      className="dot"
                      style={
                        o.color && !o.color.startsWith('http')
                          ? { background: o.color }
                          : undefined
                      }
                      aria-hidden
                    />
                    {titleCase(o.name)}
                  </button>
                );
              })}
            </div>
          ) : task.priority ? (
            <span className="trk-chip trk-chip--priority">
              <i className="dot" aria-hidden />
              {titleCase(task.priority)}
            </span>
          ) : (
            <span className="muted small">None</span>
          )}
        </div>
      ) : null}

      {showDue ? (
        <div className="trk-controls__group">
          <span className="trk-controls__label">Due</span>
          {canEdit ? (
            <div className="trk-due">
              <input
                type="date"
                className="input trk-due__input"
                value={task.due_date || ''}
                disabled={busy}
                onChange={(e) => void onPatch({ due_date: e.target.value })}
              />
              {task.due_date ? (
                <button
                  type="button"
                  className="btn btn--sm btn--ghost"
                  disabled={busy}
                  title="Clear due date"
                  onClick={() => void onPatch({ due_date: '' })}
                >
                  Clear
                </button>
              ) : null}
            </div>
          ) : (
            <span className="muted small">{task.due_date || '—'}</span>
          )}
        </div>
      ) : null}

      {showAssignees ? (
        <div className="trk-controls__group trk-controls__group--grow">
          <span className="trk-controls__label">Assignees</span>
          {canEdit ? (
            <AssigneePicker
              selected={task.assignees}
              options={
                (task.assignable?.length ? task.assignable : task.assignees) ?? []
              }
              multi={multiAssignees}
              disabled={busy}
              onChange={(ids) => void onPatch({ assignee_ids: ids })}
            />
          ) : task.assignees.length ? (
            <span className="trk-assignees__stack">
              {task.assignees.map((a) => (
                <span key={a.id} className="row" style={{ gap: 6 }}>
                  <AssigneeAvatar person={a} />
                  <span className="small">{a.name || a.email}</span>
                </span>
              ))}
            </span>
          ) : (
            <span className="muted small">Unassigned</span>
          )}
        </div>
      ) : null}
    </div>
  );
}
