#!/usr/bin/env bash
# Lightweight post-edit context. Quiet unless the path is high-signal.
set -euo pipefail

input=$(cat)
path=$(printf '%s' "$input" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('file_path') or d.get('path') or d.get('file') or '')
" 2>/dev/null || true)

hint=""
case "$path" in
  *frontend/src/styles/*|*frontend/src/pages/*|*frontend/src/components/*)
    hint="UI edit: keep parity with idea-hub.html and CSS variables in tokens.css."
    ;;
  *backend/app/routers/*)
    hint="Router edit: keep handlers thin; business logic belongs in services."
    ;;
  *backend/app/services/*|*backend/app/repositories/*)
    hint="Backend layer edit: preserve routers→services→repos; no secrets in source."
    ;;
  *backend/alembic/*)
    hint="Migration edit: ensure upgrade/downgrade pair; run alembic upgrade head before seed."
    ;;
  *)
    hint=""
    ;;
esac

if [[ -z "$hint" ]]; then
  printf '%s\n' '{}'
  exit 0
fi

python3 -c "import json,sys; print(json.dumps({'additional_context': sys.argv[1]}))" "$hint"
exit 0
