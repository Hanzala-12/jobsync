from __future__ import annotations

import json
import os
import re
from typing import List

from core.resume_standards import COMMON_JOB_KEYWORDS

try:
    import spacy
except Exception:  # pragma: no cover - optional dependency
    spacy = None

# Load mapping file from data/skills_mapping.json
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAPPING_PATH = os.path.join(_ROOT, "data", "skills_mapping.json")

if os.path.exists(_MAPPING_PATH):
    try:
        with open(_MAPPING_PATH, "r", encoding="utf-8") as f:
            SKILL_MAP = {k.lower(): v for k, v in json.load(f).items()}
    except Exception:
        SKILL_MAP = {}
else:
    SKILL_MAP = {}

# A small curated fallback list of common skills (used when NER not available)
FALLBACK_SKILLS = [
    "python",
    "javascript",
    "java",
    "c#",
    "c++",
    "sql",
    "aws",
    "azure",
    "docker",
    "kubernetes",
    "react",
    "node.js",
    "django",
    "flask",
    "fastapi",
    "pandas",
    "numpy",
    "machine learning",
    "data analysis",
    "html",
    "css",
    "git",
    "testing",
    "communication",
]

DISPLAY_SKILL_MAP = {
    "ai": "AI",
    "api": "API",
    "apis": "APIs",
    "aws": "AWS",
    "azure": "Azure",
    "c#": "C#",
    "c++": "C++",
    "ci/cd": "CI/CD",
    "css": "CSS",
    "css3": "CSS3",
    "docker": "Docker",
    "gcp": "GCP",
    "git": "Git",
    "github": "GitHub",
    "html": "HTML",
    "html5": "HTML5",
    "javascript": "JavaScript",
    "kubernetes": "Kubernetes",
    "ml": "ML",
    "node.js": "Node.js",
    "nosql": "NoSQL",
    "python": "Python",
    "react": "React",
    "rest api": "REST API",
    "rest apis": "REST APIs",
    "seo": "SEO",
    "sql": "SQL",
    "ui/ux": "UI/UX",
    "typescript": "TypeScript",
}


def _skill_pattern(skill: str) -> str:
    lowered = skill.lower().strip()
    if lowered == "node.js":
        return r"\bnode(?:\.?\s*js)?\b"
    if lowered == "react":
        return r"\breact(?:\.js|\s+native)?\b"
    if lowered == "ai":
        return r"\bai\b|artificial intelligence"
    if lowered == "ci/cd":
        return r"\bci\s*[/\-]?\s*cd\b"
    if lowered == "c#":
        return r"\bc#\b"
    if lowered == "c++":
        return r"\bc\+\+\b"
    if lowered == "gcp":
        return r"\bgcp\b|google cloud platform"
    if lowered == "rest api":
        return r"\brest\s+apis?\b"
    if lowered == "rest apis":
        return r"\brest\s+apis\b"
    if lowered == "ui/ux":
        return r"\bui/ux\b|user experience|user interface"
    if lowered == "nestjs":
        return r"\bnest(?:\.js)?\b"
    escaped = re.escape(lowered).replace(r"\ ", r"\s+")
    return rf"(?<!\w){escaped}(?!\w)"


_KNOWN_SKILLS = sorted(
    {
        *{skill.lower() for skill in FALLBACK_SKILLS},
        *{skill.lower() for skill in COMMON_JOB_KEYWORDS},
        "ai",
        "android",
        "apis",
        "ci/cd",
        "c#",
        "c++",
        "code review",
        "express",
        "graphql",
        "html5",
        "kotlin",
        "microservices",
        "mongodb",
        "mysql",
        "nestjs",
        "node.js",
        "postgresql",
        "prompt engineering",
        "problem-solving",
        "problem solving",
        "react native",
        "rest api",
        "rest apis",
        "swift",
        "ui/ux",
    },
    key=len,
    reverse=True,
)

_KNOWN_SKILL_PATTERNS = [(skill, re.compile(_skill_pattern(skill), re.IGNORECASE)) for skill in _KNOWN_SKILLS]


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z+#.]+(?:-[A-Za-z0-9]+)?", text or "")
    return [t for t in tokens if len(t) > 1]


def normalize_skill(skill: str) -> str:
    if not skill:
        return ""
    s = str(skill).strip().lower()
    # direct mapping
    if s in SKILL_MAP:
        return SKILL_MAP[s]
    if s in DISPLAY_SKILL_MAP:
        return DISPLAY_SKILL_MAP[s]
    # strip version numbers
    s = re.sub(r"\b(v|version)\s*\d+[\.\d]*\b", "", s)
    s = re.sub(r"[\d_]+", "", s).strip()
    if s in SKILL_MAP:
        return SKILL_MAP[s]
    if s in DISPLAY_SKILL_MAP:
        return DISPLAY_SKILL_MAP[s]
    # capitalized form
    return s.title() if s else ""


def extract_skills(text: str, limit: int = 50) -> List[str]:
    """Extract skills from free text using spaCy NER (if available) and simple pattern matching.

    Returns a list of normalized skill strings.
    """
    if not text:
        return []

    found = []
    lowered = (text or "").lower()

    # use spaCy NER only when it identifies an explicit known skill/technology
    if spacy is not None:
        try:
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text)
            for ent in doc.ents:
                candidate = ent.text.strip().lower()
                if candidate and any(candidate == skill or re.fullmatch(_skill_pattern(skill), candidate) for skill in _KNOWN_SKILLS):
                    found.append(ent.text.strip())
        except Exception:
            # if model not installed or fails, fall back to pattern matching
            pass

    # Pattern-based matching for explicit skills only
    for skill, pat in _KNOWN_SKILL_PATTERNS:
        if pat.search(lowered):
            found.append(skill)

    # map and dedupe
    normalized = []
    seen = set()
    for item in found:
        n = normalize_skill(item)
        if not n:
            continue
        key = n.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(n)

    collapsed = []
    for item in sorted(normalized, key=lambda value: (-len(value), value.lower())):
        lowered_item = item.lower()
        if any(re.search(rf"(?<!\w){re.escape(lowered_item)}(?!\w)", existing.lower()) for existing in collapsed):
            continue
        collapsed.append(item)

    ordered = sorted(collapsed, key=str.lower)

    # if nothing found, return curated fallback
    if not ordered:
        for s in FALLBACK_SKILLS[:limit]:
            ordered.append(s.title())

    return ordered[:limit]
