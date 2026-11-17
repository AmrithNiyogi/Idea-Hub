/** External tracker API — providers come from the server registry. */

import { apiFetch } from './client';
import type {
  EffectiveConnection,
  IdeaTrackerLink,
  IdeaTrackerLinkCreateBody,
  IdeaTrackerRemoteUpdateBody,
  LiveTrackerTask,
  TrackerConnection,
  TrackerConnectionCreateBody,
  TrackerProvider,
} from '../types/trackers';

export const trackersApi = {
  listProviders: () =>
    apiFetch<TrackerProvider[]>('/trackers/providers'),

  listConnections: () =>
    apiFetch<TrackerConnection[]>('/trackers/connections'),

  listEffective: () =>
    apiFetch<EffectiveConnection[]>('/trackers/connections/effective'),

  connect: (body: TrackerConnectionCreateBody) =>
    apiFetch<TrackerConnection>('/trackers/connections', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  disconnect: (connectionId: string) =>
    apiFetch<void>(`/trackers/connections/${connectionId}`, {
      method: 'DELETE',
    }),

  listLinks: (ideaId: string) =>
    apiFetch<IdeaTrackerLink[]>(`/ideas/${ideaId}/tracker-links`),

  listLiveTasks: (ideaId: string) =>
    apiFetch<LiveTrackerTask[]>(`/ideas/${ideaId}/tracker-links/live`),

  getLiveTask: (ideaId: string, linkId: string) =>
    apiFetch<LiveTrackerTask>(
      `/ideas/${ideaId}/tracker-links/${linkId}/live`,
    ),

  updateRemote: (
    ideaId: string,
    linkId: string,
    body: IdeaTrackerRemoteUpdateBody,
  ) =>
    apiFetch<LiveTrackerTask>(
      `/ideas/${ideaId}/tracker-links/${linkId}/remote`,
      {
        method: 'PATCH',
        body: JSON.stringify(body),
      },
    ),

  createOrLink: (ideaId: string, body: IdeaTrackerLinkCreateBody) =>
    apiFetch<IdeaTrackerLink>(`/ideas/${ideaId}/tracker-links`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  unlink: (ideaId: string, linkId: string) =>
    apiFetch<void>(`/ideas/${ideaId}/tracker-links/${linkId}`, {
      method: 'DELETE',
    }),
};
