import MockAdapter from 'axios-mock-adapter';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  confirmTotp,
  disableTotp,
  getAuthProviders,
  getCurrentUser,
  getTotpStatus,
  completeLogin,
  login,
  logout,
  microsoftLoginUrl,
  refreshToken,
  sendLoginOtp,
  setupTotp,
  switchRole,
} from './auth';
import { http } from './http';
import { mockUser } from '../test/fixtures';

describe('auth API', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(http);
  });

  afterEach(() => {
    mock.restore();
  });

  it('providers + microsoft URL helpers', async () => {
    mock.onGet('/auth/providers').reply(200, {
      password_otp: true,
      microsoft: true,
    });
    await expect(getAuthProviders()).resolves.toEqual({
      password_otp: true,
      microsoft: true,
    });

    mock.onGet('/auth/providers').reply(500);
    await expect(getAuthProviders()).resolves.toEqual({
      password_otp: true,
      microsoft: false,
    });

    expect(microsoftLoginUrl('/explore')).toContain(
      'redirect=%2Fexplore',
    );
    expect(microsoftLoginUrl('//evil')).not.toContain('redirect=');
    expect(microsoftLoginUrl()).toMatch(/\/auth\/microsoft\/login$/);
  });

  it('sendLoginOtp / login / me / switchRole / logout / refresh', async () => {
    mock.onPost('/auth/send-login-otp').reply(200, {
      message: 'sent',
      email: 'a***@example.com',
      resend_after_seconds: 30,
      totp_enabled: false,
      email_otp_sent: true,
    });
    await expect(
      sendLoginOtp({ email: 'a@example.com', password: 'pw' }),
    ).resolves.toMatchObject({ resend_after_seconds: 30, totp_enabled: false });

    mock.onPost('/auth/login').reply(200, {
      message: 'ok',
      user: mockUser,
      requires_role_selection: false,
    });
    await expect(
      login({
        email: 'a@example.com',
        password: 'pw',
        otp: '123456',
        otp_method: 'email',
      }),
    ).resolves.toMatchObject({ user: mockUser });

    mock.onPost('/auth/complete-login').reply(200, {
      message: 'ok',
      user: { ...mockUser, active_role: 'lead' },
    });
    await expect(
      completeLogin({ login_ticket: 't1', role: 'lead' }),
    ).resolves.toMatchObject({ user: { active_role: 'lead' } });

    mock.onGet('/users/me').reply(200, mockUser);
    await expect(getCurrentUser()).resolves.toEqual(mockUser);

    mock.onPost('/auth/switch-role').reply(200, {
      role: 'reviewer',
      user: { ...mockUser, active_role: 'reviewer' },
    });
    await expect(switchRole('reviewer')).resolves.toMatchObject({
      role: 'reviewer',
    });

    mock.onPost('/auth/logout').reply(204);
    await expect(logout()).resolves.toBeUndefined();

    mock.onPost('/auth/refresh').reply(204);
    await expect(refreshToken()).resolves.toBeUndefined();
  });

  it('TOTP setup / confirm / disable / status', async () => {
    mock.onGet('/auth/mfa/totp/status').reply(200, {
      totp_enabled: false,
      totp_pending_setup: false,
      has_password: true,
      mfa_available: true,
    });
    await expect(getTotpStatus()).resolves.toEqual({
      totp_enabled: false,
      totp_pending_setup: false,
      has_password: true,
      mfa_available: true,
    });

    mock.onPost('/auth/mfa/totp/setup').reply(200, {
      secret: 'S',
      otpauth_uri: 'otpauth://x',
      qr_png_base64: 'xx',
      expires_in_seconds: 300,
    });
    await expect(setupTotp()).resolves.toMatchObject({ secret: 'S' });


    mock.onPost('/auth/mfa/totp/confirm').reply(200, { message: 'ok' });
    await expect(confirmTotp('123456')).resolves.toEqual({ message: 'ok' });

    mock.onPost('/auth/mfa/totp/disable').reply(200, { message: 'off' });
    await expect(
      disableTotp({ password: 'pw', code: '123456' }),
    ).resolves.toEqual({ message: 'off' });
  });

  it('wraps failures as Error with message', async () => {
    // Prefer non-401 for /users/me so the shared refresh interceptor does not
    // attempt a real network refresh against localhost.
    mock.onPost('/auth/send-login-otp').reply(403, { detail: 'bad creds' });
    await expect(
      sendLoginOtp({ email: 'a@example.com', password: 'x' }),
    ).rejects.toThrow('bad creds');

    mock.onPost('/auth/login').reply(403, { detail: 'bad otp' });
    await expect(
      login({ email: 'a@example.com', password: 'x', otp: '000000' }),
    ).rejects.toThrow('bad otp');

    mock.onGet('/users/me').reply(403, { detail: 'no session' });
    await expect(getCurrentUser()).rejects.toThrow('no session');

    mock.onPost('/auth/logout').reply(500, { detail: 'fail' });
    await expect(logout()).rejects.toThrow('fail');

    mock.onPost('/auth/switch-role').reply(403, { detail: 'forbidden' });
    await expect(switchRole('admin')).rejects.toThrow('forbidden');

    mock.onGet('/auth/mfa/totp/status').reply(500, { detail: 'nope' });
    await expect(getTotpStatus()).rejects.toThrow('nope');

    mock.onPost('/auth/mfa/totp/setup').reply(500, { detail: 'setup fail' });
    await expect(setupTotp()).rejects.toThrow('setup fail');

    mock.onPost('/auth/mfa/totp/confirm').reply(400, { detail: 'bad code' });
    await expect(confirmTotp('000000')).rejects.toThrow('bad code');

    mock.onPost('/auth/mfa/totp/disable').reply(400, { detail: 'bad' });
    await expect(
      disableTotp({ password: 'x', code: '000000' }),
    ).rejects.toThrow('bad');
  });
});
