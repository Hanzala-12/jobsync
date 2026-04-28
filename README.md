# CareerPrep Job-Hunting Agent

A file-driven AI agent for job search, resume tailoring, interview preparation, and application tracking. Enhanced with Groq LLM for intelligent analysis.

## GAME Framework

**Goal**: Help students search for jobs, analyze job posters, tailor resumes, generate interview questions, and track applications.

**Actions**:
- Read job posters, resumes, and knowledge base files
- Analyze job requirements using LLM and keyword matching
- Calculate skill gaps and match percentages
- Generate tailored resume suggestions
- Create interview questions from KB material
- Track application status with reminders
- Generate cover letters and LinkedIn messages

**Memory**:
- Session memory stored in `tracker/memory.json`
- Application history in `tracker/applications.csv`
- Generated reports in `outputs/`

**Environment**:
- Local file-based system
- Groq LLM API for intelligent analysis
- GitHub repository for version control

## Features

### Core Features (Professor Requirements)
- File reading from `input_jobs/`, `input_resumes/`, `input_kb/`
- Job description analysis with keyword extraction
- Resume analysis and skill extraction
- Skill-gap calculation with match percentage
- Tailored resume improvement suggestions
- Interview question generation from KB
- Application tracker with status management
- Reminder system with date-based logic

### Unique Features (Extra Marks)
1. **PDF Support** - Read PDF files for jobs, resumes, and KB material
2. **LLM Integration** - Groq API for intelligent analysis (not just keywords)
3. **Cover Letter Generator** - AI-generated tailored cover letters
4. **LinkedIn Message Generator** - Professional outreach messages
5. **Application Dashboard** - Visual status breakdown with percentages
6. **Reminder Urgency** - TODAY/TOMORROW/THIS WEEK/OVERDUE flags
7. **PDF Export** - Export final report as PDF
8. **JSON Memory** - GAME framework memory system
9. **Interactive Menu** - User-friendly CLI interface
10. **Web API** - Bonus FastAPI backend (existing JobSync features)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the root directory:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free Groq API key from: https://console.groq.com

### 3. Prepare Input Files

Add files to the input folders:

**input_jobs/**
- Add job posters or descriptions as `.txt` or `.pdf` files
- Example: `job_poster_01.txt`, `internship_ad.pdf`

**input_resumes/**
- Add your resume as `.txt` or `.pdf` file
- Example: `my_resume.txt`

**input_kb/**
- Add course slides, interview prep notes as `.txt` or `.pdf`
- Example: `interview_prep_notes.txt`, `course_slides.pdf`

### 4. Run the Agent

```bash
python app.py
```

## Usage

The agent provides an interactive menu:

1. **Run Full Analysis** - Complete pipeline (job + resume + KB analysis)
2. **List Job Files** - View available job files
3. **List Resume Files** - View available resume files
4. **Add Application** - Add new application to tracker
5. **Update Application** - Update status, dates, actions
6. **List Applications** - View all tracked applications
7. **View Reminders** - See pending actions with urgency
8. **View Dashboard** - Application status breakdown
9. **Exit** - Close the agent

## Output Files

All outputs are saved in the `outputs/` and `tracker/` folders:

### outputs/
- `job_analysis_report.txt` - Job requirements and skills
- `skill_gap_report.txt` - Match score and missing skills
- `tailored_resume_suggestions.txt` - Resume improvement tips
- `interview_questions.txt` - Technical, behavioral, and KB questions
- `cover_letter.txt` - AI-generated cover letter
- `linkedin_message.txt` - Professional outreach message
- `final_agent_report.txt` - Complete analysis report
- `final_agent_report.pdf` - PDF export (if fpdf installed)

### tracker/
- `applications.csv` - Application status tracker
- `reminders.txt` - Pending actions with urgency
- `memory.json` - Session memory (GAME framework)

## Application Tracker

The tracker maintains these fields:

| Field | Description |
|-------|-------------|
| application_id | Unique ID (APP-YYYYMMDDHHMMSS) |
| company | Company name |
| role | Job title |
| source | Where job was found |
| status | Not Applied / Applied / Interview Scheduled / Rejected / Offered |
| applied_date | Date application submitted |
| interview_date | Interview date (if scheduled) |
| follow_up_date | Date to follow up |
| next_action | What to do next |
| notes | Additional remarks |

## Reminder System

Reminders are generated based on application status:

- **Interview Scheduled** → Preparation reminder with urgency
- **Not Applied** → Reminder to tailor resume and apply
- **Applied** → Follow-up reminder after 5 days
- **Urgency Levels**: OVERDUE / TODAY / TOMORROW / THIS WEEK / In X days

## LLM Integration

The agent uses Groq's Llama 3 model for:

- Job requirement extraction and analysis
- Resume skill identification
- Intelligent skill-gap calculation
- Tailored resume suggestions with specific bullet points
- Interview question generation
- Cover letter writing
- LinkedIn message creation

**Fallback**: If LLM is unavailable, uses keyword-based analysis.

## Project Structure

```
job-hunting-agent/
├── app.py                    # Main agent file
├── requirements.txt          # Dependencies
├── README.md                 # This file
├── reflection.md             # Project reflection
├── .env                      # Environment variables
│
├── input_jobs/               # Job posters (add your files here)
├── input_resumes/            # Resumes (add your files here)
├── input_kb/                 # Knowledge base (add your files here)
│
├── outputs/                  # Generated reports
├── tracker/                  # Application tracker and memory
├── samples/                  # Sample files
│
├── backend/                  # Bonus: FastAPI web API
└── frontend/                 # Bonus: React web interface
```

## Bonus Features

This project includes a complete web application (JobSync) with:

- FastAPI backend with REST API
- React frontend with modern UI
- Database integration (SQLite)
- Additional features: job search APIs, real-time analysis

To run the web app:

```bash
# Backend
source venv/Scripts/activate
bash run.sh

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Testing

1. Add sample files to input folders
2. Run `python app.py`
3. Choose option 1 (Run Full Analysis)
4. Check `outputs/` and `tracker/` folders
5. Add applications using option 4
6. View reminders using option 7

## Requirements Met

- ✅ Folder-based input system
- ✅ File reading (TXT and PDF)
- ✅ Job analysis with keyword extraction
- ✅ Resume analysis
- ✅ Skill-gap calculation
- ✅ Resume tailoring suggestions
- ✅ Interview questions from KB
- ✅ Application tracker (CSV)
- ✅ Reminder generation
- ✅ All required output files
- ✅ GAME framework implementation
- ✅ 10+ unique features for extra marks

## Technologies

- **Python 3.8+**
- **Groq API** - LLM integration
- **PyMuPDF** - PDF reading
- **FPDF** - PDF export
- **CSV** - Application tracking
- **JSON** - Memory system

## Author

Built for Agentic AI course lab assignment.

## License

MIT License
