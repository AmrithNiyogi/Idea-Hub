/**
 * Phase 4+5+6 routes + sidebar entries.
 * Discovered automatically via `routeModules.ts` (import.meta.glob `*_routes.tsx`).
 *
 * Routes: /insights, /admin, /agents, /problems, /problems/:key
 * IdeaDetail can also render CollabTrackerPanel when `?tab=collab`.
 */

import { Route } from 'react-router-dom';
import { InsightsPage } from './pages/Insights';
import { AdminPage } from './pages/Admin';
import { AgentsPage } from './pages/Agents';
import { ProblemsPage } from './pages/Problems';
import { ProblemDetailPage } from './pages/ProblemDetail';
import type { ExtraNavItem } from './routeModules';

export const phase456Routes = (
  <>
    <Route path="/insights" element={<InsightsPage />} />
    <Route path="/admin" element={<AdminPage />} />
    <Route path="/agents" element={<AgentsPage />} />
    <Route path="/problems" element={<ProblemsPage />} />
    <Route path="/problems/:key" element={<ProblemDetailPage />} />
  </>
);

export const extraNavItems: ExtraNavItem[] = [
  {
    id: 'problems',
    label: 'Problem radar',
    icon: 'flag',
    to: '/problems',
    sectionBefore: 'Insight',
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
  InsightsPage,
  AdminPage,
  AgentsPage,
  ProblemsPage,
  ProblemDetailPage,
};
