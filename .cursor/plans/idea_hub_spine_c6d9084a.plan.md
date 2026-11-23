---
name: IdeaKonnekt Spine
overview: Scaffold `backend/` (FastAPI + Postgres + Redis) and `frontend/` (Vite + React + TS) from the HTML prototype, mirroring Kompass admin’s email+password → OTP → JWT cookie auth, shipping the IdeaKonnekt spine only (auth, users/roles, ideas lifecycle, explore/detail, engagement, review).
todos:
  - id: infra
    content: Root docker-compose (Postgres+Redis), backend FastAPI scaffold, frontend Vite+React+TS scaffold, .env examples
    status: completed
  - id: auth
    content: "Mirror Kompass admin OTP+JWT auth: send-login-otp, login, refresh, logout, Redis OTP service, cookie JWTs, /users/me"
    status: completed
  - id: domain
    content: "Postgres models + Alembic: users/roles/teams/categories/ideas/status_history/comments/votes/follows + review decisions"
    status: completed
  - id: apis
    content: "Spine APIs: ideas CRUD/draft/submit/lifecycle, explore filters, engagement, review queue+decide, seed 6 demo users"
    status: completed
  - id: frontend
    content: Login 2-step UI, AuthProvider+API client, shell, Home/Explore/Idea detail/Submit/Review/My ideas wired to APIs
    status: completed
  - id: verify
    content: Boot stack, login with seeded user+OTP (console), submit+review golden path smoke
    status: completed
isProject: false
---

# IdeaKonnekt — Spine foundation (auth + core lifecycle)