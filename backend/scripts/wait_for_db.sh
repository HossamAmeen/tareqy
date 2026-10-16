#!/usr/bin/env bash
# Waits until the database in DATABASE_URL accepts TCP connections (no-op for SQLite).
set -euo pipefail

python - <<'PY'
import os, socket, sys, time
from urllib.parse import urlparse

url = urlparse(os.environ.get("DATABASE_URL", ""))
if not url.scheme.startswith("postgres"):
    sys.exit(0)

host, port = url.hostname, url.port or 5432
for _ in range(60):
    try:
        socket.create_connection((host, port), timeout=2).close()
        sys.exit(0)
    except OSError:
        time.sleep(1)
print(f"Database {host}:{port} not reachable", file=sys.stderr)
sys.exit(1)
PY
