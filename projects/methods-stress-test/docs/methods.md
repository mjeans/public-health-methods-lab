# Design and interpretation

## Aim, data, estimands, methods, performance

The study follows the planning vocabulary of [Morris, White, and Crowther (2019)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6492164/): specify the question, generating process, target, competing methods, and evaluation measures. Monte Carlo error is reported rather than treating a finite simulation as exact truth.

The [JSON design](../config/design.json) fixes 23 scenarios and 2,000 repetitions each. Experiments are separate, not a complete factorial crossing of every threat. Values are chosen to make mechanisms inspectable, not calibrated to TX Sprouts or NHANES. Outcomes/exposures are standardized, not clinical units.

## Experiment 1: measurement error

For 800 independent people, generate independent standard-normal X and E, with Y = beta * X + E. The target beta is 0 or 0.5. Two recall-like measurements are W1 = X + U1 and W2 = X + U2. Each error has SD 0, 0.75, or 1.5. The final high-error scenario has error correlation 0.5; the others have independent errors.

Compare OLS slopes using one recall, the two-recall average, a calibrated two-recall slope, and the latent X oracle. OLS uses residual variance and a t critical value with n-2 degrees of freedom. Calibration divides the estimate and its entire interval by the assumed reliability 1 / (1 + error_SD^2 / 2). Error variance is treated as known, and independent errors are assumed. Its intervals omit calibration-parameter uncertainty.

Under the actual generating model, two-recall reliability is 1 / (1 + error_SD^2 * (1 + correlation) / 2). Thus the correlated-error case deliberately violates calibration's assumption. The latent-X oracle is not observable in dietary research. Neither this benchmark nor averaging two recalls is an implementation of a usual-intake model.

NCI distinguishes [random and systematic dietary measurement error](https://epi.grants.cancer.gov/dietary-assessment-primer/concepts/error/error-types.html). Our Gaussian errors illustrate only selected mechanisms; bounded intakes, episodic consumption, nonlinear relationships, and intake-dependent reporting are not modeled.

## Experiment 2: missing outcomes

For 800 independent people, X and E are standard normal and Y = 0.5 * X + E. The target is the superpopulation mean E[Y] = 0, not the realized finite-sample mean. X is observed for everyone; Y is available only if R = 1.

- MCAR: response probability is 0.65.
- MAR: probability is clip(expit(0.2 - 0.8 * X), 0.03, 0.97).
- MNAR: probability is clip(expit(0.2 - 0.8 * X - 0.8 * E), 0.03, 0.97).

Compare the complete-case mean, self-normalized inverse-probability weighting, regression standardization, and the full-outcome oracle. IPW receives the known generating response probability in MCAR/MAR. In MNAR it still assumes the stated MAR probability based only on X; it is not given E or missing Y. Known probabilities are a favorable benchmark, not evidence that real response models are known.

For IPW, weights are R / assumed_probability, the estimate is sum(w * Y) / sum(w), and the influence value is w * (Y - estimate) / mean(w). The SE is the sample SD of influence values divided by sqrt(n). No weight trimming is applied; the response mechanism itself is bounded.

For standardization, fit observed Y on Z = (1, X), then average predictions across the entire X distribution. Let A = mean(R * Z * Z'), a = mean(Z), and b be the observed-outcome OLS coefficients. The influence value is a' * inverse(A) * R * Z * (Y - Z' * b) + (Z - a)' * b. The second term accounts for sampling variability in the covariate distribution. Its SE uses the sample SD of influence values divided by sqrt(n), with a normal critical value.

Complete-case and full-data means use t intervals. Regression standardization relies on its outcome model and the relevant missingness assumptions. No method here repairs arbitrary MNAR selection. This experiment does not compare multiple imputation or claim universal superiority of weighting or standardization.

## Experiment 3: clustered treatment assignment

Generate 16 or 48 schools, 30 pupils per school, and randomly assign half the schools to treatment. The target effect delta is 0 or 0.3. For pupil i in school j:

`Y_ij = delta * treatment_j + sqrt(ICC) * U_j + sqrt(1 - ICC) * E_ij`

Independent school effects and pupil errors are standard normal; ICC is 0, 0.05, or 0.20. Compare an ordinary equal-variance two-sample t interval over pupils with the same test over school means. Both have the same point estimate because cluster sizes are equal. The first uses n-2 degrees of freedom; the second uses schools-2.

The school-mean procedure is justified here by independent, equally sized, normally distributed clusters with common variance and balanced assignment. It is not a general prescription for unequal cluster sizes, covariate adjustment, informative cluster size, non-Gaussian outcomes, or every small-cluster setting.

## Performance, pairing, and reproducibility

Each method reports bias, bias MCSE, empirical SD, mean model-based SE, RMSE, mean interval width, coverage, rejection of zero, and successful/failed counts. Reject-zero is type-I error only at a null target; otherwise it is power. Coverage is evaluated against the true generating parameter even when a naive regression converges to an attenuated slope.

Bias MCSE is empirical SD / sqrt(R). Proportion MCSE is sqrt(p * (1-p) / R). The corresponding 95% Wilson intervals are also reported and plotted: zero observed events do not establish zero uncertainty. At R=2,000, proportion MCSE is at most about 0.0112 and is about 0.0049 near p=0.95. Bias intervals use a normal Monte Carlo approximation.

Methods share data within a repetition. Paired estimate and coverage differences use the empirical SD of within-repetition differences / sqrt(R), not an independence assumption across methods. Separate scenarios use SeedSequence([20261115, scenario_id, repetition]); scenario reordering cannot change their streams.

Unexpected estimator exceptions stop the run. Nonfinite estimates are counted as failures in summaries, with both successful-fit and all-attempt coverage denominators exposed. All reference scenarios completed without failures. No raw synthetic person-level records are stored.

A rerun checks implementation reproducibility, not external validity. The published computational plan was not externally registered. Broad research conclusions require different, justified generating mechanisms and further validation.
