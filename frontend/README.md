# KonnektIdea — Frontend (spine)

Vite + React 18 + TypeScript. Cookie JWT auth mirrors Kompass admin (email+password → OTP → login).

## Run

```bash
cd frontend
cp .env.example .env   # VITE_API_BASE_URL= empty → same-origin /api via Vite proxy
npm install
npm run dev            # http://localhost:5173
```

Backend must be on `:8000` with CORS credentials enabled for the Vite origin. Dev OTP is printed in the backend console.

```bash
npm run build          # tsc -b && vite build
npm run preview
```

## Quality gates

Analogous to the backend lint/type/test gate. Run everything with:

```bash
npm run check          # lint + typecheck + test:coverage
```

| Script | What it does |
|--------|----------------|
| `npm run lint` | ESLint flat config (`eslint.config.js`) |
| `npm run typecheck` | `tsc -b` (no emit) |
| `npm run test` | Vitest once, **fail-fast** (`--bail=1`) |
| `npm run test:coverage` | Same + `@vitest/coverage-v8`, **fails under 85%** |
| `npm run format:check` | Optional Prettier check |

**Coverage scope (≥85% lines / functions / branches / statements):**
`src/api`, `src/auth`, `src/utils`, `src/constants`, and presentational
`src/components` (excludes `Icons.tsx` path/avatar helpers, `shell/*`,
`CollabTrackerPanel`). Page shells under `src/pages` are exercised by focused
tests (e.g. Login) but are not part of the coverage threshold — they are large
Router+data UIs; gate the testable core the same way backend gates services/repos.

```bash
npm run test:watch
npm run format         # write Prettier fixes
```

## Routes

| Path | Page |
|------|------|
| `/login` | 2-step OTP login |
| `/` | Home aggregates |
| `/explore` | Search / filters |
| `/ideas/:id` | Detail (+ Delivery tab) |
| `/submit` | Draft + submit |
| `/review`, `/review/:id` | Queue + decide |
| `/my` | Submitted / following / drafts |
| `/ideathons`, `/ideathons/:id` | Phase 2/3 |
| `/recognition` | Phase 2/3 |
| `/people/:id` | Phase 2/3 profile |
