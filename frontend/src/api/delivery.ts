/** Delivery tab API — mirrors idea-hub.html `api.delivery.*`. */

import { apiFetch } from './client';
import type {
  DeliveryDetail,
  HoursDecideBody,
  HoursLogBody,
  HoursRequest,
  HoursRequestBody,
  MarkImplementedBody,
  TaskCreateBody,
  TaskStatusBody,
} from '../types/delivery';

export const deliveryApi = {
  get: (ideaId: string) =>
    apiFetch<DeliveryDetail>(`/ideas/${ideaId}/delivery`),

  requestHours: (ideaId: string, body: HoursRequestBody) =>
    apiFetch(`/ideas/${ideaId}/delivery/hours-requests`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  listHoursRequests: (opts?: { state?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (opts?.state) q.set('state', opts.state);
    if (opts?.limit) q.set('limit', String(opts.limit));
    const qs = q.toString();
    return apiFetch<HoursRequest[]>(
      `/delivery/hours-requests${qs ? `?${qs}` : ''}`,
    );
  },

  decideHours: (requestId: string, body: HoursDecideBody) =>
    apiFetch(`/delivery/hours-requests/${requestId}/decide`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  logHours: (ideaId: string, body: HoursLogBody) =>
    apiFetch(`/ideas/${ideaId}/delivery/hours-log`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  addContributor: (ideaId: string, userId: string, role: string) =>
    apiFetch(`/ideas/${ideaId}/delivery/contributors`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, role }),
    }),

  removeContributor: (ideaId: string, userId: string) =>
    apiFetch(`/ideas/${ideaId}/delivery/contributors/${userId}`, {
      method: 'DELETE',
    }),

  addTask: (ideaId: string, body: TaskCreateBody) =>
    apiFetch(`/ideas/${ideaId}/delivery/tasks`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  setTaskStatus: (taskId: string, body: TaskStatusBody) =>
    apiFetch(`/delivery/tasks/${taskId}/status`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  postUpdate: (ideaId: string, body: string, taskId?: string) =>
    apiFetch(`/ideas/${ideaId}/delivery/updates`, {
      method: 'POST',
      body: JSON.stringify({ body, task_id: taskId ?? null }),
    }),

  markImplemented: (ideaId: string, body: MarkImplementedBody) =>
    apiFetch(`/ideas/${ideaId}/delivery/mark-implemented`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  verifyImpact: (ideaId: string, entryId: string, note: string) =>
    apiFetch(`/ideas/${ideaId}/delivery/impact/${entryId}/verify`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),
};
