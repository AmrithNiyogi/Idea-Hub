import { apiFetch } from './client';
import type { Role } from '../types/auth';
import type { AdminConfig } from '../types/phase456';

/** Admin People and roles directory row (``GET /admin/users``). */
export interface AdminUser {
  id: string;
  email: string;
  name: string;
  title: string;
  roles: Role[];
  primary_role: Role;
  status: string;
  is_active: boolean;
}

export interface AdminRoleMutation {
  user: AdminUser;
  fell_back?: boolean;
  panels_left?: number;
  needs_confirm?: boolean;
  panels?: string[];
}

export type CategoryColorKey =
  | 'tech'
  | 'business'
  | 'process'
  | 'innovation'
  | 'amber'
  | 'green'
  | 'violet'
  | 'coral';

export interface CategoryCreateBody {
  label: string;
  description: string;
  color_key: CategoryColorKey;
  reviewer_id: string;
  slug?: string;
}

export interface CategoryUpdateBody {
  label?: string;
  description?: string;
  enabled?: boolean;
  color?: string;
  color_key?: CategoryColorKey;
}

export interface PanelCreateBody {
  category_id: string;
  name?: string;
  member_ids: string[];
  chair_id?: string;
}

export interface PanelUpdateBody {
  name?: string;
  member_ids?: string[];
  chair_id?: string | null;
}

export const adminApi = {
  config: () => apiFetch<AdminConfig>('/admin/config'),

  listUsers: (q?: string) => {
    const qs = q?.trim() ? `?q=${encodeURIComponent(q.trim())}` : '';
    return apiFetch<AdminUser[]>(`/admin/users${qs}`);
  },

  addUserRole: (userId: string, role: Role) =>
    apiFetch<AdminRoleMutation>(`/admin/users/${userId}/roles`, {
      method: 'POST',
      body: JSON.stringify({ role }),
    }),

  removeUserRole: (userId: string, role: Role, confirm = false) =>
    apiFetch<AdminRoleMutation>(
      `/admin/users/${userId}/roles/${encodeURIComponent(role)}${
        confirm ? '?confirm=true' : ''
      }`,
      { method: 'DELETE' },
    ),

  setUserPrimaryRole: (userId: string, role: Role) =>
    apiFetch<AdminRoleMutation>(`/admin/users/${userId}/primary-role`, {
      method: 'PUT',
      body: JSON.stringify({ role }),
    }),

  saveTimelines: (body: Record<string, number>) =>
    apiFetch<Record<string, number>>('/admin/timelines', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  saveScoring: (criteria: AdminConfig['scoring']) =>
    apiFetch<AdminConfig['scoring']>('/admin/scoring', {
      method: 'PUT',
      body: JSON.stringify({ criteria }),
    }),

  savePoints: (overrides: Record<string, number>) =>
    apiFetch<Record<string, number>>('/admin/points', {
      method: 'PUT',
      body: JSON.stringify({ overrides }),
    }),

  createCategory: (body: CategoryCreateBody) =>
    apiFetch<AdminConfig['categories'][number]>('/admin/categories', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  updateCategory: (id: string, body: CategoryUpdateBody) =>
    apiFetch<AdminConfig['categories'][number]>(`/admin/categories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  createPanel: (body: PanelCreateBody) =>
    apiFetch<AdminConfig['panels'][number]>('/admin/panels', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  updatePanel: (id: string, body: PanelUpdateBody) =>
    apiFetch<AdminConfig['panels'][number]>(`/admin/panels/${id}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  addPanelMember: (panelId: string, userId: string) =>
    apiFetch<AdminConfig['panels'][number]>(
      `/admin/panels/${panelId}/members`,
      {
        method: 'POST',
        body: JSON.stringify({ user_id: userId }),
      },
    ),

  removePanelMember: (panelId: string, userId: string) =>
    apiFetch<AdminConfig['panels'][number]>(
      `/admin/panels/${panelId}/members/${userId}`,
      { method: 'DELETE' },
    ),

  setPanelChair: (panelId: string, userId: string) =>
    apiFetch<AdminConfig['panels'][number]>(
      `/admin/panels/${panelId}/chair`,
      {
        method: 'PUT',
        body: JSON.stringify({ user_id: userId }),
      },
    ),

  audit: (limit = 50) => apiFetch(`/admin/audit?limit=${limit}`),

  exportInventory: () => apiFetch('/admin/export'),

  reset: () =>
    apiFetch<{ ok: boolean; message: string }>('/admin/reset', {
      method: 'POST',
    }),
};
