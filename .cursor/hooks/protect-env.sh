#!/usr/bin/env bash
# Block staging/committing secrets files (.env). Fail open on parse errors.
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('command') or '')" 2>/dev/null || true)

# Deny git add/commit/stage that clearly targets .env files
if printf '%s' "$cmd" | grep -Eqi 'git[[:space:]]+(add|commit|stage|restore[[:space:]]+--staged)'; then
  if printf '%s' "$cmd" | grep -Eqi '(^|[[:space:]=/])\.env([.[:space:]]|$)|/\.env([.[:space:]]|$)|backend/\.env|frontend/\.env'; then
    printf '%s\n' '{
      "permission": "deny",
      "user_message": "Blocked: do not git-add or commit .env files. Use .env.example for placeholders.",
      "agent_message": "Hook denied a shell command that stages or commits a .env secrets file. Use backend/.env.example / frontend/.env.example instead."
    }'
    exit 0
  fi
fi

printf '%s\n' '{ "permission": "allow" }'
exit 0
