const { defineConfig } = require('@playwright/test')

const skipWebServer = process.env.PLAYWRIGHT_SKIP_WEB_SERVER === '1'

module.exports = defineConfig({
  testDir: './e2e',
  testMatch: /gradcareer\.spec\.js$/,
  timeout: 5 * 60 * 1000,
  expect: {
    timeout: 15000,
  },
  use: {
    baseURL: process.env.FRONTEND_BASE || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  ...(skipWebServer ? {} : {
    webServer: {
      command: 'npm run dev -- --host 127.0.0.1 --port 3000',
      url: 'http://127.0.0.1:3000',
      reuseExistingServer: true,
      cwd: __dirname,
    },
  }),
})
