import MockAdapter from 'axios-mock-adapter';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { accountApi, avatarAbsoluteUrl } from './account';
import { API_BASE_URL, http } from './http';
import { mockUser } from '../test/fixtures';

describe('avatarAbsoluteUrl', () => {
  it('handles empty, absolute, data, uploads, and passthrough', () => {
    expect(avatarAbsoluteUrl(null)).toBeNull();
    expect(avatarAbsoluteUrl(undefined)).toBeNull();
    expect(avatarAbsoluteUrl('https://cdn/x.png')).toBe('https://cdn/x.png');
    expect(avatarAbsoluteUrl('data:image/png;base64,xx')).toMatch(/^data:/);
    const origin = API_BASE_URL.replace(/\/api\/v1\/?$/, '');
    expect(avatarAbsoluteUrl('/uploads/avatars/a.png')).toBe(
      `${origin}/uploads/avatars/a.png`,
    );
    expect(avatarAbsoluteUrl('relative/path')).toBe('relative/path');
  });
});

describe('accountApi', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(http);
  });

  afterEach(() => {
    mock.restore();
    vi.unstubAllGlobals();
  });

  it('me / updateMe / changePassword / uploadAvatar', async () => {
    mock.onGet('/users/me').reply(200, mockUser);
    await expect(accountApi.me()).resolves.toEqual(mockUser);

    mock.onPatch('/users/me').reply(200, { ...mockUser, name: 'Bob' });
    await expect(accountApi.updateMe({ name: 'Bob' })).resolves.toMatchObject({
      name: 'Bob',
    });

    mock.onPost('/users/me/password').reply(200, { message: 'ok' });
    await expect(
      accountApi.changePassword({
        current_password: 'a',
        new_password: 'b',
        confirm_password: 'b',
      }),
    ).resolves.toEqual({ message: 'ok' });

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockUser,
      }),
    );
    const file = new File(['x'], 'a.png', { type: 'image/png' });
    await expect(accountApi.uploadAvatar(file)).resolves.toEqual(mockUser);
  });

  it('throws wrapped errors', async () => {
    // Avoid 401 here — http interceptor would attempt session refresh.
    mock.onGet('/users/me').reply(403, { detail: 'gone' });
    await expect(accountApi.me()).rejects.toThrow('gone');

    mock.onPatch('/users/me').reply(400, { detail: 'bad' });
    await expect(accountApi.updateMe({})).rejects.toThrow('bad');

    mock.onPost('/users/me/password').reply(400, { detail: 'weak' });
    await expect(
      accountApi.changePassword({
        current_password: 'a',
        new_password: 'b',
        confirm_password: 'b',
      }),
    ).rejects.toThrow('weak');

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 413,
        statusText: 'Too Large',
        json: async () => ({ detail: 'too big' }),
      }),
    );
    await expect(
      accountApi.uploadAvatar(new File(['x'], 'a.png')),
    ).rejects.toMatchObject({ message: 'too big', status: 413 });

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Server Error',
        json: async () => {
          throw new Error('not json');
        },
        text: async () => 'oops',
      }),
    );
    await expect(
      accountApi.uploadAvatar(new File(['x'], 'a.png')),
    ).rejects.toMatchObject({ status: 500 });
  });
});
