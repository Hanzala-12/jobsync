# JobSync - Project Structure

## Overview
JobSync is a complete FastAPI backend application for job search assistance with AI-powered features.

## Project Structure

```
jobsync/
├── backend/                          # Main backend package
│   ├── __init__.py                   # Package initialization
│   ├── main.py                       # FastAPI app entry point
│   ├── database.py                   # SQLAlchemy database configuration
│   ├── models.py                     # Database models (UserProfile, Job, Application)
│   ├── schemas.py                    # Pydantic schemas for API validation
│   │
│   ├── routers/                      # API route handlers
│   │   ├── __init__.py
│   │   ├── resume.py                 # Resume upload & analysis
│   │   ├── jobs.py                   # Job search & matching
│   │   ├── applications.py           # Application tracking
│   │   ├── cover_letter.py           # Cover letter generation
│   │   └── intelligence.py           # Skill gap & interview prep
│   │
│   ├── services/                     # Business logic & integrations
│   │   ├── __init__.py
│   │   ├── ai_client.py              # Groq AI integration
│   │   ├── job_apis.py               # Job board API integrations
│   │   └── pdf_parser.py             # PDF text extraction
│   │
│   ├── requirements.txt              # Production dependencies
│   ├── requirements-dev.txt          # Development dependencies
│   └── .env.example                  # Environment variables template
│
├── .env                              # Your environment variables (not in git)
├── .gitignore                        # Git ignore rules
├── README.md                         # Full documentation
├── QUICKSTART.md                     # Quick start guide
├── PROJECT_STRUCTURE.md              # This file
├── setup.sh                          # Setup script
└── run.sh                            # Run script
```

## Key Components

### Database Models (`backend/models.py`)
- **UserProfile**: Stores user resume text, skills, and ATS score
- **Job**: Stores job listings from various sources
- **Application**: Tracks job applications with status

### API Routers
1. **Resume Router** (`/resume`)
   - Upload and analyze resume PDFs
   - Extract text and calculate ATS score
   - Identify missing keywords

2. **Jobs Router** (`/jobs`)
   - Search jobs from multiple sources
   - Match jobs with user resume
   - Calculate match percentage

3. **Applications Router** (`/applications`)
   - Create and track applications
   - Update application status
   - Filter by status

4. **Cover Letter Router** (`/cover-letter`)
   - Generate tailored cover letters
   - Use resume context and job description

5. **Intelligence Router** (`/intelligence`)
   - Analyze skill gaps
   - Generate interview questions
   - Provide suggested answers

### Services
1. **AI Client** (`ai_client.py`)
   - Groq API integration
   - LLM prompt handling
   - Error handling

2. **Job APIs** (`job_apis.py`)
   - RemoteOK integration
   - Arbeitnow integration
   - Adzuna integration (optional)
   - Job deduplication

3. **PDF Parser** (`pdf_parser.py`)
   - Extract text from PDF resumes
   - Uses PyMuPDF library

## Technology Stack

### Backend Framework
- **FastAPI**: Modern, fast web framework
- **Uvicorn**: ASGI server
- **SQLAlchemy**: ORM for database
- **Pydantic**: Data validation

### AI & ML
- **Groq**: Fast LLM inference (free tier)
- **Llama 3**: Open-source language model

### Data Processing
- **PyMuPDF**: PDF text extraction
- **Requests**: HTTP client for job APIs

### Database
- **SQLite**: Lightweight database (development)
- Can be upgraded to PostgreSQL for production

## API Endpoints

### Resume
- `POST /resume/analyze` - Upload and analyze resume

### Jobs
- `GET /jobs/search?query=developer` - Search jobs
- `GET /jobs/{job_id}/match` - Get match score

### Applications
- `POST /applications/` - Create application
- `GET /applications/` - List applications
- `GET /applications/{app_id}` - Get application
- `PATCH /applications/{app_id}/status` - Update status

### Cover Letter
- `POST /cover-letter/generate` - Generate cover letter

### Intelligence
- `POST /intelligence/skill-gap` - Analyze skill gaps
- `POST /intelligence/interview-prep` - Get interview questions

## Environment Variables

Required:
- `GROQ_API_KEY`: Your Groq API key (get from https://console.groq.com)

Optional:
- `ADZUNA_APP_ID`: Adzuna API ID
- `ADZUNA_APP_KEY`: Adzuna API key

## Database Schema

### user_profiles
- id (PK)
- resume_text (TEXT)
- skills (TEXT, comma-separated)
- latest_ats_score (FLOAT)
- created_at (DATETIME)

### jobs
- id (PK)
- source (VARCHAR)
- external_id (VARCHAR, UNIQUE)
- title (VARCHAR)
- company (VARCHAR)
- location (VARCHAR)
- description (TEXT)
- url (VARCHAR)
- posted_date (VARCHAR)
- fetched_at (DATETIME)

### applications
- id (PK)
- job_id (INT, nullable FK)
- company (VARCHAR)
- role (VARCHAR)
- applied_date (DATETIME)
- status (VARCHAR)
- notes (TEXT)
- resume_version (VARCHAR)
- contact_email (VARCHAR)

## Running the Application

1. **Setup**: `bash setup.sh`
2. **Configure**: Edit `.env` with your API keys
3. **Run**: `bash run.sh` or `uvicorn backend.main:app --reload`
4. **Access**: http://localhost:8000/docs

## Development

### Install Dev Dependencies
```bash
pip install -r backend/requirements-dev.txt
```

### Run Tests
```bash
pytest
```

### Format Code
```bash
black backend/
```

### Lint Code
```bash
flake8 backend/
```

## Deployment Considerations

1. **Database**: Migrate from SQLite to PostgreSQL
2. **Environment**: Use proper environment variable management
3. **Security**: Add authentication and authorization
4. **Rate Limiting**: Implement rate limiting for API endpoints
5. **Caching**: Add Redis for caching job search results
6. **Monitoring**: Add logging and monitoring
7. **CORS**: Configure CORS properly for production

## Future Enhancements

- [ ] User authentication and multi-user support
- [ ] Email notifications for application updates
- [ ] Calendar integration for interview scheduling
- [ ] Resume builder and editor
- [ ] Job alerts and saved searches
- [ ] Analytics dashboard
- [ ] Mobile app
- [ ] Browser extension
