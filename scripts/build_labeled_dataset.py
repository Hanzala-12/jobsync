from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.matching_eval_utils import DATA_PATH, make_labeled_pairs


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a labeled resume-job matching dataset.")
    parser.add_argument("--output", type=Path, default=DATA_PATH, help="Output CSV path")
    args = parser.parse_args()

    df = make_labeled_pairs()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding="utf-8")
    print(f"Wrote {len(df)} labeled pairs to {args.output}")
    print(df["relevance_score"].value_counts().sort_index().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
