# Design and methods

## The question and the comparison

Does adding two-day dietary information improve out-of-sample prediction of measured HbA1c beyond age, recorded sex, family income-to-poverty ratio, BMI, and waist circumference? This is a cross-sectional predictive comparison. It is not a dietary intervention estimate, prospective diabetes-risk model, or clinical screening validation.

The [analysis plan](../config/analysis-plan.json) fixes features, cohorts, tuning candidates, primary metric, random seed, subgroup suppression, and resampling count. Both feature sets use the same eligible participants. This holds the sample and outcome constant when comparing diet's added value.

## Public inputs and cohort

Six CDC components per cycle are joined one-to-one on SEQN: DEMO, BMX, GHB, DR1TOT, DR2TOT, and DIQ. All 12 source downloads are checked for SAS XPORT headers, size, and SHA-256 against the [manifest](../data/source-manifest.json). Raw records remain local and are ignored by Git.

Include age 20+, two reliable recalls (both status=1), positive two-day dietary weight, observed HbA1c, valid survey-design fields, and positive two-day energy. Exclude known pregnancy; unknown pregnancy status is retained and is not interpreted as a negative test. Outcome values are not imputed or winsorized. No exclusions are selected by test performance. The cohort flow lists sequential exclusions; the missingness table uses the adult two-recall sample before the outcome exclusion as its denominator.

The mean of both recall days supplies energy. Fiber, total sugars, saturated fat, protein, and sodium are divided by mean energy and multiplied by 1,000. Thus density is the ratio of the two-day means, not the mean of daily ratios. Gram-based nutrients are g/1,000 kcal; sodium is mg/1,000 kcal. A missing constituent stays missing; a single day is not substituted. Two recalls do not identify an individual's usual diet.

## Weights and the represented sample

WTDR2D is used because requiring both recalls is more restrictive than the full-sample examination/HbA1c component. Fit weights are normalized to mean one within each training fold and final training sample; evaluation uses the original relative weights. Age/sex coding is unchanged between cycles. Numeric medians, missing indicators, and standardization are fitted on training rows only. Preprocessing medians and scaling are unweighted; model losses and primary selection/evaluation are weighted.

No cycles are pooled for estimation: 2015-2016 supplies development, 2017-2018 supplies test evaluation. Consequently these are not four-year national estimates and weights are not divided by two. Laboratory-item nonresponse can still be selective; dietary weights do not fix all outcome missingness. The benchmark's target is performance in the eligible observed-outcome sample, not an asserted unbiased national performance parameter. Unweighted RMSE is shown as a sensitivity comparison.

## Leakage control and model selection

Only the five base predictors and six dietary predictors can enter a model. HbA1c, other laboratories, diabetes diagnosis, medication, diabetes-specific diet, race/ethnicity, participant IDs, survey weights, and sample-design IDs are not predictors. Recorded race/ethnicity is retained for error auditing, not treated as a biological exposure; exclusion does not ensure fairness. Recorded sex is binary in these public files and is not a measure of gender identity.

Four-fold GroupKFold keeps every masked PSU (stratum + PSU) intact within the development sample. All imputation and scaling are re-fit inside each fold. The folds are not probability samples, so CV is a tuning tool, not design-based inference. Pooled weighted out-of-fold RMSE selects each model family's hyperparameters separately for each feature set. The best development-CV pipeline is also chosen per feature set before test evaluation; the constant baseline is eligible for both. Candidate order resolves within-family ties and deterministic key order resolves pipeline ties.

Candidates: weighted mean; elastic net with two penalties; random forest with two minimum leaf sizes; histogram gradient boosting with two leaf-count limits. The tuning grid is deliberately bounded. Early stopping is disabled to avoid an ungrouped hidden validation split. Trees use a fixed seed and one execution thread. No test-driven feature changes or search expansion are permitted. Models are refit on all development rows and selection is written before building the test cohort. All family results are then reported; the test winner is not substituted for the development-selected pipeline.

## Error, uncertainty, and added dietary value

Primary metric: weighted root mean squared error in HbA1c percentage points. MAE, signed prediction bias, R², and unweighted RMSE are secondary. R² uses weighted test variance and may be negative. The constant benchmark predicts the development weighted mean, not the test mean.

For each test stratum, sample n_h-1 masked PSUs with replacement and multiply selected-unit weights by n_h/(n_h-1). In these data, two PSUs means choosing one and doubling its weight. Repeat 1,000 times with a fixed seed. Recompute RMSE and paired differences using the same replicate weights for both models. Report 2.5th and 97.5th percentiles. Singleton strata cause a hard failure rather than silently switching to independent-row bootstrap. These approximate conditional intervals reflect test-sample clustering; they do not incorporate model fitting, hyperparameter search, measurement error, or future-cycle shift.

The primary contrast compares the independently development-selected base and dietary pipelines. Within-family contrasts hold the model family fixed but allow tuning to differ. Negative dietary-minus-base RMSE favors diet; crossing zero does not establish improvement. None of these comparisons estimates a causal effect of diet.

## Diagnostics and sensitivity

Age, recorded sex, and recorded race/ethnicity audits use fixed test predictions and sample weights, with groups below 30 suppressed. Intervals use the full cohort's PSU resamples restricted to the subgroup; they are not multiplicity-adjusted. Prediction-decile plots publish weighted aggregate means and counts, never individuals. A decile with fewer than 30 people is omitted.

First-order accumulated local effects use development observations between each feature's 5th and 95th percentiles. Within each bin, predictions are differenced at the bin endpoints and averaged with dietary weights; bin effects are accumulated and centered. This describes local fitted-model behavior, not an intervention, mechanism, or causal relationship. Curves are not confidence bands.

Prespecified restrictions evaluate the same fitted pipelines among respondents reporting no diabetes diagnosis (DIQ010=2), and among participants complete on the base predictors. Neither restriction changes model fitting or reverses prior diagnosis/treatment effects. No-diagnosis is not no-disease. Disentangling diabetes treatment, reverse causation, and habitual intake would require a different design.

## Sources

- [CDC NHANES weighting guidance](https://wwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx).
- [2017-2018 dietary component](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DR1TOT_J.htm), including two-day weights and recall status.
- [2015-2016 HbA1c](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/GHB_I.htm) and [2017-2018 HbA1c](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/GHB_J.htm). CDC documents a change in the secondary assay method in 2017-2018; cross-cycle comparability is not assumed to be perfect.
- [Scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage) and [GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html).
- [Survey package documentation for Rao-Wu n-1 replicate resampling](https://r-survey.r-forge.r-project.org/pkgdown/docs/reference/as.svrepdesign.html). This implementation uses a single-stage masked-PSU approximation, not unavailable confidential multistage design information.
