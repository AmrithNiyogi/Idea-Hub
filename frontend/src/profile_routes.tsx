/**
 * Account / My Profile / Integrations routes — signed-in editable settings.
 *
 * Public contribution profiles remain at `/people/:id` (phase23).
 * Discovered via `routeModules.ts` (`*_routes.tsx`).
 */

import { Route } from 'react-router-dom';
import { AccountSettingsPage } from './pages/AccountSettings';
import { IntegrationDetailPage } from './pages/IntegrationDetail';
import { IntegrationsPage } from './pages/Integrations';
import type { ExtraNavItem } from './routeModules';

export const extraRoutes = (
  <>
    <Route path="/profile" element={<AccountSettingsPage />} />
    <Route path="/settings" element={<AccountSettingsPage />} />
    <Route path="/integrations" element={<IntegrationsPage />} />
    <Route path="/integrations/:providerId" element={<IntegrationDetailPage />} />
  </>
);

export const extraNavItems: ExtraNavItem[] = [
  {
    id: 'profile',
    label: 'My profile',
    icon: 'user',
    to: '/profile',
    sectionBefore: 'You',
  },
  {
    id: 'integrations',
    label: 'Integrations',
    icon: 'layers',
    to: '/integrations',
  },
];

export { AccountSettingsPage, IntegrationDetailPage, IntegrationsPage };
