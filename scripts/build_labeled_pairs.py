from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models import Job

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "labeled_resume_jd_pairs.csv"

SKILL_HINTS = [
    ("Python", r"python"),
    ("FastAPI", r"fastapi"),
    ("PostgreSQL", r"postgres|postgresql|sql"),
    ("AWS", r"aws|amazon web services"),
    ("Docker", r"docker"),
    ("Kubernetes", r"kubernetes|k8s"),
    ("React", r"react"),
    ("TypeScript", r"typescript|ts"),
    ("JavaScript", r"javascript|js"),
    ("Node.js", r"node\.js|nodejs|node"),
    ("Django", r"django"),
    ("REST APIs", r"rest api|api"),
    ("SEO", r"seo|search engine optimization"),
    ("Google Analytics", r"google analytics|analytics"),
    ("Social Media", r"social media|social media marketing"),
    ("CRM", r"crm|salesforce"),
    ("Cold Calling", r"cold calling|outbound"),
    ("Lead Generation", r"lead generation|outreach"),
    ("Selenium", r"selenium|qa|testing"),
    ("Pytest", r"pytest|testing"),
    ("Tableau", r"tableau"),
    ("Power BI", r"power bi"),
    ("Excel", r"excel|microsoft excel"),
    ("WordPress", r"wordpress|wp"),
    ("PHP", r"php"),
    ("Magento", r"magento"),
    ("Adobe", r"adobe"),
    ("Content Strategy", r"content strategy|copywriting|content"),
    ("Paid Ads", r"paid ads|ppc|google ads"),
    ("Growth Marketing", r"growth marketing|growth"),
    ("A/B Testing", r"a/b testing|ab testing|testing"),
    ("Linux", r"linux"),
    ("Terraform", r"terraform"),
    ("CI/CD", r"ci/cd|continuous integration|continuous delivery"),
    ("Customer Support", r"customer support|support"),
    ("Troubleshooting", r"troubleshooting|debug"),
    ("Android SDK", r"android sdk|android"),
    ("Firebase", r"firebase"),
    ("Kotlin", r"kotlin"),
    ("MongoDB", r"mongodb|mongo"),
]


def _safe_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\r", " ").replace("\n", " ")).strip()


def _extract_skills(job: Job) -> list[str]:
    text = f"{job.title or ''} {job.description or ''}".lower()
    skills = []
    for label, pattern in SKILL_HINTS:
        if re.search(pattern, text):
            skills.append(label)
    if not skills:
        skills = ["Python", "Communication", "Problem Solving"]
    # Ensure diversity and a manageable skill list
    return list(dict.fromkeys(skills[:7]))


def _build_resume_text(job: Job, variant: str, label: int) -> str:
    title = _safe_text(job.title)
    skills = _extract_skills(job)
    company = _safe_text(job.company) or "Target Company"
    summary = ""

    if variant == "exact":
        summary = (
            f"Experienced {title.lower()} with a background in {' and '.join(skills[:3])}. "
            f"I build reliable systems, translate business needs into implementation, and work effectively across engineering and product teams."
        )
    elif variant == "ambiguous":
        secondary = skills[3] if len(skills) > 3 else "Communication"
        summary = (
            f"Cross-functional {title.lower()} with hands-on experience in {' and '.join(skills[:2])}. "
            f"I also collaborate on {secondary.lower()} workflows, stakeholder communication, and delivery-oriented execution."
        )
    elif variant == "partial":
        summary = (
            f"Hands-on professional focused on {' and '.join(skills[:2])}. "
            f"I enjoy shipping practical products, improving delivery quality, and communicating clearly with teammates."
        )
    else:
        summary = (
            f"Generalist with experience in project coordination, communication, and cross-functional delivery. "
            f"I have worked across product, operations, and customer-facing environments."
        )

    bullets = [
        f"Built and improved {' and '.join(skills[:2])} workflows with measurable quality and delivery gains.",
        f"Collaborated with product, design, and operations teams to translate requirements into working outcomes.",
    ]

    if label == 0:
        bullets = [
            "Led customer-facing coordination and documentation efforts.",
            "Supported cross-functional planning and reporting for stakeholders.",
        ]

    resume = (
        f"Candidate Profile\n"
        f"Name: Amina Candidate\n"
        f"Location: Karachi, Pakistan\n"
        f"Summary: {summary}\n\n"
        f"Skills\n- {'; '.join(skills)}\n\n"
        f"Experience\n"
        + "\n".join(f"- {bullet}" for bullet in bullets)
        + "\n\n"
        f"Education\n- BS Computer Science, National University\n\n"
        f"Projects\n- Delivered a production-ready {title.lower()} portfolio project for {company}."
    )
    return resume


def _select_positive_jobs(db) -> list[Job]:
    jobs = (
        db.query(Job)
        .filter(Job.description.is_not(None))
        .filter(Job.title.is_not(None))
        .order_by(Job.id.asc())
        .all()
    )
    # Keep jobs with enough signal; skip junk entries that are clearly placeholders.
    filtered = [job for job in jobs if len(_safe_text(job.description)) >= 60 and "example domain" not in (job.description or "").lower()]
    if len(filtered) < 30:
        raise RuntimeError(f"Need at least 30 usable jobs, found {len(filtered)}")
    return filtered[:30]


def main() -> int:
    db = SessionLocal()
    try:
        positives = _select_positive_jobs(db)
        negatives = [job for job in db.query(Job).order_by(Job.id.asc()).all() if job not in positives]

        rows = []
        # 120 strong matches, 20 partial matches, 10 low-signal negatives
        for job in positives:
            for variant in ("exact", "exact", "exact", "ambiguous"):
                rows.append(
                    {
                        "query_id": f"q-{job.id}-{variant}-1",
                        "resume_text": _build_resume_text(job, variant, 2),
                        "target_job_id": str(job.id),
                        "target_title": _safe_text(job.title),
                        "label": 2,
                        "difficulty": "strong" if variant == "exact" else "medium",
                        "variant": variant,
                        "job_description": _safe_text(job.description),
                    }
                )
        # Add partial matches on a subset of jobs to make reranking harder.
        for job in positives[:20]:
            rows.append(
                {
                    "query_id": f"q-{job.id}-partial-1",
                    "resume_text": _build_resume_text(job, "partial", 1),
                    "target_job_id": str(job.id),
                    "target_title": _safe_text(job.title),
                    "label": 1,
                    "difficulty": "partial",
                    "variant": "partial",
                    "job_description": _safe_text(job.description),
                }
            )

        # Add 10 low-signal negatives to keep the dataset aligned with 0/1/2 labels.
        for index, job in enumerate(negatives[:10]):
            rows.append(
                {
                    "query_id": f"q-negative-{index + 1}",
                    "resume_text": _build_resume_text(job, "negative", 0),
                    "target_job_id": "",
                    "target_title": "",
                    "label": 0,
                    "difficulty": "negative",
                    "variant": "negative",
                    "job_description": "",
                }
            )

        rows = rows[:150]
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DATA_PATH.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "query_id",
                    "resume_text",
                    "target_job_id",
                    "target_title",
                    "label",
                    "difficulty",
                    "variant",
                    "job_description",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        print(f"Wrote {len(rows)} labeled pairs to {DATA_PATH}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
