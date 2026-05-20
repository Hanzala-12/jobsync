from __future__ import annotations

from core.rag_service import (
    build_cover_letter_prompt,
    generate_cover_letter_with_rag,
    retrieve_relevant_chunks,
    save_cover_letter_artifacts,
)


def retrieve(job_text, k=5, where=None):
    chunks = retrieve_relevant_chunks(job_text, k=k, where=where)
    return [
        {
            "id": chunk.id,
            "text": chunk.text,
            "metadata": chunk.metadata,
            "distance": chunk.distance,
        }
        for chunk in chunks
    ]


def build_prompt(job_text, resume_summary, retrieved):
    chunks = [
        type("Chunk", (), {"id": item["id"], "text": item["text"], "metadata": item["metadata"]})
        for item in retrieved
    ]
    return build_cover_letter_prompt(job_text, resume_summary, chunks)


def generate_cover_letter(job_text, resume_summary, k=5, where=None):
    cover_letter, source_ids, retrieved_chunks = generate_cover_letter_with_rag(
        job_text,
        resume_summary,
        top_k=k,
        metadata_filter=where,
    )
    return cover_letter, source_ids, retrieved_chunks


if __name__ == '__main__':
    sample_job = "We are hiring a backend Python developer with experience in APIs, PostgreSQL, and AWS. Remote/Hybrid."
    sample_resume = "Software engineer with 4 years experience building web services in Python, PostgreSQL, and AWS. Focus on APIs and data pipelines."
    try:
        cover, ids, retrieved = generate_cover_letter(sample_job, sample_resume)
        save_cover_letter_artifacts(None, cover, ids, retrieved, metadata={"job_text": sample_job, "resume_summary": sample_resume})
        print('\n=== Cover Letter ===\n')
        print(cover)
        print('\nRetrieved IDs:', ids)
    except Exception as e:
        print('Error:', e)
