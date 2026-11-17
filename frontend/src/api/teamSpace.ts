import { apiFetch } from './client';
import type {
  IdeaMcpConnection,
  McpToolCallResult,
  TeamChannel,
  TeamMeeting,
  TeamMessage,
  TeamSpace,
} from '../types/teamSpace';

export const teamSpaceApi = {
  get: (ideaId: string) =>
    apiFetch<TeamSpace>(`/ideas/${ideaId}/team-space`),

  createChannel: (
    ideaId: string,
    body: { name: string; slug?: string; description?: string; kind?: string },
  ) =>
    apiFetch<TeamChannel>(`/ideas/${ideaId}/team-space/channels`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  messages: (ideaId: string, channelId: string, limit = 80) =>
    apiFetch<TeamMessage[]>(
      `/ideas/${ideaId}/team-space/channels/${channelId}/messages?limit=${limit}`,
    ),

  postMessage: (ideaId: string, channelId: string, body: string) =>
    apiFetch<TeamMessage>(
      `/ideas/${ideaId}/team-space/channels/${channelId}/messages`,
      {
        method: 'POST',
        body: JSON.stringify({ body }),
      },
    ),

  meetings: (ideaId: string) =>
    apiFetch<TeamMeeting[]>(`/ideas/${ideaId}/team-space/meetings`),

  scheduleMeeting: (
    ideaId: string,
    body: {
      title: string;
      starts_at: string;
      ends_at?: string;
      description?: string;
      join_url?: string;
      channel_id?: string;
      channel_slug?: string;
      notify_teams?: boolean;
      announce_in_channel?: boolean;
    },
  ) =>
    apiFetch<TeamMeeting>(`/ideas/${ideaId}/team-space/meetings`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  listMcp: (ideaId: string) =>
    apiFetch<IdeaMcpConnection[]>(`/ideas/${ideaId}/team-space/mcp`),

  connectMcp: (
    ideaId: string,
    body: {
      label?: string;
      endpoint_url: string;
      auth_header_name?: string;
      auth_header_value?: string;
      transport?: 'http_jsonrpc' | 'stub';
      seed_stub_tools?: boolean;
    },
  ) =>
    apiFetch<IdeaMcpConnection>(`/ideas/${ideaId}/team-space/mcp`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  discoverMcp: (ideaId: string, mcpId: string) =>
    apiFetch<IdeaMcpConnection>(
      `/ideas/${ideaId}/team-space/mcp/${mcpId}/discover`,
      { method: 'POST' },
    ),

  callMcp: (
    ideaId: string,
    mcpId: string,
    body: { name: string; arguments?: Record<string, unknown> },
  ) =>
    apiFetch<McpToolCallResult>(
      `/ideas/${ideaId}/team-space/mcp/${mcpId}/call`,
      {
        method: 'POST',
        body: JSON.stringify(body),
      },
    ),

  deleteMcp: (ideaId: string, mcpId: string) =>
    apiFetch<void>(`/ideas/${ideaId}/team-space/mcp/${mcpId}`, {
      method: 'DELETE',
    }),
};
