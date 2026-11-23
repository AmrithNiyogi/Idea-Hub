import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { HelpChatFab } from '../HelpChatFab';
import { GuideTour } from '../onboarding/GuideTour';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

const TITLE_MAP: Record<string, string> = {
  '/': 'Home',
  '/explore': 'Explore',
  '/my': 'My ideas',
  '/submit': 'Submit an idea',
  '/review': 'Review queue',
  '/login': 'Log in',
  '/ideathons': 'Ideathons',
  '/recognition': 'Recognition',
  '/pipeline': 'Pipeline',
  '/approvals': 'Approvals',
  '/insights': 'Insights',
  '/admin': 'Admin',
  '/agents': 'Agent hub',
  '/problems': 'Problem radar',
  '/groups': 'Groups',
  '/dms': 'Messages',
  '/profile': 'My profile',
  '/settings': 'Account settings',
  '/integrations': 'Integrations',
};

function pageTitle(pathname: string): string {
  if (TITLE_MAP[pathname]) return TITLE_MAP[pathname];
  if (pathname.startsWith('/integrations/')) return 'Integration';
  if (pathname.startsWith('/ideas/')) return 'Idea';
  if (pathname.startsWith('/review/')) return 'Review';
  if (pathname.startsWith('/ideathons/')) return 'Ideathon';
  if (pathname.startsWith('/people/')) return 'Profile';
  if (pathname.startsWith('/problems/')) return 'Problem';
  if (pathname.startsWith('/groups/')) return 'Group';
  if (pathname.startsWith('/dms/')) return 'Message';
  return 'KonnektIdea';
}

export function AppShell() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem('ih.sidebarCollapsed') === '1';
    } catch {
      return false;
    }
  });
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try {
      return (localStorage.getItem('ih.theme') as 'light' | 'dark') || 'light';
    } catch {
      return 'light';
    }
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem('ih.theme', theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  useEffect(() => {
    try {
      localStorage.setItem('ih.sidebarCollapsed', collapsed ? '1' : '0');
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  const title = pageTitle(location.pathname);
  useEffect(() => {
    document.title = `${title} | KonnektIdea`;
  }, [title]);

  const appClass = [
    'app',
    collapsed ? 'is-collapsed' : '',
    drawerOpen ? 'drawer-open' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={appClass} id="app">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
      />
      <div
        className="scrim"
        id="scrim"
        onClick={() => setDrawerOpen(false)}
        aria-hidden={!drawerOpen}
      />
      <div className="main">
        <Topbar
          title={title}
          theme={theme}
          onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
          onOpenDrawer={() => setDrawerOpen(true)}
        />
        <main className="view" id="view" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
      <HelpChatFab />
      <GuideTour />
    </div>
  );
}
