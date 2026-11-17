---
name: idea-hub-ui-html-parity
description: Port Idea Hub UI from idea-hub.html into the Vite React app while preserving design tokens, layout, and status styling. Use when building or restyling pages, components, CSS, or when the user asks for HTML prototype parity.
---

# UI parity with idea-hub.html

## Source of truth

1. Visual / interaction design → root `idea-hub.html`
2. Token values → `frontend/src/styles/tokens.css` (already ported from HTML)
3. Global layout CSS → `frontend/src/styles/app.css`

## Port workflow

1. Locate the screen/section in `idea-hub.html` (search by route label, heading, or `data-` / class names).
2. List required React pieces: page under `src/pages/`, shell slots, shared components.
3. Reuse before inventing: `AppShell`, `Sidebar`, `Topbar`, `StatusPill`, `IdeaCard`, `Icons`.
4. Map colors/spacing to CSS variables — no new hex unless adding a token both in HTML and `tokens.css`.
5. Wire data through `src/api/*` + types in `src/types/*`; keep presentational props typed.
6. Visually check light theme first; dark theme only if HTML defines matching `[data-theme="dark"]` rules.

## Checklist

- [ ] Same hierarchy and primary CTAs as HTML for that view
- [ ] Status / category / stage colors match tokens
- [ ] Typography uses `--font-sans` / `--font-mono`
- [ ] No divergent “AI purple dashboard” chrome
- [ ] Empty / loading / error states fit existing patterns

## Anti-patterns

- Cards-for-everything when HTML uses flat sections
- Random Tailwind palette instead of tokens
- Duplicating shell chrome inside a page
