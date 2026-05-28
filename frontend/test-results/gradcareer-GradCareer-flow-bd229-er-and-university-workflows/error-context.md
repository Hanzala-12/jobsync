# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: gradcareer.spec.js >> GradCareer flows >> signup/login, jobs, resume, cover letter, and university workflows
- Location: e2e\gradcareer.spec.js:48:3

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:3000/signup
Call log:
  - navigating to "http://127.0.0.1:3000/signup", waiting until "domcontentloaded"

```

# Test source

```ts
  1  | const { test, expect } = require('@playwright/test')
  2  | 
  3  | const FRONTEND_BASE = process.env.FRONTEND_BASE || 'http://localhost:3000'
  4  | 
  5  | function createApiMocks(page) {
  6  |   const state = { authenticated: false }
  7  |   const user = { id: 1, email: 'grad@example.com', name: 'Grad User', is_active: true, token_version: 0 }
  8  |   const profile = { profiles: [], selected_profile_id: 1, selected_profile: null, exists: true, total: 0 }
  9  |   const job = { id: 11, title: 'Backend Engineer', company: 'Acme Corp', location: 'Remote', description: 'Build Python APIs with FastAPI and SQL', source: 'manual' }
  10 |   const university = { id: 5, name: 'Tech University', country: 'Malaysia', city: 'Kuala Lumpur', ranking_global: 120, website: 'https://tech.example.com', acceptance_rate: 0.35, student_population: 20000, accreditation: 'ABET' }
  11 |   const program = { id: 11, university_id: 5, name: 'Computer Science MSc', degree_level: 'Masters', duration_years: 2, estimated_tuition_fees: 18000, currency: 'USD', min_gpa: 3, ranking_global: 125, ranking_national: 5, min_ielts: 6.5, min_toefl: 90, application_deadline: '2026-03-01', semester_intake: 'Fall', living_cost_estimate: 10000, scholarship_available: true, program_url: 'https://tech.example.com/cs', source_url: 'https://tech.example.com/cs', data_quality_score: 4 }
  12 | 
  13 |   const json = (data) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(data) })
  14 | 
  15 |   return page.route('**/api/**', async (route) => {
  16 |     const url = route.request().url()
  17 |     const method = route.request().method()
  18 | 
  19 |     if (url.includes('/auth/me') && method === 'GET') return route.fulfill(state.authenticated ? json(user) : { status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Unauthorized' }) })
  20 |     if (url.includes('/auth/refresh') && method === 'POST') return route.fulfill(json({ access_token: 'access-token' }))
  21 |     if (url.includes('/auth/login') && method === 'POST') { state.authenticated = true; return route.fulfill(json({ access_token: 'access-token', refresh_token: 'refresh-token', user })) }
  22 |     if (url.includes('/auth/signup') && method === 'POST') { state.authenticated = true; return route.fulfill(json({ access_token: 'access-token', refresh_token: 'refresh-token', user })) }
  23 |     if (url.includes('/student/profiles') && method === 'GET') return route.fulfill(state.authenticated ? json(profile) : { status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Unauthorized' }) })
  24 |     if (url.includes('/student/profile') && method === 'POST') return route.fulfill(json({ id: 1, gpa: 3.7, gre_score: 320, toefl_score: 110, ielts_score: 7.5, budget_per_year: 18000, preferred_countries: ['Malaysia'], intended_major: 'Computer Science', degree_level: 'Masters', academic_background: 'BS CS' }))
  25 |     if (url.includes('/student/profile') && method === 'GET') return route.fulfill(json({ id: 1, gpa: 3.7, gre_score: 320, toefl_score: 110, ielts_score: 7.5, budget_per_year: 18000, preferred_countries: ['Malaysia'], intended_major: 'Computer Science', degree_level: 'Masters', academic_background: 'BS CS', profile_skills: ['Python', 'SQL'] }))
  26 |     if (url.includes('/student/university-countries') && method === 'GET') return route.fulfill(json({ countries: ['Malaysia', 'Singapore'] }))
  27 |     if (url.includes('/student/universities/filter') && method === 'GET') return route.fulfill(json({ items: [{ university, programs: [program] }], total: 1, page: 1, limit: 24 }))
  28 |     if (url.includes(`/student/university/${university.id}/detail`) && method === 'GET') return route.fulfill(json({ university, programs: [program], scholarships: [{ id: 21, name: 'Merit Scholarship', amount_usd: 5000, deadline: '2026-02-01', eligibility_criteria: 'High GPA' }] }))
  29 |     if (url.includes(`/student/verify/${university.id}/${program.id}`) && method === 'GET') return route.fulfill(json({ university, program, verification: { classification: 'verified', tuition_estimated: 18000, tuition_currency: 'USD', confidence: 91, data_fresh: true, source_url: 'https://tech.example.com/cs', source_title: 'University site', requirements_summary: 'IELTS 6.5', admission_summary: 'Strong academic record', advice: 'Apply early', summary: 'Live verification passed' } }))
  30 |     if (url.includes(`/student/match/program/${program.id}`) && method === 'GET') return route.fulfill(json({ match: { match_score: 87, academic_fit: 90, budget_fit: 85, location_fit: 80, strengths: ['Python'], missing_requirements: ['IELTS 6.5'], summary: 'Great fit' }, analysis: { match_score: 87, academic_fit: 90, budget_fit: 85, location_fit: 80, strengths: ['Python'], missing_requirements: ['IELTS 6.5'], summary: 'Great fit' }, program, university, verification: { classification: 'verified', tuition_estimated: 18000, tuition_currency: 'USD', confidence: 91, data_fresh: true } }))
  31 |     if (url.includes('/student/save') && method === 'POST') return route.fulfill(json({ id: 1, student_id: 1, program_id: 11, saved_at: '2026-01-01T00:00:00Z', student: { id: 1, gpa: 3.7, intended_major: 'Computer Science' }, program, university }))
  32 |     if (url.includes('/student/apply') && method === 'POST') return route.fulfill(json({ id: 1, student_id: 1, program_id: 11, status: 'applied', notes: '', student: { id: 1, gpa: 3.7, intended_major: 'Computer Science' }, program, university }))
  33 |     if (url.includes('/student/applications/1') && method === 'GET') return route.fulfill(json([{ id: 1, status: 'applied', student_id: 1, program_id: 11, student: { id: 1 }, program, university }]))
  34 |     if (url.includes('/student/saved/1') && method === 'GET') return route.fulfill(json([{ id: 1, student_id: 1, program_id: 11, student: { id: 1 }, program, university }]))
  35 |     if (url.includes('/student/programs/11/report-outdated') && method === 'POST') return route.fulfill(json({ id: 9, reason: 'Wrong tuition', message: 'Needs update', program_id: 11 }))
  36 |     if (url.includes('/jobs/search') && method === 'GET') return route.fulfill(json([job]))
  37 |     if (url.includes('/jobs/11/match') && method === 'GET') return route.fulfill(json({ job_id: 11, match_percentage: 91, explanation: 'Great fit', matched_skills: ['Python', 'FastAPI'], missing_skills: ['Docker'] }))
  38 |     if (url.includes('/jobs/upsert') && method === 'POST') return route.fulfill(json({ id: 11, title: job.title, company: job.company, location: job.location, description: job.description, url: '', source: 'manual' }))
  39 |     if (url.includes('/build_resume/11') && method === 'POST') return route.fulfill(json({ original_resume: 'Resume', fixed_resume_text: 'Tailored resume text', simple_text_version: 'Tailored resume text', ats_score: 82, changes_made: ['Added keywords'], html_resume: '<html><body>Tailored resume text</body></html>', validation_passed: true, validation_message: 'Consider reducing repetition of keywords; the resume reads a bit dense.', cached: false }))
  40 |     if (url.includes('/cover-letter/generate') && method === 'POST') return route.fulfill(json({ draft: 'Dear Hiring Manager, ...', source_ids: ['source-1'] }))
  41 |     if (url.includes('/profile') && method === 'GET') return route.fulfill(json({ profiles: [], selected_profile_id: 1, selected_profile: null, exists: true, total: 0 }))
  42 | 
  43 |     return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
  44 |   })
  45 | }
  46 | 
  47 | test.describe('GradCareer flows', () => {
  48 |   test('signup/login, jobs, resume, cover letter, and university workflows', async ({ page }) => {
  49 |     await createApiMocks(page)
  50 | 
> 51 |     await page.goto(`${FRONTEND_BASE}/signup`, { waitUntil: 'domcontentloaded' })
     |                ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:3000/signup
  52 |     await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible()
  53 |     await page.getByLabel('Email').fill('grad@example.com')
  54 |     await page.getByLabel('Password').fill('password123')
  55 |     await page.getByRole('button', { name: 'Sign up' }).click()
  56 |     await expect(page).toHaveURL(/\/$/)
  57 | 
  58 |     await page.goto(`${FRONTEND_BASE}/jobs`)
  59 |     await expect(page.getByText('Backend Engineer')).toBeVisible()
  60 |     await page.getByRole('button', { name: 'Match Me' }).click()
  61 |     await expect(page.getByText('Great fit')).toBeVisible()
  62 |     await page.getByRole('button', { name: 'Tailor Resume' }).click()
  63 |     await expect(page.getByText('Tailored resume text')).toBeVisible()
  64 | 
  65 |     await page.goto(`${FRONTEND_BASE}/cover-letter`)
  66 |     await page.fill('input[placeholder*="Senior Frontend Engineer"]', 'Backend Engineer')
  67 |     await page.fill('input[placeholder*="Acme Corp"]', 'Acme Corp')
  68 |     await page.fill('textarea[placeholder*="Paste the full job description here"]', 'Build Python APIs with FastAPI and SQL')
  69 |     await page.getByRole('button', { name: 'Generate Cover Letter' }).click()
  70 |     await expect(page.getByText('Dear Hiring Manager')).toBeVisible()
  71 | 
  72 |     await page.goto(`${FRONTEND_BASE}/student/profile`)
  73 |     await page.locator('input[type="number"]').nth(0).fill('3.7')
  74 |     await page.locator('button:has-text("Next")').click()
  75 |     await page.fill('textarea[placeholder*="BSc in Software Engineering"]', 'BS Computer Science')
  76 |     await page.locator('button:has-text("Next")').click()
  77 |     await page.fill('input[placeholder*="Computer Science"]', 'Computer Science')
  78 |     await page.fill('input[placeholder*="Masters"]', 'Masters')
  79 |     await page.locator('select[multiple]').selectOption(['Malaysia'])
  80 |     await page.getByRole('button', { name: 'Create Profile' }).click()
  81 |     await expect(page.getByText('Profile created.')).toBeVisible()
  82 | 
  83 |     await page.goto(`${FRONTEND_BASE}/student/search`)
  84 |     await expect(page.getByText('Tech University')).toBeVisible()
  85 |     await page.getByRole('button', { name: 'Save Program' }).click()
  86 | 
  87 |     await page.goto(`${FRONTEND_BASE}/student/matches`)
  88 |     await expect(page.getByText('Tech University')).toBeVisible()
  89 |     await page.getByRole('button', { name: 'View Details' }).click()
  90 |     await expect(page.getByText('verified')).toBeVisible()
  91 |     await page.getByRole('button', { name: 'Refresh live verification' }).click()
  92 |     await page.getByRole('button', { name: 'Save to My List' }).click()
  93 |     await page.getByRole('button', { name: 'Apply Now' }).click()
  94 |   })
  95 | })
  96 | 
```