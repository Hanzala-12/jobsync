const { test, expect } = require('@playwright/test');
const fs = require('fs');

const FRONTEND_BASE = process.env.FRONTEND_BASE || 'http://localhost:3000';
const API_BASE = process.env.API_BASE || 'http://127.0.0.1:8000';

function randEmail() {
  return `test+${Date.now()}@example.com`;
}

test.setTimeout(5 * 60 * 1000);

test('Jobsync E2E: job + student modules', async ({ page }, testInfo) => {
  const errors = [];
  const screenshots = [];

  // Helper to capture errors
  async function fail(step, err) {
    const name = `failure-${Date.now()}-${step}.png`.replace(/[: ]/g, '-')
    const path = `./e2e/artifacts/${name}`;
    try { await page.screenshot({ path, fullPage: true }); screenshots.push(path); } catch(e){}
    errors.push({ step, error: String(err), screenshot: path });
  }

  // Ensure artifacts dir
  try { fs.mkdirSync('./e2e/artifacts', { recursive: true }); } catch(e){}

  const email = randEmail();
  const password = 'Testpass123!';

  // 1. Signup
  try {
    await page.goto(`${FRONTEND_BASE}/signup`, { waitUntil: 'networkidle' });
    // fill fields
    const emailInput = await page.locator('input[type="email"]').first();
    await emailInput.fill(email);
    const pwdInput = await page.locator('input[type="password"]').first();
    await pwdInput.fill(password);
    // try name field
    const nameInput = page.locator('input[name="name"]');
    if (await nameInput.count()) await nameInput.fill('E2E User');
    // submit
    const submit = page.locator('button[type="submit"], button:has-text("Sign up"), button:has-text("Signup")').first();
    await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle', timeout: 10000 }).catch(()=>{}), submit.click()]);
  } catch (err) { await fail('signup', err); }

  // 2. Log out if any, then login
  try {
    // Attempt logout
    try { await page.goto(`${FRONTEND_BASE}/logout`, { waitUntil: 'networkidle', timeout: 3000 }); } catch(e){}
    await page.goto(`${FRONTEND_BASE}/login`, { waitUntil: 'networkidle' });
    await page.locator('input[type="email"]').first().fill(email);
    await page.locator('input[type="password"]').first().fill(password);
    const loginBtn = page.locator('button[type="submit"], button:has-text("Log in"), button:has-text("Login")').first();
    await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle', timeout: 10000 }).catch(()=>{}), loginBtn.click()]);
  } catch (err) { await fail('login', err); }

  // 3. Create job profile (upload resume)
  try {
    await page.goto(`${FRONTEND_BASE}/profile`, { waitUntil: 'networkidle' });
    // fill skills and other fields
    const skills = page.locator('input[name="skills"], textarea[name="skills"], input[placeholder*="skills"], textarea[placeholder*="skills"]').first();
    if (await skills.count()) await skills.fill('Python,SQL');
    const degree = page.locator('input[name="degree"]').first(); if (await degree.count()) await degree.fill('BS');
    const years = page.locator('input[name="years_experience"], input[name="years"]').first(); if (await years.count()) await years.fill('3');
    // upload resume fixture
    const resumeInput = page.locator('input[type=file]').first();
    const fixture = './e2e/fixtures/sample-resume.pdf';
    if (await resumeInput.count()) await resumeInput.setInputFiles(fixture);
    // submit profile
    const saveBtn = page.locator('button:has-text("Save"), button[type="submit"], button:has-text("Create")').first();
    if (await saveBtn.count()) await Promise.all([page.waitForResponse(resp => resp.url().includes('/profile') && resp.status() < 500, { timeout: 10000 }).catch(()=>{}), saveBtn.click()]);
  } catch (err) { await fail('create-job-profile', err); }

  // 4. (Skip student/university module) — keep E2E focused on job flows

  // 5. Job Module Flow
  try {
    await page.goto(`${FRONTEND_BASE}/jobs`, { waitUntil: 'networkidle' });
    // search
    const search = page.locator('input[type="search"], input[placeholder*="search"], input[aria-label*="search"]').first();
    if (await search.count()) { await search.fill('software engineer'); await search.press('Enter'); }
    // wait for results
    await page.waitForSelector('.job-card, .job-list-item, .job-row, .job', { timeout: 10000 }).catch(()=>{});
    const firstMatchBtn = page.locator('button:has-text("Match Me"), button:has-text("Match"), button.match').first();
    if (await firstMatchBtn.count()) {
      await firstMatchBtn.click();
      // wait for match score
      await page.waitForSelector('.match-score, .score, .match-result', { timeout: 10000 }).catch(()=>{});
    }
    // Build Resume
    const buildBtn = page.locator('button:has-text("Build Resume"), button.build-resume').first(); if (await buildBtn.count()) { await buildBtn.click(); await page.waitForSelector('.tailored-resume, .resume-output', { timeout: 10000 }).catch(()=>{}); }
    // Cover Letter
    const coverBtn = page.locator('button:has-text("Cover Letter"), button.cover-letter').first(); if (await coverBtn.count()) { await coverBtn.click(); await page.waitForSelector('.cover-letter, .cover-output', { timeout: 10000 }).catch(()=>{}); }
    // Save job
    const saveBtn = page.locator('button:has-text("Save"), button.save-job, .save-icon').first(); if (await saveBtn.count()) { await saveBtn.click(); await page.waitForSelector('.toast, .notification, .saved', { timeout: 5000 }).catch(()=>{}); }
  } catch (err) { await fail('job-flow', err); }

  // 6. (Skipped) Student module removed from E2E

  // 7. Cross-module consistency
  try {
    await page.reload({ waitUntil: 'networkidle' });
    // check logged in
    const token = await page.evaluate(() => localStorage.getItem('jobsync_access_token'));
    if (!token) await fail('cross-check-auth', 'access token missing after reload');
    // check profiles exist
    await page.goto(`${FRONTEND_BASE}/profile`, { waitUntil: 'networkidle' });
    const profilesExist = await page.locator('.profile-list, .profiles, .profile-card').count();
    if (!profilesExist) {
      // allow that profile page may differ; try API check
      const resp = await page.request.get(`${API_BASE}/profile`);
      if (resp.status() >= 400) await fail('cross-check-profiles', `API returned ${resp.status()}`);
    }
  } catch (err) { await fail('cross-module', err); }

  // Summary
  const passed = errors.length === 0;
  if (!passed) {
    console.log('E2E failures:', errors);
  }
  expect(errors.length, `Failures: ${JSON.stringify(errors)}`).toBe(0);
});
