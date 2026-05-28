from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.models import Application, Job, UserProfile
from sentence_transformers import InputExample, SentenceTransformer, losses


POSITIVE_STATUSES = {"applied", "interviewing", "offered"}
NEGATIVE_STATUSES = {"rejected"}


def _job_text(job: Job) -> str:
    parts = [str(job.title or ""), str(job.company or ""), str(job.location or ""), str(job.description or "")]
    return "\n".join([part.strip() for part in parts if part and part.strip()])


def _build_examples(max_rows: int = 5000) -> List[InputExample]:
    db = SessionLocal()
    try:
        rows = (
            db.query(Application, Job, UserProfile)
            .join(Job, Job.id == Application.job_id)
            .join(UserProfile, UserProfile.user_id == Application.user_id)
            .filter(UserProfile.resume_text.isnot(None), Job.description.isnot(None))
            .order_by(Application.applied_date.desc().nullslast(), Application.id.desc())
            .limit(max_rows)
            .all()
        )

        positives: List[Tuple[str, str]] = []
        negatives: List[Tuple[str, str]] = []

        for application, job, profile in rows:
            resume_text = str(profile.resume_text or "").strip()
            job_text = _job_text(job)
            if not resume_text or not job_text:
                continue
            status = str(application.status or "").strip().lower()
            if status in POSITIVE_STATUSES:
                positives.append((resume_text, job_text))
            elif status in NEGATIVE_STATUSES:
                negatives.append((resume_text, job_text))

        # Add synthetic negatives by cross-user mismatch for contrastive signal.
        random.shuffle(positives)
        for idx in range(min(len(positives), 2000)):
            resume_text, _ = positives[idx]
            _, other_job = positives[(idx + 7) % len(positives)] if positives else ("", "")
            if resume_text and other_job:
                negatives.append((resume_text, other_job))

        examples: List[InputExample] = []
        for resume_text, job_text in positives:
            examples.append(InputExample(texts=[resume_text[:3000], job_text[:3000]], label=1.0))
        for resume_text, job_text in negatives:
            examples.append(InputExample(texts=[resume_text[:3000], job_text[:3000]], label=0.0))

        random.shuffle(examples)
        return examples
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune embedding model on JobSync interaction data")
    parser.add_argument("--base-model", type=str, default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--output-dir", type=str, default="models/finetuned-embeddings")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-rows", type=int, default=5000)
    args = parser.parse_args()

    examples = _build_examples(max_rows=args.max_rows)
    if len(examples) < 20:
        raise RuntimeError("Not enough labeled examples to fine-tune embeddings. Need at least 20 pairs.")

    model = SentenceTransformer(args.base_model)
    train_dataloader = DataLoader(examples, shuffle=True, batch_size=max(2, args.batch_size))
    train_loss = losses.CosineSimilarityLoss(model=model)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    warmup_steps = max(1, int(len(train_dataloader) * max(1, args.epochs) * 0.1))
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=max(1, args.epochs),
        warmup_steps=warmup_steps,
        output_path=str(output_dir),
        show_progress_bar=True,
    )

    manifest = {
        "trained_at": datetime.utcnow().isoformat(),
        "base_model": args.base_model,
        "examples": len(examples),
        "epochs": int(args.epochs),
        "batch_size": int(args.batch_size),
    }
    (output_dir / "training_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved fine-tuned model to {output_dir}")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
