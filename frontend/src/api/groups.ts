import { apiFetch, ApiError, API_BASE_URL } from './client';
import type {
  Group,
  GroupChannel,
  GroupInvite,
  GroupMeeting,
  GroupMessage,
  GroupMcpConnection,
  GroupMember,
  GroupSummary,
  McpToolCallResult,
} from '../types/groups';

export const groupsApi = {
  list: (kind?: 'group' | 'dm') => {
    const q = kind ? `?kind=${kind}` : '';
    return apiFetch<GroupSummary[]>(`/groups${q}`);
  },

  create: (body: { name: string; description?: string; idea_id?: string }) =>
    apiFetch<Group>('/groups', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  get: (groupId: string) => apiFetch<Group>(`/groups/${groupId}`),

  update: (
    groupId: string,
    body: {
      name?: string;
      description?: string;
      idea_id?: string;
      clear_idea?: boolean;
      avatar_url?: string;
      clear_avatar?: boolean;
    },
  ) =>
    apiFetch<Group>(`/groups/${groupId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  softDelete: (groupId: string) =>
    apiFetch<void>(`/groups/${groupId}`, { method: 'DELETE' }),

  uploadAvatar: async (groupId: string, file: File): Promise<Group> => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API_BASE_URL}/groups/${groupId}/avatar`, {
      method: 'POST',
      credentials: 'include',
      body: form,
    });
    if (!res.ok) {
      let detail = 'Avatar upload failed';
      try {
        const body = (await res.json()) as { detail?: string };
        if (body.detail) detail = body.detail;
      } catch {
        /* ignore */
      }
      throw new ApiError(res.status, detail);
    }
    return (await res.json()) as Group;
  },

  forIdea: (ideaId: string) =>
    apiFetch<Group | null>(`/ideas/${ideaId}/group`),

  myInvites: () => apiFetch<GroupInvite[]>('/groups/invites/mine'),

  invite: (
    groupId: string,
    body: { user_id: string; role?: 'admin' | 'member' },
  ) =>
    apiFetch<GroupInvite>(`/groups/${groupId}/invites`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  cancelInvite: (groupId: string, inviteId: string) =>
    apiFetch<void>(`/groups/${groupId}/invites/${inviteId}`, {
      method: 'DELETE',
    }),

  acceptInvite: (inviteId: string) =>
    apiFetch<Group>(`/groups/invites/${inviteId}/accept`, { method: 'POST' }),

  declineInvite: (inviteId: string) =>
    apiFetch<void>(`/groups/invites/${inviteId}/decline`, { method: 'POST' }),

  removeMember: (groupId: string, userId: string) =>
    apiFetch<void>(`/groups/${groupId}/members/${userId}`, {
      method: 'DELETE',
    }),

  openDm: (userId: string) =>
    apiFetch<Group>('/groups/dms', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    }),

  createChannel: (
    groupId: string,
    body: { name: string; slug?: string; description?: string; kind?: string },
  ) =>
    apiFetch<GroupChannel>(`/groups/${groupId}/channels`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  messages: (groupId: string, channelId: string, limit = 80) =>
    apiFetch<GroupMessage[]>(
      `/groups/${groupId}/channels/${channelId}/messages?limit=${limit}`,
    ),

  postMessage: (groupId: string, channelId: string, body: string) =>
    apiFetch<GroupMessage>(
      `/groups/${groupId}/channels/${channelId}/messages`,
      {
        method: 'POST',
        body: JSON.stringify({ body }),
      },
    ),

  meetings: (groupId: string) =>
    apiFetch<GroupMeeting[]>(`/groups/${groupId}/meetings`),

  scheduleMeeting: (
    groupId: string,
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
    apiFetch<GroupMeeting>(`/groups/${groupId}/meetings`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  listMcp: (groupId: string) =>
    apiFetch<GroupMcpConnection[]>(`/groups/${groupId}/mcp`),

  connectMcp: (
    groupId: string,
    body: {
      label?: string;
      endpoint_url: string;
      auth_header_name?: string;
      auth_header_value?: string;
      transport?: 'http_jsonrpc' | 'stub';
      seed_stub_tools?: boolean;
    },
  ) =>
    apiFetch<GroupMcpConnection>(`/groups/${groupId}/mcp`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  discoverMcp: (groupId: string, mcpId: string) =>
    apiFetch<GroupMcpConnection>(
      `/groups/${groupId}/mcp/${mcpId}/discover`,
      { method: 'POST' },
    ),

  callMcp: (
    groupId: string,
    mcpId: string,
    body: { name: string; arguments?: Record<string, unknown> },
  ) =>
    apiFetch<McpToolCallResult>(`/groups/${groupId}/mcp/${mcpId}/call`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  deleteMcp: (groupId: string, mcpId: string) =>
    apiFetch<void>(`/groups/${groupId}/mcp/${mcpId}`, { method: 'DELETE' }),
};

// Keep type export for callers that imported GroupMember from the API module.
export type { GroupMember };
