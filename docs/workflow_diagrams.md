# Workflow Diagrams

This document captures the implemented request flows for the job and university modules, plus shared infrastructure that supports both.

## 1) Job Module workflow

```mermaid
flowchart TD
    A[Jobs page / Profile page / Applications page] --> B[Frontend calls /api/jobs/search or /api/jobs/search/stream]
    B --> C[backend.routers.jobs.search_jobs_endpoint or search_jobs_stream]
    C --> D[backend.services.job_apis.search_jobs]
    D --> E[Source adapters: Rozee, Mustakbil, Brightspyre, Bing, LinkedIn, company careers]
    E --> F[Normalized job payloads]
    F --> G[backend.routers.jobs._upsert_jobs]
    G --> H[(SQLAlchemy DB / Job table)]
    H --> I[backend.routers.jobs._refresh_job_search_query]
    I --> J[Profile-aware sorting via _score_job_for_profile]
    J --> K[backend.services.job_ranking.rerank_job_candidates]
    K --> L[Return JobOut list to frontend]

    L --> M[User can Save]
    M --> N[applicationsAPI.create / updateStatus]
    N --> O[backend.routers.applications]

    L --> P[User can Match Me]
    P --> Q[backend.routers.jobs.match_job]
    Q --> R[load UserProfile.resume_text]
    R --> S[extract_skills + explain_match_for]
    S --> T[Return JobMatch payload]

    L --> U[User can open Resume Builder]
    U --> V[backend.routers.profile.build_resume]
    V --> W[load active profile and job]
    W --> X[analyze_and_fix_resume + render_resume_html]
    X --> Y[save_resume_artifacts]
    Y --> Z[Return tailored resume payload]

    L --> AA[User can request salary estimate]
    AA --> AB[backend.routers.jobs.salary_estimate]
    AB --> AC[LLMProvider fallback JSON generation]
    AC --> AD[Return salary estimate]

    L --> AE[Optional streaming path]
    AE --> AF[search_jobs_stream emits partial events and final results]
    AF --> AG[Frontend updates live search counts]
```

### Notes

- The job search endpoint uses live fetches and then persists results so the DB can be reused for subsequent searches.
- The job ranking path combines profile-aware heuristics and optional cross-encoder reranking through [backend/services/job_ranking.py](backend/services/job_ranking.py).
- Resume tailoring is implemented in [backend/routers/profile.py](backend/routers/profile.py) and uses resume analysis, HTML rendering, and artifact saving.

## 2) University Module workflow

```mermaid
flowchart TD
    A[StudentProfileForm / StudentUniversitySearch / UniversityMatchList / SavedUniversities page] --> B[Frontend calls /api/student/profile, /api/student/universities/filter, /api/student/match/recommend, /api/student/verify/{id}/{program_id}, /api/student/save, /api/student/apply]
    B --> C[backend.routers.student_university.api_router]
    C --> D[Student profile CRUD]
    D --> E[(SQLAlchemy DB / student_profiles and user_preferences)]

    C --> F[GET /universities/filter]
    F --> G[Query University + Program data]
    G --> H[Return university/program payloads]

    C --> I[POST /match/recommend]
    I --> J[backend.services.university_match_service.retrieve_similar_programs]
    J --> K[Heuristic vector-style ranking across Program + University rows]
    K --> L[backend.services.university_match_service.get_match_for_program]
    L --> M{Cached match exists?}
    M -->|Yes| N[Return cached StudentProgramMatch]
    M -->|No| O[Load verification data if enabled]
    O --> P[backend.services.university_verification_service.verify_program_live]
    P --> Q[SearXNG + parsing + cache update]
    Q --> R[LLMProvider-powered match analysis fallback]
    R --> S[Persist StudentProgramMatch]
    S --> T[Return match payload]

    C --> U[GET /verify/{university_id}/{program_id}]
    U --> V[Resolve selected student profile]
    V --> W[verify_program_live]
    W --> X[Cache hit or live fetch + heuristics]
    X --> Y[Return verification payload]

    C --> Z[POST /save]
    Z --> AA[Create SavedProgram]
    AA --> AB[Return saved payload]

    C --> AC[POST /apply]
    AC --> AD[Create/update StudyApplication]
    AD --> AE[Return application payload]

    C --> AF[GET /applications/{student_id}]
    AF --> AG[Return saved applications]
```

### Notes

- Profile management and selection are handled in [backend/routers/student_university.py](backend/routers/student_university.py).
- Program recommendations use a combination of heuristic scoring and verification-aware analysis in [backend/services/university_match_service.py](backend/services/university_match_service.py).
- Live verification uses SearXNG plus cache-backed fallbacks in [backend/services/university_verification_service.py](backend/services/university_verification_service.py).

## 3) Shared infrastructure

```mermaid
flowchart TD
    A[Frontend React app] --> B[FastAPI backend entrypoint]
    B --> C[backend.main.app]
    C --> D[CORS + gzip + rate limiting + logging + AB testing middleware]
    C --> E[Routers: jobs, profile, applications, cover_letter, intelligence, auth, student_university, kanban, voice_interview, browser_extension, followup, daily_scout]
    E --> F[(SQLAlchemy sessions via backend.database.get_db)]
    F --> G[(Database tables for jobs, profiles, applications, university data, verification cache, match cache)]

    C --> H[Startup migrations via Alembic]
    H --> I[Schema validation / required table checks]

    E --> J[LLMProvider]
    J --> K[OpenRouter / OpenAI-compatible providers / fallback behavior]

    E --> L[Chroma / embeddings via core.rag_service and university_match_service]
    L --> M[Vector retrieval for university matching and resume artifacts]

    E --> N[Background executor for job artifacts]
    N --> O[Cover letter / resume artifact generation]

    A --> P[Browser extension / follow-up routes]
```

### Notes

- The API bootstraps core middleware and routers in [backend/main.py](backend/main.py).
- Shared infrastructure includes authentication, logging, rate limiting, startup migrations, and provider fallback logic.
- The job and university flows both depend on the same API and persistence layer, but their recommendation logic is separated into dedicated services.
