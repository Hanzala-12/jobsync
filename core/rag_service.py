"""Shared RAG utilities for job-specific generation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv

try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except Exception:  # pragma: no cover - optional dependency fallback
    SentenceTransformer = None  # type: ignore[assignment]
    _HAS_SENTENCE_TRANSFORMERS = False

import chromadb
from core.llm_provider import LLMProvider, is_fallback_mode_enabled

load_dotenv()

DEFAULT_CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR") or os.getenv("CHROMA_DB_DIR") or os.path.join(os.getcwd(), "chroma_db")
DEFAULT_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "jobfit_docs")
DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs", "cover_letters")
DEFAULT_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEFAULT_FINETUNED_MODEL_PATH = os.getenv("FINETUNED_EMBEDDING_MODEL_PATH", os.path.join(os.getcwd(), "models", "finetuned-embeddings"))
DEFAULT_OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "gpt-4o-mini")
ENABLE_FINETUNED_EMBEDDINGS = (os.getenv("ENABLE_FINETUNED_EMBEDDINGS", "false").strip().lower() in {"1", "true", "yes", "on"})
ENABLE_HYBRID_SEARCH = (os.getenv("ENABLE_HYBRID_SEARCH", "false").strip().lower() in {"1", "true", "yes", "on"})
HYBRID_VECTOR_WEIGHT = float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.5") or 0.5)
HYBRID_BM25_WEIGHT = float(os.getenv("HYBRID_BM25_WEIGHT", "0.5") or 0.5)
HYBRID_CANDIDATE_LIMIT = max(10, int(os.getenv("HYBRID_CANDIDATE_LIMIT", "200") or 200))

try:
    from rank_bm25 import BM25Okapi
except Exception:  # pragma: no cover - optional dependency fallback
    BM25Okapi = None

_embedding_model: SentenceTransformer | None = None
_chroma_client: chromadb.PersistentClient | None = None
_collection = None
LLM_FALLBACK_MODE = is_fallback_mode_enabled()


@dataclass
class RetrievedChunk:
    id: str
    text: str
    metadata: Dict[str, Any]
    distance: Optional[float] = None


def ensure_output_dir(output_dir: str = DEFAULT_OUTPUT_DIR) -> str:
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if not _HAS_SENTENCE_TRANSFORMERS:
        raise RuntimeError("sentence_transformers is unavailable in this environment")
    if _embedding_model is None:
        if ENABLE_FINETUNED_EMBEDDINGS:
            try:
                _embedding_model = SentenceTransformer(DEFAULT_FINETUNED_MODEL_PATH)
                return _embedding_model
            except Exception:
                # Fall back to the previously working baseline model.
                _embedding_model = SentenceTransformer(DEFAULT_EMBEDDING_MODEL)
        else:
            _embedding_model = SentenceTransformer(DEFAULT_EMBEDDING_MODEL)
    return _embedding_model


def get_chroma_collection(collection_name: str = DEFAULT_COLLECTION_NAME, persist_dir: str = DEFAULT_CHROMA_DIR):
    global _chroma_client, _collection
    if _collection is not None:
        return _collection

    _chroma_client = chromadb.PersistentClient(path=persist_dir)
    _collection = _chroma_client.get_or_create_collection(collection_name)
    return _collection


def get_openrouter_client():
    provider = LLMProvider()
    if not provider.backends:
        raise RuntimeError("No LLM API key is set in environment")
    backend = provider.backends[0]
    if backend.provider not in {"openrouter", "openai"}:
        raise RuntimeError("No OpenAI-compatible LLM API key is set in environment")

    from openai import OpenAI

    base_url = backend.base_url or (DEFAULT_OPENROUTER_BASE_URL if backend.provider == "openrouter" else os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    return OpenAI(base_url=base_url, api_key=backend.api_key)


def _query_collection_with_embedding(query_embedding: List[float], k: int, where: Optional[Dict[str, Any]]) -> List[RetrievedChunk]:
    collection = get_chroma_collection()
    query_kwargs: Dict[str, Any] = {"query_embeddings": [query_embedding], "n_results": k}
    if where:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)
    ids = (results.get("ids") or [[]])[0]
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    chunks: List[RetrievedChunk] = []
    for idx, doc, metadata, distance in zip(ids, documents, metadatas, distances):
        chunks.append(
            RetrievedChunk(
                id=str(idx),
                text=str(doc or ""),
                metadata=dict(metadata or {}),
                distance=float(distance) if distance is not None else None,
            )
        )
    return chunks


def _normalize_scores(values: List[float]) -> List[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi - lo <= 1e-12:
        return [1.0 for _ in values]
    return [(value - lo) / (hi - lo) for value in values]


def _hybrid_fusion(query_text: str, query_embedding: List[float], k: int, where: Optional[Dict[str, Any]]) -> List[RetrievedChunk]:
    if BM25Okapi is None:
        return _query_collection_with_embedding(query_embedding, k, where)

    candidate_size = max(k * 4, HYBRID_CANDIDATE_LIMIT)

    vector_chunks = _query_collection_with_embedding(query_embedding, candidate_size, where)
    if not vector_chunks:
        return []

    # BM25 scores are computed on the same candidate set to keep the operation lightweight.
    docs = [chunk.text for chunk in vector_chunks]
    tokenized_docs = [doc.lower().split() for doc in docs]
    bm25 = BM25Okapi(tokenized_docs)
    query_tokens = query_text.lower().split()
    bm25_scores_raw = [float(value) for value in bm25.get_scores(query_tokens)]

    vector_scores_raw: List[float] = []
    for chunk in vector_chunks:
        distance = float(chunk.distance or 0.0)
        vector_scores_raw.append(1.0 / (1.0 + max(distance, 0.0)))

    vector_scores = _normalize_scores(vector_scores_raw)
    bm25_scores = _normalize_scores(bm25_scores_raw)

    fused: List[Tuple[float, RetrievedChunk]] = []
    for idx, chunk in enumerate(vector_chunks):
        score = (HYBRID_VECTOR_WEIGHT * vector_scores[idx]) + (HYBRID_BM25_WEIGHT * bm25_scores[idx])
        fused.append((score, chunk))

    fused.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in fused[:k]]


def retrieve_relevant_chunks(job_text: str, k: int = 5, where: Optional[Dict[str, Any]] = None, use_hybrid: bool = True) -> List[RetrievedChunk]:
    embedding_model = get_embedding_model()
    query_embedding = embedding_model.encode([job_text], convert_to_numpy=True)[0].tolist()
    if ENABLE_HYBRID_SEARCH and use_hybrid:
        try:
            return _hybrid_fusion(job_text, query_embedding, k, where)
        except Exception:
            return _query_collection_with_embedding(query_embedding, k, where)
    return _query_collection_with_embedding(query_embedding, k, where)


async def retrieve_relevant_chunks_async(job_text: str, k: int = 5, where: Optional[Dict[str, Any]] = None, use_hybrid: bool = True) -> List[RetrievedChunk]:
    import asyncio
    embedding_model = get_embedding_model()
    loop = asyncio.get_running_loop()
    embs = await loop.run_in_executor(None, lambda: embedding_model.encode([job_text], convert_to_numpy=True))
    query_embedding = embs[0].tolist()
    if ENABLE_HYBRID_SEARCH and use_hybrid:
        try:
            return _hybrid_fusion(job_text, query_embedding, k, where)
        except Exception:
            return _query_collection_with_embedding(query_embedding, k, where)
    return _query_collection_with_embedding(query_embedding, k, where)


def _format_evidence(chunks: Sequence[RetrievedChunk]) -> str:
    pieces: List[str] = []
    for chunk in chunks:
        source_label = chunk.metadata.get("source_id") or chunk.metadata.get("source") or chunk.id
        pieces.append(f"[{source_label}] {chunk.text}")
    return "\n\n".join(pieces)


def _fallback_cover_letter(
    job_text: str,
    resume_summary: str,
    retrieved: Sequence[RetrievedChunk],
    company_name: str,
    role: str,
    tone: str,
) -> Tuple[str, List[str], List[RetrievedChunk]]:
    source_ids = [chunk.metadata.get("source_id") or chunk.metadata.get("source") or chunk.id for chunk in retrieved]
    source_ids = [str(item) for item in source_ids if item]
    company_line = f" at {company_name}" if company_name else ""
    role_line = f" for the {role} role" if role else ""
    evidence = _format_evidence(retrieved[:3])
    cover_letter = (
        f"Dear Hiring Manager,{os.linesep}{os.linesep}"
        f"I am writing to express my interest{role_line}{company_line}. "
        f"This fallback draft is generated without an LLM so the application flow remains testable.{os.linesep}{os.linesep}"
        f"Tone: {tone}{os.linesep}{os.linesep}"
        f"Resume summary:{os.linesep}{resume_summary}{os.linesep}{os.linesep}"
        f"Job context:{os.linesep}{job_text[:1200]}{os.linesep}{os.linesep}"
        f"Relevant evidence:{os.linesep}{evidence or 'No retrieved evidence available.'}{os.linesep}{os.linesep}"
        f"Thank you for considering my application. I would welcome the opportunity to discuss how my background aligns with your needs.{os.linesep}"
        f"Sincerely,{os.linesep}Applicant"
    )
    return cover_letter, source_ids, list(retrieved)


def build_cover_letter_prompt(
    job_text: str,
    resume_summary: str,
    retrieved_chunks: Sequence[RetrievedChunk],
    company_name: str = "",
    role: str = "",
    tone: str = "professional",
) -> str:
    evidence = _format_evidence(retrieved_chunks)
    company_line = f"Company: {company_name}\n" if company_name else ""
    role_line = f"Role: {role}\n" if role else ""

    return f"""You are a professional cover-letter writer for job applications in Pakistan.
Write a tailored cover letter using the provided context only. Do not invent facts.

Tone: {tone}
{company_line}{role_line}
Job description:
{job_text}

Candidate resume summary:
{resume_summary}

Relevant retrieved passages:
{evidence}

Requirements:
- Write 250-350 words.
- Keep it specific and concise.
- If you use a fact from retrieved passages, include the source id in brackets.
- End with a short call to action.
"""


def _generate_cover_letter_with_prompt(
    retrieved: List[RetrievedChunk],
    job_text: str,
    resume_summary: str,
    company_name: str,
    role: str,
    tone: str,
) -> Tuple[str, List[str], List[RetrievedChunk]]:
    if LLM_FALLBACK_MODE:
        return _fallback_cover_letter(job_text, resume_summary, retrieved, company_name, role, tone)

    prompt = build_cover_letter_prompt(
        job_text=job_text,
        resume_summary=resume_summary,
        retrieved_chunks=retrieved,
        company_name=company_name,
        role=role,
        tone=tone,
    )

    llm = LLMProvider()
    response = llm.ask(
        "You write crisp, accurate cover letters and never hallucinate company facts.",
        prompt,
        temperature=0.6,
    )
    if response.startswith("AI error:"):
        return _fallback_cover_letter(job_text, resume_summary, retrieved, company_name, role, tone)

    cover_letter = response.strip()
    source_ids = [chunk.metadata.get("source_id") or chunk.metadata.get("source") or chunk.id for chunk in retrieved]
    source_ids = [str(item) for item in source_ids if item]
    return cover_letter, source_ids, retrieved


def generate_cover_letter_with_rag(
    job_text: str,
    resume_summary: str,
    *,
    company_name: str = "",
    role: str = "",
    tone: str = "professional",
    top_k: int = 5,
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[str], List[RetrievedChunk]]:
    retrieved = retrieve_relevant_chunks(job_text, k=top_k, where=metadata_filter)
    return _generate_cover_letter_with_prompt(retrieved, job_text, resume_summary, company_name, role, tone)


async def generate_cover_letter_with_rag_async(
    job_text: str,
    resume_summary: str,
    *,
    company_name: str = "",
    role: str = "",
    tone: str = "professional",
    top_k: int = 5,
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[str], List[RetrievedChunk]]:
    retrieved = await retrieve_relevant_chunks_async(job_text, k=top_k, where=metadata_filter)
    return _generate_cover_letter_with_prompt(retrieved, job_text, resume_summary, company_name, role, tone)


def save_cover_letter_artifacts(
    job_id: Optional[int],
    cover_letter: str,
    source_ids: Sequence[str],
    retrieved_chunks: Sequence[RetrievedChunk],
    *,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    file_prefix: str = "cover_letter",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    ensure_output_dir(output_dir)

    suffix = str(job_id) if job_id is not None else "unscoped"
    txt_path = os.path.join(output_dir, f"{file_prefix}_{suffix}.txt")
    json_path = os.path.join(output_dir, f"{file_prefix}_{suffix}.json")

    with open(txt_path, "w", encoding="utf-8") as file:
        file.write(cover_letter)

    payload = {
        "job_id": job_id,
        "source_ids": list(source_ids),
        "retrieved_chunks": [
            {
                "id": chunk.id,
                "text": chunk.text,
                "metadata": chunk.metadata,
                "distance": chunk.distance,
            }
            for chunk in retrieved_chunks
        ],
    }
    if metadata:
        payload.update(metadata)

    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return {"text_path": txt_path, "json_path": json_path}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _student_profile_summary(student_profile: Dict[str, Any]) -> str:
    preferred_countries = student_profile.get("preferred_countries") or []
    preferred_text = ", ".join(str(item) for item in preferred_countries if item)
    return (
        f"GPA: {student_profile.get('gpa', 'N/A')}\n"
        f"GRE: {student_profile.get('gre_score', 'N/A')}\n"
        f"TOEFL: {student_profile.get('toefl_score', 'N/A')}\n"
        f"Budget per year: {student_profile.get('budget_per_year', 'N/A')}\n"
        f"Preferred countries: {preferred_text or 'Any'}\n"
        f"Intended major: {student_profile.get('intended_major', '')}\n"
        f"Degree level: {student_profile.get('degree_level', '')}"
    )


def _program_summary(program: Dict[str, Any], university: Dict[str, Any]) -> str:
    return (
        f"University: {university.get('name', '')}\n"
        f"Country: {university.get('country', '')}\n"
        f"City: {university.get('city', '')}\n"
        f"Program: {program.get('name', '')}\n"
        f"Degree level: {program.get('degree_level', '')}\n"
        f"Duration years: {program.get('duration_years', '')}\n"
        f"Estimated tuition fees: {program.get('estimated_tuition_fees', '')} {program.get('currency', '')}\n"
        f"Minimum GPA: {program.get('min_gpa', 'N/A')}"
    )


def build_match_analysis_prompt(
    student_profile: Dict[str, Any],
    program: Dict[str, Any],
    university: Dict[str, Any],
    retrieved_chunks: Sequence[RetrievedChunk],
) -> str:
    evidence = _format_evidence(retrieved_chunks)
    return f"""You are an admissions advisor helping a student compare a university program to their profile.
Return STRICT JSON with exactly these keys:
{{"match_score": 0-100 integer, "explanation": "brief explanation"}}

Student profile:
{_student_profile_summary(student_profile)}

Program details:
{_program_summary(program, university)}

Relevant retrieved evidence:
{evidence or 'No retrieved evidence available.'}

Instructions:
- Give a realistic score from 0 to 100.
- Explain the fit in 2-4 concise sentences.
- Mention admissions constraints, budget fit, academic fit, and country preference when relevant.
- Do not add markdown or extra keys.
"""


def _heuristic_match_analysis(student_profile: Dict[str, Any], program: Dict[str, Any], university: Dict[str, Any]) -> Tuple[int, str]:
    score = 50
    explanations: List[str] = []

    student_gpa = float(student_profile.get("gpa") or 0)
    min_gpa = float(program.get("min_gpa") or 0)
    budget = int(student_profile.get("budget_per_year") or 0)
    tuition = int(program.get("estimated_tuition_fees") or 0)
    preferred_countries = {str(item).strip().lower() for item in (student_profile.get("preferred_countries") or []) if str(item).strip()}
    country = str(university.get("country") or "").strip().lower()
    degree_level = str(student_profile.get("degree_level") or "").strip().lower()
    program_level = str(program.get("degree_level") or "").strip().lower()
    intended_major = str(student_profile.get("intended_major") or "").strip().lower()
    program_name = str(program.get("name") or "").strip().lower()

    if min_gpa:
        if student_gpa >= min_gpa:
            score += 18
            explanations.append("The GPA requirement looks achievable.")
        else:
            gap = min_gpa - student_gpa
            score -= min(20, max(5, int(gap * 20)))
            explanations.append("The GPA is below the stated minimum, so admission may be challenging.")

    if tuition and budget:
        if budget >= tuition:
            score += 15
            explanations.append("The estimated tuition fits within the yearly budget.")
        else:
            score -= 18
            explanations.append("The tuition appears above the stated budget.")

    if country and country in preferred_countries:
        score += 10
        explanations.append("The university is in a preferred country.")

    if degree_level and program_level and degree_level == program_level:
        score += 8
        explanations.append("The degree level matches the student’s goal.")

    major_tokens = {token for token in intended_major.split() if len(token) > 2}
    program_tokens = {token for token in program_name.split() if len(token) > 2}
    if major_tokens.intersection(program_tokens):
        score += 9
        explanations.append("The program title aligns with the intended major.")

    score = max(0, min(100, score))
    if not explanations:
        explanations.append("The match is moderate based on the available program and profile details.")

    return score, " ".join(explanations)


def _parse_match_payload(content: str) -> Dict[str, Any]:
    raw = (content or "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(raw[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    return {}


def _generate_match_analysis_with_prompt(
    retrieved: List[RetrievedChunk],
    student_profile: Dict[str, Any],
    program: Dict[str, Any],
    university: Dict[str, Any],
) -> Tuple[int, str, List[str], List[RetrievedChunk]]:
    if LLM_FALLBACK_MODE:
        score, explanation = _heuristic_match_analysis(student_profile, program, university)
        source_ids = [str(chunk.metadata.get("source_id") or chunk.metadata.get("source") or chunk.id) for chunk in retrieved]
        source_ids = [item for item in source_ids if item]
        return score, explanation, source_ids, retrieved

    prompt = build_match_analysis_prompt(student_profile, program, university, retrieved)

    try:
        content = LLMProvider().ask(
            "You evaluate university-program fit and always return strict JSON.",
            prompt,
            temperature=0.2,
        )
        if content.startswith("AI error:"):
            raise RuntimeError(content)
        parsed = _parse_match_payload(content)
        score = _safe_int(parsed.get("match_score"), 0)
        explanation = str(parsed.get("explanation") or "").strip()
        if not explanation:
            score, explanation = _heuristic_match_analysis(student_profile, program, university)
        score = max(0, min(100, score))
    except Exception:
        score, explanation = _heuristic_match_analysis(student_profile, program, university)

    source_ids = [str(chunk.metadata.get("source_id") or chunk.metadata.get("source") or chunk.id) for chunk in retrieved]
    source_ids = [item for item in source_ids if item]
    return score, explanation, source_ids, retrieved


def generate_match_analysis(
    student_profile: Dict[str, Any],
    program: Dict[str, Any],
    university: Dict[str, Any],
    *,
    top_k: int = 5,
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> Tuple[int, str, List[str], List[RetrievedChunk]]:
    query_text = "\n".join(
        [
            _student_profile_summary(student_profile),
            _program_summary(program, university),
        ]
    )
    try:
        retrieved = retrieve_relevant_chunks(query_text, k=top_k, where=metadata_filter)
    except Exception:
        retrieved = []
    return _generate_match_analysis_with_prompt(retrieved, student_profile, program, university)


async def generate_match_analysis_async(
    student_profile: Dict[str, Any],
    program: Dict[str, Any],
    university: Dict[str, Any],
    *,
    top_k: int = 5,
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> Tuple[int, str, List[str], List[RetrievedChunk]]:
    query_text = "\n".join([
        _student_profile_summary(student_profile),
        _program_summary(program, university),
    ])
    try:
        retrieved = await retrieve_relevant_chunks_async(query_text, k=top_k, where=metadata_filter)
    except Exception:
        retrieved = []
    return _generate_match_analysis_with_prompt(retrieved, student_profile, program, university)
