from __future__ import annotations

RESUME_STANDARD_HEADINGS = ["Experience", "Skills", "Education", "Projects"]

ATS_FRIENDLY_FONTS = ["Arial", "Calibri", "Times New Roman", "Georgia"]

PROHIBITED_ELEMENTS = ["tables", "columns", "graphics", "images", "headers", "footers"]

WEAK_PHRASE_REPLACEMENTS = {
    "responsible for": "achieved",
    "helped with": "delivered",
    "worked on": "built",
    "assisted with": "supported",
    "in charge of": "led",
    "tasked with": "owned",
    "involved in": "contributed to",
    "helped to": "improved",
    "used to": "optimized",
    "participated in": "shaped",
    "worked closely with": "partnered with",
}

COMMON_JOB_KEYWORDS = [
    "python",
    "sql",
    "excel",
    "power bi",
    "tableau",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "git",
    "github",
    "ci/cd",
    "rest api",
    "rest apis",
    "fastapi",
    "flask",
    "django",
    "react",
    "typescript",
    "javascript",
    "node.js",
    "data analysis",
    "machine learning",
    "deep learning",
    "nlp",
    "etl",
    "dashboard",
    "automation",
    "testing",
    "stakeholder management",
    "project management",
    "communication",
    "leadership",
    "agile",
    "scrum",
    "seo",
    "content strategy",
    "marketing",
    "analytics",
    "research",
    "system design",
]

SECTION_ALIASES = {
    "experience": "Experience",
    "work experience": "Experience",
    "professional experience": "Experience",
    "employment": "Experience",
    "skills": "Skills",
    "technical skills": "Skills",
    "core skills": "Skills",
    "education": "Education",
    "academic background": "Education",
    "projects": "Projects",
    "project experience": "Projects",
    "summary": "Summary",
    "professional summary": "Summary",
    "profile": "Summary",
    "contact": "Contact",
    "contact information": "Contact",
}

DEFAULT_SKILLS_BLOCK = ["Python", "Communication", "Problem Solving", "SQL", "Project Delivery"]
