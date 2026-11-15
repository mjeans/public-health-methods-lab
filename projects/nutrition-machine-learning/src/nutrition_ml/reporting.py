"""Publish aggregate results and accessible scientific figures only."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .modeling import FAMILY_NAMES

NAVY, TEAL, GRAY, GOLD = "#183247", "#007f78", "#697784", "#b57221"


def label(key):
    fs, family = key.split(":")
    return FAMILY_NAMES[family] + (" + diet" if fs == "diet" else " | base" if family != "mean" else "")


def table(frame, columns, digits=3):
    head = "| " + " | ".join(columns) + " |\n|" + "|".join(["---"] * len(columns)) + "|\n"
    def format_value(v):
        return f"{v:.{digits}f}" if isinstance(v, (float, np.floating)) else str(v)
    return head + "\n".join("| " + " | ".join(format_value(v) for v in row) + " |" for row in frame[columns].itertuples(index=False, name=None))


def save(fig, root, name, description):
    svg = root / f"assets/{name}.svg"
    fig.savefig(svg, metadata={"Date": None, "Description": description}, facecolor="white")
    # Matplotlib adds spaces before path-data newlines; normalize the text asset.
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
                   encoding="utf-8", newline="\n")
    fig.savefig(root / f"assets/{name}.png", dpi=140, facecolor="white")
    plt.close(fig)


def figures(root, scores, comparisons, diagnostics, effects, selection):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.labelcolor": NAVY, "text.color": NAVY,
                         "xtick.color": GRAY, "ytick.color": NAVY, "svg.fonttype": "none",
                         "svg.hashsalt": "nutrition-ml", "axes.titleweight": "bold"})
    fig, ax = plt.subplots(figsize=(11, 6.4))
    d = scores.sort_values("rmse", ascending=False).reset_index(drop=True)
    for i, r in d.iterrows():
        color = TEAL if r.model.startswith("diet:") else NAVY
        ax.plot([r.rmse_lower, r.rmse_upper], [i, i], color=color, lw=2.5, alpha=.65)
        ax.scatter(r.rmse, i, color=color, s=65, zorder=3)
        ax.annotate(f"{r.rmse:.3f}", (r.rmse_upper, i), xytext=(8, 0), textcoords="offset points", va="center", fontsize=10)
    ax.set_yticks(range(len(d)), [label(k) for k in d.model])
    ax.set_xlabel("Survey-weighted RMSE (HbA1c percentage points)  |  Lower is better", labelpad=12)
    ax.set_xlim(max(0, d.rmse_lower.min() - .03), d.rmse_upper.max() + .14)
    ax.grid(axis="x", color="#e6ecee", zorder=0)
    ax.set_axisbelow(True)
    fig.suptitle("Does complexity improve prediction?", x=.04, ha="left", fontsize=21, fontweight="bold", y=.97)
    fig.text(.04, .89, "2017-2018 holdout  /  Hyperparameters selected using 2015-2016 only", color=GRAY)
    fig.text(.04, .025, "Teal: dietary features added. Lines: approximate 95% stratified-PSU bootstrap intervals.\nIntervals condition on fitted models; test results did not determine model selection.", fontsize=9, color=GRAY)
    fig.subplots_adjust(left=.30, right=.96, top=.81, bottom=.19)
    save(fig, root, "model-comparison", "Model RMSE and conditional 95% intervals on the later NHANES cycle; lower is better.")

    fig, ax = plt.subplots(figsize=(11, 5.6))
    for i, r in comparisons.iterrows():
        ax.plot([r.lower, r.upper], [i, i], color=TEAL, lw=3)
        ax.scatter(r.rmse_difference, i, color=NAVY, s=65, zorder=4)
    ax.axvline(0, color=GRAY, linestyle="--", lw=1)
    names = [FAMILY_NAMES.get(x, x) for x in comparisons.comparison]
    ax.set_yticks(range(len(comparisons)), names)
    ax.invert_yaxis()
    ax.set_xlabel("RMSE with diet minus RMSE without diet (HbA1c percentage points)", labelpad=14)
    ax.grid(axis="x", color="#e6ecee")
    fig.suptitle("What do dietary measures add?", x=.04, ha="left", fontsize=21, fontweight="bold", y=.97)
    fig.text(.04, .87, "Same participants  /  Same test cycle  /  Paired comparisons", color=GRAY)
    fig.text(.04, .025, "Negative favors dietary features. An interval crossing zero does not establish an improvement.\nSelected pipelines may use different model families; family rows select tuning separately for each feature set.", color=GRAY, fontsize=9)
    fig.subplots_adjust(left=.24, right=.96, top=.77, bottom=.22)
    save(fig, root, "dietary-added-value", "Paired RMSE differences and conditional 95% intervals; negative values favor adding diet.")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.6))
    if not diagnostics.empty:
        x, y = diagnostics.predicted, diagnostics.observed
        a, b = min(x.min(), y.min()) - .07, max(x.max(), y.max()) + .07
        axes[0].plot([a, b], [a, b], "--", color=GRAY, lw=1)
        axes[0].plot(x, y, "o-", color=TEAL, lw=2)
        axes[0].set(xlabel="Mean predicted HbA1c (%)", ylabel="Mean observed HbA1c (%)", xlim=(a, b), ylim=(a, b))
        axes[1].axhline(0, color=GRAY, linestyle="--", lw=1)
        axes[1].plot(x, diagnostics.residual, "o-", color=GOLD, lw=2)
        axes[1].set(xlabel="Mean predicted HbA1c (%)", ylabel="Observed minus predicted (percentage points)")
    for ax in axes:
        ax.grid(alpha=.15)
    fig.suptitle("Where does the model miss?", x=.04, ha="left", fontsize=21, fontweight="bold", y=.97)
    fig.text(.04, .87, "Development-selected dietary pipeline: " + label(selection["champions"]["diet"]), color=GRAY)
    fig.text(.04, .025, "Weighted means within predicted-score deciles (at least 30 people per bin).\nAggregate diagnostics; no individual records are displayed. Positive residuals indicate underprediction.", fontsize=9, color=GRAY)
    fig.subplots_adjust(left=.08, right=.96, top=.77, bottom=.22, wspace=.37)
    save(fig, root, "prediction-diagnostics", "Aggregate observed-versus-predicted values and residuals by prediction decile.")

    fig, axes = plt.subplots(1, 3, figsize=(12, 5.4), sharey=True)
    labels = {"bmi": "BMI (kg/m²)", "fiber_density": "Fiber (g / 1,000 kcal)", "energy_kcal": "Energy (kcal/day)"}
    for ax, variable in zip(axes, labels):
        d = effects[effects.variable == variable]
        ax.axhline(0, color=GRAY, lw=1, linestyle="--")
        ax.plot(d.value, d.effect, "o-", color=TEAL, lw=2, ms=4)
        ax.set_xlabel(labels[variable], fontsize=10)
        ax.grid(alpha=.15)
    axes[0].set_ylabel("Centered model response\n(HbA1c percentage points)")
    fig.suptitle("How does the fitted model respond?", x=.04, ha="left", fontsize=21, fontweight="bold", y=.97)
    fig.text(.04, .87, "Accumulated local effects  /  Common y-scale  /  Development data, central 90%", color=GRAY)
    fig.text(.04, .025, "These curves describe the model, not nutritional or causal effects. No confidence intervals are implied.\nLocal changes reduce extrapolation but cannot remove confounding, measurement error, or model bias.", fontsize=9, color=GRAY)
    fig.subplots_adjust(left=.09, right=.97, top=.75, bottom=.24, wspace=.37)
    save(fig, root, "model-effects", "Development-sample accumulated local effects, not causal effects.")


def write_report(root, scores, comparisons, groups, sensitivity, flow, missing, selection, runtime):
    selected = selection["champions"]["diet"]
    primary = comparisons.iloc[0]
    evidence = ("The interval includes zero: this comparison does not establish an improvement."
                if primary.lower <= 0 <= primary.upper else
                "The interval favors the dietary pipeline on this test sample." if primary.upper < 0 else
                "The interval favors the base pipeline on this test sample.")
    text = f"""# Executed cross-cycle benchmark

## Main finding

The development-selected base pipeline is **{label(selection['champions']['base'])}**; the dietary pipeline is **{label(selected)}**.
On the separate 2017-2018 sample, adding diet changes weighted RMSE by **{primary.rmse_difference:+.4f} HbA1c percentage points**
(approximate conditional 95% interval **{primary.lower:+.4f} to {primary.upper:+.4f}**). {evidence}

This is prediction of a contemporaneously measured biomarker, not prediction of future diabetes and not a test of whether changing diet changes HbA1c.

## Test performance

{table(scores, ['model', 'n', 'rmse', 'rmse_lower', 'rmse_upper', 'mae', 'bias', 'r2', 'unweighted_rmse'])}

RMSE and MAE are in HbA1c percentage points. Bias is predicted minus observed. Weighted R² uses the test-sample weighted mean as its reference; it can be negative. The constant benchmark instead uses the development weighted mean.

![Model comparison](../assets/model-comparison.svg)

## Dietary added value

{table(comparisons, ['comparison', 'base_model', 'diet_model', 'rmse_difference', 'lower', 'upper'], digits=4)}

![Dietary added value](../assets/dietary-added-value.svg)

## Error patterns

![Prediction diagnostics](../assets/prediction-diagnostics.svg)

{table(groups, ['dimension', 'group', 'n', 'status', 'rmse', 'mae', 'bias', 'rmse_lower', 'rmse_upper'])}

Subgroup results are descriptive audits, not proof of fairness. Groups below 30 are suppressed; intervals are conditional and differences are not multiplicity-adjusted.

## Prespecified sensitivity checks

{table(sensitivity, ['subset', 'feature_set', 'model', 'n', 'rmse', 'mae', 'bias'])}

These are evaluation restrictions on already-fitted models, not newly trained models. Reported absence of diabetes diagnosis is not evidence of absence of diabetes. No fasting laboratory measurements or medications enter the predictors.

## Model interpretation

![Accumulated local effects](../assets/model-effects.svg)

The dietary model was selected before test evaluation. Curves use development observations only. Correlated nutrients and noisy two-day recall summaries limit substantive interpretation.

## Cohort accounting

{table(flow, ['cycle', 'step', 'remaining', 'excluded'])}

Missingness below is measured among adults with two reliable recalls and positive dietary weights, before outcome exclusions:

{table(missing, ['cycle', 'variable', 'missing_n', 'denominator_n'])}

## Reproduction record

- Plan SHA-256: `{selection['plan_sha256']}`.
- Hyperparameters and selected pipelines: [selection.json](selection.json).
- Every candidate's development performance: [cv-results.csv](cv-results.csv).
- Development-only fold counts: [cv-folds.csv](cv-folds.csv).
- Raw data integrity: [CDC source hashes](../data/source-manifest.json).
- Runtime: `{json.dumps(runtime, sort_keys=True)}`.
- Test rows did not enter fitting, preprocessing, hyperparameter selection, or model choice. Reproduction reruns the frozen workflow; it is not a new independent validation study.

## Limits that matter

WTDR2D accounts for dietary interview selection/nonresponse, not every missing laboratory result or covariate. This benchmark describes the eligible observed-outcome sample; it does not establish unbiased population-wide predictive performance. Two-day intake is not usual intake. The cycles are independent cross-sectional samples, not longitudinal follow-up. Known diabetes and treatment can alter both diet and HbA1c; reverse causation and residual confounding remain. The primary assay was comparable across these cycles, with a secondary-method change documented by CDC in 2017-2018.

Intervals use 1,000 stratified masked-PSU resamples and hold fitted models fixed. They are approximate, do not include development/model-selection uncertainty, and are not clinical prediction intervals. A strong average score would not establish safe performance for an individual. See [methods](../docs/methods.md) and [model card](../docs/model-card.md).
"""
    (root / "outputs/report.md").write_text(text, encoding="utf-8", newline="\n")
