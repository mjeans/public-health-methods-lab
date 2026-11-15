"""Reproduce the frozen development-to-test benchmark from public CDC files."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import joblib
import pandas as pd
from threadpoolctl import threadpool_limits
from nutrition_ml.data import fetch_all, build_cohort
from nutrition_ml.modeling import development_fit, features
from nutrition_ml.evaluation import evaluate, binned_diagnostics, ale_curve
from nutrition_ml.reporting import figures, write_report


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-only", action="store_true")
    args = parser.parse_args()
    for folder in ["outputs", "assets", "artifacts"]:
        (ROOT / folder).mkdir(exist_ok=True)
    provenance = fetch_all(ROOT)
    write_json(ROOT / "data/source-manifest.json", provenance)
    if args.download_only:
        return
    plan = json.loads((ROOT / "config/analysis-plan.json").read_text())
    dev, flow_dev, missing_dev = build_cohort(ROOT, plan["development_cycle"])
    with threadpool_limits(limits=1):
        models, selection, cv, folds = development_fit(dev, plan)
        # Persist selection before building or evaluating the held-out cohort.
        write_json(ROOT / "outputs/selection.json", selection)
        cv.to_csv(ROOT / "outputs/cv-results.csv", index=False, float_format="%.8f")
        folds.to_csv(ROOT / "outputs/cv-folds.csv", index=False)
        joblib.dump(models, ROOT / "artifacts/development-models.joblib")
        test, flow_test, missing_test = build_cohort(ROOT, plan["test_cycle"])
        if set(dev.SEQN) & set(test.SEQN):
            raise ValueError("Participant identifiers overlap development and test cycles")
        predictions = {key: model.predict(test[features(plan, key.split(":")[0])]) for key, model in models.items()}
        scores, comparisons, groups, sensitivity = evaluate(test, predictions, selection, plan)
        champion = selection["champions"]["diet"]
        diagnostics = binned_diagnostics(test, predictions[champion])
        cols = features(plan, champion.split(":")[0])
        effects = pd.concat([ale_curve(models[champion], dev, cols, variable) for variable in ["bmi", "fiber_density", "energy_kcal"] if variable in cols], ignore_index=True)
        flow, missing = pd.DataFrame(flow_dev + flow_test), pd.DataFrame(missing_dev + missing_test)
        for name, frame in {"test-metrics": scores, "dietary-comparisons": comparisons, "subgroup-audit": groups,
                            "sensitivity": sensitivity, "binned-diagnostics": diagnostics, "model-effects": effects,
                            "cohort-flow": flow, "missingness": missing}.items():
            frame.to_csv(ROOT / f"outputs/{name}.csv", index=False, float_format="%.8f")
        runtime = {name: importlib.metadata.version(name) for name in ["numpy", "pandas", "scipy", "scikit-learn", "matplotlib"]}
        runtime["python"] = platform.python_version()
        write_json(ROOT / "outputs/runtime.json", runtime)
        figures(ROOT, scores, comparisons, diagnostics, effects, selection)
        write_report(ROOT, scores, comparisons, groups, sensitivity, flow, missing, selection, runtime)
    print("Completed: aggregate test results, uncertainty, diagnostics, and report.", flush=True)


if __name__ == "__main__":
    main()
