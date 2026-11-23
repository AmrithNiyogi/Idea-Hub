/** Admin service tokens API (`/admin/service-tokens`). The token itself is returned once, on create. */

import { apiFetch } from './client';

export type ServiceTokenStatus = 'active' | 'expired' | 'revoked';

export interface ServiceToken {
  id: string;
  name: string;
  prefix: string;
  status: ServiceTokenStatus;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface ServiceTokenCreated {
  token: string;
  record: ServiceToken;
}

export const serviceTokensApi = {
  list: () => apiFetch<ServiceToken[]>('/admin/service-tokens'),

  create: (body: { name: string; expires_in_days: number | null }) =>
    apiFetch<ServiceTokenCreated>('/admin/service-tokens', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  revoke: (id: string) =>
    apiFetch<ServiceToken>(`/admin/service-tokens/${id}/revoke`, { method: 'POST' }),
};
