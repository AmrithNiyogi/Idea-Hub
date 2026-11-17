export type Role =
  | 'contributor'
  | 'reviewer'
  | 'lead'
  | 'leadership'
  | 'admin';

export type OtpMethod = 'email' | 'totp';

export interface User {
  id: string;
  email: string;
  name: string;
  title: string;
  team_id: string | null;
  roles: Role[];
  primary_role: Role;
  active_role: Role;
  status: string;
  avatar: number;
  /** Optional profile image (https or /uploads/avatars/…). */
  avatar_url?: string | null;
  slug: string;
  /** Authenticator-app MFA enrolled and confirmed. */
  totp_enabled?: boolean;
  /**
   * True when password login is available.
   * False for Microsoft SSO-only accounts (MFA enroll hidden).
   */
  has_password?: boolean;
}

export interface SendLoginOtpResponse {
  message: string;
  email: string;
  resend_after_seconds: number;
  totp_enabled: boolean;
  email_otp_sent: boolean;
}

export interface LoginResponse {
  message: string;
  user?: User | null;
  /** When true, cookies are not set; redeem via completeLogin. */
  requires_role_selection?: boolean;
  login_ticket?: string | null;
  roles?: Role[];
  primary_role?: Role | null;
  name?: string | null;
}

/** Result of OTP verify when the account must pick a role before session cookies. */
export interface RoleSelectionPending {
  login_ticket: string;
  roles: Role[];
  primary_role: Role;
  name: string;
}

export interface SwitchRoleResponse {
  role: Role;
  user: User;
}

export interface AuthProviders {
  password_otp: boolean;
  microsoft: boolean;
}

export interface TotpSetupResponse {
  secret: string;
  otpauth_uri: string;
  qr_png_base64: string;
  expires_in_seconds: number;
}

export interface TotpStatusResponse {
  totp_enabled: boolean;
  totp_pending_setup: boolean;
  /** Usable local password path (false for SSO-only). */
  has_password: boolean;
  /** Same as has_password — whether MFA enroll/disable UI should show. */
  mfa_available: boolean;
}
