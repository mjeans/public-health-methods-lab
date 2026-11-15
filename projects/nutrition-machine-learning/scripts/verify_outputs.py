"""Validate aggregate outputs against a deliberately accepted reference run."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "tests/reference-results.json"
TABLES = ["cv-results", "cv-folds", "test-metrics", "dietary-comparisons", "subgroup-audit",
          "sensitivity", "binned-diagnostics", "model-effects", "cohort-flow", "missingness"]


def snapshot():
    result = {name: pd.read_csv(ROOT / f"outputs/{name}.csv").replace({np.nan: None}).to_dict(orient="records") for name in TABLES}
    result["selection"] = json.loads((ROOT / "outputs/selection.json").read_text())
    return result


def compare(actual, expected, path="root"):
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise AssertionError(f"Schema differs at {path}")
        for key in expected:
            compare(actual[key], expected[key], path + "/" + key)
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            raise AssertionError(f"Row count differs at {path}")
        for i, (a, e) in enumerate(zip(actual, expected)):
            compare(a, e, path + f"/{i}")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not np.isclose(actual, expected, atol=2e-6, rtol=2e-6):
            raise AssertionError(f"Numeric drift at {path}: {actual} != {expected}")
    elif actual != expected:
        raise AssertionError(f"Value differs at {path}: {actual} != {expected}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accept-reference", action="store_true", help="explicitly accept a reviewed execution; never used by CI")
    args = parser.parse_args()
    actual = snapshot()
    if args.accept_reference:
        REFERENCE.write_text(json.dumps(actual, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
        print("Accepted reviewed reference aggregates.")
    else:
        compare(actual, json.loads(REFERENCE.read_text()))
        print("All ten aggregate tables and model selections match the reference within 2e-6 tolerance.")
    # A project may live at the repository root or inside a larger methods lab.
    in_git = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT,
                            text=True, capture_output=True)
    if in_git.returncode == 0 and in_git.stdout.strip() == "true":
        tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
        forbidden = [p for p in tracked if p.startswith(("data/raw/", "data/derived/", "artifacts/")) or p.lower().endswith((".xpt", ".joblib", ".pkl"))]
        if forbidden:
            raise AssertionError(f"Do not publish raw data or fitted model artifacts: {forbidden}")
        print("No raw records or fitted model artifacts tracked.")


if __name__ == "__main__":
    main()
