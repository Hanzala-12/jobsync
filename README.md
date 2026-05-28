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

## Matching Evaluation
The repo now includes a labeled synthetic resume/job dataset and an evaluation script for job matching quality.

Run it with:

```powershell
& .\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "e:/job finder"
$env:ENABLE_CROSS_ENCODER = "false"
python scripts/build_labeled_dataset.py --output data/labeled_resume_jd_pairs.csv
python scripts/evaluate_matching.py --dataset data/labeled_resume_jd_pairs.csv --output evaluation/baseline_metrics.json
$env:ENABLE_CROSS_ENCODER = "true"
python scripts/evaluate_matching.py --dataset data/labeled_resume_jd_pairs.csv --output evaluation/cross_encoder_metrics.json
```

Current sample results on the synthetic dataset:

| Stage | NDCG@5 | MRR | Precision@5 |
| --- | ---: | ---: | ---: |
| BM25 | 0.8801 | 1.0000 | 0.7200 |
| BM25 + bi-encoder | 0.9013 | 1.0000 | 0.7200 |
| BM25 + bi-encoder + pairwise reranker | 0.8943 | 1.0000 | 0.7000 |

The evaluator will fall back to a TF-IDF-based dense backend if `sentence-transformers` cannot import cleanly in the current Windows environment.

## Contributing / Quick Tests
- Unit and integration tests live in `tests/` and `finder/tests/`; run them with `pytest`.

---
If you'd like, I can now commit this `README.md`, push to GitHub, and start both backend and frontend locally for you to test. Reply with `yes` to proceed, or `no` to stop here.

## Hybrid Resume Generator (Blueprint + LLM)

This repository now includes a hybrid resume generation and tailoring system that combines a canonical JSON blueprint with LLM-driven per-section content. The hybrid approach provides deterministic, ATS-friendly formatting while allowing the LLM to produce adaptive, role-specific section content.

Key files added/modified:

- `blueprints/resume_blueprint.json` — canonical resume blueprint (sections, field hints).
- `core/resume_blueprint_engine.py` — loads the blueprint and renders filled resume text from section JSON or structured profile data.
- `core/resume_analyzer.py` — updated to request per-section JSON from the LLM and assemble via the blueprint engine; includes safe fallbacks when LLM backends are unavailable.
- `core/llm_provider.py` — adjusted to avoid leaking LLM error strings into user-facing output.
- `scripts/test_hybrid_resume.py` — deterministic integration test that simulates LLM output, validates blueprint conformance, and generates a PDF sample (`outputs/hybrid_resume_test.pdf`).
- `HYBRID_RESUME_ANALYSIS.md` — short architecture note, blueprint snippet, and rationale.

How to run the hybrid resume integration test locally (use the project venv):

Windows PowerShell:

```powershell
& .\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "e:/job finder"
python scripts/test_hybrid_resume.py
```

To exercise the true LLM polishing path, set your LLM credentials in the environment before running the tests (examples):

```powershell
$env:OPENAI_API_KEY = "<your-openai-key>"
# or
$env:OPENROUTER_API_KEY = "<your-openrouter-key>"
```

Result: a sample PDF is written to `outputs/hybrid_resume_test.pdf` when the test completes successfully.

See `HYBRID_RESUME_ANALYSIS.md` for architecture details and rationale.
