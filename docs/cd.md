# CD (staging / production)

> **Status: written but NOT exercised.** `.github/workflows/cd.yml` and `.github/actions/deploy/action.yml` were
> never run, not even on a throwaway host. Expect to debug the first run. CI (`ci.yml`) was verified locally only.

## Flow

1. **Trigger:** CI succeeded on `main` (`workflow_run`), or a tag `vX.Y.Z` is pushed.
2. **build:** builds `backend/docker/production/Dockerfile`, pushes `ghcr.io/<owner>/<repo>/backend:<sha>` (plus `:main` or the tag), and builds the frontend (`vue-tsc -b && vite build`) into a `frontend-dist` artifact.
3. **deploy-staging:** automatic (GitHub Environment `staging`).
4. **deploy-production:** only for tags, after staging succeeds, and only after a reviewer approves the `production` Environment.

Deploy step (`.github/actions/deploy`): rsync `frontend-dist` to `DEPLOY_FRONTEND_PATH`, SSH to the host, `git checkout --detach <sha>` in `DEPLOY_APP_PATH`, then run one of the repo's existing paths:

- `DEPLOY_MODE=systemd` (default): `backend/deploy/scripts/deploy.sh <env>` (pip install, migrate, collectstatic, nginx conf, systemd unit, restart, `healthcheck.sh`).
- `DEPLOY_MODE=docker`: `docker compose --env-file .env -f docker/<env>/docker-compose.yml up --build -d` (builds on the host; the GHCR image is pushed but **not yet pulled** by the compose files, which still use `build:`).

The host owns `backend/.env` (see `backend/.env.example`); CI never writes it.

## Required configuration (names only)

| Where | Name | Purpose |
|---|---|---|
| Environment secrets (`staging`, `production`) | `DEPLOY_HOST`, `DEPLOY_USER` | SSH target |
| | `DEPLOY_SSH_KEY` | private key for that user |
| | `DEPLOY_KNOWN_HOSTS` | `ssh-keyscan` output of the host (strict host checking is on) |
| Environment variables | `DEPLOY_APP_PATH` | repo checkout on the host (contains `backend/.env`) |
| | `DEPLOY_FRONTEND_PATH` | directory nginx serves the SPA from |
| | `DEPLOY_MODE` | `systemd` or `docker` |
| Automatic | `GITHUB_TOKEN` | push to GHCR (needs `packages: write`, set in the workflow) |

GitHub setup: create Environments `staging` and `production`; add **required reviewers** to `production`; restrict it to tags if desired. The host needs git access to the repo, `rsync`, and either the systemd/venv setup or Docker.

## Runbook

- **Deploy staging:** merge to `main` and wait for CI, deploy runs by itself.
- **Promote to production:** `git tag v1.2.3 && git push origin v1.2.3`; approve the `production` deployment in the Actions UI.
- **Roll back:** re-run the CD workflow of the previous good tag (it checks out that exact commit and redeploys), or on the host `git checkout --detach <old-sha>` and rerun `deploy.sh <env>` / compose. Migrations are **not** reversed automatically; write a reverse migration before rolling back across a schema change.
- **Smoke check:** `deploy.sh` runs `healthcheck.sh`; with Docker the compose healthcheck calls `/api/health/`.

## Known gaps / untested

- Never run: SSH/rsync step, heredoc quoting in the composite action, GHCR push, Environment approval flow.
- Image in GHCR is not what gets deployed (hosts build from source); switch compose `build:` to `image:` to use it.
- The Dockerfile uses Python 3.13 while CI tests on 3.12; align one of them.
- No Sentry, backups, uptime alert, or automatic DB rollback.
- Secrets are referenced by name only; none exist yet.
