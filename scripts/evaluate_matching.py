from __future__ import annotations

import argparse
import json
import os
import sys
import re
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import normalize as sklearn_normalize

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.matching_eval_utils import DATA_PATH, BM25Scorer, evaluate_rankings, stage_rankings

DEFAULT_BI_ENCODER_MODEL = os.getenv("BI_ENCODER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEFAULT_CROSS_ENCODER_MODEL = os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
DEFAULT_ENABLE_CROSS_ENCODER = os.getenv("ENABLE_CROSS_ENCODER", "false").lower() in {"1", "true", "yes", "on"}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9#+.-]+", (text or "").lower())


class TfIdfEncoder:
    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")

    def fit(self, texts: list[str]) -> "TfIdfEncoder":
        self.vectorizer.fit(texts)
        return self

    def encode(self, texts, convert_to_numpy: bool = True, normalize_embeddings: bool = True):
        matrix = self.vectorizer.transform(texts)
        if normalize_embeddings:
            matrix = sklearn_normalize(matrix)
        if convert_to_numpy:
            return matrix.toarray()
        return matrix


class TfIdfPairScorer:
    def __init__(self, encoder: TfIdfEncoder) -> None:
        self.encoder = encoder

    def predict(self, pairs):
        scores = []
        for query_text, job_text in pairs:
            query_tokens = set(_tokenize(query_text))
            job_tokens = set(_tokenize(job_text))
            overlap = len(query_tokens & job_tokens) / max(1, len(query_tokens))
            query_vector = self.encoder.encode([query_text], convert_to_numpy=False, normalize_embeddings=True)
            job_vector = self.encoder.encode([job_text], convert_to_numpy=False, normalize_embeddings=True)
            cosine = float(query_vector.multiply(job_vector).sum())
            scores.append(0.75 * cosine + 0.25 * overlap)
        return np.asarray(scores, dtype=float)


class PairwiseLogisticScorer:
    def __init__(self, encoder: TfIdfEncoder) -> None:
        self.encoder = encoder
        self.model = LogisticRegression(max_iter=1000, class_weight="balanced")

    def _features(self, pairs):
        rows = []
        for query_text, job_text in pairs:
            query_tokens = set(_tokenize(query_text))
            job_tokens = set(_tokenize(job_text))
            query_vector = self.encoder.encode([query_text], convert_to_numpy=False, normalize_embeddings=True)
            job_vector = self.encoder.encode([job_text], convert_to_numpy=False, normalize_embeddings=True)
            cosine = float(query_vector.multiply(job_vector).sum())
            overlap = len(query_tokens & job_tokens)
            union = len(query_tokens | job_tokens)
            jaccard = overlap / max(1, union)
            coverage = overlap / max(1, len(query_tokens))
            density = len(job_tokens & query_tokens) / max(1, len(job_tokens))
            rows.append([cosine, jaccard, coverage, density, len(query_tokens), len(job_tokens)])
        return np.asarray(rows, dtype=float)

    def fit(self, dataset: pd.DataFrame) -> "PairwiseLogisticScorer":
        pairs = list(zip(dataset["resume_text"].tolist(), dataset["jd_text"].tolist()))
        labels = (dataset["relevance_score"].astype(int) > 0).astype(int).to_numpy()
        self.model.fit(self._features(pairs), labels)
        return self

    def predict(self, pairs):
        probabilities = self.model.predict_proba(self._features(pairs))
        return probabilities[:, 1]


def _load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}. Run scripts/build_labeled_dataset.py first.")
    df = pd.read_csv(path)
    required = {"resume_id", "resume_text", "jd_id", "jd_text", "relevance_score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    return df


def _build_relevance_matrix(df: pd.DataFrame, resume_ids: list[str], jd_ids: list[str]) -> list[list[int]]:
    pivot = df.pivot_table(index="resume_id", columns="jd_id", values="relevance_score", aggfunc="max", fill_value=0)
    matrix: list[list[int]] = []
    for resume_id in resume_ids:
        row = pivot.loc[resume_id] if resume_id in pivot.index else pd.Series([0] * len(jd_ids), index=jd_ids)
        matrix.append([int(row.get(jd_id, 0)) for jd_id in jd_ids])
    return matrix


def _format_metrics(metrics: dict[str, dict[str, float]]) -> str:
    rows = []
    for stage_name, stage_metrics in metrics.items():
        rows.append(
            {
                "stage": stage_name,
                "NDCG@5": round(stage_metrics["ndcg_at_5"], 4),
                "MRR": round(stage_metrics["mrr"], 4),
                "Precision@5": round(stage_metrics["precision_at_5"], 4),
            }
        )
    return pd.DataFrame(rows).to_string(index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the matching pipeline with IR metrics.")
    parser.add_argument("--dataset", type=Path, default=DATA_PATH, help="CSV file containing labeled resume/JD pairs")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "evaluation" / "metrics.json", help="Where to write metrics JSON")
    parser.add_argument("--top-k", type=int, default=5, dest="top_k", help="Cutoff for evaluation metrics")
    parser.add_argument("--rerank-top-k", type=int, default=20, dest="rerank_top_k", help="How many candidates to rerank at each stage")
    args = parser.parse_args()

    df = _load_dataset(args.dataset)
    resumes = df[["resume_id", "resume_text"]].drop_duplicates("resume_id").sort_values("resume_id")
    jobs = df[["jd_id", "jd_text"]].drop_duplicates("jd_id").sort_values("jd_id")

    resume_ids = resumes["resume_id"].tolist()
    jd_ids = jobs["jd_id"].tolist()
    resume_texts = resumes["resume_text"].tolist()
    job_texts = jobs["jd_text"].tolist()

    relevance_matrix = _build_relevance_matrix(df, resume_ids, jd_ids)

    bm25 = BM25Scorer(job_texts)
    try:
        from sentence_transformers import CrossEncoder, SentenceTransformer  # type: ignore

        bi_encoder = SentenceTransformer(DEFAULT_BI_ENCODER_MODEL)
        cross_encoder_factory = lambda: CrossEncoder(DEFAULT_CROSS_ENCODER_MODEL)
        dense_backend = "sentence-transformers"
    except Exception as exc:
        print(f"Dense embedding backend unavailable, using TF-IDF fallback: {exc}")
        bi_encoder = TfIdfEncoder().fit(resume_texts + job_texts)
        cross_encoder_factory = lambda: PairwiseLogisticScorer(bi_encoder).fit(df)
        dense_backend = "tfidf-fallback"

    cross_encoder = None
    if DEFAULT_ENABLE_CROSS_ENCODER:
        try:
            cross_encoder = cross_encoder_factory()
        except Exception as exc:
            print(f"Cross-encoder unavailable, falling back to baseline-only evaluation: {exc}")

    rankings = stage_rankings(
        resume_texts=resume_texts,
        job_texts=job_texts,
        bm25=bm25,
        bi_encoder=bi_encoder,
        cross_encoder=cross_encoder,
        rerank_top_k=args.rerank_top_k,
    )

    stage_metrics: dict[str, dict[str, float]] = {
        "bm25": evaluate_rankings(rankings["bm25"], relevance_matrix, k=args.top_k).to_dict(),
        "bm25_bi_encoder": evaluate_rankings(rankings["bi_encoder"], relevance_matrix, k=args.top_k).to_dict(),
    }

    final_stage_name = "bm25_bi_encoder"
    if cross_encoder is not None and "cross_encoder" in rankings:
        stage_metrics["bm25_bi_encoder_cross_encoder"] = evaluate_rankings(rankings["cross_encoder"], relevance_matrix, k=args.top_k).to_dict()
        final_stage_name = "bm25_bi_encoder_cross_encoder"

    final_metrics = stage_metrics[final_stage_name]
    payload = {
        "dataset_path": str(args.dataset),
        "num_queries": len(resume_ids),
        "num_pairs": len(df),
        "candidate_pool_size": len(jd_ids),
        "enable_cross_encoder": bool(cross_encoder is not None),
        "dense_backend": dense_backend,
        "pipeline": final_stage_name,
        "stages": stage_metrics,
        "final_metrics": final_metrics,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(_format_metrics(stage_metrics))
    print(f"\nWrote metrics to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
