"""Shared RAG utilities for job-specific generation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

import chromadb

load_dotenv()

DEFAULT_CHROMA_DIR = os.getenv("CHROMA_DB_DIR", os.path.join(os.getcwd(), "chroma_db"))
DEFAULT_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "jobfit_docs")
DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs", "cover_letters")
DEFAULT_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEFAULT_OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "gpt-4o-mini")

_embedding_model: SentenceTransformer | None = None
_chroma_client: chromadb.PersistentClient | None = None
_collection = None
_openrouter_client: OpenAI | None = None


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
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(DEFAULT_EMBEDDING_MODEL)
    return _embedding_model


def get_chroma_collection(collection_name: str = DEFAULT_COLLECTION_NAME, persist_dir: str = DEFAULT_CHROMA_DIR):
    global _chroma_client, _collection
    if _collection is not None:
        return _collection

    _chroma_client = chromadb.PersistentClient(path=persist_dir)
    _collection = _chroma_client.get_or_create_collection(collection_name)
    return _collection


def get_openrouter_client() -> OpenAI:
    global _openrouter_client
    if _openrouter_client is not None:
        return _openrouter_client

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set in environment")

    _openrouter_client = OpenAI(base_url=DEFAULT_OPENROUTER_BASE_URL, api_key=api_key)
    return _openrouter_client


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


def retrieve_relevant_chunks(job_text: str, k: int = 5, where: Optional[Dict[str, Any]] = None) -> List[RetrievedChunk]:
    embedding_model = get_embedding_model()
    query_embedding = embedding_model.encode([job_text], convert_to_numpy=True)[0].tolist()
    return _query_collection_with_embedding(query_embedding, k, where)


async def retrieve_relevant_chunks_async(job_text: str, k: int = 5, where: Optional[Dict[str, Any]] = None) -> List[RetrievedChunk]:
    import asyncio
    embedding_model = get_embedding_model()
    loop = asyncio.get_running_loop()
    embs = await loop.run_in_executor(None, lambda: embedding_model.encode([job_text], convert_to_numpy=True))
    query_embedding = embs[0].tolist()
    return _query_collection_with_embedding(query_embedding, k, where)


def _format_evidence(chunks: Sequence[RetrievedChunk]) -> str:
    pieces: List[str] = []
    for chunk in chunks:
        source_label = chunk.metadata.get("source_id") or chunk.metadata.get("source") or chunk.id
        pieces.append(f"[{source_label}] {chunk.text}")
    return "\n\n".join(pieces)


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
    prompt = build_cover_letter_prompt(
        job_text=job_text,
        resume_summary=resume_summary,
        retrieved_chunks=retrieved,
        company_name=company_name,
        role=role,
        tone=tone,
    )

    client = get_openrouter_client()
    completion = client.chat.completions.create(
        model=DEFAULT_OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": "You write crisp, accurate cover letters and never hallucinate company facts."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=900,
    )

    cover_letter = completion.choices[0].message.content.strip()
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
