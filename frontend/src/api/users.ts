/** Directory helpers — users and teams for search / pickers. */

import { apiFetch } from './client';
import type { User } from '../types/auth';

export interface Team {
  id: string;
  slug: string;
  name: string;
  lead_id: string | null;
}

export const usersApi = {
  list: () => apiFetch<User[]>('/users'),
  /** Name/email search for invite + DM pickers (server-side, capped). */
  search: (q: string, limit = 8) =>
    apiFetch<User[]>(
      `/users?q=${encodeURIComponent(q.trim())}&limit=${limit}`,
    ),
  get: (id: string) => apiFetch<User>(`/users/${id}`),
  teams: () => apiFetch<Team[]>('/teams'),
};
