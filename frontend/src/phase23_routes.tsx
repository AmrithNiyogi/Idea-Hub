/**
 * Phase 2+3 routes + sidebar entries.
 * Discovered automatically via `routeModules.ts` (import.meta.glob `*_routes.tsx`).
 * IdeaDetail also renders DeliveryTab on `?tab=delivery`.
 *
 * Also mounts Pipeline (stage board) and Approvals (innovation hours inbox).
 */

import { Route } from 'react-router-dom';
import { IdeathonsPage } from './pages/Ideathons';
import { IdeathonDetailPage } from './pages/IdeathonDetail';
import { IdeathonNewPage } from './pages/IdeathonNew';
import { IdeathonEditPage } from './pages/IdeathonEdit';
import { RecognitionPage } from './pages/Recognition';
import { ProfilePage } from './pages/Profile';
import { PipelinePage } from './pages/Pipeline';
import { ApprovalsPage } from './pages/Approvals';
import type { ExtraNavItem } from './routeModules';

export const phase23Routes = (
  <>
    <Route path="/pipeline" element={<PipelinePage />} />
    <Route path="/approvals" element={<ApprovalsPage />} />
    <Route path="/ideathons" element={<IdeathonsPage />} />
    <Route path="/ideathons/new" element={<IdeathonNewPage />} />
    <Route path="/ideathons/:id" element={<IdeathonDetailPage />} />
    <Route path="/ideathons/:id/edit" element={<IdeathonEditPage />} />
    <Route path="/recognition" element={<RecognitionPage />} />
    <Route path="/people/:id" element={<ProfilePage />} />
  </>
);

export const extraNavItems: ExtraNavItem[] = [
  {
    id: 'pipeline',
    label: 'Pipeline',
    icon: 'columns',
    to: '/pipeline',
  },
  {
    id: 'approvals',
    label: 'Approvals',
    icon: 'clock',
    to: '/approvals',
    roles: ['leadership', 'admin'],
  },
  {
    id: 'ideathons',
    label: 'Ideathons',
    icon: 'flag',
    to: '/ideathons',
    sectionBefore: 'Community',
  },
  {
    id: 'recognition',
    label: 'Recognition',
    icon: 'award',
    to: '/recognition',
  },
];

export {
  IdeathonsPage,
  IdeathonDetailPage,
  IdeathonNewPage,
  IdeathonEditPage,
  RecognitionPage,
  ProfilePage,
  PipelinePage,
  ApprovalsPage,
};
