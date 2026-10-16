#!/usr/bin/env bash
# Fails unless the backend becomes healthy. The token is sent as a header and never printed.
set -euo pipefail
source "$(dirname "$0")/_env.sh"
for _ in $(seq 1 30); do
  if curl -fsS -o /dev/null -H "X-Health-Check-Token: ${HEALTH_CHECK_PASSWORD}" "http://127.0.0.1:${BACKEND_PORT}/api/health/"; then
    echo "Backend is healthy."; exit 0
  fi
  sleep 2
done
echo "Backend did not become healthy." >&2; exit 1
