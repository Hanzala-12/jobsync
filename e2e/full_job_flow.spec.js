const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const FRONTEND = process.env.FRONTEND_URL || 'http://localhost:5173';
const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000';

test.setTimeout(5 * 60 * 1000);

test('Full job flow: auth, search, match, tailor resume, download PDF, profile', async ({ page, context }) => {
  const artifactsDir = path.resolve(process.cwd(), 'e2e-artifacts');
  if (!fs.existsSync(artifactsDir)) fs.mkdirSync(artifactsDir, { recursive: true });

  // 1) Authentication: try to login if login page exists
  await page.goto(`${FRONTEND}/login`);
  try {
    const emailInput = await page.locator('input[type="email"]').first();
    await emailInput.fill(process.env.E2E_TEST_EMAIL || `e2e+test+${Date.now()}@example.com`);
    const passwordInput = await page.locator('input[type="password"]').first();
    await passwordInput.fill(process.env.E2E_TEST_PASSWORD || 'Password123!');
    const submit = page.locator('button:has-text("Log in"), button:has-text("Login"), button:has-text("Sign in")').first();
    if (await submit.count()) {
      await Promise.all([
        page.waitForNavigation({ url: /.*\/(|dashboard)?/ , timeout: 20000 }).catch(() => {}),
        submit.click().catch(() => {}),
      ]);
    }
  } catch (e) {
    // if login not present, continue
  }

  // verify logged in UI (dashboard or auth.me)
  await page.goto(`${FRONTEND}/`);
  await page.waitForTimeout(1000);
  // Check for presence of profile link or user email
  const profileLink = page.locator('a:has-text("Profile"), text=Profile');
  expect(await profileLink.count()).toBeGreaterThan(0);

  // 2) Job search and matching
  await page.goto(`${FRONTEND}/jobs`);
  await page.waitForSelector('input[placeholder*="Search"], input[placeholder*="software engineer"]', { timeout: 15000 });
  const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="software engineer"]').first();
  await searchInput.fill('software engineer');
  const searchBtn = page.locator('button:has-text("Search")').first();
  if (await searchBtn.count()) await searchBtn.click();
  await page.waitForTimeout(1500);
  // wait for job cards
  await page.waitForSelector('text=Tailor Resume, button:has-text("Tailor Resume"), text=Match Me', { timeout: 20000 });

  // Click Match Me on first visible job card
  const firstMatchBtn = page.locator('button:has-text("Match Me")').first();
  if (await firstMatchBtn.count()) {
    await firstMatchBtn.click();
    await page.waitForSelector('text=Match Score, text=Match', { timeout: 15000 }).catch(() => {});
    // close modal (assume close button exists)
    const close = page.locator('button:has-text("Close"), button[aria-label="Close"]').first();
    if (await close.count()) await close.click();
  }

  // 3) Tailor resume flow
  const tailorBtn = page.locator('button:has-text("Tailor Resume")').first();
  await tailorBtn.click();
  // wait for the modal
  await page.waitForSelector('.resume-modal', { timeout: 30000 });
  // verify sections in the optimized resume text area
  const afterText = await page.locator('.resume-diff-card .resume-diff-text').first().innerText();
  expect(afterText.toLowerCase()).toContain('summary');
  expect(afterText.toLowerCase()).toContain('skills');
  expect(afterText.toLowerCase()).toContain('experience');
  expect(afterText.toLowerCase()).toContain('education');
  expect(afterText).not.toContain('Add your degree here');
  // check skills count: at least 3 comma-separated
  const skillsMatch = afterText.match(/skills[:\s]*([\w ,\-]+)\n/i);
  if (skillsMatch && skillsMatch[1]) {
    const skills = skillsMatch[1].split(',').map(s=>s.trim()).filter(Boolean);
    expect(skills.length).toBeGreaterThanOrEqual(3);
  }

  // missing keywords panel if present
  const missingPanel = page.locator('.resume-missing-keywords');
  if (await missingPanel.count()) {
    expect(await missingPanel.isVisible()).toBeTruthy();
  }

  // 4) PDF download
  const downloadBtn = page.locator('button:has-text("Download PDF")').first();
  let downloaded = null;
  if (await downloadBtn.count()) {
    const [ download ] = await Promise.all([
      page.waitForEvent('download', { timeout: 30000 }),
      downloadBtn.click()
    ]).catch(() => [null]);

    if (download) {
      const saveTo = path.join(artifactsDir, await download.suggestedFilename());
      await download.saveAs(saveTo);
      downloaded = saveTo;
      const stat = fs.statSync(saveTo);
      expect(stat.size).toBeGreaterThan(100);
      // basic check: open as PDF by magic bytes
      const fd = fs.openSync(saveTo, 'r');
      const header = Buffer.alloc(4);
      fs.readSync(fd, header, 0, 4, 0);
      fs.closeSync(fd);
      expect(header.toString()).toBe('%PDF');
    }
  }

  // 5) Profile update (optional)
  await page.goto(`${FRONTEND}/profile`);
  await page.waitForTimeout(1000);
  // Try to find a skills input and add a skill
  const skillInput = page.locator('input[placeholder*="skill"], input[name*="skills"]').first();
  if (await skillInput.count()) {
    await skillInput.fill('Playwright');
    const saveBtn = page.locator('button:has-text("Save"), button:has-text("Update")').first();
    if (await saveBtn.count()) {
      await Promise.all([page.waitForResponse(r => r.status() < 500, { timeout: 10000 }).catch(()=>{}), saveBtn.click().catch(()=>{})]);
    }
  }

  // take final success screenshot
  await page.screenshot({ path: path.join(artifactsDir, 'final_success.png'), fullPage: true });
  // write a minimal result JSON
  fs.writeFileSync(path.join(artifactsDir, 'result.json'), JSON.stringify({ downloaded: downloaded || null }, null, 2));
});
