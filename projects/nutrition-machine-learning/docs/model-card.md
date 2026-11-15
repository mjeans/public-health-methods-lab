# Model card

**Purpose:** A public research portfolio benchmark asking whether a small set of dietary summaries adds predictive value for measured HbA1c. Not a clinical product or deployed service.

**Author:** Matthew Jeans, PhD, PMP. [ORCID](https://orcid.org/0000-0002-1140-3185).

**Data:** CDC/NCHS public-use NHANES 2015-2016 (development) and 2017-2018 (test), restricted to adults with two reliable dietary recalls and an observed HbA1c measurement. The published repository contains code, hashes, and aggregate results, not respondent files or individual predictions.

**Model:** A training-only preprocessing pipeline plus weighted mean, elastic net, random forest, or gradient boosting. The [selection record](../outputs/selection.json) names development-selected pipelines and parameters; the [executed report](../outputs/report.md) reports their subsequent performance. The development CV metric, not the test result, determines selection.

**Intended users:** Researchers and reviewers inspecting reproducible predictive methodology. Appropriate activities include rerunning the benchmark, examining error patterns, and discussing whether the data and validation support a proposed use.

**Not appropriate for:** Diagnosing diabetes, predicting future disease, recommending diets, replacing a laboratory test, targeting individual patients, allocating or denying care/insurance/services, or claiming that a feature causes an outcome. No clinical threshold or individual risk calculator is supplied.

**Strengths demonstrated:** A locked feature allowlist; grouped cross-validation; later-cycle evaluation; model and dietary-feature comparisons on identical samples; survey-weighted losses; paired cluster-aware uncertainty; subgroup audits; source checksums; regression tests; reproducible aggregate reporting.

**Limits:** Independent survey cycles are not longitudinal follow-up. Recall error, missing laboratory data, nonresponse, diagnosis/treatment-related dietary changes, weak incremental signal, and correlated predictors can all limit performance and interpretation. Training weights do not magically convert a predictive model into a causal estimator. Excluding race/ethnicity from features does not establish fairness. Minimum sample sizes and intervals are reporting safeguards, not proof of sufficient subgroup validity.

**Before any real-world use:** Define an authorized use and population, obtain appropriate governance review, acquire suitable contemporary data, validate externally and prospectively, evaluate individual errors and subgroup harms, and establish human oversight and monitoring. This repository makes no claim that those requirements have been met.

**Maintenance:** Source or dependency changes require a reviewed full rerun. Do not tune against the existing test cycle after inspecting its results. Material modeling changes need a fresh validation design; a rerun of the same holdout is a reproduction check, not new validation evidence.
