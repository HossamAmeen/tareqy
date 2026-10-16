#!/usr/bin/env bash
# Renders nginx.conf from the template using variables from .env.
# Usage: deploy/nginx/generate.sh [output-file]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
set -a; source "$ROOT/.env"; set +a

for v in DOMAIN BACKEND_PORT FRONTEND_PORT BACKEND_PATH FRONTEND_PATH MEDIA_PATH STATIC_PATH; do
  [ -n "${!v:-}" ] || { echo "Missing required variable: $v" >&2; exit 1; }
done

OUT="${1:-$ROOT/deploy/nginx/generated/${DOMAIN}.conf}"
mkdir -p "$(dirname "$OUT")"
envsubst '${DOMAIN} ${BACKEND_PORT} ${FRONTEND_PORT} ${BACKEND_PATH} ${FRONTEND_PATH} ${MEDIA_PATH} ${STATIC_PATH}' \
  < "$ROOT/deploy/nginx/templates/nginx.conf.template" > "$OUT"
echo "Generated $OUT"
