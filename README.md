# 🚀 JobSync Pro

JobSync Pro is a production-ready, showcase-quality AI-assisted job search and application management ecosystem. It integrates a **FastAPI backend**, a **React dashboard**, a **Chrome Browser Extension**, a **CLI tool**, and an **automated background indexing loop**. It provides job seekers with automated scouting, AI-driven match analysis, cold outreach templates, voice-activated mock interviews, and PDF resume tailoring.

---

## 🧰 Recent Hardening Updates

The following production fixes have been applied to keep the backend and study module aligned with the live database:

- Added an Alembic migration for the `universities` table timestamp fields: `created_at`, `updated_at`, and `last_scraped_at`.
- Updated the `University` SQLAlchemy model to match the live schema with timezone-aware timestamp columns.
- Rewrote the university filter endpoint in SQLAlchemy 2 style using `select()` and explicit `db.execute(...)` calls.
- Added structured `503` handling in the university filter path so database issues return a clear API error instead of a raw crash.
- Added a startup schema guard that warns if required university columns are missing.
- Hardened `backend/job_indexer.py` to use `sqlalchemy.text()` with bound parameters and per-job exception logging.
- Reworked `scripts/verify_production.py` so it can be run directly and performs real environment, database, and HTTP smoke checks.

---

## ✨ Features & Capabilities

### 🔍 1. Automated Job Scouting & Prefetch Indexing (NEW)
- **Background Prefetch Indexer (`backend/job_indexer.py`)**: Runs continuously as a background process or scheduled task. It pre-fetches popular job queries (such as Software Engineer, Data Analyst, Data Scientist, Product Manager, DevOps, and Designer) hourly and stores them in a local SQLite cache.
- **Sub-Second Job Search**: The `/jobs/search` endpoint utilizes token-based query matching (with `AND` logic) to find prefetched jobs instantaneously. On cache misses, it transparently falls back to a multi-source live API query (Adzuna, Remotive, Jobicy) and updates the local cache asynchronously.
- **Location-First Filters**: Toggle between local (e.g., Pakistan cities: Karachi, Lahore, Islamabad) and global remote postings.

### 🤖 2. In-Page AI Match Analysis (NEW)
- **Glassmorphic Match Me Modal**: A beautiful, interactive in-page modal dialog that calculates job-to-resume ATS compatibility.
- **Score Progress Indicators**: Visually charts compatibility percentage using styled CSS progress bars.
- **Key Skill Gap Visualizer**: Pinpoints missing keywords and technical terms, displaying them as responsive tag chips (rose/green badge layout).
- **Outreach & Preparation Routing**: Flow parameters directly from the modal into the Resume Rewriter or Cover Letter Generator without losing search context.

### 📄 3. Document Tailoring & Outreach
- **Asynchronous Cover Letter Generation**: Generates customized cover letters using user-profile embeddings and a RAG (Retrieval-Augmented Generation) loop. Runs asynchronously in a background thread to prevent search latency, gated behind the `ENABLE_JOB_ARTIFACTS` configuration flag.
- **Resume Re-writer & ATS Scanner**: Upload your resume PDF, paste the job description, and automatically get an ATS matching score, missing keywords, and structural tips.
- **Outreach Generator**: Creates personalized cold outreach emails and LinkedIn messages using local company/role contexts.

### 📋 4. Kanban Tracking & Stale Reminders
- **Visual Application Pipeline**: Drag-and-drop your applications through *Saved*, *Applied*, *Interviewing*, *Rejected*, and *Offered*.
- **Follow-up Agent**: Periodically checks for stale applications (5+ days without response) and automatically drafts follow-up emails.

### 🎤 5. Interview Prep & Voice Evaluation
- **Voice Mock Interviews**: Practice standard or role-specific questions and record or paste answers to get score evaluation and improvement suggestions.

### 🌐 6. Chrome Browser Extension
- **1-Click URL Scraping**: Analyze any job posting page directly from your browser. Extract metadata, evaluate match scores, and save it to your dashboard.

---

## 📂 Project Layout

```text
├── backend/                  # FastAPI backend
│   ├── routers/              # Endpoint modules (Kanban, Scout, Extension, Match, etc.)
│   ├── services/             # Integrations (Job sources, scraping, etc.)
│   ├── database.py           # SQLAlchemy setup and SQLite schemas
│   ├── job_indexer.py        # Hourly background prefetch daemon
│   └── main.py               # Main application entry point
├── core/                     # Shared Core Library (RAG, LLM engines, PDF generation)
│   ├── engine.py             # LLM Analysis Engine (Groq / OpenRouter)
│   ├── llm_provider.py       # Decoupled LLM factory
│   ├── daily_scout.py        # Automated scout matching loops
│   └── pdf_generator.py      # ATS-optimized PDF exports
├── extension/                # Chrome Browser Extension (Manifest V3)
├── frontend/                 # React + Vite frontend dashboard
├── tracker/                  # Kanban CSV fallbacks and application memory
└── app.py                    # Command-line interface tool
```

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- SQLite3

### 1. Backend Setup
1. Clone the repository and navigate to the project root.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure the environment variables. Copy `.env.example` to `.env` and populate:
   ```env
   GROQ_API_KEY=your_llm_api_key_here
   ENABLE_JOB_ARTIFACTS=false
   PREFETCH_INTERVAL_HOURS=1
   ```

### 2. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Build or run the development server:
   ```bash
   npm run dev
   ```

### 3. Load the Chrome Extension
1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Toggle **Developer mode** on (top-right corner).
3. Click **Load unpacked** (top-left) and select the `extension/` directory.

---

## 🚀 Running the Services

### Start the Backend Server
Run the FastAPI web service:
```bash
python -m uvicorn backend.main:app --reload --port 8000
```
API Documentation will be accessible at: [http://localhost:8000/docs](http://localhost:8000/docs)

### Start the Background Prefetch Indexer
To run the background prefetcher daemon continuously:
```bash
python -m backend.job_indexer
```

### Start the React Frontend Dashboard
In the `frontend/` directory, run:
```bash
npm run dev
```
Open [http://localhost:5173/](http://localhost:5173/) to access the dashboard.
