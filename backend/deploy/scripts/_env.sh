# Sourced by the other scripts: loads .env and validates required variables.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
set -a; source "$ROOT/.env"; set +a
for v in DOMAIN BACKEND_PORT BACKEND_PATH STATIC_PATH SYSTEMD_SERVICE_NAME HEALTH_CHECK_PASSWORD; do
  [ -n "${!v:-}" ] || { echo "Missing required variable: $v" >&2; exit 1; }
done
PYBIN="${BACKEND_PATH}/venv/bin/python"
