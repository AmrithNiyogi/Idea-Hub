# Authenticator-app MFA (TOTP)

KonnektIdea supports **TOTP authenticator MFA** alongside the existing **email OTP** login path. Microsoft SSO is unchanged and still skips OTP/TOTP.

## SSO-only accounts (no MFA)

Authenticator MFA requires a **usable local password** so enroll/disable can verify credentials.

| Account | `users.has_password` | MFA enroll / confirm / disable |
|---------|----------------------|--------------------------------|
| Seed / password login | `true` | Allowed |
| Microsoft SSO **only** (random unusable hash at create) | `false` | **Rejected** (HTTP 403); Account settings hides the MFA section |
| Seed (or password-linked) **plus** Microsoft SSO | `true` (unchanged on SSO link) | Allowed — password login still works |

Signal on API:

- `GET /api/v1/users/me` → `has_password`
- `GET /api/v1/auth/mfa/totp/status` → `has_password`, `mfa_available` (same meaning)

New SSO users are created with `has_password=false` in `upsert_microsoft_user`. Changing password sets `has_password=true`.

Pre-flag SSO-only rows (created before `users.has_password`) still default to `true` after migration. Correct known SSO-only accounts with:

```sql
UPDATE users SET has_password = false WHERE email = 'user@example.com';
```

## Enroll (signed in)

1. Open **Account** → `/profile` or `/settings`.
2. Under **Authenticator app (MFA)** click **Set up authenticator**.
3. Scan the QR with Google Authenticator, Microsoft Authenticator, or Authy (or enter the base32 secret manually).
4. Enter the 6-digit code → **Confirm and enable**.

API:

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/v1/auth/mfa/totp/status` | cookie | `{ totp_enabled, totp_pending_setup, has_password, mfa_available }` |
| `POST` | `/api/v1/auth/mfa/totp/setup` | cookie | secret + `otpauth://` URI + QR PNG (base64) |
| `POST` | `/api/v1/auth/mfa/totp/confirm` | cookie | `{ "code": "123456" }` → enable MFA |
| `POST` | `/api/v1/auth/mfa/totp/disable` | cookie | `{ "password", "code" }` → clear MFA |

Secrets are Fernet-encrypted at rest (`users.totp_secret`); `users.totp_enabled` gates login.

## Login

1. Email + password on `/login` → `POST /api/v1/auth/send-login-otp`.
2. If MFA is **off**: email OTP is issued (unchanged).
3. If MFA is **on**: the API may skip email when `issue_email_otp=false`; the verify step shows tabs **Email code** | **Authenticator app**.
4. `POST /api/v1/auth/login` with `otp` and optional `otp_method` (`email` | `totp`).  
   When `otp_method` is omitted: TOTP if enrolled, else email OTP.
5. Same JWT cookies as before.

Email OTP + SMTP remain available even when TOTP is enabled.

## Lockout recovery

Backup codes are not implemented yet. If a user loses their authenticator:

1. Prefer self-service disable while they still have the app + password.
2. Otherwise an **admin** clears MFA in Postgres:

```sql
UPDATE users
SET totp_enabled = false, totp_secret = NULL
WHERE email = 'user@example.com';
```

Then the user can sign in with email OTP and re-enroll.

## Test with Google / Microsoft Authenticator

1. `cd backend && uv sync && uv run alembic upgrade head`
2. Sign in with email OTP as a seed user.
3. `/settings` → set up authenticator → scan QR → confirm.
4. Log out → log in with password → on verify, choose **Authenticator app** → enter the rotating code.
5. Switch to **Email code** → Resend → enter the emailed OTP to confirm both paths still work.

## Microsoft env keys (SSO)

Placeholders live in `backend/.env.example` / `settings.py` (never commit real Azure secrets):

- `MICROSOFT_ENABLED`
- `MICROSOFT_CLIENT_ID`
- `MICROSOFT_CLIENT_SECRET`
- `MICROSOFT_TENANT_ID`
- `MICROSOFT_REDIRECT_URI`
- `MICROSOFT_FRONTEND_SUCCESS_URL`
- `MICROSOFT_DEFAULT_ROLE`
- `MICROSOFT_SSO_STATE_TTL_SECONDS`

See [`MICROSOFT_SSO.md`](./MICROSOFT_SSO.md).
