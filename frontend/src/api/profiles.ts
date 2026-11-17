/** Profiles API — thin person views. */

import { apiFetch } from './client';
import type { Profile } from '../types/profile';

export const profilesApi = {
  get: (userId: string) => apiFetch<Profile>(`/people/${userId}`),
};
