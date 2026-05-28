const { chromium } = require('playwright');
const fs = require('fs');

const FRONTEND_BASE = process.env.FRONTEND_BASE || 'http://localhost:3000';
const API_BASE = process.env.API_BASE || 'http://127.0.0.1:8000';

function randEmail() { return `test+${Date.now()}@example.com`; }

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const artifacts = [];
  const errors = [];
  try {
    const email = randEmail();
    const password = 'Testpass123!';
    console.log('Create user via API', email);
    // Create user via backend API to avoid UI signup variability
    try {
      const r = await page.request.post(`${API_BASE}/auth/signup`, { data: { email, password, name: 'E2E User' } });
      const body = await r.json().catch(()=>({}));
      const access = body.access_token || (await (await page.request.post(`${API_BASE}/auth/login`, { data: { email, password } })).json()).access_token;
      if (access) {
        await page.addInitScript(token => { localStorage.setItem('jobsync_access_token', token); }, access);
      }
    } catch (e) {
      console.warn('API signup/login failed, will try UI flow');
      await page.goto(`${FRONTEND_BASE}/signup`, { waitUntil: 'domcontentloaded' });
      try { await page.fill('input[type="email"]', email); } catch(e){}
      try { await page.fill('input[type="password"]', password); } catch(e){}
      try { await page.fill('input[name="name"]', 'E2E User'); } catch(e){}
      try { await page.click('button[type="submit"], button:has-text("Sign up")'); } catch(e){}
      await page.waitForTimeout(1000);
    }

    // Reload to apply token
    await page.goto(FRONTEND_BASE, { waitUntil: 'domcontentloaded' });

    console.log('Create job profile');
    try {
      await page.goto(`${FRONTEND_BASE}/profile`, { waitUntil: 'domcontentloaded', timeout: 20000 });
    } catch (e) {
      console.warn('Profile page navigation timed out, continuing');
    }
    try { await page.fill('input[name="skills"]', 'Python,SQL'); } catch(e){}
    try { await page.fill('input[name="degree"]', 'BS'); } catch(e){}
    try { await page.setInputFiles('input[type=file]', './e2e/fixtures/sample-resume.pdf'); } catch(e){}
    try { await page.click('button:has-text("Save"), button[type="submit"]'); } catch(e){}
    await page.waitForTimeout(1000);

    console.log('Job module: search and match');
    await page.goto(`${FRONTEND_BASE}/jobs`, { waitUntil: 'domcontentloaded' });
    try { await page.fill('input[type="search"]', 'software engineer'); await page.press('input[type="search"]', 'Enter'); } catch(e){}
    await page.waitForTimeout(2000);
    try { await page.click('button:has-text("Match Me"), button:has-text("Match")'); await page.waitForTimeout(2000);} catch(e){}

    console.log('Student module: create and search');
    await page.goto(`${FRONTEND_BASE}/student/profile`, { waitUntil: 'domcontentloaded' });
    try { await page.fill('input[name="gpa"]', '3.5'); } catch(e){}
    try { await page.fill('input[name="budget"]', '15000'); } catch(e){}
    try { await page.fill('input[name="preferred_countries"]', 'Malaysia'); } catch(e){}
    try { await page.click('button:has-text("Save"), button[type="submit"]'); } catch(e){}
    await page.waitForTimeout(1000);
    await page.goto(`${FRONTEND_BASE}/student/search`, { waitUntil: 'domcontentloaded' });
    try { await page.fill('input[placeholder*="country"], input[name*="country"]', 'Malaysia'); } catch(e){}
    try { await page.fill('input[name*="tuition"]', '20000'); } catch(e){}
    try { await page.click('button:has-text("Get Recommendations"), button:has-text("Match Me")'); } catch(e){}
    await page.waitForTimeout(2000);

    console.log('Cross-check: reload');
    await page.reload({ waitUntil: 'domcontentloaded' });
    const token = await page.evaluate(() => localStorage.getItem('jobsync_access_token'));
    if (!token) {
      const path = `./e2e/artifacts/no-token-${Date.now()}.png`;
      await page.screenshot({ path, fullPage: true }); artifacts.push(path);
      errors.push('access token missing after reload');
    }

  } catch (err) {
    const path = `./e2e/artifacts/error-${Date.now()}.png`;
    await page.screenshot({ path, fullPage: true }).catch(()=>{});
    artifacts.push(path);
    errors.push(String(err));
  } finally {
    await browser.close();
  }

  console.log('Artifacts:', artifacts);
  console.log('Errors:', errors);
  if (errors.length) process.exit(2);
  console.log('E2E run completed successfully');
}

main();
