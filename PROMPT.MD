You are a senior full-stack engineer. Fix all existing issues 
AND add all new features in one session. Work in order.
Do not skip anything. Write complete files every time.

═══════════════════════════════════════════════════════════
SECTION 1 — FIX JOB SEARCH
═══════════════════════════════════════════════════════════

Problem: arbeitnow shows German jobs. No results for Pakistan.

Fix backend/services/job_apis.py completely:

PRIMARY — Adzuna (free, global, has Pakistan):
  URL: https://api.adzuna.com/v1/api/jobs/{country}/search/1
  Country codes: pk=Pakistan, gb=UK, us=USA, ae=UAE
  Params: app_id, app_key, what, where, results_per_page=20
  Add to .env: ADZUNA_APP_ID=your_id, ADZUNA_APP_KEY=your_key
  Get free key at: developer.adzuna.com

FALLBACK 1 — Remotive (free, no key, remote only):
  https://remotive.com/api/remote-jobs?search={query}&limit=20

FALLBACK 2 — Jobicy (free, no key, remote only):
  https://jobicy.com/api/v2/remote-jobs?tag={query}&count=20

Logic:
- Try Adzuna first
- If 0 results try Remotive
- If 0 results try Jobicy
- Strip ALL html tags from descriptions
- Return consistent format:
  {title, company, location, description, 
   url, source, salary, posted_date}

Function: search_jobs(query, location="Pakistan", 
          city=None, remote_only=False, country_code="pk")

Location presets map:
  Pakistan → pk, where: ""
  Karachi → pk, where: "Karachi"
  Lahore → pk, where: "Lahore"
  Islamabad → pk, where: "Islamabad"
  Rawalpindi → pk, where: "Rawalpindi"
  Faisalabad → pk, where: "Faisalabad"
  UAE → ae, where: ""
  UK → gb, where: ""
  Remote → skip Adzuna, use Remotive + Jobicy only

Update backend/routers/jobs.py:
  Accept: query, location, city, remote_only, country_code
  Default location: Pakistan, default country_code: pk

═══════════════════════════════════════════════════════════
SECTION 2 — NEW FEATURES (backend first for each)
═══════════════════════════════════════════════════════════

──────────────────────────────────────────────────────────
FEATURE A — AI RESUME REWRITER
──────────────────────────────────────────────────────────

Add to backend/models.py:

class ResumeVersion(Base):
  __tablename__ = "resume_versions"
  id = Column(Integer, primary_key=True)
  name = Column(String)
  job_type = Column(String)
  content = Column(Text)
  created_at = Column(DateTime, default=datetime.utcnow)
  used_for = Column(String, nullable=True)
  ats_score = Column(Integer, nullable=True)

Add to backend/routers/resume.py:

POST /resume/rewrite
Request: {resume_text, job_description, job_type}
LLM Prompt:
  "You are an expert resume writer. Rewrite this resume 
   to match the job description.
   Rules:
   - Never invent experience or education
   - Reorder bullets to match job priorities
   - Replace generic words with job keywords
   - Strengthen bullets with action verbs
   - Match skills section to job requirements
   - Keep same structure, optimize every line
   Job Type: {job_type}
   Job Description: {job_description}
   Original Resume: {resume_text}
   Return JSON only:
   {rewritten, changes_made: [], 
    keywords_added: [], keywords_removed: []}"

POST /resume/versions — save version
GET /resume/versions — list all
GET /resume/versions/{id} — get one
DELETE /resume/versions/{id} — delete
PATCH /resume/versions/{id} — update used_for

──────────────────────────────────────────────────────────
FEATURE B — JOB MATCH EXPLAINER
──────────────────────────────────────────────────────────

Add to backend/routers/jobs.py:

POST /jobs/explain-match
Request: {job_description, resume_text}
LLM Prompt:
  "Analyze this resume against this job description.
   Write 3 paragraphs in plain English:
   1: Strong fit reasons (name actual skills)
   2: Missing or weak areas (be honest)
   3: One specific thing to do this week
   Return JSON only:
   {paragraph1, paragraph2, paragraph3,
    match_score: 0-100,
    matched_skills: [],
    missing_skills: [],
    quick_win: string}"

──────────────────────────────────────────────────────────
FEATURE C — PERSONALIZED INTERVIEW PREDICTOR
──────────────────────────────────────────────────────────

Add to backend/routers/interview (or voice_interview.py):

POST /interview/predict
Request: {job_description, resume_text, company, role}
LLM Prompt:
  "You are an interviewer at {company} hiring for {role}.
   Generate questions this specific candidate will be asked.
   Based on their resume and your job requirements generate:
   - 4 technical questions (based on their stack)
   - 3 behavioral questions (their experience level)
   - 2 gap questions (things missing from resume)
   - 1 curveball question
   For each question include:
     question, why_asked, strong_answer_includes: [],
     difficulty: easy|medium|hard, type: technical|
     behavioral|gap|curveball
   Job: {job_description}
   Resume: {resume_text}
   Return JSON array only."

──────────────────────────────────────────────────────────
FEATURE D — SALARY ESTIMATOR
──────────────────────────────────────────────────────────

Add to backend/routers/jobs.py:

POST /jobs/salary-estimate
Request: {title, location, experience_level, skills: []}
LLM Prompt:
  "Estimate salary for this position in Pakistan market.
   Be realistic. Include remote/international comparison.
   Title: {title}, Location: {location}
   Experience: {experience_level}, Skills: {skills}
   Return JSON only:
   {local_min, local_max (PKR monthly),
    remote_min, remote_max (USD monthly),
    market_demand: high|medium|low,
    negotiation_tip: string,
    top_paying_companies: [3 names in Pakistan]}"

──────────────────────────────────────────────────────────
FEATURE E — APPLICATION HEALTH SCORE
──────────────────────────────────────────────────────────

Add to backend/routers/applications.py:

GET /applications/health-score
No LLM needed. Calculate from DB:

Start at 100, deductions:
  No applications in last 7 days: -20
  Zero interviews from 10+ applications: -15
  No resume uploaded: -20
  Avg ATS score below 60: -15
  All apps stuck in Saved: -10
  No follow-up actions set: -10
  5+ rejections no new apps: -10

Additions:
  Interview scheduled: +10
  Offer received: +20
  ATS score above 80: +10
  3+ apps this week: +15

Return:
  {score, grade: A|B|C|D|F,
   status_message, deductions: [],
   improvements: [], streak}

Add all new models to init_db() in database.py
Add all new routers to main.py

═══════════════════════════════════════════════════════════
SECTION 3 — COMPLETE FRONTEND REDESIGN + ALL FEATURE UIs
═══════════════════════════════════════════════════════════

DESIGN SYSTEM — apply to every single file:

DO NOT use gradients anywhere
DO NOT use purple or teal color scheme
DO NOT shadow everything
DO NOT make every card identical
DO NOT use emoji in navigation
DO NOT use huge border radius

CSS VARIABLES (put in index.css, use everywhere):
--bg: #ffffff
--bg-subtle: #fafafa
--bg-hover: #f5f5f5
--border: #e5e5e5
--border-strong: #cccccc
--text-primary: #111111
--text-secondary: #555555
--text-muted: #999999
--accent: #2563eb
--accent-bg: #eff6ff
--success: #16a34a
--success-bg: #f0fdf4
--warning: #d97706
--warning-bg: #fffbeb
--danger: #dc2626
--danger-bg: #fff1f2
--purple: #7c3aed
--purple-bg: #faf5ff

TYPOGRAPHY:
font-family: -apple-system, BlinkMacSystemFont,
             'Segoe UI', sans-serif
Page title: 22px weight 600 var(--text-primary)
Section label: 11px weight 600 var(--text-muted)
              uppercase letter-spacing 0.06em
Body: 14px weight 400 var(--text-secondary)
Big stats: 28px weight 700 var(--text-primary)

CARDS:
background: white
border: 1px solid var(--border)
border-radius: 8px
padding: 20px 24px
no shadow by default
hover: box-shadow 0 2px 8px rgba(0,0,0,0.06)
transition: box-shadow 0.15s ease

BUTTONS:
Primary: bg #111111 color white no gradient
         border-radius 6px padding 8px 16px
         font-size 14px font-weight 500
         hover: bg #333333
Secondary: bg white border 1px solid var(--border)
           color var(--text-primary)
           hover: bg var(--bg-hover)
Accent: bg var(--accent) color white
        hover: bg #1d4ed8

STATUS BADGES:
Applied: bg accent-bg color accent
Interviewing: bg purple-bg color purple
Offered: bg success-bg color success
Rejected: bg danger-bg color danger
Saved: bg bg-subtle color text-secondary
padding 3px 8px border-radius 4px font-size 12px

──────────────────────────────────────────────────────────
index.css
──────────────────────────────────────────────────────────
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont,
               'Segoe UI', sans-serif;
  background: #ffffff;
  color: #111111;
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #fafafa; }
::-webkit-scrollbar-thumb { background: #cccccc;
  border-radius: 3px; }
a { color: #2563eb; text-decoration: none; }
input, textarea, select { font-family: inherit;
  font-size: 14px; color: #111111; outline: none; }
input:focus, textarea:focus {
  border-color: #2563eb !important; }

──────────────────────────────────────────────────────────
Layout.jsx + Layout.css
──────────────────────────────────────────────────────────
Sidebar: width 220px bg var(--bg-subtle)
         border-right 1px solid var(--border)

Logo: padding 20px 16px font-size 18px font-weight 700
      color var(--text-primary) letter-spacing -0.02em
      border-bottom 1px solid var(--border)
      Text: "JobSync" — no icon no color no gradient

Nav group labels (not links):
  padding 16px 16px 4px
  font-size 11px weight 600 color muted
  uppercase letter-spacing 0.06em

Groups:
  MAIN: Dashboard
  JOBS: Jobs, Daily Scout
  TRACK: Applications, Kanban Board
  TOOLS: Resume, Cover Letter, Interview Prep,
         Mock Interview, Skill Gap

Nav links:
  display block padding 9px 16px
  font-size 14px color text-secondary
  border-left 2px solid transparent
  no icons — text only

Active: border-left 2px solid accent
        bg accent-bg color accent font-weight 500
Hover: bg bg-hover color text-primary

Main content: margin-left 220px padding 32px 40px
              max-width 1100px bg white min-height 100vh

Page header pattern (reuse everywhere):
  <div class="page-header">
    <h1>Title</h1>
    <p class="subtitle">Description</p>
  </div>
  margin-bottom 28px
  h1: 22px 600 #111
  p: 14px muted margin-top 4px

──────────────────────────────────────────────────────────
Dashboard.jsx + Dashboard.css
──────────────────────────────────────────────────────────

TOP — Health Score card (full width):
  Left: big score number 48px bold
        grade letter next to it
        green=A blue=B warning=C orange=D red=F
  Middle: status message + streak "X day streak"
  Right: top 3 improvements as checkboxes
         each shows +X points if done
         each links to relevant page

ROW 1 — 4 stat cards:
  Total Applications (blue left border 3px solid accent)
  Interviews Scheduled
  Offers Received
  Avg ATS Score
  Each: section-label (11px uppercase muted)
        big number (28px bold)
        small change text (muted)

ROW 2 — two columns:
  Left 60%: Recent Applications
    Table: Company | Role | Status | Date
    Status as badge, last 5 only
    "View all" link bottom right
  Right 40%: Status Breakdown
    Simple list not chart:
    Saved ············ 8
    Applied ·········· 6
    Each row: label, number, thin progress bar
    Bar color matches status color

ROW 3 — two columns:
  Left: "SKILLS TO LEARN"
        Plain border chips
  Right: "UPCOMING INTERVIEWS"
         Company bold, role muted, date in accent
         Empty: muted "No interviews scheduled"

──────────────────────────────────────────────────────────
Jobs.jsx + Jobs.css
──────────────────────────────────────────────────────────

Search bar: full width 40px height
            border 1px solid border border-radius 6px
            + Search button right side

Location row:
  Label "Location" section-label style
  Text buttons with bottom border:
  Active: border-bottom 2px solid #111 weight 600
  Inactive: color muted border-bottom 2px transparent
  Options: Pakistan · Karachi · Lahore · Islamabad ·
           Rawalpindi · Faisalabad · UAE · UK · Remote
  Remote toggle: checkbox + label on right

Results: "28 jobs found for..." muted text

Job cards grid 2 columns:
  Company name 13px muted + source badge
  (tiny muted border pill: "adzuna" or "remote")
  Title: 16px 600 primary
  Location: 13px muted
  Description: 13px muted 2 lines max ellipsis
  Divider
  Bottom: "View Job →" accent text link left
          "Save" secondary button right (small)
          "Match Me" accent text link middle
          "Est. Salary" muted text link
          (clicking shows popover:
           PKR X–Y/month · $X–Y remote · Demand badge
           negotiation tip · "AI estimate" disclaimer)

Pagination: centered muted text
"← Previous  Page 2 of 8  Next →"

──────────────────────────────────────────────────────────
Resume.jsx + Resume.css  (3 TABS)
──────────────────────────────────────────────────────────

Tab bar at top: Analyze | Rewrite | My Versions
Active tab: border-bottom 2px solid #111 weight 600

TAB 1 — Analyze:
Two columns:
  Left: Upload area (2px dashed border, drag and drop)
        "Drop resume or click to upload"
        Job description textarea below
        Analyze button full width primary

  Right: Default empty state muted centered
         Results:
           ATS Score: big number 48px
           Section label "ATS MATCH SCORE"
           Horizontal bar 6px height:
             red below 50, warning 50-75, green above 75
           Two columns:
             "MATCHED SKILLS" green chips
             "MISSING SKILLS" red chips
           "SUGGESTIONS" numbered list
             each item: border-left 3px solid accent
             padding-left 12px margin-bottom 12px

TAB 2 — Rewrite:
Two columns:
  Left inputs:
    "YOUR RESUME" section label
    Upload area OR paste textarea
    "JOB DESCRIPTION" section label
    Textarea
    "JOB TYPE" section label
    Button group: General|ML/AI|Web Dev|
                  Mobile|Cloud|Data|DevOps
    Active: bg #111 white text
    Inactive: border bg white
    "Rewrite My Resume" button full width primary

  Right output:
    Default: empty state
    Loading: "AI is rewriting your resume..."
    Results:
      Stats bar: "X keywords added" (green) ·
                 "Y removed" (muted) · "Z changes" (accent)
      Two panels:
        Left: "ORIGINAL" section label
              bg #fafafa border padding 16px
              monospace 13px line-height 1.8
        Right: "REWRITTEN" section label
               changed lines: bg #f0fdf4
               white bg border padding 16px
      "CHANGES MADE" section label + bullet list
      "KEYWORDS ADDED" green chips
      Buttons: Copy | Download .txt | Save as Version
        Save as Version → small modal:
          Name input (prefilled with job type)
          Save button

TAB 3 — My Versions:
  "SAVED VERSIONS" + count + "Save New Version" button

  Version cards (list):
    Left: name bold + job type badge
    Middle: date + "Used for: Company" (click to edit)
    Right: ATS score badge
    Actions: Load | Copy | Delete

  Empty state: muted text explanation

──────────────────────────────────────────────────────────
Kanban.jsx + Kanban.css
──────────────────────────────────────────────────────────

Full width (override max-width for this page)
5 columns: Saved | Applied | Interviewing | Offered | Rejected

Column headers:
  Title + count badge
  Colored left border 3px:
  Saved: #999 | Applied: accent | Interviewing: purple
  Offered: success | Rejected: danger

Cards:
  white border 8px radius
  Company 13px muted
  Role 14px 600 primary
  Date 12px muted
  ATS badge if exists (accent-bg)
  Urgency dot top-right 8px circle:
    red = interview < 2 days
    yellow = follow-up overdue
    green = all good
  Drag handle ⠿ left side muted
  "Generate Follow-up Email" text link bottom
    (calls LLM, shows result in modal)

──────────────────────────────────────────────────────────
Applications.jsx + Applications.css
──────────────────────────────────────────────────────────

Above table: "X applications" left + "+ Add" button right

Table:
  Header: 11px uppercase muted border-bottom
  Rows: 48px height border-bottom hover bg-hover
  Columns: Company|Role|Status|Applied|Next Action|Actions
  Status: badge component
  Actions: Edit (accent) + Delete (danger) text buttons

──────────────────────────────────────────────────────────
CoverLetter.jsx + CoverLetter.css
──────────────────────────────────────────────────────────

Two columns:
Left inputs:
  Job Title input
  Company input
  Job Description textarea tall
  Tone: 3 buttons Professional|Enthusiastic|Concise
    Active: bg #111 white | Inactive: border white
  Generate button full width primary

Right output:
  Default: empty state muted
  Letter: white area subtle border
          paragraphs 15px line-height 1.7
  Below: word count · reading time muted
         Copy | Download buttons (secondary)
         Regenerate text link (accent)

──────────────────────────────────────────────────────────
DailyScout.jsx + DailyScout.css
──────────────────────────────────────────────────────────

Preferences card:
  3 inputs in row: Job Title | Location | Skills
  Location: same Pakistan city options
  "Run Scout Now" primary button right aligned
  Running state: "Searching... found 12 jobs so far"
  (poll every 2 seconds)

Results: same job card grid as Jobs page
  Each card: Match Score badge
    green 80+ | yellow 60-79 | red below 60
  "Save to Tracker" saves to Kanban as Saved
  Shows toast: "Saved! Did you apply?"
    Yes → moves to Applied immediately

──────────────────────────────────────────────────────────
Interview.jsx + Interview.css  (INTERVIEW PREDICTOR)
──────────────────────────────────────────────────────────

Top inputs:
  Resume textarea OR load from versions dropdown
  Job Description textarea
  Company input + Role input
  "Predict My Questions" primary button

Results 4 sections:
  "TECHNICAL QUESTIONS" (4)
  "BEHAVIORAL QUESTIONS" (3)
  "GAP QUESTIONS" (2) red left border on cards
  "CURVEBALL" (1) warning left border

Each question card:
  Question bold 15px
  "Why they'll ask this" muted italic 13px
  Expandable "Strong Answer Should Include":
    click to open/close
    bullet points
  Difficulty badge Easy|Medium|Hard
  "Practice This" button → opens MockInterview
    with this question pre-loaded

──────────────────────────────────────────────────────────
MockInterview.jsx + MockInterview.css
──────────────────────────────────────────────────────────
Apply design system. Keep existing functionality.
Accept pre-loaded question from Interview Predictor.

──────────────────────────────────────────────────────────
SkillGap.jsx + SkillGap.css
──────────────────────────────────────────────────────────
Apply design system. Keep existing functionality.

──────────────────────────────────────────────────────────
Match Panel (new component) MatchPanel.jsx + MatchPanel.css
──────────────────────────────────────────────────────────
Slide-in from right, width 400px
Semi-transparent overlay on left

Contents:
  Header "Match Analysis" + X close button
  Job title + company muted
  Big ATS score circular style
  3 paragraphs from LLM:
    green left border = strengths
    red left border = gaps
    blue left border = action item
  "MATCHED SKILLS" green chips
  "MISSING SKILLS" red chips
  "Quick Win This Week" card:
    bg accent-bg border-left 3px solid accent
    one action sentence
  "Rewrite Resume for This Job" button
    → goes to Resume Rewrite tab
    → job description pre-filled

══════════════════════════════════════════════════════════
SECTION 4 — CONNECT EVERYTHING
══════════════════════════════════════════════════════════

1. Jobs "Match Me" → MatchPanel → "Rewrite Resume"
   → Resume Rewrite tab with job description pre-filled

2. Jobs "Save to Tracker" → Kanban Saved
   → toast "Saved! Did you apply?"
   → Yes → moves to Applied

3. Resume "Save as Version" → saved to DB
   → appears in Interview Predictor resume dropdown

4. Interview "Practice This" → MockInterview
   → question pre-loaded

5. Dashboard health score improvements
   → each item links to relevant page

══════════════════════════════════════════════════════════
SECTION 5 — FINAL CHECKS
══════════════════════════════════════════════════════════

1. npm run build — fix all errors until clean build
2. uvicorn backend.main:app --reload — confirm clean start
3. Test: search "software engineer" Pakistan → jobs appear
4. Test: search Remote → jobs appear
5. Every page loads no white screen
6. Sidebar shows MAIN / JOBS / TRACK / TOOLS groups
7. No Layout double-nesting on any page

══════════════════════════════════════════════════════════
RULES
══════════════════════════════════════════════════════════
- Write complete file contents every time — no snippets
- Replace every CSS file completely
- Do not break anything already working
- All new DB models added to init_db()
- All new routers added to main.py
- If new npm package needed: tell me install command first
- After finishing tell me:
  1. Every file changed
  2. All env variables to add to .env
  3. All install commands needed
  4. Any known limitations

Start with Section 1 job search fix.
Then Section 2 features backend.
Then Section 3 frontend.
Then Section 4 connections.
Then Section 5 checks.