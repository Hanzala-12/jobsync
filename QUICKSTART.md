# Quick Start Guide

## Prerequisites

- Python 3.8+ installed
- Node.js 16+ installed
- Groq API key (free from https://console.groq.com)

## Option 1: Complete Setup (Backend + Frontend)

### 1. Install All Dependencies

```bash
bash setup-all.sh
```

This will:
- Create Python virtual environment
- Install backend dependencies
- Install frontend dependencies
- Create .env files

### 2. Configure Environment

Edit the `.env` file in the root directory and add your Groq API key:

```
GROQ_API_KEY=gsk_your_actual_key_here
ADZUNA_APP_ID=optional
ADZUNA_APP_KEY=optional
```

### 3. Run Both Servers

```bash
bash run-all.sh
```

Or run them separately:

**Terminal 1 - Backend:**
```bash
source venv/Scripts/activate  # Windows Git Bash
bash run.sh
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Option 2: Backend Only Setup

## Option 2: Backend Only Setup

### 1. Install Python Dependencies

First, make sure you have Python 3.8+ installed. Then run:

```bash
# For Windows (Git Bash)
python -m venv venv
source venv/Scripts/activate
pip install -r backend/requirements.txt
```

## 2. Get Your Groq API Key

1. Go to https://console.groq.com
2. Sign up for a free account
3. Create an API key
4. Copy the key (starts with `gsk_`)

## 3. Configure Environment

Edit the `.env` file in the root directory and replace `gsk_your_free_key_here` with your actual Groq API key:

```
GROQ_API_KEY=gsk_your_actual_key_here
ADZUNA_APP_ID=optional
ADZUNA_APP_KEY=optional
```

## 4. Run the Server

```bash
# Make sure your virtual environment is activated
source venv/Scripts/activate  # Windows Git Bash

# Run the server
uvicorn backend.main:app --reload
```

Or simply:
```bash
bash run.sh
```

## 5. Test the API

Open your browser and go to:
- **API Documentation**: http://localhost:8000/docs
- **API Root**: http://localhost:8000

## 6. Try It Out (API Only)

### Upload a Resume
1. Go to http://localhost:8000/docs
2. Find the `POST /resume/analyze` endpoint
3. Click "Try it out"
4. Upload a PDF resume
5. Click "Execute"

### Search for Jobs
1. Find the `GET /jobs/search` endpoint
2. Click "Try it out"
3. Enter a search query (e.g., "python developer")
4. Click "Execute"

### Create an Application
1. Find the `POST /applications/` endpoint
2. Click "Try it out"
3. Fill in the JSON body:
```json
{
  "company": "Tech Corp",
  "role": "Software Engineer",
  "notes": "Applied via LinkedIn"
}
```
4. Click "Execute"

## Troubleshooting

### Import Errors
If you get import errors, make sure you're running the server from the project root directory and your virtual environment is activated.

### Database Errors
The SQLite database is created automatically. If you have issues, delete `jobsync.db` and restart the server.

### API Key Errors
Make sure your `.env` file is in the root directory (not in the backend folder) and contains a valid Groq API key.

### Port Already in Use
If port 8000 is already in use, you can specify a different port:
```bash
uvicorn backend.main:app --reload --port 8001
```

## Next Steps

- Check out the full API documentation at http://localhost:8000/docs
- Read the README.md for more details
- Customize the AI prompts in the router files
- Add more job board integrations in `backend/services/job_apis.py`
