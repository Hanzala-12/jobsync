# JobSync Pro — Local Dev & Overview

JobSync Pro is an AI-assisted job search and application assistant with a FastAPI backend, a React (Vite) frontend, and a Chrome extension for in-browser scraping and analysis. This `README` focuses on the current state and how to run the project locally for quick testing.

## Quick Snapshot
- Backend: FastAPI with SQLite, background prefetch/indexer, and API routes in `backend/`.
- Frontend: Vite + React app in `frontend/` (dev server via `npm run dev`).
- Extension: Chrome manifest and extension sources in `extension/` for local loading.

## Local Development (fast path)

Prerequisites:
- Python 3.10+
- Node.js 18+
- SQLite3

1) Create and activate your Python virtual environment (prefer existing venv):

```powershell
python -m venv venv
& .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Set environment variables (copy `.env.example` if present):

```powershell
copy .env.example .env
# edit .env to add keys (GROQ_API_KEY, ENABLE_JOB_ARTIFACTS, etc.)
```

3) Start the backend (development):

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

4) Start the frontend (development):

```bash
cd frontend
npm install
npm run dev
```

Open the React UI at http://localhost:5173/

5) Load the extension (optional):
- In Chrome, enable Developer mode at `chrome://extensions/` and `Load unpacked` → select the `extension/` folder.

## Running the background prefetch indexer
To run the background prefetcher independently:

```powershell
python -m backend.job_indexer
```

## Notes
- Use `backend/main.py` as the FastAPI entrypoint; the repository includes tasks and helper scripts for indexing, scraping, and verification.
- If you prefer, a VS Code task is available to launch the API debug server (label: `api-debug-server`).

## Contributing / Quick Tests
- Unit and integration tests live in `tests/` and `finder/tests/`; run them with `pytest`.

---
If you'd like, I can now commit this `README.md`, push to GitHub, and start both backend and frontend locally for you to test. Reply with `yes` to proceed, or `no` to stop here.
