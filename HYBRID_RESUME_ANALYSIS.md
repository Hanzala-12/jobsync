**Resume Blueprint**:

```json
{
  "metadata": {
    "version": "2026-05-28",
    "author": "JobSync Pro",
    "description": "ATS-optimized resume blueprint based on 2026 hiring guidelines"
  },
  "sections": [
    {
      "name": "contact",
      "title": "Contact Information",
      "mandatory": true,
      "order": 1,
      "fields": [
        "full_name", "job_title", "email", "phone", "location",
        "linkedin_url", "portfolio_url"
      ],
      "layout_hint": "inline_row"
    },
    {
      "name": "summary",
      "title": "Professional Summary",
      "mandatory": true,
      "order": 2,
      "style_hint": "paragraph",
      "max_length": 150
    },
    {
      "name": "skills",
      "title": "Skills",
      "mandatory": true,
      "order": 3,
      "style_hint": "comma_list"
    },
    {
      "name": "experience",
      "title": "Work Experience",
      "mandatory": true,
      "order": 4,
      "entry_template": {
        "title": "{job_title}",
        "company": "{company}",
        "dates": "{start_date} – {end_date or 'Present'}",
        "bullets": []
      }
    },
    {
      "name": "education",
      "title": "Education",
      "mandatory": true,
      "order": 5,
      "entry_template": {
        "degree": "{degree}",
        "institution": "{institution}",
        "dates": "{start_year} – {end_year}",
        "gpa": "{gpa}"
      }
    },
    {
      "name": "projects",
      "title": "Projects",
      "mandatory": false,
      "order": 6,
      "entry_template": {
        "name": "{name}",
        "description": "{description}",
        "technologies": "{technologies}"
      }
    }
  ]
}
```

**Architecture**:

- `blueprints/resume_blueprint.json`: canonical JSON blueprint enforcing single-column layout, standard headings, and section style hints.
- `core/resume_blueprint_engine.py`: loads the blueprint and renders a plain-text resume from either LLM-provided section content or structured profile data.
- `core/resume_analyzer.py`: updated LLM prompt to request per-section JSON according to the blueprint. The analyzer now asks the LLM for section content, parses JSON, then assembles the final resume using the blueprint engine. If LLM backends are unavailable, the analyzer falls back to a conservative structured fill using profile fields.
- `scripts/test_hybrid_resume.py`: deterministic test that simulates LLM section output, runs the engine, asserts the blueprint structure, and exports a PDF via `core/pdf_generator.py`.

**Why Hybrid (Blueprint + LLM) is superior**:

- Consistency: The blueprint guarantees a single-column, ATS-friendly structure and standard headings. This removes hallucination-driven structural variations.
- Precision: The LLM focuses on content generation within clearly defined fields (e.g., `experience[].bullets`), producing targeted, keyword-aware text.
- Safety & Fallbacks: When LLMs are unavailable or return malformed output, the engine can still produce usable resumes from structured profile data.
- Traceability: JSON section outputs are easier to validate, test, and post-process than freeform text.

**Verdict**:

The hybrid approach delivers predictable formatting and ATS compliance from the blueprint while leveraging the LLM for adaptive, role-specific content. This reduces downstream PDF rendering issues, improves keyword placement for ATS matching, and offers robust fallbacks for production reliability.
