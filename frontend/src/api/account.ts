/**
 * Signed-in account settings APIs — profile, password, avatar upload.
 *
 * Distinct from `profiles.ts` (public contribution views at /people/:id).
 */

import { API_BASE_URL, ApiError, getApiErrorMessage, http } from './http';
import type { User } from '../types/auth';

export interface UpdateMePayload {
  name?: string;
  title?: string;
  avatar?: number;
  /** Pass empty string to clear a stored image URL. */
  avatar_url?: string | null;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export const accountApi = {
  me: () =>
    http.get<User>('/users/me').then((r) => r.data).catch((e) => {
      throw new Error(getApiErrorMessage(e));
    }),

  updateMe: (body: UpdateMePayload) =>
    http
      .patch<User>('/users/me', body)
      .then((r) => r.data)
      .catch((e) => {
        throw new Error(getApiErrorMessage(e));
      }),

  changePassword: (body: ChangePasswordPayload) =>
    http
      .post<{ message: string }>('/users/me/password', body)
      .then((r) => r.data)
      .catch((e) => {
        throw new Error(getApiErrorMessage(e));
      }),

  uploadAvatar: async (file: File): Promise<User> => {
    const form = new FormData();
    form.append('file', file);
    // Use fetch so the browser sets multipart boundary (axios defaults JSON CT).
    const res = await fetch(`${API_BASE_URL}/users/me/avatar`, {
      method: 'POST',
      credentials: 'include',
      body: form,
    });
    if (!res.ok) {
      let body: unknown = null;
      try {
        body = await res.json();
      } catch {
        body = await res.text();
      }
      const msg =
        typeof body === 'object' && body && 'detail' in body
          ? String((body as { detail: unknown }).detail)
          : res.statusText;
      throw new ApiError(res.status, msg, body);
    }
    return res.json() as Promise<User>;
  },
};

/** Absolute URL for a stored avatar path (used by settings preview). */
export function avatarAbsoluteUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path) || path.startsWith('data:')) return path;
  if (path.startsWith('/uploads/')) {
    const origin = API_BASE_URL.replace(/\/api\/v1\/?$/, '');
    return `${origin}${path}`;
  }
  return path;
}
