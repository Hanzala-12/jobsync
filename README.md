# JobSync Pro

JobSync Pro is an AI-powered job search and application management platform with a FastAPI backend and a React/Vite frontend. The repository combines job discovery, profile-aware resume tailoring, blueprint-based cover letter generation, university matching, background automation, and operational tooling in a single workspace.

## What It Does

- Searches and normalizes jobs from multiple sources, then ranks them against the selected candidate profile.
- Builds tailored resumes and cover letters from structured profile data.
- Generates cover letters through a fast blueprint engine with optional LLM polishing and PDF download support.
- Supports a student/university workflow with profile CRUD, recommendation scoring, live verification, and provenance-aware detail views.
- Includes background jobs, monitoring endpoints, schema migrations, and end-to-end test coverage.

## Architecture

The application is organized into three main layers:

- `backend/` contains the FastAPI application, routers, database models, services, tasks, and migrations.
- `core/` contains reusable business logic such as blueprint engines, PDF generation, RAG helpers, ranking, validation, and normalization.
- `frontend/` contains the React UI, API client, pages, shared components, and browser tests.

Supporting assets live in:

- `blueprints/` for structured generation templates.
- `scripts/` for validation, imports, smoke tests, and data utilities.
- `tests/` for backend integration coverage.
- `docs/` for user-facing workflow documentation.

## Key Features

### Job Workflow

- Multi-source job search and normalization.
- Streaming job search updates in the UI.
- Profile-aware ranking and match explanations.
- Resume tailoring and application tracking.
- Salary estimation and daily scout automation.

### Cover Letters

- Blueprint-driven generation for fast, deterministic drafts.
- Optional short-timeout LLM polishing for the body section only.
- Cached responses for repeated requests.
- PDF download endpoint for finished letters.

### University Workflow

- Student profile CRUD and profile selection.
- University browsing, filtering, and recommendation scoring.
- Live verification with freshness and provenance metadata.
- On-demand scraping and correction reporting.

### Operations

- Alembic migrations and startup schema checks.
- Health and metrics endpoints.
- In-process rate limiting and logging middleware.
- Celery integration hooks and task dispatch helpers.

## Technology Stack

- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic, Celery, Redis, ReportLab.
- Frontend: React, Vite, React Router, Axios, Lucide icons, Vitest, Playwright.
- AI and retrieval: Groq, OpenAI-compatible providers, ChromaDB, sentence-transformers, rank_bm25.
- Data and scraping: Requests, BeautifulSoup, lxml, pandas, spaCy, scikit-learn.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An installed Python virtual environment for this repo

### Backend Setup

From the project root, activate the existing environment and install dependencies:

```bash
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the API locally:

```bash
venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend Setup

Install frontend dependencies:

```bash
cd frontend
npm install
```

Run the UI:

```bash
npm run dev
```

## Configuration

Set environment variables in `.env` or your shell as needed. Common values include:

- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `GROQ_API_KEY`
- `CORS_ORIGINS`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

The application supports provider fallback behavior, so the exact AI key used depends on your deployment configuration.

## Common Commands

Backend checks:

```bash
venv\Scripts\python.exe -m pytest
```

Frontend checks:

```bash
cd frontend
npm test
npm run lint
npm run build
```

Cover letter validation:

```bash
venv\Scripts\python.exe scripts/test_cover_letter_blueprint.py
```

## API Surface

Notable endpoints include:

- `POST /auth/login`
- `GET /jobs/search`
- `POST /resume/analyze`
- `POST /cover-letter/generate`
- `POST /cover-letter/download`
- `GET /applications/`
- `GET /health`
- `GET /metrics`

## Testing

The repository includes backend integration tests, frontend component tests, browser-level E2E coverage, and targeted validation scripts. The cover-letter blueprint flow is covered by `tests/test_cover_letter.py` and `scripts/test_cover_letter_blueprint.py`.

## Deployment Notes

- Startup migrations run through `backend.main` when enabled.
- Redis-backed background and rate-limiting features are optional but supported.
- The frontend expects the API base URL to be configured for non-local deployments.
- Production deployments should set `CORS_ORIGINS` explicitly.

## Project Structure

```text
backend/        FastAPI app, routers, services, models, tasks, migrations
core/           Shared business logic and generation engines
frontend/       React app, pages, components, API client, tests
blueprints/     Structured generation templates
scripts/        Validation, import, and smoke-test scripts
tests/          Backend integration tests
docs/           Product and workflow documentation
```

## Current Focus Areas

- Blueprint-based cover letter generation for fast responses.
- Profile-aware job and resume workflows.
- University matching with live verification and provenance.
- Operational hardening around background execution and monitoring.
