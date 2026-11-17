/** Tab strip matching idea-hub.html `tabsNav()` — links or buttons. */

import { Link } from 'react-router-dom';

export interface TabItem {
  id: string;
  label: string;
  href?: string;
  count?: number | null;
}

export function TabsNav({
  tabs,
  active,
  onSelect,
}: {
  tabs: TabItem[];
  active: string;
  onSelect?: (id: string) => void;
}) {
  return (
    <nav className="tabs" role="tablist" aria-label="Sections">
      {tabs.map((t) => {
        const selected = t.id === active;
        const count =
          t.count != null && t.count > 0 ? (
            <span className="count">{t.count}</span>
          ) : null;
        if (t.href) {
          return (
            <Link
              key={t.id}
              to={t.href}
              role="tab"
              aria-selected={selected}
              aria-current={selected ? 'page' : undefined}
            >
              {t.label}
              {count}
            </Link>
          );
        }
        return (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onSelect?.(t.id)}
          >
            {t.label}
            {count}
          </button>
        );
      })}
    </nav>
  );
}
