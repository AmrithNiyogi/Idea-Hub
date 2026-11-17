import { http, getApiErrorMessage, API_BASE_URL } from './http';
import type {
  AuthProviders,
  LoginResponse,
  OtpMethod,
  SendLoginOtpResponse,
  SwitchRoleResponse,
  TotpSetupResponse,
  TotpStatusResponse,
  User,
} from '../types/auth';

export async function getAuthProviders(): Promise<AuthProviders> {
  try {
    const res = await http.get<AuthProviders>('/auth/providers');
    return res.data;
  } catch {
    return { password_otp: true, microsoft: false };
  }
}

/**
 * Full-page redirect into Microsoft Entra ID authorize (not an XHR).
 * Cookies are set on the API callback before returning to the frontend.
 */
export function microsoftLoginUrl(redirect?: string | null): string {
  const params = new URLSearchParams();
  if (redirect && /^\/(?!\/|\\)/.test(redirect)) {
    params.set('redirect', redirect);
  }
  const qs = params.toString();
  return `${API_BASE_URL}/auth/microsoft/login${qs ? `?${qs}` : ''}`;
}

export async function sendLoginOtp(data: {
  email: string;
  password: string;
  /** When false, skip email OTP (for authenticator-first login). */
  issue_email_otp?: boolean;
}): Promise<SendLoginOtpResponse> {
  try {
    const res = await http.post<SendLoginOtpResponse>('/auth/send-login-otp', {
      email: data.email,
      password: data.password,
      issue_email_otp: data.issue_email_otp ?? true,
    });
    return res.data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}

export async function login(data: {
  email: string;
  password: string;
  otp: string;
  otp_method?: OtpMethod;
}): Promise<LoginResponse> {
  try {
    const res = await http.post<LoginResponse>('/auth/login', data);
    return res.data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}

export async function completeLogin(data: {
  login_ticket: string;
  role: string;
}): Promise<LoginResponse> {
  try {
    const res = await http.post<LoginResponse>('/auth/complete-login', data);
    return res.data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}

export async function refreshToken(): Promise<void> {
  await http.post('/auth/refresh');
}

export async function getCurrentUser(): Promise<User> {
  try {
    const res = await http.get<User>('/users/me');
    return res.data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}

export async function logout(): Promise<void> {
  try {
    await http.post('/auth/logout');
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}

export async function switchRole(role: string): Promise<SwitchRoleResponse> {
  try {
    const res = await http.post<SwitchRoleResponse>('/auth/switch-role', {
      role,
    });
    return res.data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}

export async function getTotpStatus(): Promise<TotpStatusResponse> {
  try {
    const res = await http.get<TotpStatusResponse>('/auth/mfa/totp/status');
    return res.data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}

export async function setupTotp(): Promise<TotpSetupResponse> {
  try {
    const res = await http.post<TotpSetupResponse>('/auth/mfa/totp/setup');
    return res.data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}

export async function confirmTotp(code: string): Promise<{ message: string }> {
  try {
    const res = await http.post<{ message: string }>('/auth/mfa/totp/confirm', {
      code,
    });
    return res.data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}

export async function disableTotp(data: {
  password: string;
  code: string;
}): Promise<{ message: string }> {
  try {
    const res = await http.post<{ message: string }>(
      '/auth/mfa/totp/disable',
      data,
    );
    return res.data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error));
  }
}
