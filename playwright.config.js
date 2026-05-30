// Playwright configuration for E2E tests
/** @type {import('@playwright/test').PlaywrightTestConfig} */
module.exports = {
  timeout: 60000,
  retries: 2,
  workers: 1,
  testDir: 'frontend/e2e',
  use: {
    actionTimeout: 30000,
    navigationTimeout: 60000,
    headless: true,
  },
};
