# في طريقي — frontend

Vue 3 + TypeScript + Vite + Pinia PWA (RTL, Arabic).

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server (proxies `/api` to `http://localhost:8000`, override with `VITE_API_PROXY`) |
| `npm test` | Unit/component tests (Vitest) |
| `npm run lint` | ESLint |
| `npm run build` | Type-check and production build |
| `npm run test:e2e` | Browser end-to-end tests (Playwright, Chromium) |

`npm ci` works as-is: `.npmrc` sets `legacy-peer-deps` because `openapi-typescript` has not yet allowed TypeScript 6.

## End-to-end tests

The suite drives the real UI in Chromium against a real Django backend and a real Vite dev server. Nothing is mocked except the browser's geolocation (set to the seeded «المحطة» area) and the SMS provider.

One-time setup:

```sh
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements/development.txt   # backend deps
cd ../frontend && npm ci && npx playwright install --with-deps chromium
```

Run (from `frontend/`; starts and stops both servers itself):

```sh
npm run test:e2e                       # everything
npx playwright test e2e/trip-flow.e2e.ts -g AC8   # one spec / test
E2E_PYTHON=python npm run test:e2e     # use another Python (default: ../backend/.venv/bin/python)
```

Ports: backend `8100` (`E2E_BACKEND_PORT`), frontend `5174` (`E2E_FRONTEND_PORT`). Servers are never reused, so stop anything on those ports first.

How it is wired:

- `e2e/backend.sh` deletes `backend/e2e.sqlite3`, migrates, seeds (`manage.py e2e_seed`: the three areas with coordinates, compatibility rules, and a staff user) and serves with `config.settings.e2e`.
- `config.settings.e2e` (backend, e2e only) keeps OTP codes in memory, removes the OTP resend delay, raises throttle limits, and keeps driver verification **on**. The URL module `e2e_support` adds two test-only endpoints: `GET /e2e/otp/?phone=` (latest code) and `POST /e2e/expire/<id>/` (force a request past its expiry). They exist only under these settings.
- Tests sign in through the real OTP screens, in separate browser contexts for customer, driver and staff. Drivers are verified through the admin dashboard, as in production.
- Tests share one database and run serially; each uses fresh phone numbers and unique request notes.

What is covered (acceptance criteria of business doc §20):

| Spec | Covers |
|---|---|
| `customer-requests.e2e.ts` | AC1, AC2 (UI and API), edit and cancel a request |
| `driver-matching.e2e.ts` | AC3 (verification gate, toggle, location freshness), AC4, AC5, AC6, AC7, AC11, non-matching requests hidden |
| `trip-flow.e2e.ts` | AC8 (two customer tabs confirming different drivers), AC9, AC10, AC12 (expiry during confirmation), AC13 (offline then reconnect shows server state), AC14 (status history), trip cancel before start, problem report resolved by staff |
| `admin.e2e.ts` | Dashboard for staff, denied for customers/drivers, suspending an account blocks sign-in |

Not covered: real Web Push delivery, the PWA install prompt / service worker (the dev server does not register it), real SMS, and the truly simultaneous double-confirm (that needs PostgreSQL row locks and is tested in the backend suite).
