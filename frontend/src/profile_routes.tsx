/**
 * Account / My Profile routes — signed-in editable settings.
 *
 * Public contribution profiles remain at `/people/:id` (phase23).
 * Discovered via `routeModules.ts` (`*_routes.tsx`).
 */

import { Route } from 'react-router-dom';
import { AccountSettingsPage } from './pages/AccountSettings';
import type { ExtraNavItem } from './routeModules';

export const extraRoutes = (
  <>
    <Route path="/profile" element={<AccountSettingsPage />} />
    <Route path="/settings" element={<AccountSettingsPage />} />
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
];

export { AccountSettingsPage };
