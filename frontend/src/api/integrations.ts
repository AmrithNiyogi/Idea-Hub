/** Integrations settings API — personal + org-default connections. */

import { apiFetch } from './client';
import type {
  EffectiveConnection,
  IntegrationProvider,
  TrackerConnection,
  TrackerConnectionCreateBody,
} from '../types/trackers';

export const integrationsApi = {
  listProviders: (category?: string) => {
    const qs = category
      ? `?category=${encodeURIComponent(category)}`
      : '';
    return apiFetch<IntegrationProvider[]>(`/integrations/providers${qs}`);
  },

  listEffective: (category?: string) => {
    const qs = category
      ? `?category=${encodeURIComponent(category)}`
      : '';
    return apiFetch<EffectiveConnection[]>(
      `/integrations/connections/effective${qs}`,
    );
  },

  listMine: () =>
    apiFetch<TrackerConnection[]>('/integrations/connections'),

  connectMine: (body: TrackerConnectionCreateBody) =>
    apiFetch<TrackerConnection>('/integrations/connections', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  startMcpOAuth: (body: { endpoint_url: string; label?: string }) =>
    apiFetch<{ authorize_url: string }>('/integrations/mcp/oauth/start', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  disconnectMine: (connectionId: string) =>
    apiFetch<void>(`/integrations/connections/${connectionId}`, {
      method: 'DELETE',
    }),

  listOrg: () =>
    apiFetch<TrackerConnection[]>('/integrations/org/connections'),

  connectOrg: (body: TrackerConnectionCreateBody) =>
    apiFetch<TrackerConnection>('/integrations/org/connections', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  disconnectOrg: (connectionId: string) =>
    apiFetch<void>(`/integrations/org/connections/${connectionId}`, {
      method: 'DELETE',
    }),
};
