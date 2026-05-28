from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "labeled_resume_jd_pairs.csv"

DOMAIN_RELATIONS: dict[str, set[str]] = {
    "backend": {"cloud", "devops", "security"},
    "frontend": {"mobile", "qa"},
    "data": {"ml", "product"},
    "devops": {"backend", "cloud", "security"},
    "mobile": {"frontend", "qa"},
    "ml": {"data", "cloud"},
    "qa": {"frontend", "mobile", "product"},
    "product": {"data", "qa", "frontend"},
    "cloud": {"backend", "devops", "ml", "security"},
    "security": {"devops", "cloud", "backend"},
}

DOMAIN_LIBRARY: dict[str, dict[str, Any]] = {
    "backend": {
        "resume_title": "Backend Engineer",
        "resume_location": "Karachi",
        "summary": "Backend engineer specializing in APIs, services, SQL, and cloud-backed systems.",
        "skills": ["Python", "FastAPI", "SQL", "PostgreSQL", "Docker", "AWS"],
        "experience": [
            "Architected REST APIs for internal platforms and partner integrations.",
            "Improved service latency through query tuning, caching, and async processing.",
            "Collaborated with product and frontend teams to ship backend features weekly.",
        ],
        "project": "Built a payment orchestration service with idempotent APIs and audit trails.",
        "domain_terms": ["REST APIs", "microservices", "backend services", "database optimization"],
    },
    "frontend": {
        "resume_title": "Frontend Engineer",
        "resume_location": "Lahore",
        "summary": "Frontend engineer focused on React, component systems, accessibility, and product polish.",
        "skills": ["React", "TypeScript", "JavaScript", "CSS", "Accessibility", "Testing Library"],
        "experience": [
            "Built reusable UI components and design-system patterns for product teams.",
            "Improved page performance and accessibility scores across major customer flows.",
            "Partnered with designers to translate wireframes into polished user experiences.",
        ],
        "project": "Launched a responsive analytics dashboard with filters, charts, and exports.",
        "domain_terms": ["React", "UI components", "frontend", "design system"],
    },
    "data": {
        "resume_title": "Data Analyst",
        "resume_location": "Islamabad",
        "summary": "Data analyst turning business questions into dashboards, SQL insights, and measurable outcomes.",
        "skills": ["SQL", "Python", "Tableau", "Power BI", "Excel", "Data Visualization"],
        "experience": [
            "Built KPI dashboards and weekly reporting packs for leadership.",
            "Wrote SQL analyses that improved funnel visibility and retention tracking.",
            "Worked with stakeholders to define metrics and automate recurring reports.",
        ],
        "project": "Created a churn analysis notebook that guided retention experiments.",
        "domain_terms": ["analytics", "dashboards", "SQL", "reporting"],
    },
    "devops": {
        "resume_title": "DevOps Engineer",
        "resume_location": "Remote",
        "summary": "DevOps engineer supporting CI/CD, infrastructure automation, containerization, and reliability.",
        "skills": ["Docker", "Kubernetes", "CI/CD", "AWS", "Linux", "Terraform"],
        "experience": [
            "Automated builds, deployments, and rollbacks to reduce release friction.",
            "Standardized containerized environments and infrastructure provisioning.",
            "Improved observability through monitoring, logging, and alerting workflows.",
        ],
        "project": "Created a deployment pipeline that cut release time and reduced failed rollouts.",
        "domain_terms": ["CI/CD", "deployment", "infrastructure", "containers"],
    },
    "mobile": {
        "resume_title": "Mobile Engineer",
        "resume_location": "Karachi",
        "summary": "Mobile engineer building reliable Android and iOS features with clean architecture.",
        "skills": ["Kotlin", "Swift", "Android", "iOS", "REST APIs", "Testing"],
        "experience": [
            "Delivered mobile features with offline support and smooth API integrations.",
            "Reduced crash rates by improving state handling and tests.",
            "Worked closely with backend teams to ship app updates on a fast cadence.",
        ],
        "project": "Built a booking flow with cached screens and resilient sync behavior.",
        "domain_terms": ["Android", "iOS", "mobile", "app store"],
    },
    "ml": {
        "resume_title": "Machine Learning Engineer",
        "resume_location": "Remote",
        "summary": "Machine learning engineer building models, pipelines, and data-driven product features.",
        "skills": ["Python", "PyTorch", "scikit-learn", "MLOps", "Feature Engineering", "SQL"],
        "experience": [
            "Trained and evaluated models for ranking, classification, and prediction workflows.",
            "Built reproducible data pipelines and feature stores for experimentation.",
            "Collaborated with product teams to turn model outputs into measurable improvements.",
        ],
        "project": "Shipped an intent-ranking model with offline evaluation and monitoring.",
        "domain_terms": ["model", "training", "prediction", "ranking"],
    },
    "qa": {
        "resume_title": "QA Automation Engineer",
        "resume_location": "Rawalpindi",
        "summary": "QA engineer focused on automation, regression stability, and release confidence.",
        "skills": ["Playwright", "Selenium", "Python", "Test Automation", "CI/CD", "API Testing"],
        "experience": [
            "Automated end-to-end and API regression suites for product releases.",
            "Reduced flaky tests and improved deployment confidence.",
            "Partnered with engineers to reproduce and fix issues before release.",
        ],
        "project": "Built a regression suite for checkout and auth flows with CI integration.",
        "domain_terms": ["testing", "automation", "regression", "quality assurance"],
    },
    "product": {
        "resume_title": "Product Analyst",
        "resume_location": "Lahore",
        "summary": "Product analyst translating usage data into insights, priorities, and business decisions.",
        "skills": ["SQL", "Analytics", "A/B Testing", "Dashboards", "Figma", "Stakeholder Management"],
        "experience": [
            "Tracked product funnels and surfaced insights for roadmap prioritization.",
            "Partnered with design and engineering to validate experiments and releases.",
            "Synthesized user feedback and KPI trends into actionable recommendations.",
        ],
        "project": "Built an experiment analysis dashboard for feature rollout decisions.",
        "domain_terms": ["product", "metrics", "analysis", "experiments"],
    },
    "cloud": {
        "resume_title": "Cloud Engineer",
        "resume_location": "Remote",
        "summary": "Cloud engineer building scalable infrastructure, secure deployments, and platform automation.",
        "skills": ["AWS", "Docker", "Terraform", "Linux", "Networking", "Kubernetes"],
        "experience": [
            "Provisioned scalable cloud infrastructure and secure deployment environments.",
            "Improved platform reliability through automation and monitoring.",
            "Worked with backend and DevOps teams to support production systems.",
        ],
        "project": "Migrated a monolith to containerized services with blue-green deployment.",
        "domain_terms": ["cloud", "infrastructure", "deployment", "AWS"],
    },
    "security": {
        "resume_title": "Security Engineer",
        "resume_location": "Islamabad",
        "summary": "Security engineer focused on application security, tooling, and risk reduction.",
        "skills": ["AppSec", "Threat Modeling", "Python", "AWS", "IAM", "Security Testing"],
        "experience": [
            "Identified and remediated application security risks across backend services.",
            "Automated security checks and reviewed access controls for production systems.",
            "Partnered with engineering teams to improve secure coding practices.",
        ],
        "project": "Implemented a vulnerability scanning workflow for CI/CD pipelines.",
        "domain_terms": ["security", "vulnerabilities", "access control", "threat"],
    },
}

JOB_TEMPLATES: list[dict[str, Any]] = [
    {"job_id": "job_backend_platform", "domain": "backend", "title": "Platform Backend Engineer", "company": "Nexa Systems", "location": "Karachi", "description": "Build scalable backend services, REST APIs, data pipelines, and database optimizations using Python, FastAPI, SQL, Docker, and AWS."},
    {"job_id": "job_backend_integrations", "domain": "backend", "title": "Backend Integrations Engineer", "company": "Blue Harbor", "location": "Remote", "description": "Develop backend integrations, microservices, and asynchronous processing for partner workflows and internal platforms."},
    {"job_id": "job_frontend_product", "domain": "frontend", "title": "Product Frontend Engineer", "company": "Pixel Forge", "location": "Lahore", "description": "Design accessible React interfaces, reusable UI systems, and polished product experiences with performance in mind."},
    {"job_id": "job_frontend_design_system", "domain": "frontend", "title": "Design Systems Engineer", "company": "Northstar Labs", "location": "Remote", "description": "Build component libraries, frontend tooling, and accessible design-system patterns for modern React applications."},
    {"job_id": "job_data_analytics", "domain": "data", "title": "Data Analyst", "company": "Insight Loop", "location": "Islamabad", "description": "Analyze KPIs, build dashboards, and write SQL queries to support business decisions and reporting workflows."},
    {"job_id": "job_data_engineering", "domain": "data", "title": "Analytics Engineer", "company": "Metric Hive", "location": "Karachi", "description": "Build data pipelines, analytics models, and reporting layers with SQL and Python for growth teams."},
    {"job_id": "job_devops_platform", "domain": "devops", "title": "DevOps Engineer", "company": "CloudPath", "location": "Remote", "description": "Automate CI/CD, manage containerized deployments, and improve observability across cloud infrastructure."},
    {"job_id": "job_devops_sre", "domain": "devops", "title": "Site Reliability Engineer", "company": "Signal Stack", "location": "Lahore", "description": "Support infrastructure automation, incident response, monitoring, and scalable deployment pipelines."},
    {"job_id": "job_mobile_android", "domain": "mobile", "title": "Android Engineer", "company": "AppNest", "location": "Karachi", "description": "Ship Android features, integrate REST APIs, and improve mobile reliability, performance, and testing."},
    {"job_id": "job_mobile_ios", "domain": "mobile", "title": "iOS Engineer", "company": "AppNest", "location": "Remote", "description": "Build iOS app features, manage state and sync flows, and collaborate with backend teams on API integration."},
    {"job_id": "job_ml_ranking", "domain": "ml", "title": "Machine Learning Engineer", "company": "VectorAI", "location": "Remote", "description": "Train ranking and classification models, build feature pipelines, and deploy ML systems with monitoring."},
    {"job_id": "job_ml_applied", "domain": "ml", "title": "Applied Scientist", "company": "DeepSignal", "location": "Lahore", "description": "Research applied ML systems, evaluate models, and ship product features backed by experimentation and data."},
    {"job_id": "job_qa_automation", "domain": "qa", "title": "QA Automation Engineer", "company": "TestBloom", "location": "Rawalpindi", "description": "Automate regression suites, stabilize releases, and run API and end-to-end tests in CI/CD pipelines."},
    {"job_id": "job_qa_platform", "domain": "qa", "title": "Quality Engineer", "company": "TestBloom", "location": "Remote", "description": "Improve testing strategy, reduce flaky tests, and partner with engineers to validate product quality."},
    {"job_id": "job_product_analytics", "domain": "product", "title": "Product Analyst", "company": "Northline", "location": "Islamabad", "description": "Translate analytics into product insights, dashboarding, and experiment analysis for roadmap decisions."},
    {"job_id": "job_product_ops", "domain": "product", "title": "Product Operations Analyst", "company": "Northline", "location": "Lahore", "description": "Support product metrics, stakeholder communication, and experiment tracking across feature releases."},
    {"job_id": "job_cloud_platform", "domain": "cloud", "title": "Cloud Platform Engineer", "company": "SkyGrid", "location": "Remote", "description": "Manage AWS infrastructure, containerized deployments, Terraform automation, and platform reliability."},
    {"job_id": "job_cloud_infra", "domain": "cloud", "title": "Infrastructure Engineer", "company": "SkyGrid", "location": "Karachi", "description": "Build resilient cloud infrastructure, optimize deployments, and support secure platform operations."},
    {"job_id": "job_security_appsec", "domain": "security", "title": "Application Security Engineer", "company": "FortifyPro", "location": "Islamabad", "description": "Identify vulnerabilities, automate security checks, and improve application security across backend systems."},
    {"job_id": "job_security_platform", "domain": "security", "title": "Security Platform Engineer", "company": "FortifyPro", "location": "Remote", "description": "Develop security tooling, manage access controls, and partner with engineers on secure coding practices."},
]

RESUME_TEMPLATES: list[dict[str, Any]] = [
    {"resume_id": "resume_backend", "domain": "backend"},
    {"resume_id": "resume_frontend", "domain": "frontend"},
    {"resume_id": "resume_data", "domain": "data"},
    {"resume_id": "resume_devops", "domain": "devops"},
    {"resume_id": "resume_mobile", "domain": "mobile"},
    {"resume_id": "resume_ml", "domain": "ml"},
    {"resume_id": "resume_qa", "domain": "qa"},
    {"resume_id": "resume_product", "domain": "product"},
    {"resume_id": "resume_cloud", "domain": "cloud"},
    {"resume_id": "resume_security", "domain": "security"},
]


def _normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\r", " ").replace("\n", " ")).strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9#+.-]+", (text or "").lower())


class BM25Scorer:
    def __init__(self, documents: list[str]) -> None:
        self.documents = documents
        self.tokenized = [_tokenize(document) for document in documents]
        self.doc_lengths = [len(tokens) for tokens in self.tokenized]
        self.doc_count = len(self.tokenized)
        self.avg_doc_length = sum(self.doc_lengths) / max(1, self.doc_count)
        self.doc_freq: dict[str, int] = {}
        for tokens in self.tokenized:
            seen = set(tokens)
            for token in seen:
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1

    def score(self, query: str) -> list[float]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return [0.0 for _ in self.documents]

        scores = [0.0 for _ in self.documents]
        for token in set(query_tokens):
            df = self.doc_freq.get(token, 0)
            if df == 0:
                continue
            idf = math.log(1 + (self.doc_count - df + 0.5) / (df + 0.5))
            for idx, tokens in enumerate(self.tokenized):
                freq = tokens.count(token)
                if freq == 0:
                    continue
                denom = freq + 1.5 * (1 - 0.75 + 0.75 * (self.doc_lengths[idx] / self.avg_doc_length))
                scores[idx] += idf * ((freq * (1.5 + 1)) / denom)
        return scores


def _normalize_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi - lo <= 1e-12:
        return [1.0 for _ in values]
    return [(value - lo) / (hi - lo) for value in values]


def build_resume_text(domain: str, variant_index: int = 0) -> str:
    spec = DOMAIN_LIBRARY[domain]
    title = spec["resume_title"]
    location = spec["resume_location"]
    skills = ", ".join(spec["skills"])
    experience_lines = "\n".join(f"- {item}" for item in spec["experience"])
    project_line = spec["project"]
    variant_note = [
        "Led measurable product delivery across backend and analytics workflows.",
        "Shipped reliable features with testing, automation, and stakeholder collaboration.",
    ][variant_index % 2]
    return _normalize(
        f"""
        {title} | {location}
        Contact: candidate@{domain}.example.com | https://{domain}.example.com
        Summary: {spec['summary']} {variant_note}
        Skills: {skills}
        Experience:
        {experience_lines}
        Education:
        - BS Computer Science | {domain.title()} University | 2016-2020
        Projects:
        - {project_line} | Technologies: {skills.split(', ')[0]}, {skills.split(', ')[1]}
        Certifications:
        - {domain.title()} Practitioner Certificate | {domain.title()} Institute | 2022
        Languages:
        - English | Professional
        Achievements:
        - Improved delivery quality and stakeholder alignment.
        - Automated repetitive workflow steps.
        """
    )


def build_job_text(job: dict[str, Any]) -> str:
    spec = DOMAIN_LIBRARY[job["domain"]]
    domain_terms = ", ".join(spec["domain_terms"])
    return _normalize(
        f"""
        {job['title']} at {job['company']}
        Location: {job['location']}
        {job['description']}
        We value experience with {domain_terms} and practical delivery in production systems.
        """
    )


def make_labeled_pairs() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for resume_index, resume in enumerate(RESUME_TEMPLATES):
        resume_text = build_resume_text(resume["domain"], variant_index=resume_index)
        for job in JOB_TEMPLATES:
            relevance = 0
            if job["domain"] == resume["domain"]:
                relevance = 2
            elif job["domain"] in DOMAIN_RELATIONS.get(resume["domain"], set()):
                relevance = 1

            rows.append(
                {
                    "resume_id": resume["resume_id"],
                    "resume_domain": resume["domain"],
                    "resume_text": resume_text,
                    "jd_id": job["job_id"],
                    "jd_domain": job["domain"],
                    "jd_title": job["title"],
                    "jd_text": build_job_text(job),
                    "relevance_score": relevance,
                }
            )
    return pd.DataFrame(rows)


@dataclass
class RankingStageMetrics:
    ndcg_at_5: float
    mrr: float
    precision_at_5: float

    def to_dict(self) -> dict[str, float]:
        return {
            "ndcg_at_5": float(self.ndcg_at_5),
            "mrr": float(self.mrr),
            "precision_at_5": float(self.precision_at_5),
        }


def dcg_at_k(relevances: list[int], k: int = 5) -> float:
    score = 0.0
    for index, relevance in enumerate(relevances[:k], start=1):
        if relevance <= 0:
            continue
        score += (2**relevance - 1) / math.log2(index + 1)
    return score


def ndcg_at_k(relevances: list[int], k: int = 5) -> float:
    actual = dcg_at_k(relevances, k)
    ideal = dcg_at_k(sorted(relevances, reverse=True), k)
    return actual / ideal if ideal > 0 else 0.0


def mrr(relevances: list[int]) -> float:
    for index, relevance in enumerate(relevances, start=1):
        if relevance > 0:
            return 1.0 / index
    return 0.0


def precision_at_k(relevances: list[int], k: int = 5) -> float:
    if k <= 0:
        return 0.0
    hits = sum(1 for relevance in relevances[:k] if relevance > 0)
    return hits / k


def evaluate_rankings(ranked_job_indices: list[list[int]], relevance_matrix: list[list[int]], k: int = 5) -> RankingStageMetrics:
    ndcg_values: list[float] = []
    mrr_values: list[float] = []
    precision_values: list[float] = []
    for ranking, labels in zip(ranked_job_indices, relevance_matrix):
        ordered_labels = [labels[idx] for idx in ranking]
        ndcg_values.append(ndcg_at_k(ordered_labels, k))
        mrr_values.append(mrr(ordered_labels))
        precision_values.append(precision_at_k(ordered_labels, k))
    return RankingStageMetrics(
        ndcg_at_5=float(sum(ndcg_values) / max(1, len(ndcg_values))),
        mrr=float(sum(mrr_values) / max(1, len(mrr_values))),
        precision_at_5=float(sum(precision_values) / max(1, len(precision_values))),
    )


def stage_rankings(
    resume_texts: list[str],
    job_texts: list[str],
    bm25: BM25Scorer,
    bi_encoder,
    cross_encoder=None,
    rerank_top_k: int = 20,
) -> dict[str, list[list[int]]]:
    bm25_rankings: list[list[int]] = []
    bi_rankings: list[list[int]] = []
    cross_rankings: list[list[int]] = []

    query_embeddings = bi_encoder.encode(resume_texts, convert_to_numpy=True, normalize_embeddings=True)
    job_embeddings = bi_encoder.encode(job_texts, convert_to_numpy=True, normalize_embeddings=True)

    for query_index, query_text in enumerate(resume_texts):
        bm25_scores = bm25.score(query_text)
        bm25_ranking = sorted(range(len(job_texts)), key=lambda idx: bm25_scores[idx], reverse=True)
        bm25_rankings.append(bm25_ranking)

        bi_scores = job_embeddings @ query_embeddings[query_index]
        top_ids = bm25_ranking[: min(rerank_top_k, len(job_texts))]
        bi_top = sorted(top_ids, key=lambda idx: float(bi_scores[idx]), reverse=True)
        bi_ranking = bi_top + [idx for idx in bm25_ranking if idx not in bi_top]
        bi_rankings.append(bi_ranking)

        if cross_encoder is not None:
            cross_scores = [float(score) for score in cross_encoder.predict([(query_text, job_texts[idx]) for idx in top_ids])]
            bi_top_scores = [float(bi_scores[idx]) for idx in top_ids]
            cross_scores_norm = _normalize_scores(cross_scores)
            bi_scores_norm = _normalize_scores(bi_top_scores)
            blended_scores = [0.85 * bi_value + 0.15 * cross_value for cross_value, bi_value in zip(cross_scores_norm, bi_scores_norm)]
            cross_top = sorted(zip(top_ids, blended_scores), key=lambda item: item[1], reverse=True)
            cross_top_ids = [idx for idx, _ in cross_top]
            cross_ranking = cross_top_ids + [idx for idx in bi_ranking if idx not in cross_top_ids]
            cross_rankings.append(cross_ranking)

    rankings = {
        "bm25": bm25_rankings,
        "bi_encoder": bi_rankings,
    }
    if cross_rankings:
        rankings["cross_encoder"] = cross_rankings
    return rankings
