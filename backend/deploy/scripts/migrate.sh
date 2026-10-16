#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_env.sh"
cd "$BACKEND_PATH" && "$PYBIN" manage.py migrate --noinput
