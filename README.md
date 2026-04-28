# JobSync

<div align="center">

**Sync yourself with your dream job.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg)](https://fastapi.tiangolo.com)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

An AI-powered job search assistant that helps you find jobs, analyze resumes, track applications, generate cover letters, and prepare for interviews. JobSync streamlines your job search process with intelligent automation and insights.

[Features](#features) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Contributing](#contributing)

</div>

---

## Features

✨ **Resume Analysis** - Upload your resume and get ATS score, missing keywords, and improvement tips

🔍 **Job Search** - Search jobs from multiple sources (RemoteOK, Arbeitnow, Adzuna)

🎯 **Job Matching** - AI-powered matching between your resume and job descriptions

📊 **Application Tracking** - Track your job applications with status updates

✍️ **Cover Letter Generation** - Generate tailored cover letters using AI

📈 **Skill Gap Analysis** - Identify missing skills based on job descriptions

💼 **Interview Prep** - Get AI-generated interview questions and suggested answers

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite
- **AI**: Groq API (free tier with Llama 3)
- **PDF Processing**: PyMuPDF

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Groq API key (free from [console.groq.com](https://console.groq.com))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/jobsync.git
   cd jobsync
   ```

2. **Run the setup script**
   ```bash
   bash setup.sh
   ```

3. **Activate the virtual environment**
   ```bash
   # Windows (Git Bash)
   source venv/Scripts/activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

4. **Configure environment variables**
   
   Edit `.env` file and add your Groq API key:
   ```env
   GROQ_API_KEY=gsk_your_actual_key_here
   ADZUNA_APP_ID=optional
   ADZUNA_APP_KEY=optional
   ```

5. **Run the server**
   ```bash
   bash run.sh
   ```

6. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs

📖 For detailed setup instructions, see [QUICKSTART.md](QUICKSTART.md)

## API Endpoints

### Resume
- `POST /resume/analyze` - Upload and analyze resume PDF

### Jobs
- `GET /jobs/search?query=developer` - Search for jobs
- `GET /jobs/{job_id}/match` - Get AI match score for a job

### Applications
- `POST /applications/` - Create new application
- `GET /applications/` - List all applications
- `GET /applications/{app_id}` - Get specific application
- `PATCH /applications/{app_id}/status` - Update application status

### Cover Letter
- `POST /cover-letter/generate` - Generate tailored cover letter

### Intelligence
- `POST /intelligence/skill-gap` - Analyze skill gaps
- `POST /intelligence/interview-prep` - Get interview questions

## Project Structure

```
jobsync/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # Database configuration
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/             # API route handlers
│   │   ├── resume.py
│   │   ├── jobs.py
│   │   ├── applications.py
│   │   ├── cover_letter.py
│   │   └── intelligence.py
│   ├── services/            # Business logic
│   │   ├── ai_client.py     # Groq AI integration
│   │   ├── job_apis.py      # Job board API integrations
│   │   └── pdf_parser.py    # PDF text extraction
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment variables template
├── .env                     # Your environment variables
├── setup.sh                 # Setup script
├── run.sh                   # Run script
└── README.md               # This file
```

## Usage Examples

### 1. Analyze Resume
```bash
curl -X POST "http://localhost:8000/resume/analyze" \
  -F "file=@your_resume.pdf"
```

### 2. Search Jobs
```bash
curl "http://localhost:8000/jobs/search?query=python+developer"
```

### 3. Create Application
```bash
curl -X POST "http://localhost:8000/applications/" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Tech Corp",
    "role": "Software Engineer",
    "notes": "Applied via LinkedIn"
  }'
```

### 4. Generate Cover Letter
```bash
curl -X POST "http://localhost:8000/cover-letter/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Tech Corp",
    "role": "Software Engineer",
    "job_description": "We are looking for..."
  }'
```

## Documentation

- [Quick Start Guide](QUICKSTART.md) - Step-by-step setup instructions
- [Project Structure](PROJECT_STRUCTURE.md) - Detailed architecture overview
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- AI powered by [Groq](https://groq.com/)
- Job data from RemoteOK, Arbeitnow, and Adzuna

## Support

If you find JobSync helpful, please consider:
- ⭐ Starring the repository
- 🐛 Reporting bugs
- 💡 Suggesting new features
- 🤝 Contributing to the project

---

<div align="center">
Made with ❤️ for job seekers everywhere
</div>
