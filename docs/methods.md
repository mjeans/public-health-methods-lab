# Methods and assumptions

## Nutrient density and dietary recalls

For each synthetic participant, two 24-hour recalls are averaged before fiber and sodium are expressed per 1,000 kilocalories:

```text
Nutrient density = nutrient amount / energy intake * 1,000
```

Group contrasts are the nutrition-education mean minus the comparison mean, with a normal-approximation confidence interval based on independent group standard errors. These are descriptive contrasts, not causal effects.

Energy adjustment can make nutrient comparisons less dependent on total energy intake, but it does not correct recall bias, correlated reporting error, or within-person variation. Two recalls are not treated as an estimate of long-term usual intake. No dietary-guideline or clinical threshold is applied to the synthetic observations. See the [nutrition case study](nutrition-case-study.md) for the complete design and interpretation boundaries.

## Direct age standardization

For age stratum `i`, the observed rate is `r_i = d_i / n_i`, where `d_i` is the number of cases and `n_i` is person-time. The directly standardized rate is:

```text
R_std = sum(w_i * r_i)
```

The standard-population weights `w_i` are normalized to sum to one. The approximate variance assumes Poisson case counts:

```text
Var(R_std) = sum(w_i^2 * d_i / n_i^2)
```

The lab reports the standardized rate and a normal-approximation 95% confidence interval per 100,000 person-weeks. A production analysis should prespecify the standard population, consider exact or gamma-based intervals when counts are sparse, and preserve the stratum-level data needed to audit the calculation.

## Surveillance signal

Each week after the first four is compared with the preceding four-week mean and sample standard deviation. A z-score at or above 2.5 is labeled a signal. This rule is deliberately simple and inspectable. It does not adjust for seasonality, secular trend, reporting delay, day-of-week effects, overdispersion, or multiple monitoring.

Real surveillance work should use a method and alert protocol suited to the outcome, reporting process, and operational consequences. A statistical signal should prompt verification, not automatically declare an outbreak.

## Cohort risk ratio

The outbreak example estimates:

```text
RR = risk among exposed / risk among unexposed
```

The 95% confidence interval is calculated on the log scale using the standard large-sample variance for two cohort risks. The example contains no zero cells. Sparse or zero-cell tables would require a different interval or a prespecified correction.

The risk ratio is an association conditional on the case definition, enrollment, exposure measurement, and follow-up. It does not by itself establish the outbreak source.

## Kaplan-Meier estimation

The retention example treats disengagement from care as the event and ongoing observation as right-censoring. At each event time, the Kaplan-Meier estimator multiplies the preceding survival probability by `1 - d_j / n_j`. Events are processed before censoring at tied times. Confidence limits use Greenwood's variance and a log-log transformation.

The comparison is descriptive. Censoring is assumed to be non-informative for the displayed estimator, and the synthetic outreach groups were not randomized. A causal comparison would require an appropriate design and adjustment strategy; a multivariable time-to-event analysis would also require proportional-hazards and functional-form checks when a Cox model is used.

## Privacy and reporting

No real health information is stored. In real public-health reporting, the analytic plan should specify minimum-cell suppression, complementary suppression where needed, geographic aggregation, access controls, retention rules, and disclosure review before publication.
