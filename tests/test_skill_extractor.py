from core import skill_extractor


def test_normalize_skill_preserves_common_abbreviations(monkeypatch):
    monkeypatch.setattr(skill_extractor, "spacy", None)

    assert skill_extractor.normalize_skill("ai") == "AI"
    assert skill_extractor.normalize_skill("node.js") == "Node.js"
    assert skill_extractor.normalize_skill("ci/cd") == "CI/CD"


def test_extract_skills_ignores_generic_prose(monkeypatch):
    monkeypatch.setattr(skill_extractor, "spacy", None)

    text = (
        "Careem is building an inspiring platform across internal systems and challenges. "
        "We need AI, code review, automation, problem-solving, Android, Kotlin, React Native, "
        "Node.js, and TypeScript."
    )

    skills = skill_extractor.extract_skills(text)
    lower_skills = {skill.lower() for skill in skills}

    assert "careem" not in lower_skills
    assert "across" not in lower_skills
    assert "internal" not in lower_skills
    assert "challenge" not in lower_skills
    assert "ai" in lower_skills
    assert "android" in lower_skills
    assert "kotlin" in lower_skills
    assert "node.js" in lower_skills
    assert "typescript" in lower_skills


def test_explain_match_for_uses_readable_skill_labels(monkeypatch):
    monkeypatch.setattr(skill_extractor, "spacy", None)

    from core.match_explainer import explain_match_for

    payload = explain_match_for(
        {
            "id": 1,
            "description": "Careem builds Android apps with Kotlin, React Native, Node.js, TypeScript, AI, code review, and automation.",
            "experience_required": "2-4 years",
            "job_skills": [],
        },
        {
            "id": 2,
            "resume_text": "Built React Native and Node.js apps with TypeScript and AI tooling.",
            "profile_skills": [],
        },
    )

    assert payload["matching_skills"] == ["AI", "Node.js", "React Native", "TypeScript"]
    assert payload["missing_skills"] == ["Android", "Automation", "Code Review", "Kotlin"]
