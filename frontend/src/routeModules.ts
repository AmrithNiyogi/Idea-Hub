/**
 * Eagerly loads every `*_routes.tsx` next to App so sibling phase drops
 * (phase23, phase456, …) mount without editing App.tsx again.
 *
 * Each module may export:
 * - `phase23Routes` | `phase456Routes` | `extraRoutes` — React Router route tree
 * - `extraNavItems` — sidebar entries
 */

import { Fragment, createElement, type ReactNode } from 'react';
import type { Role } from './types/auth';

export interface ExtraNavItem {
  id: string;
  label: string;
  icon: string;
  to: string;
  roles?: Role[];
  sectionBefore?: string;
}

interface RouteModule {
  phase23Routes?: ReactNode;
  phase456Routes?: ReactNode;
  extraRoutes?: ReactNode;
  extraNavItems?: ExtraNavItem[];
}

const modules = import.meta.glob('./*_routes.tsx', {
  eager: true,
}) as Record<string, RouteModule>;

export function collectExtraRoutes(): ReactNode[] {
  return Object.entries(modules).flatMap(([file, m]) => {
    const nodes: ReactNode[] = [];
    // Each module's fragment needs a key: App renders them as a list inside <Routes>.
    if (m.phase23Routes) nodes.push(createElement(Fragment, { key: `${file}:phase23` }, m.phase23Routes));
    if (m.phase456Routes) nodes.push(createElement(Fragment, { key: `${file}:phase456` }, m.phase456Routes));
    if (m.extraRoutes) nodes.push(createElement(Fragment, { key: `${file}:extra` }, m.extraRoutes));
    return nodes;
  });
}

export function collectExtraNavItems(): ExtraNavItem[] {
  return Object.values(modules).flatMap((m) => m.extraNavItems ?? []);
}

export function discoveredRouteFiles(): string[] {
  return Object.keys(modules);
}
