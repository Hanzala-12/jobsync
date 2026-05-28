# University Module Analysis

## Current State

The university module already has the core student workflow in place:

- `University` and `Program` store the catalog data.
- `StudentProfile`, `SavedProgram`, and `StudyApplication` support matching, saving, and applying.
- `UniversityVerificationCache` caches live verification results.
- The student router exposes filtering, detail, matching, saving, applying, reporting, and live verification endpoints.

## What Is Populated For Non-US Programs

Non-US universities are currently seeded from the Hipo universities API, while programs are generated from fixed templates in `scripts/ingest_universities.py`.

Typical populated fields are:

- University name, country, city, website, ranking, and student population.
- Program name, degree level, duration, estimated tuition, currency, and minimum GPA.

College Scorecard enrichment is US-only, so non-US universities do not get the US-specific acceptance rate, SAT, ACT, or net price enrichment.

## Mock Or Default Fields

The non-US program records still rely on template defaults for most of the detailed admissions and cost data:

- `application_deadline`
- `semester_intake`
- `min_ielts`
- `min_toefl`
- `living_cost_estimate`
- `scholarship_available`
- `source_url`
- `data_quality_score` defaults to `1`

The tuition values are also template-derived rather than scraped from official program pages.

## Live Verification Flow

Live verification is handled by `backend/services/university_verification_service.py`.

- It first checks `UniversityVerificationCache`.
- If a fresh cache row exists, it returns the cached verification result.
- If live verification is enabled and SearXNG is configured, it searches several queries for tuition and admissions information.
- It extracts tuition estimates and textual summaries from the search results.
- If live search is unavailable or returns nothing, it falls back to stored program data.

Triggered paths in the current app include the `/api/student/verify/{university_id}/{program_id}` endpoint and matching flows that call `verify_program_live()`.

## Search And Popularity Tracking

Before this update, there was no dedicated program search log table for popularity tracking.

There were related analytics tables for other features:

- `ABTestEvent` tracks feature events such as match requests, saves, and applications.
- `ProgramCorrection` tracks user-reported outdated data.

Neither of those tables is a clean replacement for program search intent, so a dedicated `ProgramSearchLog` table is needed for ranking popular programs in the background refresh job.
