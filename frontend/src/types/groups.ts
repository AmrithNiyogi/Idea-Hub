export type GroupMember = {
  user_id: string;
  role: string;
  joined_at: string;
  name: string;
  email: string;
  avatar: number;
  avatar_url: string | null;
};

export type GroupInvite = {
  id: string;
  group_id: string;
  group_name: string;
  invitee_id: string;
  invited_by: string;
  role: string;
  status: string;
  created_at: string;
  responded_at: string | null;
  invitee_name: string;
  invitee_email: string;
  invitee_avatar: number;
  invitee_avatar_url: string | null;
  invited_by_name: string;
};

export type GroupChannel = {
  id: string;
  group_id: string;
  slug: string;
  name: string;
  description: string;
  kind: string;
  sort_order: number;
  created_at: string;
};

export type GroupMessage = {
  id: string;
  channel_id: string;
  author_id: string;
  body: string;
  message_type: string;
  meta: Record<string, unknown>;
  created_at: string;
};

export type GroupMeeting = {
  id: string;
  group_id: string;
  channel_id: string | null;
  title: string;
  description: string;
  starts_at: string;
  ends_at: string | null;
  join_url: string;
  created_by: string;
  notify_via: string;
  notify_status: string;
  notify_detail: string;
  meta: Record<string, unknown>;
  created_at: string;
};

export type GroupPoll = {
  id: string;
  group_id: string;
  question: string;
  options: string[];
  created_by: string;
  closed_at: string | null;
  ends_at: string | null;
  created_at: string;
  multi_select: boolean;
  counts: number[];
  total_votes: number;
  my_votes: number[];
};

export type GroupMcpConnection = {
  id: string;
  group_id: string;
  idea_id: string | null;
  label: string;
  endpoint_url: string;
  auth_header_name: string;
  has_auth: boolean;
  transport: string;
  tools_cache: Array<{
    name: string;
    description?: string;
    inputSchema?: Record<string, unknown>;
  }>;
  last_discovered_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type GroupSummary = {
  id: string;
  name: string;
  description: string;
  kind: 'group' | 'dm' | string;
  idea_id: string | null;
  avatar_url: string | null;
  created_by: string;
  created_at: string;
  member_count: number;
  my_role: string | null;
  peer_user_id: string | null;
  peer_avatar: number;
  peer_avatar_url: string | null;
};

export type Group = {
  id: string;
  name: string;
  description: string;
  kind: 'group' | 'dm' | string;
  idea_id: string | null;
  avatar_url: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  channels: GroupChannel[];
  members: GroupMember[];
  pending_invites: GroupInvite[];
  can_post: boolean;
  can_manage: boolean;
  peer_user_id: string | null;
  peer_avatar: number;
  peer_avatar_url: string | null;
};

export type McpToolCallResult = {
  ok: boolean;
  result?: unknown;
  error?: string;
};
