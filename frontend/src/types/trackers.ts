/** External tracker / integration providers, connections, and idea links. */

export type TrackerConnectField = {
  key: string;
  label: string;
  secret: boolean;
  required: boolean;
  placeholder: string;
  help_text: string;
  /** When true, Integrations UI nests the field under Advanced. */
  advanced?: boolean;
};

export type TrackerProvider = {
  id: string;
  display_name: string;
  description: string;
  auth_mode: string;
  connect_fields: TrackerConnectField[];
};

export type IntegrationCategory = 'tracker' | 'docs' | 'chat' | 'sheets';

export type IntegrationProvider = {
  id: string;
  display_name: string;
  description: string;
  category: IntegrationCategory | string;
  status: 'available' | 'coming_soon';
  auth_mode: string;
  connect_fields: TrackerConnectField[];
  coming_soon_note: string;
  connectable: boolean;
};

export type ConnectionScope = 'user' | 'organization';

export type TrackerConnection = {
  id: string;
  provider_id: string;
  label: string;
  display_label: string;
  scope: ConnectionScope;
  external_account_id: string;
  meta: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type EffectiveConnection = {
  provider_id: string;
  source: 'user' | 'organization' | 'none';
  connection: TrackerConnection | null;
};

export type IdeaTrackerLink = {
  id: string;
  idea_id: string;
  connection_id: string | null;
  provider_id: string;
  external_id: string;
  external_key: string;
  external_url: string;
  title: string;
  created_by: string;
  created_at: string;
  meta: Record<string, unknown>;
};

export type TrackerConnectionCreateBody = {
  provider_id: string;
  label?: string;
  credentials: Record<string, string>;
};

export type IdeaTrackerLinkCreateBody = {
  connection_id?: string;
  provider_id?: string;
  mode: 'create' | 'link';
  title?: string;
  description?: string;
  external_id_or_url?: string;
  extra?: Record<string, unknown>;
};

export type RemoteAssignee = {
  id: string;
  name: string;
  email: string;
  avatar_url?: string;
  idea_hub_user_id?: string | null;
};

export type RemoteStatusOption = {
  id: string;
  name: string;
  color: string;
  type: string;
};

export type RemotePriorityOption = {
  id: string;
  name: string;
  color: string;
};

/** Stored link + live remote fields from GET …/tracker-links/live */
export type LiveTrackerTask = {
  link_id: string;
  provider_id: string;
  external_id: string;
  external_key: string;
  external_url: string;
  stored_title: string;
  title: string;
  status: string;
  status_id: string;
  status_color: string;
  status_type: string;
  priority: string;
  priority_id: string;
  priority_color: string;
  due_date: string;
  url: string;
  assignees: RemoteAssignee[];
  assignable: RemoteAssignee[];
  status_options: RemoteStatusOption[];
  priority_options: RemotePriorityOption[];
  editable_fields: string[];
  live: boolean;
  error: string | null;
  can_update_status: boolean;
  can_update: boolean;
};

export type IdeaTrackerRemoteUpdateBody = {
  status?: string;
  title?: string;
  priority?: string;
  due_date?: string;
  assignee_ids?: string[];
  /** Notion: append markdown/plain text as new page blocks. */
  append_content?: string;
};
