# JobSync / CareerPrep

An AI-assisted job search workspace with a Python CLI, FastAPI backend, and React dashboard. It combines file-based assignment workflows with live job scouting, resume analysis, application tracking, and generated outreach content.

## What It Does

- Reads job posters, resumes, and knowledge base files from local folders
- Analyzes jobs and resumes with LLM-backed and rule-based fallbacks
- Scores match quality, highlights missing skills, and suggests improvements
- Generates cover letters, LinkedIn messages, and interview prep questions
- Tracks applications, reminders, follow-ups, and Kanban status
- Scans live job feeds and saves strong matches into the tracker

## Highlights

- PDF and text support for jobs, resumes, and KB files
- FastAPI backend with SQLite persistence
- React dashboard with analytics, Kanban, resume analysis, and daily scout views
- Daily job scout with live progress polling and actionable job cards
- Cover letter generator with tone selection and export actions
- Application tracker with follow-up metadata and urgency flags

## Project Layout

```text
app.py                 CLI entry point
backend/               FastAPI backend and routers
core/                  Shared analysis, search, and generation logic
frontend/              React + Vite web app
input_jobs/            Sample and user job posters
input_resumes/         Sample and user resumes
input_kb/              Sample and user knowledge base files
outputs/               Generated reports and drafts
tracker/               CSV tracker, reminders, memory
```

## Setup

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Configure your API key in a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here
```

3. Add sample or real `.txt` / `.pdf` files to the input folders.

4. Start the CLI:

```bash
python app.py
```

5. Start the web app:

```bash
cd frontend
npm install
npm run dev
```

## Web App

The web interface includes:

- Dashboard analytics
- Jobs browser and matching
- Resume analyzer and re-analysis
- Kanban application board
- Daily Scout job discovery
- Cover letter generator

## Outputs

Generated artifacts are written to `outputs/` and `tracker/`.

### `outputs/`

- `job_analysis_report.txt`
- `skill_gap_report.txt`
- `tailored_resume_suggestions.txt`
- `interview_questions.txt`
- `cover_letter.txt`
- `linkedin_message.txt`
- `final_agent_report.txt`
- `final_agent_report.pdf` when PDF export is available

### `tracker/`

- `applications.csv`
- `reminders.txt`
- `memory.json`

## Validation

Recommended smoke checks:

```bash
python app.py
cd frontend && npm run build
```

## Screenshots

Add screenshots here when packaging or submitting the project.

## Contributing

1. Fork or branch.
2. Make a focused change.
3. Run the relevant backend or frontend validation.
4. Open a pull request with a short summary.

## License

MIT
