#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_env.sh"
sudo systemctl restart "$SYSTEMD_SERVICE_NAME"
if [ "${CELERY_ENABLED:-False}" = "True" ]; then
  sudo systemctl restart "${SYSTEMD_SERVICE_NAME}-celery"
fi
