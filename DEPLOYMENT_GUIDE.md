# Deployment Guide

## Backend Deployment

### Environment Variables
Set the required variables in your deployment environment or `.env` file.

- `OPENROUTER_API_KEY`
- `GROQ_API_KEY`
- `DATABASE_URL`
- `CHROMA_DB_DIR`
- `LLM_FALLBACK_MODE`
- `CORS_ORIGINS`
- `RATE_LIMIT_REQUESTS`
- `RATE_LIMIT_PERIOD`
- `REDIS_URL` (shared Redis endpoint for Celery and distributed rate limiting)
- `ENABLE_METRICS` (set to `true` to expose `/metrics` for Prometheus)
- `ALLOWED_INGESTION_DOMAINS` (comma-separated SSRF allowlist for URL ingestion)
- `ENABLE_STUDENT_MODULE`
- `MAX_MATCH_RESULTS`
- `MATCH_CACHE_TTL_DAYS`
- `UNIVFYI_BASE_URL`
- `UNIVFYI_API_KEY`
- `COLLEGE_SCORECARD_API_KEY` (free key from api.data.gov for U.S. university enrichment)
- `ENABLE_US_UNIVERSITY_ENRICHMENT`
- `ENABLE_STUDYPORTALS_REDIRECT`
- `SEARXNG_BASE_URL` (self-hosted search gateway for live university verification)
- `ENABLE_LIVE_VERIFICATION`
- `VERIFICATION_CACHE_TTL_HOURS`
- `ENABLE_CELERY`
- `CELERY_BROKER_URL` (defaults to `redis://localhost:6379/0`)
- `CELERY_RESULT_BACKEND` (defaults to the broker URL)
- `CELERY_QUEUE_NAME`

### Redis-backed jobs and rate limiting

Start Redis locally before enabling Celery or the distributed rate limiter:

```bash
docker-compose up -d redis
```

Then run the API and worker with `ENABLE_CELERY=true` so job scrapes, cover-letter generation, and refresh tasks are queued instead of running synchronously.

### Database Migration
Run migrations before starting the server:

```bash
alembic upgrade head
```

Validate the schema and local vector store before exposing the app:

```bash
python scripts/validate_schema.py
```

### Start the API Server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Background Jobs
Run the existing job indexer and the study match refresh job as needed:

```bash
python backend/job_indexer.py
python scripts/ingest_programs_to_vector_db.py
python scripts/refresh_match_cache.py --daemon
python scripts/import_programs_from_csv.py --csv data/programs.csv --limit 100 --index
python scripts/scrape_programs_from_univfyi.py --top-qs 10 --missing-only
python scripts/enrich_us_universities.py --delay-seconds 1.0 --retries 3
```

### Celery and Redis
Set `ENABLE_CELERY=true` when you want scrape jobs, cover-letter generation, and refresh tasks to be queued instead of running in the request worker.

Start Redis locally:

```bash
redis-server
```

Start a Celery worker:

```bash
celery -A backend.celery_app worker --loglevel=info
```

If you use Docker Compose, the repository now includes a `redis` service and a `celery-worker` service. Keep `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND` pointed at the same Redis instance so the worker, API, and rate limiter share one backend.

The task status endpoint is available at `/api/tasks/{task_id}/status` and can be polled from the frontend when a scrape or refresh has been queued.

### Monitoring

Start the monitoring stack with:

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

Prometheus scrapes the backend `/metrics` endpoint when `ENABLE_METRICS=true`, and Grafana is available on port `3001`.

### Local SQLite development

If you need a local-only SQLite database, initialize it with:

```bash
python scripts/init_local_sqlite_dev.py --path ./jobsync_local.db
```

Then set `DATABASE_URL=sqlite:///./jobsync_local.db` and `RUN_STARTUP_MIGRATIONS=false` for that developer-only environment.

### Redis integration smoke test

After `docker-compose up -d` brings up Redis and the Celery worker, run:

```bash
python scripts/test_celery_redis_integration.py
```

The script sends `backend.tasks.add(4, 5)` through the broker and waits for a real worker result.

## Frontend Deployment

### Build for Production

```bash
npm run build
```

### Frontend Environment Variables
Set the API URL for production builds:

```bash
VITE_API_URL=https://api.yourdomain.com
```

### Deploying to Vercel or Netlify
- Build the app with `npm run build`.
- Publish the generated `dist/` folder.
- Point `VITE_API_URL` at the backend API domain.
- If `VITE_API_URL` is unset, the frontend uses same-origin requests and prefixes `/api` locally.
- Resume PDF export runs entirely in the browser through `html2pdf.js`, so no extra backend PDF service or API key is required.
- The general profile page now stores structured education, work experience, certifications, projects, languages, and preferences; after deployment, run `python scripts/test_profile_completeness.py` against the live API to verify resume generation uses real profile data.

## One-Time Setup Commands

```bash
python scripts/refresh_europe_catalog.py
python scripts/ingest_programs_to_vector_db.py
python scripts/refresh_match_cache.py --daemon
```

The university refresh uses the live Europe sweep so coverage stays current and the seeded catalog is not limited to the older sample source.

### Program Data Refresh
- Set `UNIVFYI_BASE_URL` and `UNIVFYI_API_KEY` for the UnivFYI scraper.
- Use `python scripts/import_programs_from_csv.py --csv <path>` for batch imports.
- Use `python scripts/import_programs_from_csv.py --csv <path> --scrape-univfyi --index` to run the batch importer and optional UnivFYI enrichment in one pass.
- The weekly workflow is defined in `.github/workflows/enrich_programs.yml` and can also be triggered manually.

### U.S. University Enrichment
- Set `COLLEGE_SCORECARD_API_KEY` from the free api.data.gov College Scorecard application flow.
- Keep `ENABLE_US_UNIVERSITY_ENRICHMENT=true` when you want the enrichment script and monthly workflow to run.
- The monthly workflow is defined in `.github/workflows/enrich_us_universities.yml`.
- The redirect button in the student module uses the public Studyportals redirect endpoint when `ENABLE_STUDYPORTALS_REDIRECT=true`.

### Live Verification
- Run your own SearXNG instance and point `SEARXNG_BASE_URL` at it; this replaces the need for a third-party search API key.
- No `SERPER_API_KEY` is required for this flow.
- Set `ENABLE_LIVE_VERIFICATION=true` to let the verifier search live pages and cache tuition, requirements, and admissions snippets.
- Use `python scripts/verify_tuition.py --university-id <id> --program-id <id> --refresh` for a manual check.
- The monthly refresh workflow is defined in `.github/workflows/refresh_verified_data.yml`.
- Cached verification expires after `VERIFICATION_CACHE_TTL_HOURS` hours and is refreshed automatically when the backend re-runs the verifier.

## Notes
- The backend returns standardized error payloads in the form `{ "error": true, "message": string, "code": int }`.
- If you change the database schema, rerun `alembic upgrade head` before starting the services.
