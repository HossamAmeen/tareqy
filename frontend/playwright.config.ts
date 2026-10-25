import { defineConfig, devices } from '@playwright/test'

const BACKEND_PORT = process.env.E2E_BACKEND_PORT ?? '8100'
const FRONTEND_PORT = process.env.E2E_FRONTEND_PORT ?? '5174'

export const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  // One shared backend/database, so tests run one after another and isolate themselves with unique data.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
    locale: 'ar-EG',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      // Fresh SQLite database, migrated and seeded on every run.
      command: 'sh e2e/backend.sh',
      url: `${BACKEND_URL}/api/health/`,
      timeout: 120_000,
      reuseExistingServer: false,
      stdout: 'ignore',
      stderr: 'pipe',
      env: { E2E_BACKEND_PORT: BACKEND_PORT },
    },
    {
      command: `npx vite --host 127.0.0.1 --port ${FRONTEND_PORT} --strictPort`,
      url: `http://127.0.0.1:${FRONTEND_PORT}/`,
      timeout: 120_000,
      reuseExistingServer: false,
      stdout: 'ignore',
      stderr: 'pipe',
      env: { VITE_API_PROXY: BACKEND_URL },
    },
  ],
})
