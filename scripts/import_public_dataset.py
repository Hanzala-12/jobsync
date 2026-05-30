from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

try:
    from datasets import load_dataset
except ImportError as exc:  # pragma: no cover - dependency is installed in the project env
    raise SystemExit("The 'datasets' package is required. Run 'pip install datasets'.") from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_ID = "Youseff1987/resume-matching-dataset-v2"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "public_datasets"


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "dataset"


def _normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text).strip()


def _score_to_label(value: object) -> int:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0

    if score >= 80:
        return 2
    if score >= 50:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a public Hugging Face resume/job-matching dataset into the local evaluation format.")
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID, help="Hugging Face dataset identifier to import")
    parser.add_argument("--split", default="test", help="Dataset split to download (train/test/validation)")
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on imported rows (0 = all)")
    parser.add_argument("--queries", type=int, default=50, help="How many resumes to use for the candidate-pool benchmark")
    parser.add_argument("--candidates-per-query", type=int, default=20, help="How many candidate jobs to include per query")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for negative sampling")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for normalized CSV and metadata")
    args = parser.parse_args()

    dataset = load_dataset(args.dataset_id, split=args.split)
    df = dataset.to_pandas()
    if args.limit and args.limit > 0:
        df = df.head(args.limit).copy()

    if "resume_id" not in df.columns:
        df["resume_id"] = [f"resume-{idx}" for idx in range(len(df))]
    if "jd_id" not in df.columns:
        df["jd_id"] = [f"job-{idx}" for idx in range(len(df))]

    if "resume_text" not in df.columns:
        resume_source = df["resume"] if "resume" in df.columns else df.get("selfintro", "")
        if "selfintro" in df.columns:
            resume_text = resume_source.fillna("") + "\n\n" + df["selfintro"].fillna("")
        else:
            resume_text = resume_source.fillna("")
        df["resume_text"] = resume_text.map(_normalize_text)

    if "jd_text" not in df.columns:
        if "jobpost" in df.columns:
            df["jd_text"] = df["jobpost"].fillna("").map(_normalize_text)
        elif "job_description" in df.columns:
            df["jd_text"] = df["job_description"].fillna("").map(_normalize_text)
        else:
            raise ValueError("Dataset does not contain a job description column like 'jobpost' or 'job_description'.")

    if "relevance_score" not in df.columns:
        if "total_score" in df.columns:
            df["relevance_score"] = df["total_score"].map(_score_to_label)
        elif "label" in df.columns:
            df["relevance_score"] = df["label"].astype(int)
        else:
            raise ValueError("Dataset does not contain a label column like 'total_score' or 'label'.")

    normalized = pd.DataFrame(
        {
            "resume_id": df["resume_id"].astype(str),
            "resume_text": df["resume_text"].map(_normalize_text),
            "jd_id": df["jd_id"].astype(str),
            "jd_text": df["jd_text"].map(_normalize_text),
            "relevance_score": df["relevance_score"].astype(int),
        }
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(args.dataset_id) + f"-{args.split}"
    output_csv = args.output_dir / f"{slug}.csv"
    metadata_path = args.output_dir / f"{slug}.json"
    benchmark_csv = args.output_dir / f"{slug}-benchmark.csv"

    normalized.to_csv(output_csv, index=False, encoding="utf-8")

    benchmark_rows = []
    query_pool = normalized.head(min(args.queries, len(normalized))).copy().reset_index(drop=True)
    for query_index, query_row in query_pool.iterrows():
        other_rows = normalized.drop(index=query_index).reset_index(drop=True)
        negatives = other_rows.sample(n=min(args.candidates_per_query - 1, len(other_rows)), random_state=args.seed + query_index)
        candidates = pd.concat([pd.DataFrame([query_row]), negatives], ignore_index=True)
        for candidate_index, candidate_row in candidates.iterrows():
            benchmark_rows.append(
                {
                    "resume_id": f"resume-{query_index}",
                    "resume_text": query_row["resume_text"],
                    "jd_id": f"job-{query_index}-{candidate_index}",
                    "jd_text": candidate_row["jd_text"],
                    "relevance_score": 2 if candidate_index == 0 else 0,
                }
            )

    benchmark_df = pd.DataFrame(benchmark_rows)
    benchmark_df.to_csv(benchmark_csv, index=False, encoding="utf-8")
    metadata = {
        "dataset_id": args.dataset_id,
        "split": args.split,
        "rows": int(len(normalized)),
        "benchmark_rows": int(len(benchmark_df)),
        "score_mapping": "0=irrelevant, 1=partial match, 2=strong match",
        "source": "Hugging Face public dataset",
        "csv_path": str(output_csv.relative_to(ROOT)),
        "benchmark_csv_path": str(benchmark_csv.relative_to(ROOT)),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Imported {len(normalized)} rows from {args.dataset_id} ({args.split})")
    print(f"Candidate-pool benchmark rows: {len(benchmark_df)}")
    print(f"CSV: {output_csv}")
    print(f"Benchmark CSV: {benchmark_csv}")
    print(f"Metadata: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
