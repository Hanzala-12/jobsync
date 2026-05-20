from fastapi import APIRouter, UploadFile, File, Form, Depends, Body
from fastapi.responses import JSONResponse
from typing import Optional
import os
import tempfile
import json

from ingest import chunk_text
from ingest import chunk_text

from backend.database import get_db
from sqlalchemy.orm import Session
import pathlib
import datetime
from backend.models import Job, UserProfile

router = APIRouter(tags=["Profile"])


def _extract_text_from_upload(upload: UploadFile) -> str:
    fname = upload.filename.lower() if upload and upload.filename else ''
    data = b''
    try:
        data = upload.file.read()
    finally:
        try:
            upload.file.seek(0)
        except Exception:
            pass

    if fname.endswith('.pdf'):
        try:
            from pypdf import PdfReader
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(data)
                tmp.flush()
                tmp_path = tmp.name
            reader = PdfReader(tmp_path)
            pages = []
            for p in reader.pages:
                try:
                    pages.append(p.extract_text() or '')
                except Exception:
                    continue
            os.unlink(tmp_path)
            return '\n'.join(pages)
        except Exception:
            return ''

    if fname.endswith('.docx'):
        try:
            import docx2txt
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
                tmp.write(data)
                tmp.flush()
                tmp_path = tmp.name
            text = docx2txt.process(tmp_path) or ''
            os.unlink(tmp_path)
            return text
        except Exception:
            return ''

    # fallback: treat as plain text
    try:
        return data.decode('utf-8', errors='ignore')
    except Exception:
        return ''


@router.post('/profile')
async def upload_profile(
    skills: str = Form(...),
    degree: str = Form(...),
    years_experience: int = Form(...),
    interests: Optional[str] = Form(None),
    resume: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Save user profile and ingest into ChromaDB as doc_type=user_profile"""
    profile_text_parts = []
    profile_text_parts.append(f"Skills: {skills}")
    profile_text_parts.append(f"Degree: {degree}")
    profile_text_parts.append(f"Years Experience: {years_experience}")
    if interests:
        profile_text_parts.append(f"Interests: {interests}")

    resume_text = ''
    if resume:
        resume_text = _extract_text_from_upload(resume)
        if resume_text:
            profile_text_parts.append(f"Resume text: {resume_text}")

    profile_text = '\n'.join(profile_text_parts)

    # Create a new profile record so users can have multiple profiles
    new_profile = UserProfile(resume_text=profile_text, skills=skills)
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    # Chunk and embed via existing ingestion utilities
    docs = []
    uid = 'user1'
    chunks = chunk_text(profile_text, chunk_size=800, overlap=200)
    ids, metadatas, documents, embeddings = [], [], [], []
    # lazy import embedding model to avoid heavy imports at app startup
    try:
        from core.rag_service import get_embedding_model
        embedding_model = get_embedding_model()
    except Exception:
        from sentence_transformers import SentenceTransformer
        embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    for i, c in enumerate(chunks):
        doc_id = f"profile_{uid}_{i}"
        ids.append(doc_id)
        metadatas.append({"doc_type": "user_profile", "user_id": "current_user", "chunk_index": i})
        documents.append(c)

    if documents:
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            embs = await loop.run_in_executor(None, lambda: embedding_model.encode(documents, convert_to_numpy=True))
        except RuntimeError:
            embs = embedding_model.encode(documents, convert_to_numpy=True)
        embeddings = [e.tolist() for e in embs]
        # lazy get chroma collection
        try:
            from core.rag_service import get_chroma_collection
            collection = get_chroma_collection()
        except Exception:
            collection = None
        try:
            if collection is not None:
                collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
        except Exception:
            try:
                if collection is not None:
                    collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
            except Exception:
                pass

    return JSONResponse({"status": "success", "message": "Profile saved", "id": new_profile.id})


@router.get('/profile')
def profile_exists(db: Session = Depends(get_db)):
    # Return saved profiles and whether a profile is selected/exists.
    profiles = []
    try:
        rows = db.query(UserProfile).order_by(UserProfile.created_at.desc()).limit(20).all()
        for r in rows:
            profiles.append({"id": r.id, "skills": r.skills or '', "created_at": r.created_at.isoformat() if r.created_at else None})
    except Exception:
        profiles = []

    # try chroma as a best-effort exists flag
    try:
        from core.rag_service import get_chroma_collection
        collection = get_chroma_collection()
    except Exception:
        collection = None

    exists = False
    try:
        if collection is not None:
            res = collection.get(where={"doc_type": "user_profile", "user_id": "current_user"}, limit=1)
            docs = (res.get('documents') or [])
            exists = len(docs) > 0
    except Exception:
        exists = len(profiles) > 0

    # read selected profile id if set
    selected_id = None
    try:
        sel_file = pathlib.Path(os.path.dirname(__file__)) / '..' / 'selected_profile.json'
        sel_file = sel_file.resolve()
        if sel_file.exists():
            data = json.loads(sel_file.read_text(encoding='utf-8'))
            selected_id = data.get('selected_profile_id')
    except Exception:
        selected_id = None

    return {"exists": exists or len(profiles) > 0, "profiles": profiles, "selected_profile_id": selected_id}


@router.post('/profile/select')
def select_profile(payload: dict = Body(...)):
    try:
        pid = int(payload.get('profile_id'))
    except Exception:
        return JSONResponse({"status": "error", "message": "invalid profile_id"}, status_code=400)

    try:
        sel_path = pathlib.Path(os.path.dirname(__file__)) / '..' / 'selected_profile.json'
        sel_path = sel_path.resolve()
        sel_path.write_text(json.dumps({"selected_profile_id": pid, "updated_at": datetime.datetime.utcnow().isoformat()}), encoding='utf-8')
        return JSONResponse({"status": "success", "selected_profile_id": pid})
    except Exception:
        return JSONResponse({"status": "error", "message": "could not persist selection"}, status_code=500)


def _extract_json(raw: str, fallback):
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except Exception:
        pass
    # try to extract JSON blob
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end+1])
        except Exception:
            pass
    return fallback


def _get_profile_docs() -> list[str]:
    try:
        from core.rag_service import get_chroma_collection
        collection = get_chroma_collection()
    except Exception:
        return []


def _get_selected_profile_text(db: Session):
    # Try to use selected profile id persisted on disk, else fall back to first DB profile or chroma docs
    selected_id = None
    try:
        sel_file = pathlib.Path(os.path.dirname(__file__)) / '..' / 'selected_profile.json'
        sel_file = sel_file.resolve()
        if sel_file.exists():
            data = json.loads(sel_file.read_text(encoding='utf-8'))
            selected_id = int(data.get('selected_profile_id'))
    except Exception:
        selected_id = None

    profile_text = ''
    try:
        if selected_id:
            profile = db.query(UserProfile).filter(UserProfile.id == selected_id).first()
        else:
            profile = db.query(UserProfile).first()
        if profile and profile.resume_text:
            profile_text = profile.resume_text
        else:
            # fallback to chroma docs
            profile_text = '\n'.join(_get_profile_docs())
    except Exception:
        profile_text = '\n'.join(_get_profile_docs())

    return profile_text

    try:
        res = collection.get(where={"doc_type": "user_profile", "user_id": "current_user"}, limit=10)
        docs = res.get("documents") or []
        flattened = []
        for batch in docs:
            flattened.extend([doc for doc in batch if doc])
        return flattened
    except Exception:
        return []


@router.post('/match/{job_id}')
def match_job_api(job_id: int, db: Session = Depends(get_db)):
    profile_text = _get_selected_profile_text(db)
    if not profile_text:
        return JSONResponse({"error": "No profile found"}, status_code=400)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    prompt = f"User profile:\n{profile_text}\n\nJob description:\n{job.description}\n\nRespond as JSON with keys match_score (int 0-100), missing_skills (list), explanation (string)."
    try:
        from core.rag_service import get_openrouter_client
        client = get_openrouter_client()
    except Exception:
        client = None
    completion = client.chat.completions.create(
        model=os.getenv('OPENROUTER_MODEL', 'gpt-4o-mini'),
        messages=[{"role": "system", "content": "You are a hiring expert."}, {"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=400,
    )
    text = completion.choices[0].message.content
    data = _extract_json(text, {"match_score": 0, "missing_skills": [], "explanation": ""})
    return JSONResponse(data)


@router.post('/build_resume/{job_id}')
def build_resume_api(job_id: int, db: Session = Depends(get_db)):
    profile_text = _get_selected_profile_text(db)
    if not profile_text:
        return JSONResponse({"error": "No profile found"}, status_code=400)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    prompt = f"Rewrite the user's experience and skills to match the job description. Keep it professional and one page.\n\nUser profile:\n{profile_text}\n\nJob description:\n{job.description}\n\nOutput plain text resume." 
    try:
        from core.rag_service import get_openrouter_client
        client = get_openrouter_client()
    except Exception:
        client = None
    completion = client.chat.completions.create(
        model=os.getenv('OPENROUTER_MODEL', 'gpt-4o-mini'),
        messages=[{"role": "system", "content": "You are a resume-writing assistant."}, {"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=900,
    )
    resume_text = completion.choices[0].message.content.strip()
    return JSONResponse({"resume_text": resume_text})


@router.post('/cover_letter/{job_id}')
async def cover_letter_api(job_id: int, db: Session = Depends(get_db)):
    profile_text = _get_selected_profile_text(db)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    # Use existing generate_cover_letter_with_rag but pass profile_text as resume_summary
    try:
        from core.rag_service import generate_cover_letter_with_rag_async
        draft, source_ids, retrieved = await generate_cover_letter_with_rag_async(
            job.description or '',
            profile_text,
            company_name=job.company or '',
            role=job.title or '',
            tone='professional',
            top_k=5,
            metadata_filter={'company': job.company} if job.company else None,
        )
        return JSONResponse({"cover_letter": draft, "source_ids": source_ids})
    except Exception:
        return JSONResponse({"error": "Cover letter generation failed"}, status_code=500)
