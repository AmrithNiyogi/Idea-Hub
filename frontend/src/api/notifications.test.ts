import MockAdapter from 'axios-mock-adapter';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  fetchInbox,
  fetchUnreadCount,
  isNotifRead,
  markAllNotifsRead,
  markNotifRead,
} from './notifications';
import { http } from './http';

describe('notifications API', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(http);
  });

  afterEach(() => {
    mock.restore();
  });

  it('normalizes hrefs and maps inbox items', async () => {
    mock.onGet('/notifications').reply(200, {
      unread_count: 1,
      items: [
        {
          id: 'n1',
          kind: 'idea',
          text: 'hi',
          href: '#/ideas/1',
          read: false,
          created_at: '2026-01-01T00:00:00Z',
          idea_id: '1',
        },
        {
          id: 'n2',
          kind: 'idea',
          text: 'x',
          href: '',
          read: true,
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'n3',
          kind: 'idea',
          text: 'y',
          href: 'ideas/2',
          read: false,
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'n4',
          kind: 'idea',
          text: 'z',
          href: '/ideas/3',
          read: false,
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    });
    const items = await fetchInbox('u1', 'contributor');
    expect(items[0].href).toBe('/ideas/1');
    expect(items[1].href).toBe('/');
    expect(items[2].href).toBe('/ideas/2');
    expect(items[3].href).toBe('/ideas/3');
  });

  it('unread count and mark read helpers', async () => {
    mock.onGet('/notifications/unread-count').reply(200, { unread_count: 4 });
    await expect(fetchUnreadCount()).resolves.toBe(4);

    mock.onGet('/notifications/unread-count').reply(200, {});
    await expect(fetchUnreadCount()).resolves.toBe(0);

    mock.onPost('/notifications/n1/read').reply(204);
    await expect(markNotifRead('u1', 'n1')).resolves.toBeUndefined();

    mock.onPost('/notifications/read-all').reply(204);
    await expect(markAllNotifsRead('u1')).resolves.toBeUndefined();
  });

  it('isNotifRead uses item when ids match', () => {
    expect(
      isNotifRead('u1', 'n1', {
        id: 'n1',
        text: '',
        href: '/',
        at: '',
        kind: '',
        read: true,
      }),
    ).toBe(true);
    expect(isNotifRead('u1', 'n1')).toBe(false);
    expect(
      isNotifRead('u1', 'n1', {
        id: 'other',
        text: '',
        href: '/',
        at: '',
        kind: '',
        read: true,
      }),
    ).toBe(false);
  });
});
