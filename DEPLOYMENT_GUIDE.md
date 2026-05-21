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
- `ENABLE_STUDENT_MODULE`
- `MAX_MATCH_RESULTS`
- `MATCH_CACHE_TTL_DAYS`

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
```

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

## One-Time Setup Commands

```bash
python scripts/ingest_universities.py --full
python scripts/ingest_programs_to_vector_db.py
python scripts/refresh_match_cache.py --daemon
```

## Notes
- The backend returns standardized error payloads in the form `{ "error": true, "message": string, "code": int }`.
- If you change the database schema, rerun `alembic upgrade head` before starting the services.
