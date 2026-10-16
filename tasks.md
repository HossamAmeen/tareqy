# في طريقي — Tasks per Sprint

**Stack:** Django + DRF (PostgreSQL, Celery/Redis) · Vue 3 + Vite + Pinia + vite-plugin-pwa
**Legend:** `BE` backend · `FE` frontend · `OPS` devops · `QA` tests · **SP** story points (1/2/3/5/8)
**Repo layout:** `backend/` (apps: accounts, areas, trips, matching, notifications, reports, adminpanel) · `frontend/`

---

## Sprint 0 — Decisions & Setup

| ID | Type | Task | SP |
|---|---|---|---|
| S0-1 | Doc | Resolve the 9 open decisions (doc §18); record in `docs/decisions.md` | 3 |
| S0-2 | Doc | Define launch city, Areas list, and area-compatibility matrix | 3 |
| S0-3 | OPS | Init `backend/` (Django 5, DRF, drf-spectacular, psycopg, pytest-django, ruff) | 2 |
| S0-4 | OPS | Init `frontend/` (Vue 3, Vite, TS, Pinia, vue-router, vite-plugin-pwa, vitest) | 2 |
| S0-5 | OPS | docker-compose: postgres, redis, backend, frontend; fill Makefile targets | 3 |
| S0-6 | OPS | CI: lint + tests for both apps | 2 |
| S0-7 | Design | Low-fi mobile wireframes for the 9 screens (RTL, Arabic) | 5 |
| S0-8 | Doc | KPI definitions (formulas, test-data exclusion) | 1 |

---

## Sprint 1 — Accounts & Data Foundation

| ID | Type | Task | SP |
|---|---|---|---|
| S1-1 | BE | Custom `User` (phone login, `account_status`, role flags customer/driver/admin) | 3 |
| S1-2 | BE | Phone OTP auth (request/verify) + JWT (simplejwt) + throttling | 5 |
| S1-3 | BE | Models: `Area`, `AreaCompatibility`, `DriverProfile` + migrations | 3 |
| S1-4 | BE | Models: `TripRequest`, `DriverInterest` (unique `trip_request,driver`), `Trip` (partial unique constraint: one active trip per request), `Notification`, `Report` | 5 |
| S1-5 | BE | `StatusEvent` audit model + helper to log every transition | 2 |
| S1-6 | BE | Seed command for Areas + compatibility | 2 |
| S1-7 | BE | Endpoints: `GET /me`, `PATCH /me`, `GET /areas`; permissions classes (IsDriver, IsCustomer, IsAdmin) | 3 |
| S1-8 | BE | Global DRF settings: pagination, throttle rates, error format, OpenAPI schema | 2 |
| S1-9 | FE | App shell: RTL layout, router, Pinia, axios client + token refresh | 3 |
| S1-10 | FE | Login / OTP screens + role selection home | 5 |
| S1-11 | FE | PWA manifest, service worker, install prompt, offline fallback page | 3 |
| S1-12 | QA | Tests: auth flow, constraints, permissions | 3 |

---

## Sprint 2 — Customer Trip Requests

| ID | Type | Task | SP |
|---|---|---|---|
| S2-1 | BE | `TripRequest` serializer w/ validation (pickup ≠ destination, required fields, optional notes/preferred time) | 3 |
| S2-2 | BE | `POST/GET/PATCH /requests/`, `POST /requests/{id}/cancel/` (customer-scoped queryset) | 5 |
| S2-3 | BE | Request state machine service (`OPEN→CONFIRMED/CANCELLED/EXPIRED`), server-side transition checks, audit log | 5 |
| S2-4 | BE | `expires_at` from settings (`REQUEST_TTL_MINUTES`); Celery beat task to mark `EXPIRED` | 3 |
| S2-5 | BE | Substantial edit (pickup/destination change) → withdraw existing interests + notify | 3 |
| S2-6 | FE | Create-request screen (area pickers, notes, location precision indicator) | 5 |
| S2-7 | FE | "My requests" list + detail with live status (polling) | 5 |
| S2-8 | FE | Edit/cancel flows with confirmation dialogs | 3 |
| S2-9 | QA | Tests: invalid create rejected, transitions, expiry task, cancel stops matching | 5 |

---

## Sprint 3 — Driver Mode & Matching

| ID | Type | Task | SP |
|---|---|---|---|
| S3-1 | BE | `DriverProfile` endpoints: toggle availability, set destination area with `destination_expires_at` | 3 |
| S3-2 | BE | `POST /driver/location/` (store lat/lng + `location_updated_at`, throttled) | 2 |
| S3-3 | BE | Matching service: 7 candidate rules, configurable staleness/radius, area-compat lookup | 8 |
| S3-4 | BE | `GET /driver/requests/` — matched OPEN, unexpired requests only; flag `match_type: estimated` | 3 |
| S3-5 | BE | `POST/DELETE /requests/{id}/interest/` — idempotent, no dupes, blocked on closed/expired | 3 |
| S3-6 | FE | Driver mode screen: toggle, destination picker, location permission explainer + freshness indicator | 5 |
| S3-7 | FE | Geolocation composable (permission, periodic update, foreground only) | 3 |
| S3-8 | FE | "Matching requests" list + request detail + Interested/Withdraw button | 5 |
| S3-9 | QA | Matching unit tests from doc §8 examples; interest idempotency; closed requests hidden | 5 |

---

## Sprint 4 — Contact, Agreement, Atomic Confirmation

| ID | Type | Task | SP |
|---|---|---|---|
| S4-1 | BE | `GET /requests/{id}/interests/` for customer; `POST .../contacted/` marks `CONTACTED` | 3 |
| S4-2 | BE | Contact reveal: phone exposed only to the request's customer ↔ interested driver pair | 3 |
| S4-3 | BE | `Agreement` fields (price, pickup details, time) on confirmation payload with validation | 2 |
| S4-4 | BE | `POST /requests/{id}/confirm/`: `transaction.atomic` + `select_for_update` on request, Idempotency-Key header, all pre-checks (open, not cancelled, not expired, driver conflict policy) | 8 |
| S4-5 | BE | On confirm: Trip `CONFIRMED`, chosen interest `SELECTED`, others `DECLINED`, request `CONFIRMED`, audit events | 3 |
| S4-6 | BE | Driver-conflict policy implementation (per S0 decision) | 3 |
| S4-7 | FE | Customer: interested drivers list, call/WhatsApp link, agreement form, confirm button | 5 |
| S4-8 | FE | Driver: see agreement, accept/confirm state, rejection messaging | 3 |
| S4-9 | QA | Concurrency test (2 threads confirm same request → exactly 1 succeeds); expiry race; idempotent retry | 8 |

---

## Sprint 5 — Trip Lifecycle & Notifications

| ID | Type | Task | SP |
|---|---|---|---|
| S5-1 | BE | Trip state machine: `CONFIRMED→IN_PROGRESS→COMPLETED`, `CANCELLED`; reject invalid jumps | 5 |
| S5-2 | BE | Endpoints: `/trips/{id}/start|complete|cancel/` with role permissions and cancel policy | 5 |
| S5-3 | BE | Notification service + `Notification` rows (dedupe key); types per doc §14 | 3 |
| S5-4 | BE | Web Push (pywebpush, VAPID), subscription endpoint, Celery send task with retries | 5 |
| S5-5 | BE | `GET /notifications/`, `POST /notifications/{id}/read/` | 2 |
| S5-6 | BE | Reminder task: request-near-expiry notification | 2 |
| S5-7 | FE | Trip detail screen with start/complete/cancel actions | 5 |
| S5-8 | FE | Push subscription flow + service-worker handler; in-app notification center (fallback) | 5 |
| S5-9 | FE | Offline/reconnect behavior: refetch server state on resume; no stale optimistic status | 3 |
| S5-10 | QA | Tests: illegal transitions (AC 9, 10), duplicate notification safety, push failure doesn't affect state | 5 |

---

## Sprint 6 — Admin, Safety, Pilot Readiness

| ID | Type | Task | SP |
|---|---|---|---|
| S6-1 | BE | Admin API (staff-only): users, requests, trips, status history, disable account | 5 |
| S6-2 | BE | Reports: `POST /reports/`, admin review/resolve endpoints | 3 |
| S6-3 | BE | KPI endpoint(s) per doc §17 with test-data exclusion flag | 5 |
| S6-4 | BE | Security pass: throttle scopes, object-level permission audit, PII-free logs, CORS/CSRF/HTTPS settings | 3 |
| S6-5 | FE | Admin dashboard (users, requests, reports, KPI cards) | 8 |
| S6-6 | FE | Report-user/trip flow; safety guidance + terms/privacy pages | 3 |
| S6-7 | QA | Full acceptance run of AC 1–14 (checklist, e2e with Playwright) | 8 |
| S6-8 | OPS | Staging/prod deploy, backups, Sentry, uptime alert | 5 |
| S6-9 | Doc | Legal/regulatory review sign-off; pilot plan (one area, onboarding drivers) | 3 |

---

## Team-lead notes

- **Definition of Done:** merged PR, tests passing in CI, OpenAPI updated, server-validated transitions, reviewed by one other dev.
- **Critical path:** S0-1 → S1-4 → S2-3 → S3-3 → S4-4 → S5-1.
- **Contract-first:** BE publishes OpenAPI at sprint start so FE can generate a typed client (`openapi-typescript`) and work in parallel.
- **Highest-risk task:** S4-4/S4-9 (atomic confirmation); start early in Sprint 4.
