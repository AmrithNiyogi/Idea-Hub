---
name: idea-hub-auth-otp
description: IdeaKonnekt JWT cookie auth with Redis OTP and SMTP delivery (Kompass-admin pattern). Use when changing login, OTP, cookies, auth dependencies, SMTP, or debugging send-login-otp / login failures.
---

# Auth — OTP + JWT cookies

## Flow

1. `POST /api/v1/auth/send-login-otp` — verify email+password, store OTP in Redis, email via SMTP
2. `POST /api/v1/auth/login` — verify OTP, set access + refresh JWT cookies
3. Authenticated calls use cookie JWT; `GET /api/v1/users/me` for session
4. Refresh / logout via auth router (same cookie model)

## Key modules

| Concern | Location |
|---------|----------|
| Settings / SMTP / cookie flags | `backend/app/config/settings.py`, `.env.example` |
| OTP Redis TTL / attempts | `login_otp_service` (+ Redis client in `db/session`) |
| JWT + cookies | `auth_service`, `utils/cookies.py` |
| Deps | `dependencies/auth.py`, phase actors in `phase23_auth.py` |
| Frontend | `frontend/src/auth/*`, `api/auth.ts`, `pages/Login.tsx` |

## Env rules

- Copy placeholders from `backend/.env.example` → `backend/.env` only
- `OTP_EMAIL_OVERRIDE` / `NOTIFY_EMAIL_OVERRIDE` for shared inboxes in dev
- `ENV=dev`: OTP also logged to uvicorn console if send path allows
- Never commit real `SMTP_PASSWORD` or `JWT_SECRET_KEY`

## Frontend contract

- `VITE_API_BASE_URL` points at API; fetch with `credentials: 'include'`
- CORS: backend `FRONTEND_ORIGIN` must match Vite origin (`http://localhost:5173`)
- Cookie: local `COOKIE_SECURE=false`, `COOKIE_SAMESITE=lax`

## Debug order

1. Password wrong vs OTP wrong vs Redis down vs SMTP fail
2. Check Redis with `dev-services.sh status` / Redis CLI on `16379`
3. Confirm override email vs console OTP in logs
4. Cookie not set → CORS / SameSite / wrong origin
