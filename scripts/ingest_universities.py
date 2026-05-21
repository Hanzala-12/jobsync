from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import Base, SessionLocal, engine
from backend.models import Program, University


API_URL = "http://universities.hipolabs.com/search"
PROGRAM_TEMPLATES = [
    {"name": "MSc Computer Science", "degree_level": "masters", "duration_years": 2, "estimated_tuition_fees": 30000, "currency": "USD", "min_gpa": 3.0},
    {"name": "MSc Data Science", "degree_level": "masters", "duration_years": 2, "estimated_tuition_fees": 32000, "currency": "USD", "min_gpa": 3.1},
    {"name": "MBA", "degree_level": "masters", "duration_years": 2, "estimated_tuition_fees": 28000, "currency": "USD", "min_gpa": 2.8},
]


def _coerce_city(item: Dict[str, Any]) -> str:
    city = item.get("state-province") or item.get("city") or "Unknown"
    return str(city).strip() or "Unknown"


def _coerce_website(item: Dict[str, Any]) -> str:
    pages = item.get("web_pages") or []
    if isinstance(pages, list) and pages:
        return str(pages[0]).strip()
    return ""


def _coerce_ranking(index: int) -> str:
    return str(index + 1)


def _coerce_population(index: int) -> int:
    return 10000 + (index * 750)


def _mock_program_payload(index: int, university: University) -> List[Dict[str, Any]]:
    programs: List[Dict[str, Any]] = []
    for template_index, template in enumerate(PROGRAM_TEMPLATES):
        tuition_offset = (index * 700) + (template_index * 1200)
        programs.append(
            {
                "name": template["name"],
                "degree_level": template["degree_level"],
                "duration_years": template["duration_years"],
                "estimated_tuition_fees": template["estimated_tuition_fees"] + tuition_offset,
                "currency": template["currency"],
                "min_gpa": template["min_gpa"],
                "document_text": (
                    f"University: {university.name}\n"
                    f"Country: {university.country}\n"
                    f"City: {university.city}\n"
                    f"Program: {template['name']}\n"
                    f"Degree level: {template['degree_level']}\n"
                    f"Duration years: {template['duration_years']}\n"
                    f"Estimated tuition fees: {template['estimated_tuition_fees'] + tuition_offset} {template['currency']}\n"
                    f"Minimum GPA: {template['min_gpa']}"
                ),
            }
        )
    return programs


def _upsert_university(db, payload: Dict[str, Any], index: int) -> University:
    website = _coerce_website(payload)
    name = str(payload.get("name") or "").strip()
    country = str(payload.get("country") or "").strip()
    city = _coerce_city(payload)

    university = None
    if website:
        university = db.query(University).filter(University.website == website).first()
    if not university:
        university = (
            db.query(University)
            .filter(University.name == name, University.country == country, University.city == city)
            .first()
        )

    if not university:
        university = University(
            name=name,
            country=country,
            city=city,
            website=website or None,
            ranking=_coerce_ranking(index),
            student_population=_coerce_population(index),
        )
        db.add(university)
        db.flush()
        return university

    university.website = website or university.website
    university.ranking = _coerce_ranking(index)
    university.student_population = _coerce_population(index)
    return university


def _upsert_program(db, university: University, payload: Dict[str, Any]) -> Program:
    program = (
        db.query(Program)
        .filter(
            Program.university_id == university.id,
            Program.name == payload["name"],
            Program.degree_level == payload["degree_level"],
        )
        .first()
    )
    if not program:
        program = Program(university_id=university.id, **{k: payload[k] for k in ["name", "degree_level", "duration_years", "estimated_tuition_fees", "currency", "min_gpa"]})
        db.add(program)
        db.flush()
        return program

    program.duration_years = payload["duration_years"]
    program.estimated_tuition_fees = payload["estimated_tuition_fees"]
    program.currency = payload["currency"]
    program.min_gpa = payload["min_gpa"]
    return program


def _index_program_into_chroma(university: University, program: Program, document_text: str) -> None:
    try:
        from core.rag_service import get_chroma_collection, get_embedding_model

        collection = get_chroma_collection()
        embedding_model = get_embedding_model()
        embedding = embedding_model.encode([document_text], convert_to_numpy=True)[0].tolist()
        doc_id = f"university_{university.id}_program_{program.id}"
        metadata = {
            "doc_type": "university_program",
            "university_id": university.id,
            "program_id": program.id,
            "university_name": university.name,
            "country": university.country,
            "city": university.city,
            "program_name": program.name,
            "degree_level": program.degree_level,
        }
        try:
            collection.add(ids=[doc_id], documents=[document_text], metadatas=[metadata], embeddings=[embedding])
        except Exception:
            collection.upsert(ids=[doc_id], documents=[document_text], metadatas=[metadata], embeddings=[embedding])
    except Exception:
        return


def ingest_universities(limit: int = 25, country: Optional[str] = None) -> None:
    Base.metadata.create_all(bind=engine)
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("Unexpected university API response")

    db = SessionLocal()
    try:
        selected = payload
        if country:
            selected = [item for item in selected if str(item.get("country") or "").strip().lower() == country.strip().lower()]
        selected = selected[: max(1, limit)]
        for index, item in enumerate(selected):
            university = _upsert_university(db, item, index)
            db.flush()

            for program_payload in _mock_program_payload(index, university):
                program = _upsert_program(db, university, program_payload)
                db.flush()
                _index_program_into_chroma(university, program, program_payload["document_text"])

        db.commit()
        print(f"Ingested {len(selected)} universities and their mock programs.")
    finally:
        db.close()


def _run_full_enrichment(limit: int, country: Optional[str]) -> None:
    from scripts.enrich_universities import run_full_enrichment

    results = run_full_enrichment(limit=limit, country=country)
    print("Full enrichment results:")
    for key, value in results.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed universities and optionally run enrichment")
    parser.add_argument("--full", action="store_true", help="Run the full enrichment pipeline after ingesting")
    parser.add_argument("--country", type=str, default=None, help="Limit ingestion to one country")
    parser.add_argument("--limit", type=int, default=25, help="Limit the number of universities to ingest")
    args = parser.parse_args()

    ingest_universities(limit=args.limit, country=args.country)
    if args.full:
        _run_full_enrichment(limit=args.limit, country=args.country)