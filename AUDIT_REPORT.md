# JobSync Pro Audit Report

This report is being built incrementally in accordance with the staged audit instructions in `prompt.txt`.

## Phase 1: Technology Stack

### 1.1 Frontend framework and version
- **Framework:** React 18
- **Build tool:** Vite 5
- **Routing:** React Router DOM 6.21.1
- **HTTP client:** Axios 1.6.5
- **Charts/UI:** Recharts 3.8.1, Lucide React 0.303.0
- **Source files:** [frontend/package.json](frontend/package.json), [frontend/vite.config.js](frontend/vite.config.js)

### 1.2 Backend framework and version
- **Framework:** FastAPI 0.110.0
- **ASGI server:** Uvicorn 0.27.1
- **ORM / migrations:** SQLAlchemy 2.0.27 + Alembic >=1.13.0
- **Python version:** not pinned in the project metadata, but the README targets Python 3.10+
- **Source files:** [requirements.txt](requirements.txt), [README.md](README.md)

### 1.3 Database
- **Primary database:** SQLite in local dev / Docker defaults
- **Support for production:** PostgreSQL/Supabase is configured via environment variables and dependency `psycopg2-binary` / `supabase`
- **Vector database:** ChromaDB >=0.4.0
- **Source files:** [requirements.txt](requirements.txt), [.env.example](.env.example), [docker-compose.yml](docker-compose.yml)

### 1.4 LLM integration
- **Enabled providers:** OpenRouter, Groq, OpenAI, Novita (via env vars)
- **Client/library:** `groq`, `openai`, and app-level provider abstractions
- **LLM behavior:** multiple provider fallback and model overrides are modeled in env files
- **Source files:** [.env.example](.env.example), [backend/.env.example](backend/.env.example), [README.md](README.md)

### 1.5 Deployment targets
- **Frontend deployment target:** Vercel (rewrite to `/index.py`)
- **Containerization:** Docker Compose for backend and frontend
- **CI/CD:** GitHub Actions workflows are present in `.github/workflows/` but were not read in Phase 1
- **Source files:** [vercel.json](vercel.json), [docker-compose.yml](docker-compose.yml), [docker-compose.prod.yml](docker-compose.prod.yml)

### 1.6 Testing frameworks
- **Python:** pytest, pytest-asyncio, httpx
- **Frontend:** no dedicated frontend test framework is listed in [frontend/package.json](frontend/package.json)
- **Source files:** [requirements.txt](requirements.txt), [frontend/package.json](frontend/package.json)

### 1.7 Environment configuration
- **Root env template:** [.env.example](.env.example)
- **Backend env template:** [backend/.env.example](backend/.env.example)
- **Frontend env template:** [frontend/.env.example](frontend/.env.example)
- **Important gaps:** the project relies heavily on secrets and feature flags without a single canonical `.env` file

### 1.8 Key observations
- The stack is **modern and production-oriented**: FastAPI + React + Vite + ChromaDB + multiple LLM providers.
- The codebase appears to support **job search, career prep, student/university matching, cover letters, and browser extension workflows**.
- The main risks at this stage are **operational readiness**, **test coverage**, and **consistency of environment configuration**.

### 1.9 Phase 1 summary
| Area | Status | Notes |
| --- | --- | --- |
| Frontend | ✅ Present | React 18 + Vite 5 + React Router 6 |
| Backend | ✅ Present | FastAPI + SQLAlchemy + Alembic |
| Database | ✅ Present | SQLite by default, Supabase/Postgres optional |
| Vector DB | ✅ Present | ChromaDB |
| LLM providers | ✅ Present | OpenRouter, Groq, OpenAI, Novita |
| Testing | ⚠️ Partial | Python tests present, frontend tests absent |
| Deployment | ✅ Present | Vercel + Docker + GitHub Actions |

## Phase 2: Backend – Database & Core

### 2.1 SQLAlchemy model inventory
The ORM layer in [backend/models.py](backend/models.py) defines a broad schema spanning both the job-search and student/university workflows:

- **Users / auth:** `User`, `UserProfile`, `UserPreference`
- **Jobs / applications:** `Job`, `Application`, `ResumeVersion`, `PrefetchedJob`
- **University / student domain:** `University`, `Program`, `StudentProfile`, `UniversityMatchCache`, `Scholarship`, `StudentProgramMatch`, `SavedProgram`, `StudyApplication`
- **Support types:** `ApplicationStatus` enum, `TimestampMixin`

Key observations:
- `Job` stores raw scraper fields plus duplicate-fingerprint and activity metadata.
- `Application` is user-owned and tracks `status`, `notes`, `resume_version`, and follow-up dates.
- `University` and `Program` are fully modeled with creation/update timestamps and relationship links.
- `StudentProfile` includes GPA, GRE/TOEFL/IELTS, budget, preferred countries, intended major, and degree level.
- `UniversityMatchCache` and `StudentProgramMatch` provide cached recommendation output and persistent match history.

### 2.2 Database connection logic
The database wiring in [backend/database.py](backend/database.py) is intentionally strict:

- `DATABASE_URL` is **required** at import time; the app raises immediately if it is missing.
- The engine uses `create_engine(DATABASE_URL, pool_pre_ping=True)`.
- `SessionLocal` is standard SQLAlchemy session factory.
- `get_db()` yields a scoped session and closes it in a `finally` block.

Important consequences:
- There is **no SQLite fallback** in the default backend path.
- The current configuration is optimized for **Postgres/Supabase-style deployments** and is not friendly to a local development-only SQLite setup unless the env is explicitly configured.

### 2.3 Alembic migration status
The migration set under [backend/migrations/versions](backend/migrations/versions) contains multiple revision files, including merge revisions such as `fd2412b4cb73_merge_heads.py`.

The migration state was verified by running:

```bash
& 'e:\job finder\venv\Scripts\python.exe' -m alembic -c backend/alembic.ini heads
```

Observed output:

```text
7a8b9c0d1e2f (head)
d1e2f3a4b5c6 (head)
```

This means the repository currently has **multiple Alembic heads**, which is a production risk because it indicates the migration lineage is not linear and may require manual reconciliation.

### 2.4 Startup, health, and schema validation
The FastAPI entrypoint in [backend/main.py](backend/main.py) performs several important startup actions:

1. **Automatic migrations at startup**
   - `_run_startup_migrations()` runs `alembic upgrade head`.
   - If Alembic fails, it falls back to `Base.metadata.create_all(bind=engine, checkfirst=True)`.
   - This fallback is helpful for recovery but can **mask migration problems** and create divergence between schema and intended revisions.

2. **Required table verification**
   - `_verify_required_tables()` checks for a hardcoded list of required tables.
   - If any are missing, startup raises a `RuntimeError`.

3. **University schema warning check**
   - `_warn_if_university_columns_missing()` warns if the `universities` table is missing `created_at`, `updated_at`, or `last_scraped_at`.

4. **Middleware and CORS**
   - Adds `GZipMiddleware`
   - Parses `CORS_ORIGINS` and defaults to `*` if unset
   - Adds rate limiting middleware using `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_PERIOD`
   - Adds an HTTPS redirect middleware for production
   - Adds request logging middleware

5. **Router registration**
   - Registers job, resume, applications, cover letter, intelligence, student, auth, profile, kanban, voice interview, browser extension, follow-up, and daily scout routers.

6. **Health and root endpoints**
   - `/health` executes a simple database probe and verifies required tables.
   - `/` returns service metadata and feature flags.

### 2.5 Core infrastructure risks and gaps
| Area | Status | Notes |
| --- | --- | --- |
| Migration state | ❌ Needs attention | Multiple Alembic heads detected |
| DB portability | ⚠️ Partial | Strict `DATABASE_URL` requirement, no SQLite fallback |
| Startup resilience | ⚠️ Partial | Fallback `create_all` can hide migration issues |
| Schema completeness | ✅ Strong | Broad job + student domain coverage |
| Runtime validation | ✅ Present | Required-table checks and health probe are implemented |

### 2.6 Phase 2 summary
- The backend contains a **well-structured ORM and startup path**, but the **database configuration is rigid** and **migration state is currently broken**.
- The application has strong coverage for both **job-search** and **student/university** features, but the infrastructure path needs stabilization before production.

## Phase 3: Backend – Job Module Endpoints

### 3.1 Jobs router (`backend/routers/jobs.py`)

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/jobs/search` | GET | Search jobs, optionally scrape live sources, upsert, and return DB results | Public | No Pydantic validation; uses raw query params; returns DB results even if sources fail | `search_jobs`, external scrapers, `process_incoming_job`, `normalize_job` | ✅ Functional, but lacks auth and has no strict input validation |
| `/jobs/search/diagnostics` | GET | Return DB-backed job diagnostics | Public | Exceptions are swallowed into response payload | `Job` model, SQLAlchemy | ⚠️ Partial |
| `/jobs/test_rozee` | GET | Diagnostic endpoint to fetch Rozee HTML and count links | Public | Returns error string in payload; no HTTP error | `requests`, `ROZEE_USER_AGENT` | ⚠️ Partial |
| `/jobs/search/stream` | GET | Stream search results from multiple live sources | `get_current_user_from_stream` | Auth enforced via token query/header; SSE streaming errors are logged but not fully surfaced | External scrapers, `ThreadPoolExecutor`, `LLMProvider` indirectly | ⚠️ Partial |
| `/jobs/sources` | GET | Return status for Pakistan job sources | Public | No error handling beyond return payload | `get_pakistan_source_status` | ✅ Functional |
| `/jobs/{job_id}/match` | GET | Compute job-to-profile match score and explanation | Auth required | Returns `JobMatch` with 0 score and explanatory text when missing data, not a 404 | `UserProfile`, `extract_skills`, `explain_match_for` | ⚠️ Partial |
| `/jobs/upsert` | POST | Create or update a single job record | Public | `JobUpsert` validation is limited; failures become 500 | `normalize_job`, `process_incoming_job` | ⚠️ Partial |
| `/jobs/explain-match` | POST | Generate narrative match explanation from resume + job description | Public | LLM fallback JSON defaults are used | `LLMProvider` | ⚠️ Partial |
| `/jobs/salary-estimate` | POST | Generate salary estimate | Public | Fallback salary JSON is used when LLM output is invalid | `LLMProvider` | ⚠️ Partial |
| `/jobs/autocomplete` | GET | Return keyword and title suggestions | Public | Empty query returns empty list; DB/title query is wrapped in broad `except Exception: pass` | `backend.config.pakistan_jobs_config.KEYWORDS`, `Job` model | ✅ Functional |

### 3.2 Profile router (`backend/routers/profile.py`)

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/profile` | POST | Upload profile, optional resume file, and store profile text | Auth required | Resume file validation is explicit; errors are 415/413; generic failures return 500 | `UserProfile`, optional Chroma indexing | ✅ Functional |
| `/profile` | GET | List paginated profiles and selected profile metadata | Auth required | Exceptions are converted to 500 | `UserProfile`, optional Chroma collection | ✅ Functional |
| `/profile/select/{profile_id}` | POST | Select a profile by ID | Auth required | 404 when profile is missing | `UserPreference` | ✅ Functional |
| `/profile/select` | POST | Legacy selection payload | Auth required | 400 on invalid payload | `UserPreference` | ✅ Functional |
| `/profile/selected` | GET | Return selected profile | Auth required | Returns `null` state instead of 404 | `UserPreference`, `UserProfile` | ✅ Functional |
| `/profile/{profile_id}` | GET | Fetch one profile | Auth required | 404 on missing profile | `UserProfile` | ✅ Functional |
| `/profile/{profile_id}` | DELETE | Delete a profile | Auth required | 404 or 500 on failure | `UserProfile` | ✅ Functional |
| `/profile/{profile_id}` | PATCH | Update profile fields and optional resume upload | Auth required | Resume upload validated; generic failures become 500 | `UserProfile` | ⚠️ Partial |

**Profile router issues:**
- `update_profile()` rebuilds `resume_text` from the incoming fields, which can **overwrite existing resume content** and lose prior text.
- Chroma indexing is best-effort and exceptions are suppressed.

### 3.3 Applications router (`backend/routers/applications.py`)

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/applications/` | POST | Create a new application | Auth required | Uses `ApplicationCreate`; defaults status to Saved if omitted | `Application` model | ✅ Functional |
| `/applications/` | GET | List applications, optionally filtered by status | Auth required | No validation on `status` query param | `Application` model | ✅ Functional |
| `/applications/health-score` | GET | Compute job-search health score and guidance | Auth required | No explicit error handling; uses model data directly | `Application`, `UserProfile`, `ResumeVersion` | ✅ Functional |
| `/applications/{app_id}` | GET | Fetch one application | Auth required | 404 when not found | `Application` | ✅ Functional |
| `/applications/{app_id}/status` | PATCH | Update application status | Auth required | 404 when not found | `Application` | ✅ Functional |
| `/applications/{app_id}` | PATCH | Update arbitrary application fields | Auth required | Uses generic `update.model_dump`; no status whitelist | `Application` | ⚠️ Partial |
| `/applications/{app_id}` | DELETE | Delete an application | Auth required | 404 when not found | `Application` | ✅ Functional |

### 3.4 Cover letter router (`backend/routers/cover_letter.py`)

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/cover-letter/generate` | POST | Generate a tailored cover letter using RAG-backed async generation | Auth required | Returns 503 if RAG dependencies are unavailable | `generate_cover_letter_with_rag_async`, `save_cover_letter_artifacts` | ⚠️ Partial |

### 3.5 Intelligence router (`backend/routers/intelligence.py`)

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/intelligence/skill-gap` | POST | Compare user skills against job descriptions and return missing skills | Auth required | Falls back to empty response if JSON parsing fails | `LLMProvider`, `UserProfile` | ⚠️ Partial |
| `/intelligence/interview-prep` | POST | Generate interview questions | Auth required | Falls back to empty question list on parse failure | `LLMProvider` | ⚠️ Partial |

### 3.6 Voice interview router (`backend/routers/voice_interview.py`)

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/interview/evaluate` | POST | Evaluate a candidate answer with LLM coaching | Public | No auth; returns raw LLM output | `LLMProvider` | ⚠️ Partial |
| `/interview/generate-questions` | POST | Generate interview questions for a job title | Public | No auth; returns raw questions text | `LLMProvider` | ⚠️ Partial |
| `/interview/predict` | POST | Predict interview questions from resume + job description | Public | Falls back to a default question if JSON parsing fails | `LLMProvider`, `InterviewPredictRequest` | ⚠️ Partial |

### 3.7 Browser extension router (`backend/routers/browser_extension.py`)

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/extension/analyze-url` | POST | Import a job posting from a URL and save it to the DB | Public | 400 if URL extraction fails; otherwise returns saved job info | `extract_job_text_from_url`, `normalize_job`, `process_incoming_job`, `core.database.get_db` | ⚠️ Partial |

### 3.8 Kanban router (`backend/routers/kanban.py`)

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/kanban/board` | GET | Return grouped applications by status | Auth required | No explicit error handling for DB or missing app data | `Application`, `UserProfile`, `core.database.get_db` | ✅ Functional |
| `/kanban/move` | POST | Move an application between statuses | Auth required | 404 if application not found; 400 on invalid status | `Application` | ✅ Functional |
| `/kanban/follow-up-email` | POST | Generate a follow-up email draft for an application | Auth required | Fallback draft is used if LLM returns empty/AI error text | `LLMProvider` | ✅ Functional |

### 3.9 Follow-up router (`backend/routers/followup.py`)

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/followup/check` | GET | Find stale applications and generate follow-up drafts | Auth required | Returns empty list if none are stale | `Application`, `LLMProvider` | ✅ Functional |
| `/followup/send/{app_id}` | POST | Mark follow-up as sent | Auth required | 404 if application missing | `Application` | ✅ Functional |

### 3.10 Daily scout router (`backend/routers/daily_scout.py`)

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/scout/run` | POST | Run daily scout search and persist matches | Public | Relies on `ScoutRequest` validation; any downstream errors propagate | `run_daily_scout` | ⚠️ Partial |
| `/scout/status` | GET | Return scout status information | Public | No error handling; `enabled` is forced to `True` in the response | `get_scout_status` | ⚠️ Partial |

### 3.11 Phase 3 key findings
- **Authentication is inconsistent:** some endpoints are public (job search, interview, extension, daily scout), while others are protected. This is not inherently wrong, but the product surface should be deliberate and documented.
- **LLM output is not consistently validated:** several routers silently fall back to defaults or empty results when the model output is malformed.
- **The profile update flow has a real data-loss bug:** `update_profile()` can overwrite `resume_text` and drop previously saved resume content.
- **The browser extension route is unauthenticated** and accepts raw URLs plus imported content, which increases the risk of abuse and unexpected ingestion.
- **`/jobs/search/stream` is protected via a stream token flow**, but the user experience and client integration should be audited separately.

## Phase 4: Backend – Student Module Endpoints

### 4.1 Student router and API router (`backend/routers/student.py`)

The student workflow is split across two routers:
- `router = APIRouter(prefix="/student", ...)`
- `api_router = APIRouter(prefix="/api/student", ...)`

This means the same logical feature is exposed under **two path prefixes**. The frontend appears to consume the `/api/student/*` routes, so this duplication should be treated as a maintenance and compatibility risk.

### 4.2 University filtering and detail endpoints

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/api/student/universities/filter` | GET | Filter universities and programs by country, ranking, tuition, degree, intake, scholarships, and pagination | Auth required | Validates `page` and `limit`; returns 503 on DB query failures | `University`, `Program`, `Scholarship` | ✅ Functional |
| `/api/student/university/{university_id}/detail` | GET | Load a university with its programs and scholarships | Auth required | 404 when university is missing | `University`, `Program`, `Scholarship` | ✅ Functional |

### 4.3 Student profile endpoints

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/student/profile` and `/api/student/profile` | POST | Create a student profile and set it as selected | Auth required | Uses `StudentProfileCreate`; returns 200 on success | `StudentProfile`, `UserPreference` | ✅ Functional |
| `/api/student/profile` | GET | Fetch the current selected student profile, or latest profile if none selected | Auth required | 404 when no profile exists | `StudentProfile` | ✅ Functional |
| `/student/profiles` and `/api/student/profiles` | GET | List all student profiles and selected profile ID | Auth required | Cleans stale selected profile ID if missing | `StudentProfile`, `UserPreference` | ✅ Functional |
| `/student/profile/select/{profile_id}` and `/api/student/profile/select/{profile_id}` | POST | Select an existing student profile | Auth required | 404 if profile not found | `UserPreference` | ✅ Functional |
| `/student/profile/{profile_id}` and `/api/student/profile/{profile_id}` | DELETE | Delete a student profile and reselect fallback | Auth required | 404 if missing | `StudentProfile`, `UserPreference` | ✅ Functional |
| `/student/profile/{profile_id}` and `/api/student/profile/{profile_id}` | PATCH | Update a student profile | Auth required | Uses `StudentProfileUpdate`; reindexes asynchronously | `StudentProfile`, `backend.services.university_match_service` | ✅ Functional |

### 4.4 Matching and recommendation endpoints

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/student/recommend` and `/api/student/recommend` | POST | Generate university recommendations for a selected profile using RAG/LLM, with caching fallback | Auth required | 503 if recommendation dependencies unavailable; 404 if student profile missing; 422 if `intended_major` is missing | `generate_match_analysis_async`, `UniversityMatchCache`, `backend.services.university_match_service` | ⚠️ Partial |
| `/api/student/match/recommend` | POST | Produce ranked program matches using vector retrieval and per-program scoring | Auth required | Returns empty result on `TESTING_MODE`; logs and skips failures for candidate scoring | `backend.services.university_match_service` | ⚠️ Partial |
| `/api/student/match/program/{program_id}` | GET | Fetch a detailed match for one program | Auth required | 404 if student profile or program match is unavailable | `backend.services.university_match_service` | ⚠️ Partial |
| `/api/student/match/explain` | GET | Alias of match detail | Auth required | Delegates to same logic as `/match/program/{program_id}` | `backend.services.university_match_service` | ⚠️ Partial |

**Matching findings:**
- Recommendation generation has a **fallback path** when indexing is disabled, which keeps the API alive but reduces match quality.
- `recommend_universities()` caches results in `UniversityMatchCache` and uses `expires_at` semantics, but it does not appear to enforce cache invalidation beyond the expiry check.
- `match_recommend()` is vulnerable to returning an empty list when any downstream service fails, which can hide real issues unless monitored.

### 4.5 Save / apply / applications endpoints

| Path | Method | Purpose | Auth | Validation / Error Handling | Dependencies | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/api/student/save` | POST | Save a program to a student's saved list | Auth required | 404 if student profile or program missing | `SavedProgram` | ✅ Functional |
| `/api/student/saved/{student_id}` | GET | List saved programs for a student | Auth required | Returns list of saved program payloads | `SavedProgram`, `Program`, `University` | ✅ Functional |
| `/api/student/apply` | POST | Create a study application record | Auth required | 404 if student profile or program missing | `StudyApplication` | ✅ Functional |
| `/api/student/applications/{application_id}` | PUT | Update study application status and notes | Auth required | 404 if application missing | `StudyApplication` | ✅ Functional |
| `/api/student/applications/{student_id}` | GET | List study applications for a student | Auth required | Returns serialized study applications | `StudyApplication`, `Program`, `University` | ✅ Functional |

### 4.6 Phase 4 key findings
- The student module is **feature-rich**, but the path duplication between `/student/*` and `/api/student/*` introduces ambiguity in client usage and should be normalized.
- The recommendation workflow is **partially operational**: it has caching, fallbacks, and async RAG integration, but the behavior can degrade silently when indexing or matching fails.
- The API surface is **authenticated** consistently, unlike several of the job/extension routes.

## Phase 5: Core Services & AI Techniques

### 5.1 `core/rag_service.py`
- **What it does:** provides ChromaDB-backed retrieval, embedding model loading, cover-letter generation, and university-program match analysis.
- **AI/ML techniques:** sentence-transformers embeddings, ChromaDB vector search, optional LLM-based generation, heuristic fallback generation for both cover letters and university matching.
- **External dependencies:** `sentence-transformers`, `chromadb`, and reusable `LLMProvider`.
- **Performance / operations:** uses global singleton caches for the embedding model and collection; blocking synchronous load on first access; asynchronous retrieval helpers exist.
- **Strengths:** good separation of retrieval and generation; explicit fallbacks when embeddings or LLMs are unavailable.
- **Weaknesses:** large synchronous startup cost on first use; fallback logic can hide data-quality issues; no explicit retry or telemetry around Chroma operations.

### 5.2 `core/llm_provider.py`
- **What it does:** builds provider backends for OpenRouter, OpenAI, Novita, and Groq and exposes a unified `ask()` method.
- **AI/ML techniques:** provider abstraction and retry orchestration, not model training.
- **External dependencies:** `requests`, `tenacity`.
- **Performance / operations:** retries transient failures with exponential backoff; all calls are synchronous HTTP POSTs with 60-second timeouts.
- **Strengths:** multi-provider fallback, env-driven provider selection, simple integration surface.
- **Weaknesses:** provider order logic is complex and may prefer unexpected backends; if no key is configured, downstream callers often receive generic `AI error:` strings rather than structured errors.

### 5.3 `core/skill_extractor.py`
- **What it does:** extracts skills from free text using spaCy NER when available, regex heuristics, and a fallback skill mapping.
- **AI/ML techniques:** optional spaCy NER plus deterministic heuristics.
- **External dependencies:** optional `spacy` and `data/skills_mapping.json`.
- **Performance / operations:** loads `en_core_web_sm` on each call if spaCy is installed, which can be expensive.
- **Strengths:** provides a reasonable fallback even without spaCy.
- **Weaknesses:** no caching of the NLP model; the `normalize_skill()` behavior may over-normalize terms; there is no robust validation of extracted entities.

### 5.4 `core/match_explainer.py`
- **What it does:** calculates matched and missing skills, experience fit, and explanation payloads for job/profile matches.
- **AI/ML techniques:** heuristic matching only, with a 7-day in-memory cache.
- **External dependencies:** none beyond `core.skill_extractor`.
- **Strengths:** inexpensive and deterministic.
- **Weaknesses:** skill matching is simplistic and may underperform on nuanced resumes; cache is in-memory only, so it does not survive restarts.

### 5.5 `core/deduplicator.py`
- **What it does:** deduplicates incoming jobs via fingerprinting, fuzzy title/company matching, and description similarity.
- **AI/ML techniques:** uses `rapidfuzz` token sorting and ratio scoring.
- **External dependencies:** `rapidfuzz`.
- **Performance / operations:** query candidates by city and within a 60-day window.
- **Strengths:** multi-layer dedupe logic helps reduce duplicate ingestion.
- **Weaknesses:** candidate selection is limited to city-based lookups, so duplicate detection may miss cross-city duplicates; merge logic does not validate all fields thoroughly.

### 5.6 `core/normalizer.py`
- **What it does:** standardizes scraped job payloads, cleans titles/company names, parses dates and salary strings, and normalizes city names.
- **AI/ML techniques:** none.
- **External dependencies:** none.
- **Performance / operations:** simple deterministic transformations.
- **Strengths:** improves consistency across scraper outputs.
- **Weaknesses:** date parsing is heuristic-only and may mis-handle unfamiliar formats; `clean_company()` has a small hardcoded mapping set, so coverage is limited.

### 5.7 `core/geo.py`
- **What it does:** fetches countries from `restcountries.com` and provides static city fallback data.
- **AI/ML techniques:** none.
- **External dependencies:** `requests`.
- **Strengths:** easy to wire into location-based features.
- **Weaknesses:** external API dependency introduces runtime fragility; it is not currently tied deeply into the main job pipeline.

### 5.8 `core/scheduler.py`
- **What it does:** registers and runs lightweight background tasks for scrapers, dedupe cleanup, and university match refresh.
- **AI/ML techniques:** none.
- **External dependencies:** scrapers and `backend.services.university_match_service`.
- **Performance / operations:** uses an in-process thread loop and calls DB-backed tasks directly.
- **Strengths:** simple operational model and easy to inspect.
- **Weaknesses:** not production-grade for multi-instance deployments; no persistent scheduler state, no backoff/error isolation, and no queueing.

### 5.9 `core/engine.py`
- **What it does:** wraps LLM analysis for jobs, resumes, matching, salary negotiation, and filtering.
- **AI/ML techniques:** LLM-based natural language analysis.
- **External dependencies:** `LLMProvider`.
- **Strengths:** presents a clear high-level API for downstream consumers.
- **Weaknesses:** response parsing is brittle and heavily dependent on free-form model output; it is not used consistently throughout the API surface.

### 5.10 `core/daily_scout.py`
- **What it does:** searches live jobs, scores them against a lightweight heuristic, and saves top matches.
- **AI/ML techniques:** heuristic keyword overlap scoring; no real resume matching.
- **External dependencies:** `search_jobs`, `process_incoming_job`, `normalize_job`.
- **Performance / operations:** single-process, synchronous flow.
- **Strengths:** provides a usable automation path for top-match job discovery.
- **Weaknesses:** `resume_text` is initialized as an empty string and never loaded from the user profile, so the scoring is not truly user-aware; the current implementation is closer to a keyword filter than a tailored scout.

### 5.11 `core/pdf_generator.py`
- **What it does:** generates ATS-friendly PDF resumes using ReportLab.
- **AI/ML techniques:** none.
- **External dependencies:** `reportlab`.
- **Strengths:** simple, deterministic resume export path.
- **Weaknesses:** logging is print-based rather than structured; there is no validation for content structure or output directory handling.

### 5.12 Phase 5 key findings
- The core AI stack is **functional but uneven**: the project has solid service abstractions and fallback behavior, but the quality depends heavily on LLM availability and prompt stability.
- The **job-matching intelligence is not fully production-grade** because several important flows still rely on heuristics or loosely parsed LLM output.
- The **Daily Scout loop is not truly personalized** and should be treated as a partial implementation until resume/profile context is wired in.

## Phase 6: Scrapers & Ingestion Pipelines

### 6.1 Shared ingestion path
- The shared ingestion pipeline in [scrapers/common.py](scrapers/common.py) is the central path used by most scrapers.
- `normalize_and_store()` normalizes each raw payload, drops incomplete records, and sends the payload through `process_incoming_job()` for deduplication and upsert behavior.
- This is a **good design choice** because it centralizes field cleanup and duplicate handling, but it also means all scrapers inherit any bugs in `normalize_job()` and `process_incoming_job()`.

### 6.2 `scrapers/rozee_scraper.py`
- **What it does:** scrapes Rozee job pages using `requests` + retries, extracts a JSON payload from the page when possible, and falls back to HTML parsing if structured data is missing.
- **Operational behavior:** retries transient HTTP failures, uses a custom user agent, and aggregates jobs across keyword/city combinations.
- **Strengths:** strong recovery path when JSON payloads are absent; explicit retry logic.
- **Weaknesses:** the parser depends on brittle page markup and may silently miss jobs if the DOM changes; `scrape_query()` is still only a best-effort scraper.

### 6.3 `scrapers/mustakbil_scraper.py`
- **What it does:** scrapes Mustakbil listing pages and detail pages, then returns all scraped jobs regardless of the supplied keyword.
- **Operational behavior:** uses a small number of listing URLs and stops early once it has collected jobs.
- **Strengths:** simple and low-latency.
- **Weaknesses:** the `keyword` argument is effectively ignored, which makes the scraper behavior less predictable; the detail selectors are very loose and may capture unrelated page text.

### 6.4 `scrapers/brightspyre_scraper.py`
- **What it does:** scrapes BrightSpyre jobs by keyword, uses a simple card-based parser, and applies `tech_job()` filtering.
- **Operational behavior:** page-by-page search, with a short per-page cap.
- **Strengths:** the tech filter removes many non-technical job posts.
- **Weaknesses:** the selectors are generic (`.job`, `article`, `a[href*='/jobs/']`) and can produce noisy results when the markup changes.

### 6.5 `scrapers/indeed_scraper.py`
- **What it does:** uses Playwright to render Indeed pages and parse job cards.
- **Operational behavior:** rate-limits requests, uses browser automation, and attempts to capture title, company, location, salary, and snippet.
- **Strengths:** more resilient to JS-heavy pages than plain HTTP scrapers.
- **Weaknesses:** it is **browser-dependent** and heavy; `playwright` is not listed in [requirements.txt](requirements.txt), so this path is likely to fail if the dependency is not installed in the runtime environment.

### 6.6 `scrapers/careers_page_scraper.py`
- **What it does:** scrapes company careers pages from a predefined list of Pakistani companies.
- **Operational behavior:** iterates through a set of candidate URLs and stops once jobs are found.
- **Strengths:** good for company-brand sourcing.
- **Weaknesses:** the selectors are broad and the scraper is fragile against layout changes; it also depends on the quality of the `PAKISTANI_COMPANIES` configuration.

### 6.7 `scripts/scrape_rozee.py`, `scripts/scrape_mustakbil.py`, and `scripts/scrape_indeed.py`
- These scripts are the main convenience wrappers around the scrapers.
- **Bug:** `--limit` is treated as a sample-run flag instead of a true count limit, because each script sends `run_sample()` when `limit` is truthy.
- **Impact:** a user passing `--limit 10` will not get a capped full crawl; they will get a sample run instead.
- **Recommendation:** make the CLI semantics explicit and separate `--sample` from `--limit`.

### 6.8 University and vector ingestion scripts
- [scripts/ingest_universities.py](scripts/ingest_universities.py) pulls university data from `universities.hipolabs.com`, creates mock program records, and indexes them into ChromaDB.
- [scripts/enrich_universities.py](scripts/enrich_universities.py) adds enrichment data (rankings, tuition, scholarships, and program details) using several external sources and a local cache.
- [scripts/ingest_programs_to_vector_db.py](scripts/ingest_programs_to_vector_db.py) delegates indexing to `backend.services.university_match_service.index_programs_to_vector_db()`.
- [scripts/refresh_match_cache.py](scripts/refresh_match_cache.py) refreshes cached student-program matches in a loop when `--daemon` is used.
- [scripts/backfill_skills.py](scripts/backfill_skills.py) backfills `job_skills` and `profile_skills` for existing records.
- **Observation:** the university ingestion path is **more operationally complex** than the job scrapers and depends on multiple external sources and background caches.

### 6.9 Legacy ingestion path
- [ingest.py](ingest.py) is a separate, top-level seed ingestion script that chunks local `.txt` / `.json` documents and writes them into a persistent Chroma collection.
- It is **not the same pipeline** as the production job/university ingestion flow and should not be treated as a current operational ingestion path without additional integration work.

### 6.10 Phase 6 key findings
- The ingestion architecture is **split across several layers**: shared normalization, source-specific scrapers, wrapper scripts, and a separate university/vector indexing flow.
- The project has a **good centralization point** in `normalize_and_store()`, but the scraper code is still **fragile and source-specific**.
- The **CLI ergonomics are weak**: the scrape wrapper scripts make `--limit` ambiguous, and the degree of browser dependence varies sharply across sources.

## Phase 7: Frontend, UX, and Client Integration

### 7.1 Frontend application shape
- The frontend is a **React 18 + Vite 5** single-page app in [frontend/src](frontend/src) with routes defined in [frontend/src/App.jsx](frontend/src/App.jsx).
- The UI includes a **career module** and a **university module**, backed by a shared sidebar in [frontend/src/components/Layout.jsx](frontend/src/components/Layout.jsx).
- The app is clearly built to support **jobs, applications, resume, cover letters, interviews, skill gap, daily scout, and student matching**.

### 7.2 Auth and session handling
- Authentication is managed by [frontend/src/contexts/AuthContext.jsx](frontend/src/contexts/AuthContext.jsx) and a shared API client in [frontend/src/api/client.js](frontend/src/api/client.js).
- The app boots by calling `authAPI.me()` and `studentAPI.listProfiles()`, then persists the selected profile ID in local state.
- **Bug / gap:** `handleLogout()` calls `authAPI.logout()`, but [frontend/src/api/client.js](frontend/src/api/client.js) does **not** define `authAPI.logout`, so the logout flow is currently broken at the client level.
- **Gap:** the `refresh_token` is stored but never consumed by the client, so the frontend does not implement a real refresh flow.
- **Gap:** `AUTH_BYPASS` is defined in [frontend/src/App.jsx](frontend/src/App.jsx) but is never used, which suggests stale or incomplete feature-flag logic.

### 7.3 API client behavior
- The API client rewrites relative URLs for local development using the Vite proxy in [frontend/vite.config.js](frontend/vite.config.js).
- In production, the client uses `VITE_API_URL` when configured, otherwise it relies on same-origin behavior.
- **Risk:** the client has no centralized retry or refresh behavior, so expired access tokens may cause abrupt logout instead of a graceful re-auth flow.

### 7.4 Frontend quality signals
- There is **no dedicated frontend test framework** configured in [frontend/package.json](frontend/package.json).
- The build setup is present, but the UI surface has no visible automated coverage for route behavior, auth flow, or API error handling.
- The current UX is feature-rich, but it is **not yet hardened for production client reliability**.

### 7.5 Browser extension
- The extension manifest in [extension/manifest.json](extension/manifest.json) exposes a popup flow that posts the active tab URL to `/extension/analyze-url`.
- The popup implementation in [extension/popup.js](extension/popup.js) sends a raw URL payload and does not add any auth or signing step.
- **Risk:** the extension is unauthenticated and directly triggers server-side URL ingestion, which increases the blast radius of bad input or abusive use.

### 7.6 Phase 7 key findings
- The frontend is **feature-complete in breadth** but **incomplete in reliability**.
- The most concrete frontend bug is the missing `authAPI.logout()` implementation.
- The extension path is currently the least hardened part of the product surface.

## Phase 8: Deployment, CI/CD, and Operational Readiness

### 8.1 Docker and containerization
- [Dockerfile](Dockerfile) builds a backend image from `python:3.11-slim-bookworm`, installs dependencies from [requirements.txt](requirements.txt), and runs the API via Uvicorn.
- [frontend/Dockerfile](frontend/Dockerfile) builds the React app and serves it with Nginx.
- [docker-compose.yml](docker-compose.yml) is a useful local development compose file, but it relies on the root `Dockerfile` and exposes only the backend and frontend container ports.

### 8.2 Production compose behavior
- [docker-compose.prod.yml](docker-compose.prod.yml) installs dependencies at runtime (`pip install -r requirements.txt`), which is slower and less reproducible than a prebuilt image.
- The production compose file defaults to `DATABASE_URL=sqlite:///./jobsync.db`, which is fine for local testing but not ideal for production-grade deployments.
- The production frontend image uses `npm install` and `npm run build` at container startup, which increases cold-start time and does not lock dependency resolution to a prebuilt artifact.

### 8.3 Vercel and hosting assumptions
- [vercel.json](vercel.json) rewrites all requests to `/index.py` at the root level.
- [frontend/vercel.json](frontend/vercel.json) rewrites all requests to `/index.html` for the frontend build.
- **Risk:** the repository currently contains **two different Vercel configs**, which can create deployment ambiguity depending on where the project is deployed.

### 8.4 CI/CD coverage
- [ci.yml](.github/workflows/ci.yml) validates migrations, runs `pytest`, and performs basic lint checks with `flake8` and `black`.
- [scrape-jobs.yml](.github/workflows/scrape-jobs.yml) and [scrape-universities.yml](.github/workflows/scrape-universities.yml) provide scheduled ingestion workflows.
- **Gap:** the CI pipeline does not run frontend build or lint checks, and it does not validate the browser extension or the Vite client integration.

### 8.5 Operational guidance
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) is useful, but it still assumes manual operational steps such as `alembic upgrade head` and ad hoc background job execution.
- The system would benefit from a **single canonical deployment path** that clearly distinguishes local, Docker, and serverless deployments.

### 8.6 Phase 8 key findings
- The project has **good container and CI foundations**, but the deployment path is not fully normalized.
- The main operational risk is **configuration ambiguity**, especially around Vercel and runtime dependency installation.

## Phase 9: Testing and Verification Coverage

### 9.1 Python test coverage
- The repository includes a Python test suite under [tests](tests), including auth, health, and application flows.
- The test fixture in [tests/conftest.py](tests/conftest.py) uses an in-memory SQLite database and overrides the FastAPI dependency injection for `get_db()`.
- This is a clean testing setup for backend behavior and gives the project a solid starting point.

### 9.2 Gaps in test coverage
- There is **no frontend test framework** in [frontend/package.json](frontend/package.json).
- There are no visible tests for the browser extension, the Vite proxy behavior, or the frontend auth flow.
- There are no visible integration tests covering the scraper wrapper scripts or the university enrichment flow.
- The current tests validate important backend paths, but they do **not** validate the full product surface.

### 9.3 CI limitations
- [ci.yml](.github/workflows/ci.yml) performs a migration check and backend `pytest`, but it does not run the frontend build or the app-level smoke tests for the UI.
- The current pipeline is therefore **backend-heavy** and would miss several frontend and deployment regressions.

### 9.4 Phase 9 key findings
- The backend has a usable test base, but the **frontend and integration layers are not covered**.
- The project would benefit from adding a small but meaningful set of **frontend and end-to-end smoke tests**.

## Phase 10: Security, Abuse Surface, and Data Integrity

### 10.1 Public and unauthenticated surfaces
- Several routes remain public by design, including `/jobs/search`, `/interview/*`, `/extension/analyze-url`, and `/scout/run`.
- That is acceptable only if the product intentionally exposes them; otherwise, the current boundary is inconsistent with the rest of the system.

### 10.2 CORS and cross-origin exposure
- [backend/main.py](backend/main.py) defaults `CORS_ORIGINS` to `*` when unset.
- That is permissive and should be treated as a deployment risk unless the service is intentionally public or behind a trusted reverse proxy.

### 10.3 URL ingestion and SSRF risk
- [core/url_ingestion.py](core/url_ingestion.py) fetches arbitrary URLs using `requests.get()` with no allowlist, scheme validation, or hostname restrictions.
- Because the extension route and internal ingestion path both accept arbitrary URLs, this creates a **server-side request forgery (SSRF) risk**.

### 10.4 Token handling weaknesses
- The refresh token is stored in local storage by [frontend/src/api/client.js](frontend/src/api/client.js), but the client does not actually use it for refresh.
- The backend supports logout revocation via `token_version`, but the frontend never calls the logout endpoint correctly.
- This combination leaves the client-side auth flow **partially implemented**.

### 10.5 Data integrity and ingestion safety
- The scraper and extension flows can persist malformed or noisy data because the normalization and dedupe layers are best-effort rather than strict.
- Many routes fall back to empty or generic results when model parsing fails, which can mask upstream data problems.

### 10.6 Phase 10 key findings
- The project has **real security and abuse-surface issues** that should be addressed before broader production rollout.
- The highest-risk areas are **unauthenticated URL ingestion**, **permissive CORS defaults**, and **incomplete client auth lifecycle management**.

## Phase 11: Overall Assessment and Prioritized Recommendations

### 11.1 Current overall status
- The project is **ambitious and well-structured**, with a rich feature set across job search, career tools, and university matching.
- The backend and data model are the strongest parts of the system, but the **operational, frontend, and security layers are still incomplete**.

### 11.2 Highest-priority fixes
1. **Fix frontend logout and refresh flow** in [frontend/src/api/client.js](frontend/src/api/client.js) and [frontend/src/contexts/AuthContext.jsx](frontend/src/contexts/AuthContext.jsx).
2. **Harden the extension and URL ingestion path** in [backend/routers/browser_extension.py](backend/routers/browser_extension.py) and [core/url_ingestion.py](core/url_ingestion.py).
3. **Normalize deployment configuration** so there is one clear path for Vercel, Docker, and local development.
4. **Resolve the migration and startup behavior** so Alembic state and runtime fallback logic are consistent.
5. **Add frontend and integration tests** so the UI and deployment path are covered by CI.

### 11.3 Best assets in the current codebase
- The backend schema and router coverage are broad and thoughtfully designed.
- The AI/provider abstraction is flexible and can support multiple downstream use cases.
- The scraper normalization and dedupe pipeline is a solid foundation for reliable ingestion.

### 11.4 Final audit conclusion
- The codebase is **not production-ready yet**, but it is **clearly buildable and feature-rich**.
- The main blockers are **operational consistency**, **client auth correctness**, **security hardening**, and **test coverage depth**.
- If those areas are addressed, the platform has a strong foundation for a production launch.

## Phase 12: Testing, Verification, and CI Hardening

### 12.1 Test inventory
- Backend unit & integration tests: present under `tests/` and exercised by `pytest` in CI.
- Test fixture strategy: `tests/conftest.py` uses an in-memory SQLite DB and DI overrides — good for isolation.
- Missing tests: frontend unit tests, browser-extension tests, end-to-end (E2E) smoke tests for the full stack, and integration tests for scrapers/ingestion.

### 12.2 Recommended verification improvements
- Add frontend unit tests (Vitest + React Testing Library) for route/auth flows and critical pages (`Jobs`, `Profile`, `Dashboard`).
- Add a small Playwright or Cypress E2E smoke test that boots the backend (in-memory DB) and verifies key pages and `/health`.
- Expand CI to run frontend build + unit tests and to fail the pipeline on build/test failures.
- Add migration verification step that asserts Alembic heads resolve to a single lineage or fails the build.
- Introduce basic contract tests (OpenAPI-driven) to ensure client-server expectations remain stable.

### 12.3 Phase 12 key findings
- The backend test scaffold is solid; frontend and full-product integration tests are the largest coverage gaps.
- CI should be extended to run frontend build/tests and migration-head validation to prevent regression deployments.

## Phase 13: Security & Authentication Deep Dive

### 13.1 Current security posture (summary)
- Permissive CORS default (`*`) when `CORS_ORIGINS` is unset.
- Unauthenticated ingestion surfaces: extension `/extension/analyze-url` and `core/url_ingestion.py` accept arbitrary URLs.
- Client-side tokens: refresh tokens stored in `localStorage` and not actively used for refresh flows.

### 13.2 Immediate remediation recommendations
- Lock down CORS by default: require `CORS_ORIGINS` and fail open only in explicit dev mode.
- Harden URL ingestion: validate scheme, host allowlist, DNS resolution check, block private IP ranges (SSRF protections), and size/timeout limits for fetched content.
- Move refresh-token flow to secure, HttpOnly cookies (or implement rotating refresh tokens) and stop storing long-lived secrets in `localStorage`.
- Implement server-side token revocation tied to `token_version` and ensure `authAPI.logout()` calls the backend to increment/revoke token state.
- Require authentication or a signed app key from the browser extension (or rate-limit and quota extension-origin requests).

### 13.3 Operational controls
- Rate-limit unauthenticated endpoints heavily and add per-user limits for authenticated endpoints.
- Add structured logging and alerting for repeated ingestion failures, excessive `/extension/analyze-url` usage, and SSRF/DNS anomalies.
- Ensure secrets (LLM keys, DB URLs) are never checked into the repo and validate `.env` usage in CI secrets.

### 13.4 Phase 13 key findings
- Security gaps are concentrated in the ingestion surface (SSRF), auth lifecycle (refresh + logout), and permissive deployment defaults (CORS, Vercel ambiguity).

## Phase 14: Feature Completion & Gap Analysis

### 14.1 High-impact feature gaps
- Frontend `authAPI.logout()` and a working refresh-token flow (frontend + backend).
- `Profile` update path that can overwrite `resume_text` (data-loss bug).
- Personalized `Daily Scout` — resume/profile context is not supplied to the scoring pipeline.
- Alembic multiple-heads — migration lineage must be reconciled.
- Missing runtime dependency declarations (e.g., Playwright) and ambiguous CLI semantics for scraper scripts (`--limit` vs `--sample`).
- Duplicate Vercel configs and inconsistent production-compose behavior (install-at-start vs prebuilt images).

### 14.2 Suggested prioritization (short → long)
- Small (days): implement `authAPI.logout()` + frontend call, add missing `playwright` to requirements or guard that path.
- Medium (1–2 weeks): implement refresh-token rotation with secure cookies; fix `resume_text` overwrite in `profile.update`.
- Medium (1–3 weeks): add frontend unit tests + CI build step and a small Playwright/Cypress smoke test.
- Large (2–6 weeks): reconcile Alembic heads, add robust SSRF protections and extension authentication, and rework production compose to use prebuilt images.

### 14.3 Phase 14 key findings
- The product is functionally complete in features, but a short list of reliability and security fixes will materially raise production readiness.

## Phase 15: Final Assessment & Prioritized Roadmap

### 15.1 One-paragraph final assessment
- JobSync Pro is a mature, feature-rich platform with a strong backend and well-separated AI/service abstractions. To reach production readiness the team should focus on a small, high-impact surface: auth lifecycle correctness, ingestion hardening (SSRF + extension), migration consistency, and frontend test/CI coverage.

### 15.2 Minimal viable hardening roadmap (ordered)
1. **Auth lifecycle** (implement logout, refresh rotation, secure refresh cookies) — high impact, medium effort.
2. **Ingestion hardening** (SSRF allowlist, extension signing, rate limits) — high impact, medium effort.
3. **Migrations** (reconcile Alembic heads, CI migration check) — medium impact, short effort.
4. **Frontend reliability** (add unit tests, CI build step, fix logout flow) — medium impact, medium effort.
5. **Operational improvements** (prebuilt production images, centralized deployment docs, structured logging/alerts) — medium impact, medium-to-large effort.

### 15.3 Closing note
- The appended phases complete the staged audit requested in `prompt.txt`. The recommendations above are intentionally prioritized to deliver the largest safety and reliability gains first.


