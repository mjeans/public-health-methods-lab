"""Small, dependency-free epidemiology and biostatistics helpers.

The functions are intentionally transparent so reviewers can inspect the
estimands and formulas without relying on a black-box package. Production work
should use validated statistical libraries and a prespecified analysis plan.
"""

from __future__ import annotations

from math import exp, log, sqrt
from statistics import mean, stdev
from typing import Iterable, Mapping, Sequence


Z_975 = 1.959963984540054


def direct_standardized_rate(
    strata: Iterable[Mapping[str, float | int | str]],
    standard_population: Mapping[str, float],
    multiplier: float = 100_000.0,
) -> dict[str, float]:
    """Return crude and directly standardized rates with an approximate CI.

    Each stratum must contain ``age_group``, ``cases``, and ``person_time``.
    Standard-population values may be proportions or counts; they are
    normalized internally. The variance uses a Poisson approximation.
    """

    rows = list(strata)
    if not rows:
        raise ValueError("At least one stratum is required")
    if multiplier <= 0:
        raise ValueError("multiplier must be positive")

    standard_total = sum(float(value) for value in standard_population.values())
    if standard_total <= 0:
        raise ValueError("standard population must have positive total weight")

    total_cases = 0.0
    total_person_time = 0.0
    standardized_rate = 0.0
    standardized_variance = 0.0

    for row in rows:
        age_group = str(row["age_group"])
        if age_group not in standard_population:
            raise ValueError(f"Missing standard-population weight for {age_group}")

        cases = float(row["cases"])
        person_time = float(row["person_time"])
        if cases < 0 or person_time <= 0 or cases > person_time:
            raise ValueError("cases must be between zero and positive person-time")

        weight = float(standard_population[age_group]) / standard_total
        stratum_rate = cases / person_time
        standardized_rate += weight * stratum_rate
        standardized_variance += (weight**2) * cases / (person_time**2)
        total_cases += cases
        total_person_time += person_time

    crude_rate = total_cases / total_person_time
    standard_error = sqrt(standardized_variance)
    lower = max(0.0, standardized_rate - Z_975 * standard_error)
    upper = standardized_rate + Z_975 * standard_error

    return {
        "crude_rate": crude_rate * multiplier,
        "standardized_rate": standardized_rate * multiplier,
        "standard_error": standard_error * multiplier,
        "lower_95": lower * multiplier,
        "upper_95": upper * multiplier,
    }


def risk_ratio(
    exposed_cases: int,
    exposed_total: int,
    unexposed_cases: int,
    unexposed_total: int,
) -> dict[str, float]:
    """Estimate a cohort risk ratio and a log-scale 95% confidence interval."""

    cells = (exposed_cases, exposed_total, unexposed_cases, unexposed_total)
    if any(not isinstance(value, int) for value in cells):
        raise TypeError("risk-ratio inputs must be integers")
    if not (0 < exposed_cases <= exposed_total and 0 < unexposed_cases <= unexposed_total):
        raise ValueError("each group needs at least one case and a valid total")

    risk_exposed = exposed_cases / exposed_total
    risk_unexposed = unexposed_cases / unexposed_total
    estimate = risk_exposed / risk_unexposed
    standard_error = sqrt(
        (1 / exposed_cases)
        - (1 / exposed_total)
        + (1 / unexposed_cases)
        - (1 / unexposed_total)
    )

    return {
        "risk_exposed": risk_exposed,
        "risk_unexposed": risk_unexposed,
        "risk_ratio": estimate,
        "lower_95": exp(log(estimate) - Z_975 * standard_error),
        "upper_95": exp(log(estimate) + Z_975 * standard_error),
    }


def nutrient_density(
    nutrient_amount: float, energy_kcal: float, per_kcal: float = 1_000.0
) -> float:
    """Express a nutrient amount per a specified number of kilocalories."""

    if nutrient_amount < 0:
        raise ValueError("nutrient amount cannot be negative")
    if energy_kcal <= 0 or per_kcal <= 0:
        raise ValueError("energy and density denominator must be positive")
    return nutrient_amount / energy_kcal * per_kcal


def mean_difference(
    group_a: Sequence[float], group_b: Sequence[float]
) -> dict[str, float]:
    """Return a descriptive mean difference and normal-approximation 95% CI."""

    if len(group_a) < 2 or len(group_b) < 2:
        raise ValueError("each group must contain at least two observations")
    estimate = mean(group_a) - mean(group_b)
    standard_error = sqrt(
        (stdev(group_a) ** 2 / len(group_a))
        + (stdev(group_b) ** 2 / len(group_b))
    )
    return {
        "mean_a": mean(group_a),
        "mean_b": mean(group_b),
        "difference": estimate,
        "standard_error": standard_error,
        "lower_95": estimate - Z_975 * standard_error,
        "upper_95": estimate + Z_975 * standard_error,
    }


def weekly_z_signals(
    counts: Sequence[int], baseline_weeks: int = 4, threshold: float = 2.5
) -> list[dict[str, float | int | bool | None]]:
    """Flag simple weekly surveillance signals against a rolling baseline.

    This is an educational illustration, not a replacement for established
    aberration-detection methods or health-department alert protocols.
    """

    if baseline_weeks < 2:
        raise ValueError("baseline_weeks must be at least two")
    if any(count < 0 for count in counts):
        raise ValueError("weekly counts cannot be negative")

    results: list[dict[str, float | int | bool | None]] = []
    for index, count in enumerate(counts):
        if index < baseline_weeks:
            results.append(
                {"week": index + 1, "count": count, "z_score": None, "signal": False}
            )
            continue

        baseline = counts[index - baseline_weeks : index]
        baseline_sd = stdev(baseline)
        z_score = 0.0 if baseline_sd == 0 else (count - mean(baseline)) / baseline_sd
        results.append(
            {
                "week": index + 1,
                "count": count,
                "z_score": z_score,
                "signal": z_score >= threshold,
            }
        )
    return results


def kaplan_meier(
    records: Sequence[tuple[int | float, int]],
) -> list[dict[str, float | int]]:
    """Calculate a Kaplan-Meier curve and Greenwood log-log confidence limits.

    Records are ``(time, event)`` pairs, where event is 1 for the event and 0
    for right-censoring. Returned rows include time zero and each event/censor
    time. Events are applied before censoring at tied times.
    """

    if not records:
        raise ValueError("At least one survival record is required")
    if any(time < 0 or event not in (0, 1) for time, event in records):
        raise ValueError("times must be nonnegative and event must be zero or one")

    times = sorted({float(time) for time, _ in records})
    n_at_risk = len(records)
    survival = 1.0
    greenwood_sum = 0.0
    curve: list[dict[str, float | int]] = [
        {
            "time": 0.0,
            "at_risk": n_at_risk,
            "events": 0,
            "censored": 0,
            "survival": 1.0,
            "lower_95": 1.0,
            "upper_95": 1.0,
        }
    ]

    for time in times:
        events = sum(1 for observed_time, event in records if observed_time == time and event == 1)
        censored = sum(1 for observed_time, event in records if observed_time == time and event == 0)

        if events:
            survival *= 1 - (events / n_at_risk)
            if n_at_risk > events:
                greenwood_sum += events / (n_at_risk * (n_at_risk - events))

        if survival in (0.0, 1.0):
            lower, upper = survival, survival
        else:
            log_log = log(-log(survival))
            log_log_se = sqrt(greenwood_sum) / abs(log(survival))
            lower = exp(-exp(log_log + Z_975 * log_log_se))
            upper = exp(-exp(log_log - Z_975 * log_log_se))

        curve.append(
            {
                "time": time,
                "at_risk": n_at_risk,
                "events": events,
                "censored": censored,
                "survival": survival,
                "lower_95": lower,
                "upper_95": upper,
            }
        )
        n_at_risk -= events + censored

    return curve


def median_event_time(curve: Sequence[Mapping[str, float | int]]) -> float | None:
    """Return the first time with Kaplan-Meier survival at or below 0.5."""

    for row in curve:
        if float(row["survival"]) <= 0.5:
            return float(row["time"])
    return None
