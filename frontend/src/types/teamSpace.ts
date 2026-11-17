export type TeamChannel = {
  id: string;
  space_id: string;
  slug: string;
  name: string;
  description: string;
  kind: string;
  sort_order: number;
  created_at: string;
};

export type TeamMessage = {
  id: string;
  channel_id: string;
  author_id: string;
  body: string;
  message_type: string;
  meta: Record<string, unknown>;
  created_at: string;
};

export type TeamMeeting = {
  id: string;
  space_id: string;
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

export type IdeaMcpConnection = {
  id: string;
  space_id: string;
  idea_id: string;
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

export type TeamSpace = {
  id: string;
  idea_id: string;
  title: string;
  created_by: string;
  created_at: string;
  channels: TeamChannel[];
  can_post: boolean;
  can_manage: boolean;
};

export type McpToolCallResult = {
  ok: boolean;
  result?: unknown;
  error?: string;
};
