# JobSync Pro Analysis

## 1. Project Overview

JobSync Pro is an AI-assisted career and study-planning platform. It combines job discovery, resume optimization, cover letters, interview prep, application tracking, and university/program matching in one system. The product is built around two user journeys:

- a job-seeker workflow for finding roles, tailoring resumes, and tracking applications
- a student workflow for comparing universities and programs, saving matches, and tracking study applications

### High-level architecture

| Layer | What it does |
|---|---|
| Backend API | FastAPI application exposing auth, jobs, profile, resume, cover letter, interview, applications, intelligence, and student/university routes |
| Frontend dashboard | React single-page app built with Vite and React Router, providing job and student dashboards, profile editors, and AI tools |
| Chrome extension | Manifest v3 extension for capturing job posting URLs and sending them to the backend for analysis/import |
| CLI / scripts | Maintenance, scraping, smoke-test, ingestion, and verification scripts for jobs and universities |
| Background jobs | In-process scheduler and thread-pool execution for scraping, deduplication, cache refresh, and verification workflows |

The backend is organized around SQLAlchemy models, Pydantic schemas, and routers. Core business logic lives in `core/`, while integrations and source-specific scraping live in `backend/services/` and `backend/scrapers/`. The frontend consumes the API through an Axios client. Supporting scripts handle ingestion, verification, and smoke checks.

## 2. Technologies Used

### Backend
- FastAPI
- Uvicorn
- SQLAlchemy
- Alembic
- Pydantic
- Python 3.11+
- JWT authentication with bearer tokens and refresh-token support
- Tenacity for retry handling around LLM/API requests

### Database
- PostgreSQL for the main application database via `DATABASE_URL`
- Supabase/PostgreSQL deployment support
- SQLite appears in local/vector persistence and older documentation, but the backend database layer currently expects a PostgreSQL connection string

### Vector DB / Retrieval
- ChromaDB for persistent vector storage and retrieval
- sentence-transformers for embeddings
- BM25-style hybrid retrieval in the RAG layer
- RAG used for cover letters, resume support, and university/program matching

### LLM and AI
- OpenRouter
- Groq
- OpenAI-compatible provider abstraction
- Novita support in the provider layer
- sentence-transformers
- spaCy for optional skill extraction
- ChromaDB-backed retrieval augmented generation
- heuristic fallback paths when LLM or vector dependencies are unavailable

### Frontend
- React
- Vite
- Axios
- React Router
- Recharts
- Lucide icons
- Playwright for browser-based E2E tests in the frontend workspace

### Scraping and Data Processing
- requests
- BeautifulSoup / raw HTML parsing
- Playwright for browser-driven scraping where JavaScript rendering is needed
- rapidfuzz for fuzzy matching and deduplication
- pandas for data handling in scripts and imports
- url parsing and normalization utilities

### Deployment and Operations
- Docker
- docker-compose
- GitHub Actions
- Vercel
- production startup migrations through Alembic
- thread-pool-based background tasks and scheduler utilities

### Document and Resume Generation
- reportlab for PDF resume output
- HTML resume rendering for browser-side export

## 3. What Is Built

### 3.1 Job Module

The job module is the main career workflow in the product.

- Job search is backed by the database and can also fetch live listings from external sources when needed.
- Search supports streaming via server-sent events so long-running queries can update the UI progressively.
- Job matching compares a selected profile and resume text against job descriptions and skills.
- Resume upload, parsing, rewriting, and job-specific tailoring are built into the API.
- Cover letters are generated with RAG context from the user profile and the selected job.
- Application tracking is available through status views and a Kanban workflow.
- Interview preparation includes question generation and answer-related prompts.
- Skill gap analysis compares a job description to extracted or stored skills.
- Salary estimation is available for job titles and locations.
- Daily Scout supports automated discovery and refresh of jobs.
- The Chrome extension provides a one-click path for saving a job posting URL into JobSync.

#### Current job profile system
- The profile system is now structured rather than free-text only.
- `UserProfile` stores personal details, skills, achievements, preferred titles, salary preferences, location preference, and structured child records for education, work experience, certifications, projects, and languages.
- Job search can use selected-profile preferences to rank results.
- Resume generation can now build from the structured profile rather than relying only on a text blob.

### 3.2 Student (University) Module

The student/university workflow has been removed from the core codebase for the current distribution. Historical design notes and analysis remain in project documents, but active routes, components, and services for university/program matching should not be relied upon in this tree.
### 3.3 Shared / Cross-cutting

- JWT authentication protects the authenticated API surface.
- `UserPreference` stores the currently selected job profile and student profile.
- RAG is shared across resume, cover letter, and university workflows.
- The LLM provider layer abstracts OpenRouter, Groq, OpenAI-compatible, and Novita backends.
- Scraper normalization and deduplication are reused across multiple job sources.
- A scheduler coordinates refresh and ingestion jobs.
- GitHub Actions workflows automate periodic updates for jobs and universities.

## 4. How Search Works

### 4.1 Job Search

Primary job search is database-first. The backend queries the jobs table using the requested keywords, city, location, and sort mode. If the local dataset is empty or incomplete, the system triggers live scrapers in parallel, normalizes the resulting records, deduplicates them, and upserts them into the database.

Key behaviors:
- database-backed keyword search on job title and description
- optional fallback to live external sources when search coverage is low
- concurrent source fetching with timeouts
- normalization of title, location, and job metadata before storage
- deduplication using fingerprints and similarity checks
- optional profile-aware ranking based on selected profile skills and preferences
- SSE endpoint for progressive result delivery

### 4.2 University Search

University search is also database-first, with program filters handled through SQLAlchemy queries.

Key behaviors:
- filter by country, city, degree level, tuition, and scholarship availability
- compare student profile data to program requirements and tuition ranges
- use ChromaDB and heuristic rules for matching and explanations
- optionally perform live verification through SearXNG when fresh web evidence is required
- cache verification results so repeated requests are faster and more stable

## 5. Pages / Routes Offered

### Auth
| Route | Purpose |
|---|---|
| `/login` | User authentication page |
| `/signup` | User registration page |

### Job and productivity pages
| Route | Purpose |
|---|---|
| `/` | Main dashboard overview |
| `/dashboard` | Dashboard alias in the app shell |
| `/jobs` | Job search and results |
| `/profile` | Job profile editor and profile list |
| `/applications` | Job application list |
| `/kanban` | Kanban board for applications |
| `/resume` | Resume builder, analyzer, and rewriter |
| `/cover-letter` | Cover letter generation |
| `/interview` | Interview preparation |
| `/mock-interview` | Mock interview experience |
| `/skill-gap` | Skill gap analysis |
| `/daily-scout` | Automated job discovery |

### Student routes

Student-focused routes and pages have been removed from the active application routes in this repository. Refer to historical notes if you need to re-enable or port these features.

## 6. Analysis of Both Modules

### Strengths
- The product covers both job search and university planning in one platform.
- The architecture is modular, with separate routers, services, core logic, and UI pages.
- RAG is integrated into multiple user flows instead of being isolated to one feature.
- The system includes practical fallbacks, such as heuristic matching when an LLM is unavailable.
- Search and matching both rely on normalized and deduplicated data, which improves consistency.
- The current job profile system is structured and now supports richer resume generation and job ranking.

### Weaknesses / Gaps
- The university module still depends heavily on the quality and completeness of imported program data, especially outside the US.
- Personalization is still mostly rules-based and skill-overlap-based; there is no collaborative filtering or behavioral recommendation layer.
- Some scraping paths depend on optional browser tooling, so they are only as reliable as the runtime environment and installed dependencies.
- Frontend automated test coverage is limited compared with the size of the feature surface.
- Live verification is powerful, but it remains optional and dependent on external web search availability.

### Recommendations
- Expand live verification coverage to additional regions and make the evidence cache easier to review.
- Add stronger recommendation personalization beyond skills and preferences.
- Introduce more structured observability for scraping and LLM failures.
- Add frontend and API smoke tests for the most important job and student flows.
- Continue improving profile-driven ranking so search, resume generation, and cover letters all use the same canonical user data.

## 7. Conclusion

JobSync Pro is a broad, feature-rich AI career and study platform. The job module is the more mature part of the product and already includes profile-driven matching, resume support, cover letters, and application tracking. The student module is substantial and useful, but its practical value depends more heavily on the quality of the imported university and program data, especially outside the US. Overall, the project looks production-oriented, with the main remaining work centered on better data quality, stronger testing, and deeper personalization rather than missing core workflows.
