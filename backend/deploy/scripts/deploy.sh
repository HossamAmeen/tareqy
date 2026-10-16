#!/usr/bin/env bash
# Usage: deploy/scripts/deploy.sh <staging|production>
set -euo pipefail
ENVIRONMENT="${1:?usage: deploy.sh <staging|production>}"
case "$ENVIRONMENT" in staging|production) ;; *) echo "Unknown environment" >&2; exit 1;; esac

DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/_env.sh"

echo "Deploying $ENVIRONMENT to $DOMAIN"
cd "$BACKEND_PATH"
"$BACKEND_PATH/venv/bin/pip" install -r requirements/production.txt
"$DIR/migrate.sh"
"$DIR/collectstatic.sh"
"$ROOT/deploy/nginx/generate.sh" "$ROOT/deploy/nginx/generated/${DOMAIN}.conf"

envsubst '${SYSTEMD_SERVICE_NAME} ${BACKEND_PATH} ${BACKEND_PORT}' \
  < "$ROOT/deploy/systemd/templates/backend.service.template" \
  | sudo tee "/etc/systemd/system/${SYSTEMD_SERVICE_NAME}.service" > /dev/null
sudo systemctl daemon-reload

"$DIR/restart.sh"
"$DIR/healthcheck.sh"
