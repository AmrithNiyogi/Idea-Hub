/**
 * Persisted notifications inbox API.
 *
 * Replaces the previous client-side aggregate + localStorage read state.
 * Follow on an idea = subscribe to subsequent idea-scoped notifications.
 */

import { http } from './http';

export interface InboxItem {
  id: string;
  text: string;
  href: string;
  at: string;
  kind: string;
  read: boolean;
  idea_id?: string | null;
}

interface NotificationDto {
  id: string;
  kind: string;
  idea_id?: string | null;
  text: string;
  href: string;
  read: boolean;
  meta?: Record<string, unknown>;
  created_at: string;
}

interface NotificationListDto {
  items: NotificationDto[];
  unread_count: number;
}

interface UnreadCountDto {
  unread_count: number;
}

function normalizeHref(href: string): string {
  if (!href) return '/';
  if (href.startsWith('#')) return href.slice(1) || '/';
  return href.startsWith('/') ? href : `/${href}`;
}

function toInboxItem(n: NotificationDto): InboxItem {
  return {
    id: n.id,
    text: n.text,
    href: normalizeHref(n.href),
    at: n.created_at,
    kind: n.kind,
    read: n.read,
    idea_id: n.idea_id,
  };
}

export async function fetchInbox(_userId?: string, _role?: string): Promise<InboxItem[]> {
  const { data } = await http.get<NotificationListDto>('/notifications', {
    params: { limit: 40 },
  });
  return (data.items ?? []).map(toInboxItem);
}

export async function fetchUnreadCount(): Promise<number> {
  const { data } = await http.get<UnreadCountDto>('/notifications/unread-count');
  return data.unread_count ?? 0;
}

export async function markNotifRead(_userId: string, id: string): Promise<void> {
  await http.post(`/notifications/${id}/read`);
}

export async function markAllNotifsRead(_userId: string, _ids?: string[]): Promise<void> {
  await http.post('/notifications/read-all');
}

/** @deprecated Read state is server-persisted; kept for Topbar compatibility. */
export function isNotifRead(_userId: string, id: string, item?: InboxItem): boolean {
  if (item && item.id === id) return item.read;
  return false;
}
