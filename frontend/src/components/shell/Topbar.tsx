import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Avatar, Icon } from '../Icons';
import { useAuth } from '../../auth/AuthProvider';
import { useToast } from '../ToastProvider';
import { CAN_SUBMIT, roleLabel, sortRoles } from '../../constants/roles';
import type { Role } from '../../types/auth';
import { GlobalSearch } from './GlobalSearch';
import {
  fetchInbox,
  markAllNotifsRead,
  markNotifRead,
  type InboxItem,
} from '../../api/notifications';

type Popover = 'account' | 'notif' | null;

function relTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function Topbar({
  title,
  crumbs,
  theme,
  onToggleTheme,
  onOpenDrawer,
}: {
  title: string;
  crumbs?: Array<{ label: string; to?: string }>;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onOpenDrawer: () => void;
}) {
  const { user, logout, switchRole } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [popover, setPopover] = useState<Popover>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [inbox, setInbox] = useState<InboxItem[]>([]);
  const [inboxTick, setInboxTick] = useState(0);
  const popRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    fetchInbox(user.id, user.active_role as Role)
      .then((items) => {
        if (!cancelled) setInbox(items);
      })
      .catch(() => {
        if (!cancelled) setInbox([]);
      });
    return () => {
      cancelled = true;
    };
  }, [user, inboxTick]);

  // Soft refresh while authenticated so the badge stays honest.
  useEffect(() => {
    if (!user) return;
    const id = window.setInterval(() => setInboxTick((t) => t + 1), 60_000);
    return () => window.clearInterval(id);
  }, [user]);

  useEffect(() => {
    if (!popover) return;
    const onDoc = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) {
        setPopover(null);
      }
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [popover]);

  if (!user) return null;

  const others = sortRoles(user.roles).filter((r) => r !== user.active_role);
  const trail = crumbs && crumbs.length ? crumbs : [{ label: title }];
  const unread = inbox.filter((n) => !n.read).length;
  const canSubmit = CAN_SUBMIT.includes(user.active_role as Role);

  return (
    <header className="topbar">
      <button
        type="button"
        className="btn btn--ghost btn--icon"
        id="mobile-menu"
        aria-label="Open menu"
        onClick={onOpenDrawer}
      >
        <Icon name="menu" size={20} />
      </button>

      <div className="topbar__title" id="tb-title-wrap">
        <div className="crumbs" id="tb-title">
          {trail.map((c, i) => (
            <span key={`${c.label}-${i}`} style={{ display: 'contents' }}>
              {i > 0 ? <Icon name="chevronR" size={14} /> : null}
              {c.to && i < trail.length - 1 ? (
                <Link to={c.to}>{c.label}</Link>
              ) : (
                <span aria-current={i === trail.length - 1 ? 'page' : undefined}>
                  {c.label}
                </span>
              )}
            </span>
          ))}
        </div>
      </div>

      <GlobalSearch open={searchOpen} onOpenChange={setSearchOpen} />

      <div className="topbar__actions" id="tb-actions">
        {canSubmit ? (
          <Link
            className="btn btn--primary topbar__cta"
            to="/submit"
            title="Submit a new idea"
            aria-label="New idea"
          >
            <Icon name="spark" size={16} />
            <span className="topbar__cta-label">New idea</span>
          </Link>
        ) : null}

        <span
          className="role-chip"
          title={`${user.name}, working as ${roleLabel(user.active_role)}`}
        >
          <Icon name="user" size={14} />
          <span>
            <span className="role-chip__text-long">{user.name} · </span>
            <button
              type="button"
              className="role-chip__btn"
              style={{
                border: 0,
                background: 'transparent',
                color: 'inherit',
                font: 'inherit',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                padding: 0,
              }}
              onClick={() =>
                setPopover((p) => (p === 'account' ? null : 'account'))
              }
              aria-haspopup="true"
              aria-expanded={popover === 'account'}
            >
              {roleLabel(user.active_role)}
              <Icon name="chevronD" size={12} />
            </button>
          </span>
        </span>

        <button
          type="button"
          className="btn btn--ghost btn--icon"
          id="search-btn"
          aria-label="Search ideas, ideathons, teams and people"
          onClick={() => setSearchOpen(true)}
        >
          <Icon name="search" size={20} />
        </button>

        <button
          type="button"
          className="btn btn--ghost btn--icon"
          id="bell-btn"
          aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}
          aria-haspopup="true"
          aria-expanded={popover === 'notif'}
          style={{ position: 'relative' }}
          onClick={() => {
            setPopover((p) => (p === 'notif' ? null : 'notif'));
            setInboxTick((t) => t + 1);
          }}
        >
          <Icon name="bell" size={20} />
          {unread ? (
            <span
              className="nav-item__badge"
              style={{ position: 'absolute', top: 0, right: 0, margin: 0 }}
              aria-hidden="true"
            >
              {unread}
            </span>
          ) : null}
        </button>

        <button
          type="button"
          className="btn btn--ghost btn--icon"
          id="theme-btn"
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          onClick={onToggleTheme}
        >
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={20} />
        </button>

        <button
          type="button"
          className="btn btn--ghost btn--icon"
          aria-label={`Account menu. ${user.name}`}
          aria-haspopup="true"
          aria-expanded={popover === 'account'}
          onClick={() =>
            setPopover((p) => (p === 'account' ? null : 'account'))
          }
        >
          <Avatar
            name={user.name}
            avatar={user.avatar}
            avatarUrl={user.avatar_url}
          />
        </button>
      </div>

      {popover === 'notif' ? (
        <div
          ref={popRef}
          className="popover"
          role="dialog"
          aria-label="Notifications"
          id="popover"
        >
          <div className="popover__head">
            <h3>Notifications</h3>
            <button
              type="button"
              className="btn btn--sm btn--ghost"
              onClick={() => {
                void markAllNotifsRead(user.id).then(() =>
                  setInboxTick((t) => t + 1),
                );
              }}
            >
              Mark all read
            </button>
          </div>
          {inbox.length === 0 ? (
            <div className="empty" style={{ padding: 16 }}>
              <Icon name="bell" size={28} />
              <h3>Nothing yet</h3>
              <p className="muted">
                Follow ideas to get updates — decisions, questions and delivery
                milestones appear here.
              </p>
            </div>
          ) : (
            <ul>
              {inbox.slice(0, 20).map((n) => {
                const read = n.read;
                return (
                  <li key={n.id}>
                    <Link
                      className={`notif${read ? '' : ' notif--unread'}`}
                      to={n.href}
                      onClick={() => {
                        void markNotifRead(user.id, n.id).then(() => {
                          setPopover(null);
                          setInboxTick((t) => t + 1);
                        });
                      }}
                    >
                      <span className="notif__dot" aria-hidden="true" />
                      <span>
                        <span className="notif__text">{n.text}</span>
                        <span className="muted small">
                          {relTime(n.at)}
                          {read ? '' : ' · unread'}
                        </span>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : null}

      {popover === 'account' ? (
        <div
          ref={popRef}
          className="popover"
          role="dialog"
          aria-label="Account menu"
        >
          <div className="popover__head">
            <h3>Signed in</h3>
          </div>
          <div
            className="row"
            style={{
              padding: '12px 16px',
              borderBottom: '1px solid var(--border)',
            }}
          >
            <Avatar
              name={user.name}
              avatar={user.avatar}
              avatarUrl={user.avatar_url}
            />
            <span>
              <span className="strong">{user.name}</span>
              <br />
              <span className="muted small">Working as</span>{' '}
              <span className="pill pill--brand">
                {roleLabel(user.active_role)}
              </span>
            </span>
          </div>
          <ul>
            <li>
              <Link
                className="persona-item"
                to="/profile"
                onClick={() => setPopover(null)}
              >
                <Icon name="user" size={16} />
                <span>
                  <span className="strong">My profile</span>
                  <br />
                  <span className="muted small">Account settings</span>
                </span>
              </Link>
            </li>
            <li>
              <Link
                className="persona-item"
                to="/integrations"
                onClick={() => setPopover(null)}
              >
                <Icon name="layers" size={16} />
                <span>
                  <span className="strong">Integrations</span>
                  <br />
                  <span className="muted small">Trackers &amp; connections</span>
                </span>
              </Link>
            </li>
            <li>
              <Link
                className="persona-item"
                to={`/people/${user.id}`}
                onClick={() => setPopover(null)}
              >
                <Icon name="award" size={16} />
                <span>
                  <span className="strong">Public profile</span>
                  <br />
                  <span className="muted small">Contributions &amp; points</span>
                </span>
              </Link>
            </li>
          </ul>
          {others.length ? (
            <>
              <div
                className="eyebrow eyebrow--plain"
                style={{ padding: '12px 16px 4px' }}
              >
                Switch role
              </div>
              <ul>
                {others.map((r) => (
                  <li key={r}>
                    <button
                      type="button"
                      className="persona-item"
                      onClick={async () => {
                        try {
                          await switchRole(r as Role);
                          setPopover(null);
                          toast(`Now working as ${roleLabel(r)}.`);
                        } catch (err) {
                          toast(
                            err instanceof Error
                              ? err.message
                              : 'Could not switch role',
                            'error',
                          );
                        }
                      }}
                    >
                      <Icon name="refresh" size={16} />
                      <span>
                        <span className="strong">{roleLabel(r)}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="muted small" style={{ padding: '12px 16px' }}>
              You hold one role: {roleLabel(user.active_role)}.
            </p>
          )}
          <ul>
            <li>
              <button
                type="button"
                className="persona-item"
                onClick={async () => {
                  setPopover(null);
                  await logout();
                  navigate('/login');
                }}
              >
                <Icon name="lock" size={16} />
                <span className="strong">Sign out</span>
              </button>
            </li>
          </ul>
        </div>
      ) : null}
    </header>
  );
}
