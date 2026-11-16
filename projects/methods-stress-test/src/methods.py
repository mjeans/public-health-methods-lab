"""Transparent estimators for controlled, synthetic stress experiments."""
from __future__ import annotations
import numpy as np
from scipy.special import expit
from scipy.stats import t

LABELS = {
    "one_recall": "One recall",
    "two_recalls": "Two-recall average",
    "calibrated": "Calibration: independent errors",
    "latent_oracle": "Latent exposure (oracle)",
    "complete_case": "Complete-case mean",
    "ipw": "IPW: known MAR probabilities",
    "standardized": "Regression standardization",
    "full_oracle": "Full outcomes (oracle)",
    "individual_t": "Individual-level t",
    "school_t": "School-mean t",
}


def result(estimate, se, df=np.inf):
    if not np.isfinite(estimate) or not np.isfinite(se) or se <= 0:
        raise ValueError("Invalid estimator or standard error")
    critical = t.ppf(.975, df)
    return float(estimate), float(se), float(estimate-critical*se), float(estimate+critical*se)


def slope(x, y):
    x, y = np.asarray(x), np.asarray(y)
    xc, yc = x-x.mean(), y-y.mean()
    sxx = xc @ xc
    if len(x) < 4 or sxx <= 1e-12:
        raise ValueError("Insufficient variation")
    b = (xc @ yc) / sxx
    residual = yc-b*xc
    se = np.sqrt((residual @ residual) / (len(x)-2) / sxx)
    return result(b, se, len(x)-2)


def calibrated_slope(x, y, reliability):
    if not 0 < reliability <= 1:
        raise ValueError("Reliability must be in (0,1]")
    return tuple(v / reliability for v in slope(x, y))


def mean_interval(y):
    y = np.asarray(y)
    return result(y.mean(), y.std(ddof=1)/np.sqrt(len(y)), len(y)-1)


def ipw_mean(y_observed, observed, probability):
    """Self-normalized IPW; probabilities treated as known, not estimated."""
    if np.any(probability <= 0) or np.any(probability > 1):
        raise ValueError("Invalid response probabilities")
    w = observed / probability
    mu = np.sum(w*y_observed) / w.sum()
    influence = w*(y_observed-mu) / w.mean()
    return result(mu, influence.std(ddof=1)/np.sqrt(len(w)))


def standardized_mean(x, y_observed, observed):
    """OLS outcome model + all-cohort X distribution; stacked-moment SE."""
    z = np.column_stack([np.ones(len(x)), x])
    zr = z[observed]
    if observed.sum() < 5:
        raise ValueError("Too few observed outcomes")
    inv_a = np.linalg.inv(zr.T @ zr / len(x))
    beta = inv_a @ (zr.T @ y_observed[observed] / len(x))
    a = z.mean(axis=0)
    estimate = a @ beta
    residual = np.where(observed, y_observed-z @ beta, 0.)
    score = z * residual[:, None]
    # This includes uncertainty in both the fitted outcome model and X's mean.
    influence = score @ inv_a @ a + (z-a) @ beta
    return result(estimate, influence.std(ddof=1)/np.sqrt(len(x)))


def treatment_difference(y, treated):
    """Equal-variance independent-unit t interval."""
    y0, y1 = y[~treated], y[treated]
    df = len(y0)+len(y1)-2
    variance = ((len(y0)-1)*y0.var(ddof=1)+(len(y1)-1)*y1.var(ddof=1))/df
    return result(y1.mean()-y0.mean(), np.sqrt(variance*(1/len(y0)+1/len(y1))), df)


def measurement(rng, c):
    n, beta, sd, rho = c["n"], c["truth"], c["error_sd"], c["error_correlation"]
    x, noise = rng.normal(size=(2, n))
    e1, e2 = rng.normal(size=(2, n))
    w1 = x+sd*e1
    w2 = x+sd*(rho*e1+np.sqrt(1-rho*rho)*e2)
    y = beta*x+noise
    average = (w1+w2)/2
    # Calibration deliberately assumes independent replicate errors.
    reliability = 1/(1+sd*sd/2)
    return {
        "one_recall": slope(w1, y),
        "two_recalls": slope(average, y),
        "calibrated": calibrated_slope(average, y, reliability),
        "latent_oracle": slope(x, y),
    }, {"observed_fraction": 1.0}


def missingness(rng, c):
    x, noise = rng.normal(size=(2, c["n"]))
    y = .5*x+noise  # Superpopulation mean is exactly zero.
    mar_probability = np.clip(expit(.2-.8*x), .03, .97)
    mechanism = c["mechanism"]
    if mechanism == "MCAR":
        p = assumed = np.full(len(x), .65)
    elif mechanism == "MAR":
        p = assumed = mar_probability
    elif mechanism == "MNAR":
        p = np.clip(expit(.2-.8*x-.8*noise), .03, .97)
        assumed = mar_probability
    else:
        raise ValueError("Unknown missingness mechanism")
    observed = rng.uniform(size=len(x)) < p
    safe_y = np.where(observed, y, 0.)  # Unobserved outcomes cannot enter feasible methods.
    return {
        "complete_case": mean_interval(y[observed]),
        "ipw": ipw_mean(safe_y, observed, assumed),
        "standardized": standardized_mean(x, safe_y, observed),
        "full_oracle": mean_interval(y),
    }, {"observed_fraction": float(observed.mean())}


def clustering(rng, c):
    schools, pupils, icc = c["schools"], c["pupils_per_school"], c["icc"]
    treated = np.zeros(schools, dtype=bool)
    treated[rng.permutation(schools)[:schools//2]] = True
    u = rng.normal(size=schools)
    noise = rng.normal(size=(schools, pupils))
    y = c["truth"]*treated[:, None]+np.sqrt(icc)*u[:, None]+np.sqrt(1-icc)*noise
    return {
        "individual_t": treatment_difference(y.ravel(), np.repeat(treated, pupils)),
        "school_t": treatment_difference(y.mean(axis=1), treated),
    }, {"observed_fraction": 1.0}


def simulate_one(c, repetition, seed):
    # Scenario IDs are fixed in the design; reordering scenarios cannot change draws.
    rng = np.random.default_rng(np.random.SeedSequence([seed, c["id"], repetition]))
    return {"measurement": measurement, "missingness": missingness, "clustering": clustering}[c["family"]](rng, c)


def wilson_interval(p, n):
    z = 1.959963984540054
    denominator = 1 + z*z/n
    center = (p + z*z/(2*n)) / denominator
    half = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    return max(0., center-half), min(1., center+half)


def summarize(estimates, truth, attempted):
    a = np.asarray(estimates, dtype=float)
    if a.ndim != 2 or a.shape[1] != 4:
        raise ValueError("Expected estimate, SE, lower, upper")
    valid = np.isfinite(a).all(axis=1) & (a[:, 1] > 0)
    a = a[valid]
    if len(a) < 2:
        raise ValueError("Too few successful repetitions")
    cover = (a[:, 2] <= truth) & (truth <= a[:, 3])
    reject = (a[:, 2] > 0) | (a[:, 3] < 0)
    p, q, r = cover.mean(), reject.mean(), len(a)
    coverage_lower, coverage_upper = wilson_interval(p, r)
    rejection_lower, rejection_upper = wilson_interval(q, r)
    return dict(attempted=attempted,successful=r,failed=attempted-r,
                mean_estimate=a[:,0].mean(),bias=a[:,0].mean()-truth,
                bias_mcse=a[:,0].std(ddof=1)/np.sqrt(r),
                empirical_sd=a[:,0].std(ddof=1),mean_se=a[:,1].mean(),
                rmse=np.sqrt(np.mean((a[:,0]-truth)**2)),
                coverage=p,coverage_mcse=np.sqrt(p*(1-p)/r),
                coverage_lower=coverage_lower,coverage_upper=coverage_upper,
                coverage_all_attempts=cover.sum()/attempted,
                reject_zero=q,reject_zero_mcse=np.sqrt(q*(1-q)/r),
                reject_zero_lower=rejection_lower,reject_zero_upper=rejection_upper,
                mean_interval_width=np.mean(a[:,3]-a[:,2]))
