/**
 * Phase 4+5+6 routes + sidebar entries.
 * Discovered automatically via `routeModules.ts` (import.meta.glob `*_routes.tsx`).
 *
 * Routes: /groups, /groups/:id, /dms, /dms/:id, /insights, /admin, /agents, /problems, …
 */

import { Route } from 'react-router-dom';
import { InsightsPage } from './pages/Insights';
import { AdminPage } from './pages/Admin';
import { AgentsPage } from './pages/Agents';
import { ProblemsPage } from './pages/Problems';
import { ProblemDetailPage } from './pages/ProblemDetail';
import { NewsPage } from './pages/News';
import { GroupsPage } from './pages/Groups';
import { GroupDetailPage } from './pages/GroupDetail';
import type { ExtraNavItem } from './routeModules';

export const phase456Routes = (
  <>
    <Route path="/groups" element={<GroupsPage />} />
    <Route path="/groups/:id" element={<GroupDetailPage />} />
    <Route path="/dms" element={<GroupsPage defaultTab="dms" />} />
    <Route path="/dms/:id" element={<GroupDetailPage dmRoute />} />
    <Route path="/insights" element={<InsightsPage />} />
    <Route path="/admin" element={<AdminPage />} />
    <Route path="/agents" element={<AgentsPage />} />
    <Route path="/problems" element={<ProblemsPage />} />
    <Route path="/problems/:key" element={<ProblemDetailPage />} />
    <Route path="/news" element={<NewsPage />} />
  </>
);

export const extraNavItems: ExtraNavItem[] = [
  {
    id: 'groups',
    label: 'Groups',
    icon: 'message',
    to: '/groups',
    sectionBefore: 'Collaborate',
  },
  {
    id: 'dms',
    label: 'Messages',
    icon: 'send',
    to: '/dms',
  },
  {
    id: 'problems',
    label: 'Problem radar',
    icon: 'flag',
    to: '/problems',
    sectionBefore: 'Insight',
  },
  {
    id: 'news',
    label: 'AI Newsletter',
    icon: 'spark',
    to: '/news',
  },
  {
    id: 'insights',
    label: 'Insights',
    icon: 'compass',
    to: '/insights',
    roles: ['leadership', 'admin'],
  },
  {
    id: 'agents',
    label: 'Agent hub',
    icon: 'checkcircle',
    to: '/agents',
    roles: ['reviewer', 'lead', 'leadership', 'admin'],
  },
  {
    id: 'admin',
    label: 'Admin',
    icon: 'list',
    to: '/admin',
    roles: ['admin'],
  },
];

export {
  GroupsPage,
  GroupDetailPage,
  InsightsPage,
  AdminPage,
  AgentsPage,
  ProblemsPage,
  ProblemDetailPage,
  NewsPage,
};
