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
    sectionBefore: 'Work',
  },
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

  const nav = [...SPINE_NAV, ...collectExtraNavItems()].filter(
    (n) => !n.roles || n.roles.includes(active),
  );

  return (
    <aside className="sidebar" aria-label="Primary">
      <Link className="brand" to="/" aria-label="IdeaKonnekt, Idea Hub. Home">
        <span className="brand__glyph">
          <Icon name="logo" size={18} />
        </span>
        <span className="brand__text">
          <span className="brand__name">IdeaKonnekt</span>
          <span className="brand__sub">Idea Hub</span>
        </span>
      </Link>

      <nav className="nav" aria-label="Main">
        {nav.map((n) => (
          <span key={n.id} style={{ display: 'contents' }}>
            {n.sectionBefore ? (
              <div className="nav__label">{n.sectionBefore}</div>
            ) : null}
            <NavLink
              to={n.to}
              end={n.to === '/'}
              className="nav-item"
              title={n.label}
            >
              <Icon name={n.icon} size={20} />
              <span className="nav-item__text">{n.label}</span>
            </NavLink>
          </span>
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
          <Icon name="sidebar" size={18} />
          <span className="btn__text">{collapsed ? 'Expand' : 'Collapse'}</span>
        </button>
        <p className="sidebar__note">
          Ideas move through review, decision and delivery. Agents propose;
          people decide.
        </p>
      </div>
    </aside>
  );
}
