import { Link, NavLink } from 'react-router-dom';
import { Icon } from '../Icons';
import { useAuth } from '../../auth/AuthProvider';
import { collectExtraNavItems, type ExtraNavItem } from '../../routeModules';
import type { Role } from '../../types/auth';

const SPINE_NAV: ExtraNavItem[] = [
  { id: 'home', label: 'Home', icon: 'home', to: '/' },
  { id: 'explore', label: 'Explore', icon: 'compass', to: '/explore' },
  {
    id: 'my',
    label: 'My ideas',
    icon: 'list',
    to: '/my',
    roles: ['contributor', 'reviewer', 'lead'],
  },
  {
    id: 'review',
    label: 'Review',
    icon: 'checkcircle',
    to: '/review',
    roles: ['reviewer', 'admin'],
  },
];

/**
 * Sidebar order follows the idea journey: Shape → Review → Build → Recognise.
 * Items not listed here land in "More" so new modules still appear.
 */
const NAV_SECTIONS: { label: string | null; ids: string[] }[] = [
  { label: null, ids: ['home'] },
  { label: 'Shape', ids: ['explore', 'my', 'ideathons', 'problems'] },
  { label: 'Review', ids: ['review', 'approvals'] },
  { label: 'Build', ids: ['pipeline'] },
  { label: 'Recognise', ids: ['recognition'] },
  { label: 'Connect', ids: ['groups', 'dms'] },
  { label: 'Insight', ids: ['news', 'insights', 'agents'] },
  { label: 'You', ids: ['profile', 'integrations', 'admin'] },
];

export function Sidebar({
  collapsed,
  onToggleCollapse,
}: {
  collapsed: boolean;
  onToggleCollapse: () => void;
}) {
  const { user } = useAuth();
  const active = (user?.active_role ?? 'contributor') as Role;

  const all = [...SPINE_NAV, ...collectExtraNavItems()].filter(
    (n) => !n.roles || n.roles.includes(active),
  );
  const byId = new Map(all.map((n) => [n.id, n]));
  const placed = new Set(NAV_SECTIONS.flatMap((s) => s.ids));
  const sections = [
    ...NAV_SECTIONS.map((s) => ({
      label: s.label,
      items: s.ids.map((id) => byId.get(id)).filter((n): n is ExtraNavItem => !!n),
    })),
    {
      label: 'More',
      items: all.filter((n) => !placed.has(n.id)),
    },
  ].filter((s) => s.items.length > 0);

  return (
    <aside className="sidebar" aria-label="Primary">
      <Link className="brand" to="/" aria-label="IdeaKonnekt. Home">
        <span className="brand__glyph">
          <Icon name="logo" size={18} />
        </span>
        <span className="brand__text">
          <span className="brand__name">IdeaKonnekt</span>
          <span className="brand__sub">IdeaKonnekt</span>
        </span>
      </Link>

      <nav className="nav" aria-label="Main">
        {sections.map((s) => (
          <div key={s.label ?? 'top'} className="nav__group">
            {s.label ? <div className="nav__label">{s.label}</div> : null}
            {s.items.map((n) => (
              <NavLink
                key={n.id}
                to={n.to}
                end={n.to === '/'}
                className="nav-item"
                title={n.label}
              >
                <Icon name={n.icon} size={16} />
                <span className="nav-item__text">{n.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar__foot">
        <div className="dk-logo" role="img" aria-label="dotkonnekt">
          <span
            className="dk-logo__mark"
            style={{ fontWeight: 700, fontSize: 13 }}
          >
            dk
          </span>
          <span
            className="dk-logo__word"
            style={{ fontSize: 12, letterSpacing: '0.06em' }}
          >
            dotkonnekt
          </span>
        </div>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          id="collapse-btn"
          onClick={onToggleCollapse}
          aria-pressed={collapsed}
        >
          <Icon name="sidebar" size={16} />
          <span className="btn__text">{collapsed ? 'Expand' : 'Collapse'}</span>
        </button>
      </div>
    </aside>
  );
}
