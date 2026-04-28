# JobSync Frontend

React frontend for JobSync - AI-powered job search assistant.

## Tech Stack

- React 18
- Vite
- React Router
- Axios
- Lucide React (icons)

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Start development server:
```bash
npm run dev
```

The app will be available at http://localhost:3000

## Build

```bash
npm run build
```

## Features

- Dashboard with application statistics
- Resume analysis with ATS scoring
- Job search from multiple sources
- Application tracking
- Cover letter generation
- Interview preparation
- Skill gap analysis

## API Integration

The frontend connects to the JobSync backend API running on http://localhost:8000

Make sure the backend is running before starting the frontend.
