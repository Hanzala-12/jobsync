import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from backend.database import get_db, engine
from backend.models import Job, UserPreference, UserProfile
from ingest import chunk_text


MAX_PROFILE_UPLOAD_BYTES = max(1, int(os.getenv("MAX_PROFILE_UPLOAD_BYTES", str(5 * 1024 * 1024))))
ALLOWED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}

router = APIRouter(tags=["Profile"])
_preferences_table_ready = False


def _ensure_user_preferences_table() -> None:
    global _preferences_table_ready
    if _preferences_table_ready:
        return

    try:
        inspector = inspect(engine)
        if not inspector.has_table(UserPreference.__tablename__):
            UserPreference.__table__.create(bind=engine, checkfirst=True)
        _preferences_table_ready = True
    except Exception:
        # keep runtime resilient; callers can still proceed without selected state
        pass


def _get_selected_preference(db: Session) -> UserPreference | None:
    _ensure_user_preferences_table()
    try:
        return db.query(UserPreference).order_by(UserPreference.updated_at.desc(), UserPreference.id.desc()).first()
    except OperationalError:
        _ensure_user_preferences_table()
        try:
            return db.query(UserPreference).order_by(UserPreference.updated_at.desc(), UserPreference.id.desc()).first()
        except Exception:
            return None


def _get_selected_profile_id(db: Session) -> int | None:
    preference = _get_selected_preference(db)
    if preference and preference.selected_profile_id:
        return int(preference.selected_profile_id)
    return None


def _set_selected_profile_id(db: Session, profile_id: int) -> None:
    _ensure_user_preferences_table()
    preference = _get_selected_preference(db)
    if not preference:
        preference = UserPreference(selected_profile_id=profile_id)
        db.add(preference)
    else:
        preference.selected_profile_id = profile_id
    db.commit()


def _clear_selected_profile_if_matches(db: Session, profile_id: int) -> None:
    _ensure_user_preferences_table()
    preference = _get_selected_preference(db)
    if preference and preference.selected_profile_id == profile_id:
        preference.selected_profile_id = None
        db.commit()


async def _validate_resume_upload(upload: UploadFile) -> None:
    filename = (upload.filename or "").lower()
    content_type = (upload.content_type or "").lower()
    suffix = Path(filename).suffix

    if suffix not in ALLOWED_RESUME_EXTENSIONS and content_type not in ALLOWED_RESUME_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Resume must be a PDF or DOCX file")

    content = await upload.read(MAX_PROFILE_UPLOAD_BYTES + 1)
    if len(content) > MAX_PROFILE_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Resume file must be 5 MB or smaller")
    await upload.seek(0)


async def _index_profile_text(profile_text: str) -> None:
    try:
        from core.rag_service import get_chroma_collection, get_embedding_model

        collection = get_chroma_collection()
        if collection is None:
            return

        chunks = chunk_text(profile_text, chunk_size=800, overlap=200)
        if not chunks:
            return

        ids = []
        metadatas = []
        documents = []
        uid = 'user1'
        for i, chunk in enumerate(chunks):
            ids.append(f"profile_{uid}_{i}")
            metadatas.append({"doc_type": "user_profile", "user_id": "current_user", "chunk_index": i})
            documents.append(chunk)

        try:
            embedding_model = get_embedding_model()
        except Exception:
            embedding_model = None

        if embedding_model is not None:
            try:
                import asyncio

                loop = asyncio.get_running_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    lambda: embedding_model.encode(documents, convert_to_numpy=True),
                )
            except RuntimeError:
                embeddings = embedding_model.encode(documents, convert_to_numpy=True)

            embeddings_payload = [embedding.tolist() for embedding in embeddings]
            try:
                collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings_payload)
            except Exception:
                try:
                    collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings_payload)
                except Exception:
                    pass
            return

        try:
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
        except Exception:
            try:
                collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            except Exception:
                pass
    except Exception:
        return


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
    years_experience: Optional[str] = Form(None),
    interests: Optional[str] = Form(None),
    resume: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Save user profile and ingest into ChromaDB as doc_type=user_profile"""
    if resume:
        await _validate_resume_upload(resume)

    profile_text_parts = []
    profile_text_parts.append(f"Skills: {skills}")
    profile_text_parts.append(f"Degree: {degree}")
    years_value = (years_experience or "").strip()
    profile_text_parts.append(f"Years Experience: {years_value}")
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
    await _index_profile_text(profile_text)

    return {"status": "success", "message": "Profile saved", "id": new_profile.id}


@router.get('/profile')
def profile_list(page: int = 1, per_page: int = 10, db: Session = Depends(get_db)):
    # Paginated list of profiles
    try:
        query = db.query(UserProfile).order_by(UserProfile.created_at.desc())
        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        profiles = [{"id": r.id, "skills": r.skills or '', "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to list profiles")

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
        exists = total > 0

    selected_id = _get_selected_profile_id(db)

    return {"exists": exists or total > 0, "profiles": profiles, "selected_profile_id": selected_id, "page": page, "per_page": per_page, "total": total}


@router.post('/profile/select/{profile_id}')
def select_profile(profile_id: int, db: Session = Depends(get_db)):
    try:
        profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        _set_selected_profile_id(db, profile_id)
        return {"status": "success", "selected_profile_id": profile_id}
    except Exception:
        raise


@router.post('/profile/select')
def select_profile_legacy(payload: dict = Body(...), db: Session = Depends(get_db)):
    try:
        pid = int(payload.get('profile_id'))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile_id")

    profile = db.query(UserProfile).filter(UserProfile.id == pid).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    _set_selected_profile_id(db, pid)
    return {"status": "success", "selected_profile_id": pid}


@router.get('/profile/selected')
def get_selected_profile(db: Session = Depends(get_db)):
    selected_id = _get_selected_profile_id(db)
    if not selected_id:
        return {"selected_profile_id": None, "profile": None}

    profile = db.query(UserProfile).filter(UserProfile.id == selected_id).first()
    if not profile:
        return {"selected_profile_id": None, "profile": None}

    return {
        "selected_profile_id": profile.id,
        "profile": {
            "id": profile.id,
            "skills": profile.skills,
            "resume_text": profile.resume_text,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
        },
    }

@router.get('/profile/{profile_id}')
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    try:
        profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"id": profile.id, "skills": profile.skills, "resume_text": profile.resume_text, "created_at": profile.created_at.isoformat() if profile.created_at else None}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to load profile")


@router.delete('/profile/{profile_id}')
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    try:
        profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        db.delete(profile)
        db.commit()
        _clear_selected_profile_if_matches(db, profile_id)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Delete failed")

@router.patch('/profile/{profile_id}')
async def update_profile(profile_id: int,
                         skills: Optional[str] = Form(None),
                         degree: Optional[str] = Form(None),
                         years_experience: Optional[str] = Form(None),
                         interests: Optional[str] = Form(None),
                         resume: Optional[UploadFile] = File(None),
                         db: Session = Depends(get_db)):
    try:
        profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        if resume:
            await _validate_resume_upload(resume)

        # update fields if provided
        parts = []
        if skills is not None:
            profile.skills = skills
            parts.append(f"Skills: {skills}")
        if degree is not None:
            parts.append(f"Degree: {degree}")
        if years_experience is not None:
            parts.append(f"Years Experience: {years_experience.strip()}")
        if interests is not None:
            parts.append(f"Interests: {interests}")

        resume_text = ''
        if resume:
            resume_text = _extract_text_from_upload(resume)
            if resume_text:
                parts.append(f"Resume text: {resume_text}")

        if parts:
            # merge with existing resume_text
            new_text = '\n'.join(parts)
            profile.resume_text = new_text

        db.commit()
        return {"status": "success", "message": "Profile updated"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Update failed")

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

    try:
        res = collection.get(where={"doc_type": "user_profile", "user_id": "current_user"}, limit=10)
        docs = res.get("documents") or []
        flattened = []
        for batch in docs:
            flattened.extend([doc for doc in batch if doc])
        return flattened
    except Exception:
        return []


def _get_selected_profile_text(db: Session):
    selected_id = _get_selected_profile_id(db)

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


@router.post('/match/{job_id}')
def match_job_api(job_id: int, db: Session = Depends(get_db)):
    profile_text = _get_selected_profile_text(db)
    if not profile_text:
        raise HTTPException(status_code=400, detail="No profile found")

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    prompt = f"User profile:\n{profile_text}\n\nJob description:\n{job.description}\n\nRespond as JSON with keys match_score (int 0-100), missing_skills (list), explanation (string)."
    try:
        from core.rag_service import get_openrouter_client
        client = get_openrouter_client()
    except Exception:
        client = None
    if client is None:
        raise HTTPException(status_code=503, detail="LLM provider is unavailable")
    completion = client.chat.completions.create(
        model=os.getenv('OPENROUTER_MODEL', 'gpt-4o-mini'),
        messages=[{"role": "system", "content": "You are a hiring expert."}, {"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=400,
    )
    text = completion.choices[0].message.content
    data = _extract_json(text, {"match_score": 0, "missing_skills": [], "explanation": ""})
    return data


@router.post('/build_resume/{job_id}')
def build_resume_api(job_id: int, db: Session = Depends(get_db)):
    profile_text = _get_selected_profile_text(db)
    if not profile_text:
        raise HTTPException(status_code=400, detail="No profile found")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    prompt = f"Rewrite the user's experience and skills to match the job description. Keep it professional and one page.\n\nUser profile:\n{profile_text}\n\nJob description:\n{job.description}\n\nOutput plain text resume." 
    try:
        from core.rag_service import get_openrouter_client
        client = get_openrouter_client()
    except Exception:
        client = None
    if client is None:
        raise HTTPException(status_code=503, detail="LLM provider is unavailable")
    completion = client.chat.completions.create(
        model=os.getenv('OPENROUTER_MODEL', 'gpt-4o-mini'),
        messages=[{"role": "system", "content": "You are a resume-writing assistant."}, {"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=900,
    )
    resume_text = completion.choices[0].message.content.strip()
    return {"resume_text": resume_text}


@router.post('/cover_letter/{job_id}')
async def cover_letter_api(job_id: int, db: Session = Depends(get_db)):
    profile_text = _get_selected_profile_text(db)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

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
        return {"cover_letter": draft, "source_ids": source_ids}
    except Exception:
        raise HTTPException(status_code=500, detail="Cover letter generation failed")
