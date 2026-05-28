# PROJECT MASTER STATUS

Status date: 2026-05-27

## Executive Summary

JobSync Pro is no longer a thin prototype. The job module, university/study module, shared AI services, and operational scaffolding are all materially implemented in code, and the live Supabase schema migration was verified successfully during this session. The university module is the strongest area of recent work: it now has live verification, on-demand scraping, per-field provenance, freshness reporting, correction submission, and a usable frontend workflow.

The project is still not “finished.” The biggest remaining gaps are operational rather than feature-core: there is no dedicated frontend admin monitor for scrape stats, background work still relies on in-process execution rather than a durable queue, and the repository still contains legacy duplicate code paths that should be retired or clearly marked. Legacy SQLite compatibility is also not a trustworthy validation path because older migrations contain PostgreSQL-specific assumptions.

Live production verification completed during this session showed the new university provenance tables in place and populated, including program_field_provenance with 194 rows. program_scrape_jobs also exists in the live schema. That makes the current status report evidence-based rather than speculative.

## Inventory: Job Module

| Area | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Multi-source job search | Complete | backend/routers/jobs.py, backend/services/job_apis.py, frontend/src/pages/Jobs.jsx | Search pulls from multiple Pakistan and remote sources, normalizes results, and supports live fallback behavior. |
| Streamed search UI | Complete | frontend/src/pages/Jobs.jsx, backend/routers/jobs.py | The jobs page consumes the streaming endpoint and shows progressive results. |
| Job normalization and deduplication | Complete | backend/routers/jobs.py, core/normalizer.py, core/deduplicator.py | Incoming jobs are cleaned, normalized, and upserted into the database. |
| Profile-aware ranking | Complete | backend/routers/jobs.py, backend/services/job_ranking.py, backend/services/match_explainer.py | Jobs are scored against the selected profile before display. |
| Resume tailoring and cover letters | Mostly complete | frontend/src/pages/Jobs.jsx, backend/routers/jobs.py, core/rag_service.py | User-facing flows exist, but background generation is still in-process instead of a durable queue. |
| Salary estimation and match explanation | Complete | frontend/src/pages/Jobs.jsx, backend/routers/jobs.py, backend/schemas.py | Salary estimate, match explanation, and application tracking are wired end-to-end. |
| Application tracker | Complete | backend/routers/applications.py, frontend/src/components/MyApplications.jsx, backend/models.py | Saved/applied tracking is integrated with the main job workflow. |
| Daily scout and follow-up surfaces | Complete | backend/routers/daily_scout.py, backend/routers/followup.py, frontend routes in src/App.jsx | Support modules are wired into the app shell. |

## Inventory: University Module

| Area | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Student profile CRUD and selection | Complete | backend/routers/student_university.py, frontend/src/components/StudentProfileForm.jsx, tests/test_student_university.py | Profiles can be created, edited, selected, and deleted. Numeric fields are normalized before submit. |
| University browsing and filtering | Complete | backend/routers/student_university.py, frontend/src/components/StudentUniversitySearch.jsx | The frontend can browse and save universities, and the backend supports filtered listing. |
| Match scoring and recommendations | Complete | backend/services/university_match_service.py, backend/routers/student_university.py, frontend/src/components/UniversityMatchList.jsx | Matching uses academic, budget, and location fit with cached verification support. |
| University detail modal | Complete | frontend/src/components/UniversityDetailModal.jsx | The modal now shows freshness, live verification details, retry behavior, and provenance badges. |
| Live verification | Complete | backend/services/university_verification_service.py, backend/routers/student_university.py | Live verification integrates search-based evidence, caching, and confidence labeling. |
| On-demand scraping | Complete | backend/services/program_scraper.py, backend/services/parsers/, backend/routers/student_university.py | Scrape jobs, status polling, robots.txt checks, and parser registry are implemented. |
| Per-field provenance | Complete | backend/models.py, backend/services/program_scraper.py, backend/services/university_verification_service.py, frontend/src/components/UniversityDetailModal.jsx | Provenance is tracked per program field and displayed in the UI. |
| Correction reporting | Complete | backend/models.py, backend/routers/student_university.py, frontend/src/components/UniversityDetailModal.jsx | Outdated program reporting is available and includes field_name support in the model layer. |
| Saved universities and study applications | Complete | backend/routers/student_university.py, frontend/src/components/StudentSavedUniversities.jsx, frontend/src/components/MyApplications.jsx | Saving, applying, and reviewing study applications are wired through the student module. |
| Admin scrape stats | Backend complete, UI missing | backend/routers/admin.py | The endpoint exists, but no frontend route or dashboard page is wired yet. |

## Inventory: Shared Infrastructure & AI

| Area | Status | Evidence | Notes |
| --- | --- | --- | --- |
| App bootstrap and router composition | Complete | backend/main.py, frontend/src/App.jsx | Main routes and startup wiring are in place for both job and university modules. |
| Startup migrations and schema checks | Complete but risky | backend/main.py, backend/migrations/versions/ | Migrations run automatically on startup, but the repository still contains legacy migration assumptions that are not SQLite-safe. |
| Database schema expansion | Complete | backend/models.py, Supabase verification from this session | New scrape job, provenance, correction, and verification structures are present in live PostgreSQL. |
| AI provider fallback chain | Complete | core/llm_provider.py | Multiple providers are supported with fallback behavior. |
| RAG and cover-letter generation | Complete | core/rag_service.py, backend/routers/jobs.py | Retrieval-augmented generation is used for cover letters and related artifacts. |
| Scraper engine and parser registry | Complete | backend/services/program_scraper.py, backend/services/parsers/ | The scraper uses robots enforcement, candidate-link exploration, and domain-specific parsers. |
| Monitoring and refresh automation | Partial | backend/routers/admin.py, .github/workflows/refresh_verified_data.yml, scripts/summarize_scrapes.py | Backend stats and scheduled refresh are present; the UI monitor is not. |
| Security middleware and controls | Partial | backend/main.py, backend/security.py, backend/middleware/* | CORS, HTTPS redirect, logging, and in-process rate limiting exist, but the controls are still lightweight for production-scale abuse. |
| Background execution | Partial | backend/routers/jobs.py, backend/services/program_scraper.py | Background work is still process-local rather than queue-backed. |

## Inventory: Testing & Documentation

| Area | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Backend integration tests | Complete | tests/test_student_university.py, tests/test_jobs.py, tests/test_auth.py, tests/test_profile.py, tests/test_cover_letter.py, tests/test_rag_service.py, tests/test_health.py | The repo has meaningful coverage across the core API surfaces. |
| Frontend unit tests | Complete | frontend/src/__tests__/UniversityDetailModal.test.jsx, frontend/src/__tests__/StudentUniversitySearch.test.jsx, frontend/src/__tests__/Profile.test.jsx, frontend/src/__tests__/Jobs.test.jsx | The university modal, search page, profile flow, and jobs page all have targeted UI tests. |
| End-to-end tests | Complete | frontend/e2e/gradcareer.spec.js, frontend/e2e/jobsync.spec.js, scripts/test_university_e2e.py | There is both browser-level and script-based integration coverage. |
| CI pipeline | Complete | .github/workflows/ci.yml | CI runs migrations, pytest, flake8, and formatting checks. |
| Refresh pipeline | Complete | .github/workflows/refresh_verified_data.yml | Scheduled refresh applies migrations, refreshes verified data, and summarizes scrape results. |
| User documentation | Complete | docs/UNIVERSITY_USER_GUIDE.md, README.md, QUICKSTART.md, DEPLOYMENT_GUIDE.md, FRONTEND_INTEGRATION.md | The university workflow now has a user-facing guide, and core project docs exist. |
| Audit/status artifacts | Complete | AUDIT_REPORT.md, REPORT.md, TEST_REPORT.md, PRODUCTION_HARDENING_REPORT.md, UPGRADE_SUMMARY.md | The repo already contains a history of structured reporting. |

## Half-Done Features

1. Admin monitoring UI: the backend scrape-stats endpoint exists, but there is no visible frontend dashboard or route for it.
2. Durable background jobs: scraping and cover-letter generation still depend on in-process execution, so restarts can interrupt work.
3. Backfill audit trail: scripts/backfill_field_provenance.py is present and the target data exists, but the session did not capture a clean terminal completion line for the run.
4. Legacy router cleanup: backend/routers/student.py still exists as a duplicate/older student router while the application imports backend/routers/student_university.py.

## Stale Code

| Candidate | Why it looks stale | Status |
| --- | --- | --- |
| backend/routers/student.py | The app imports backend/routers/student_university.py instead, and no workspace references point back to this file. | Likely stale or legacy duplicate |
| frontend/src/components/MatchPanel.jsx | The file exists, but the current job and university UI routes use Jobs.jsx, UniversityDetailModal.jsx, and UniversityMatchList.jsx instead. | Likely stale or unused |

## Known Bugs

1. Legacy migrations are not SQLite-reliable. Older revisions use PostgreSQL-oriented DDL and defaults, so local SQLite fallback should not be treated as a real production validation path.
2. Startup migrations can fail the whole application boot if schema drift or a database connection problem exists. That is intentional, but it makes migration quality critical.
3. The admin access pattern in backend/routers/admin.py relies on user.id == 1 or a shared X-ADMIN-TOKEN header. That is workable for a small deployment, but it is a fragile authorization model.
4. In-process background work is not durable. A server restart can interrupt scrape retries or cover-letter generation mid-flight.

## Security & Operational Gaps

1. Rate limiting is implemented in-process in backend/main.py, so it is not shared across multiple replicas.
2. CORS must be explicitly configured in production. The app now defaults to an empty allow-list when CORS_ORIGINS is unset, which is safer but can still be misconfigured.
3. The scraping pipeline depends on third-party sites, robots.txt permissions, and site structure. That means failures are expected and need operational monitoring.
4. There is no queue/worker boundary yet for scrape jobs, verification refreshes, or cover-letter generation.
5. The frontend still lacks a dedicated monitoring page for scrape stats and freshness trends, even though the backend data exists.

## Recommendations

1. Add a dedicated admin monitoring page that consumes backend/routers/admin.py and surfaces scrape volume, success rate, block rate, and freshness.
2. Move scraping and background artifact generation to a durable queue or worker model so restarts do not drop work.
3. Remove or formally archive stale duplicates such as backend/routers/student.py and frontend/src/components/MatchPanel.jsx.
4. Add a PostgreSQL migration smoke test that matches the production dialect instead of relying on SQLite fallback for schema confidence.
5. Expand coverage around scrape retry behavior, admin stats, and provenance backfill so operational regressions are caught earlier.
6. Keep the university user guide and workflow docs in sync with the provenance and freshness behavior now shipped in the frontend.

## Validation Notes

Live Supabase verification during this session confirmed that the new schema is deployed and populated. The key checks that passed were:

- program_scrape_jobs exists.
- program_field_provenance exists.
- program_field_provenance contains 194 rows.
- alembic_version on Supabase includes the newer university-module revisions.

This report intentionally reflects the code and production state observed in the workspace rather than the intended roadmap.