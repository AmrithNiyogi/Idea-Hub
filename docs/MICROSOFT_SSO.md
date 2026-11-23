# Microsoft Entra ID (Azure AD) sign-in

IdeaKonnekt supports **Microsoft work/school account** OIDC alongside the existing email + password + OTP flow. This is standard Entra ID / Azure AD OAuth — the same identity M365 and Teams users already have. It is **not** a Teams bot.

OTP is **skipped** for Microsoft SSO. Successful SSO sets the same httpOnly JWT cookies as password login.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/auth/providers` | Public flags: `{ password_otp, microsoft }` |
| `GET` | `/api/v1/auth/microsoft/login?redirect=/` | 302 → Microsoft authorize (state+nonce in Redis) |
| `GET` | `/api/v1/auth/microsoft/callback` | Code exchange → validate `id_token` → upsert user → set cookies → 302 frontend |

When Azure credentials are missing or `MICROSOFT_ENABLED=false`, login/callback return **503** with `"Microsoft sign-in is not configured"` (callback failures that occur mid-flow redirect to `/login?error=…` instead).

## Environment variables

Copy placeholders from `backend/.env.example` into gitignored `backend/.env`:

| Variable | Example | Notes |
|----------|---------|--------|
| `MICROSOFT_ENABLED` | `true` | Master switch |
| `MICROSOFT_CLIENT_ID` | *(app registration Application ID)* | Required |
| `MICROSOFT_CLIENT_SECRET` | *(client secret value)* | Required; never commit |
| `MICROSOFT_TENANT_ID` | `common` | Authority: `common` (orgs + MSA), `organizations` (work/school only), or a directory GUID (single-tenant). **Must match** Azure Supported account types |
| `MICROSOFT_REDIRECT_URI` | `http://localhost:8000/api/v1/auth/microsoft/callback` | Must match Azure **exactly**. For ngrok UI + Vite `/api` proxy, use `https://<host>/api/v1/auth/microsoft/callback` |
| `MICROSOFT_FRONTEND_SUCCESS_URL` | `http://localhost:5173/` | Default landing after SSO when no relative `redirect` was requested; origin used for other paths |
| `MICROSOFT_DEFAULT_ROLE` | `contributor` | Role for newly created SSO users |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS + login-error redirect base; SSO success prefers `MICROSOFT_FRONTEND_SUCCESS_URL` |
| `CORS_ORIGINS` | *(optional)* | Comma-separated extra origins (e.g. keep `http://localhost:5173` when `FRONTEND_ORIGIN` is ngrok) |

Frontend (optional):

| Variable | Effect |
|----------|--------|
| `VITE_MICROSOFT_AUTH_ENABLED` | Set `false` to hide the button even if the API reports Microsoft ready |
| `VITE_API_BASE_URL` | API origin. **Leave empty** for same-origin `/api/v1` (Vite proxies to uvicorn). Absolute `http://localhost:8000` breaks HTTPS ngrok (mixed content → Microsoft button hidden) |

## Azure app registration

1. Azure Portal → **Microsoft Entra ID** → **App registrations** → **New registration**.
2. Name: e.g. `IdeaKonnekt`.
3. **Supported account types** (Authentication / registration wizard) — pick to match demo needs:
   - *Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant)* → use `MICROSOFT_TENANT_ID=organizations` or `common`
   - *Multitenant + personal Microsoft accounts* → use `MICROSOFT_TENANT_ID=common`
   - *This organizational directory only (Single tenant)* → use the directory GUID; **other-org / personal accounts fail** with AADSTS50020 (“does not exist in tenant Default Directory”) unless invited as guests
4. **Redirect URI**: platform **Web** — register **each** URI you will use (Azure allows multiple):
   - Local API: `http://localhost:8000/api/v1/auth/microsoft/callback`
   - Ngrok UI + Vite proxy: `https://<your-subdomain>.ngrok-free.app/api/v1/auth/microsoft/callback`
   - Production HTTPS callback when deploying  
   `MICROSOFT_REDIRECT_URI` in `.env` must equal **one** of these for the current session.
5. Register → copy **Application (client) ID** → `MICROSOFT_CLIENT_ID`.
6. **Certificates & secrets** → **New client secret** → copy the **Value** once → `MICROSOFT_CLIENT_SECRET`.
7. Set `MICROSOFT_TENANT_ID` to `common` / `organizations` (multitenant) **or** the **Directory (tenant) ID** GUID only for single-tenant.
8. **API permissions** → Microsoft Graph (delegated):
   - `openid`
   - `profile`
   - `email`
   - `User.Read`
9. Grant admin consent if your tenant requires it.
10. Set `MICROSOFT_ENABLED=true` in `backend/.env` and restart uvicorn.

### Fix: “Selected user account does not exist in tenant Default Directory” (AADSTS50020)

The app registration is still **single-tenant**, or `MICROSOFT_TENANT_ID` is a directory GUID, while the picker account is from another org / personal MSA.

**In Azure Portal (required — env alone cannot override this):**

1. **Microsoft Entra ID** → **App registrations** → app `d9d41ca3-…` (IdeaKonnekt).
2. **Authentication** (or **Manifest** if the blade is locked) → **Supported account types**.
3. Select **Accounts in any organizational directory (Multitenant)**  
   — or **Multitenant + personal Microsoft accounts** if you need `@outlook.com` / MSA.
4. Save. Optionally under **Users** invite the person as a **guest** if you must stay single-tenant.

**In `backend/.env`:** set `MICROSOFT_TENANT_ID=common` (or `organizations`), restart uvicorn. IdeaKonnekt already accepts multi-tenant `iss` values when authority is `common` / `organizations` / `consumers`.

### Optional: expose email claim

If `id_token` lacks `email` / `preferred_username` with `@`, add an optional claim under **Token configuration** → **Add optional claim** → ID → `email`, or ensure users have a mail / UPN in Entra.

## User linking behaviour

- Email from the validated `id_token` (`email`, else `preferred_username` / `upn`) is normalized to lowercase.
- If a user already exists (including seed users), they are signed in and linked by email.
- If the email is new, IdeaKonnekt creates an **active** user with `MICROSOFT_DEFAULT_ROLE` (default `contributor`) and a random unusable password hash (password+OTP login will not work until a password is set by other means).

## Local test plan

1. Fill Azure values in `backend/.env`; keep OTP SMTP config intact.
2. `uv sync` (pulls `httpx`) and restart the API.
3. Confirm providers:

   ```bash
   curl -s http://127.0.0.1:8000/api/v1/auth/providers
   # {"password_otp":true,"microsoft":true}
   ```

4. Open `http://localhost:5173/login` → **Sign in with Microsoft** (full-page redirect).
5. Sign in with a work account in the registered tenant (or any org if `common`).
6. You should land on `/` (or `?redirect=`) with cookies set; `GET /api/v1/users/me` should succeed.
7. Repeat with an email that matches a seed user → same roles as seed; with a brand-new email → contributor (or configured default).

### Curl authorize redirect (browser still required for consent)

```bash
curl -sI 'http://127.0.0.1:8000/api/v1/auth/microsoft/login?redirect=/'
# Location: https://login.microsoftonline.com/.../oauth2/v2.0/authorize?...
```

## Ngrok frontend (HTTPS UI, local API)

Symptom: login page on `https://<subdomain>.ngrok-free.app/login` shows email/password only — **no Microsoft button**.

Cause: the page called `http://localhost:8000` from an HTTPS origin (mixed content / failed `/auth/providers` probe → UI assumes `microsoft: false`). Even if the button appeared, Azure `redirect_uri` must be a URI the browser can hit after consent, and post-SSO cookies must be set on the **same host** the UI uses for `/api`.

Recommended setup (single ngrok tunnel to Vite only):

1. Frontend: `VITE_API_BASE_URL=` (empty) so the client uses same-origin `/api/v1`. Vite already proxies `/api` → `http://127.0.0.1:8000`.
2. Backend `.env` (example host `ddca-106-51-110-255.ngrok-free.app`):

   ```env
   FRONTEND_ORIGIN=https://ddca-106-51-110-255.ngrok-free.app
   CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   MICROSOFT_REDIRECT_URI=https://ddca-106-51-110-255.ngrok-free.app/api/v1/auth/microsoft/callback
   MICROSOFT_FRONTEND_SUCCESS_URL=https://ddca-106-51-110-255.ngrok-free.app/
   ```

3. Azure Portal → App registration → **Authentication** → add Web redirect URI:

   `https://ddca-106-51-110-255.ngrok-free.app/api/v1/auth/microsoft/callback`

   Keep the localhost callback registered if you still SSO against `:8000` without ngrok.

4. Restart uvicorn (settings are cached at import) and restart `npm run dev` after changing `frontend/.env`.
5. Open the ngrok login URL → confirm **Sign in with Microsoft** → complete Entra login → land on ngrok `/` with session.

You do **not** need a second ngrok tunnel for the API when using the Vite proxy. If the ngrok hostname changes, update Azure + the three `MICROSOFT_*` / `FRONTEND_ORIGIN` URLs together.

## Security notes

- State and nonce live in Redis (`ms_oauth_state:*`, TTL 600s) and are one-time use.
- `id_token` is verified with Microsoft JWKS (RS256), audience = client ID, nonce match, trusted issuer.
- Frontend `redirect` query is restricted to same-app relative paths (open-redirect safe).
- Do not commit real client secrets; only placeholders belong in `.env.example`.
