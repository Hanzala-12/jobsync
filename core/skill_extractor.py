from __future__ import annotations

import json
import os
import re
from typing import List

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
    # strip version numbers
    s = re.sub(r"\b(v|version)\s*\d+[\.\d]*\b", "", s)
    s = re.sub(r"[\d_]+", "", s).strip()
    if s in SKILL_MAP:
        return SKILL_MAP[s]
    # capitalized form
    return s.title()


def extract_skills(text: str, limit: int = 50) -> List[str]:
    """Extract skills from free text using spaCy NER (if available) and simple pattern matching.

    Returns a list of normalized skill strings.
    """
    if not text:
        return []

    found = []
    lowered = (text or "").lower()

    # use spaCy NER to extract ORG/PRODUCT/TECH tokens if available
    if spacy is not None:
        try:
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in {"ORG", "PRODUCT", "WORK_OF_ART", "NORP", "TECH"} or len(ent.text) <= 40:
                    candidate = ent.text.strip()
                    if candidate:
                        found.append(candidate)
        except Exception:
            # if model not installed or fails, fall back to simple heuristics
            pass

    # Regex-based pattern matching for common tech tokens
    patterns = [r"\bpython\b", r"\bjava(script)?\b", r"\btypescript\b", r"\breact\b", r"\bnode(?:\.js)?\b",
                r"\baws\b", r"\bazure\b", r"\bdocker\b", r"\bkubernetes\b", r"\bsql\b", r"\bpostgres(?:ql)?\b",
                r"\bpandas\b", r"\bnumpy\b", r"\bmachine learning\b", r"\bdata science\b", r"\bflask\b", r"\bdjango\b"]

    for pat in patterns:
        for m in re.finditer(pat, lowered):
            token = text[m.start():m.end()]
            found.append(token)

    # token frequency fallback
    if not found:
        tokens = _tokenize(text)
        freq = {}
        for t in tokens:
            k = t.lower()
            freq[k] = freq.get(k, 0) + 1
        ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
        for k, _ in ranked[:limit]:
            found.append(k)

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
        if len(normalized) >= limit:
            break

    # if nothing found, return curated fallback
    if not normalized:
        for s in FALLBACK_SKILLS[:limit]:
            normalized.append(s.title())

    return normalized
