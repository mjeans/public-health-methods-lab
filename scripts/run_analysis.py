"""Generate the deterministic outputs for the Public Health Methods Lab."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from public_health_methods import (  # noqa: E402
    direct_standardized_rate,
    kaplan_meier,
    mean_difference,
    median_event_time,
    nutrient_density,
    risk_ratio,
    weekly_z_signals,
)


OUTPUTS = ROOT / "outputs"
ASSETS = ROOT / "assets"
STANDARD_POPULATION = {"0-17": 22, "18-44": 36, "45-64": 24, "65+": 18}

SURVEILLANCE = {
    "North": [("0-17", 18, 24_000), ("18-44", 34, 38_000), ("45-64", 32, 21_000), ("65+", 29, 12_000)],
    "Central": [("0-17", 21, 28_000), ("18-44", 39, 42_000), ("45-64", 29, 25_000), ("65+", 25, 15_000)],
    "South": [("0-17", 27, 22_000), ("18-44", 46, 34_000), ("45-64", 38, 18_000), ("65+", 33, 10_000)],
    "Harbor": [("0-17", 15, 19_000), ("18-44", 28, 31_000), ("45-64", 25, 17_000), ("65+", 24, 9_000)],
}

WEEKLY_COUNTS = [8, 9, 7, 10, 9, 11, 8, 10, 12, 13, 29, 18]

RETENTION_RECORDS = {
    "Enhanced outreach": [
        (8, 1), (12, 0), (15, 1), (18, 0), (21, 1), (24, 0), (28, 1),
        (32, 0), (36, 1), (40, 0), (45, 0), (50, 1), (55, 0), (60, 0),
        (65, 1), (70, 0), (75, 0), (80, 1), (85, 0), (90, 0),
    ],
    "Standard outreach": [
        (5, 1), (8, 1), (10, 0), (12, 1), (15, 1), (18, 0), (20, 1),
        (24, 1), (28, 0), (30, 1), (35, 1), (40, 0), (45, 1), (50, 0),
        (55, 1), (60, 0), (65, 1), (70, 0), (80, 1), (90, 0),
    ],
}

# Person-level means from two hypothetical 24-hour recalls. The paired recall
# days are constructed around these values so the workflow remains compact and
# deterministic while still demonstrating within-person averaging.
NUTRITION_PEOPLE = {
    "Nutrition education": [
        (1_950, 23, 2_400), (2_100, 31, 2_200), (2_250, 27, 2_700),
        (2_000, 35, 2_050), (2_180, 25, 2_600), (2_320, 33, 2_350),
        (2_080, 29, 2_800), (2_240, 24, 2_250), (1_880, 32, 2_450),
        (2_160, 28, 2_900),
    ],
    "Comparison": [
        (2_050, 20, 3_100), (2_220, 16, 3_500), (2_380, 25, 2_950),
        (2_100, 18, 3_300), (2_300, 27, 3_650), (2_450, 19, 3_200),
        (2_180, 23, 3_700), (2_360, 17, 3_000), (1_980, 26, 3_400),
        (2_260, 21, 3_550),
    ],
}


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def rate_results() -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for district, values in SURVEILLANCE.items():
        strata = [
            {"age_group": age, "cases": cases, "person_time": person_time}
            for age, cases, person_time in values
        ]
        estimate = direct_standardized_rate(strata, STANDARD_POPULATION)
        output.append(
            {
                "district": district,
                "cases": sum(item[1] for item in values),
                "person_weeks": sum(item[2] for item in values),
                **{key: round(value, 2) for key, value in estimate.items()},
            }
        )
    return output


def retention_results() -> tuple[list[dict[str, object]], dict[str, float | None]]:
    rows: list[dict[str, object]] = []
    medians: dict[str, float | None] = {}
    for group, records in RETENTION_RECORDS.items():
        curve = kaplan_meier(records)
        medians[group] = median_event_time(curve)
        for row in curve:
            rows.append(
                {
                    "group": group,
                    **{
                        key: round(value, 4) if isinstance(value, float) else value
                        for key, value in row.items()
                    },
                }
            )
    return rows, medians


def nutrition_results() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    person_rows: list[dict[str, object]] = []
    for group, people in NUTRITION_PEOPLE.items():
        for index, (energy_mean, fiber_mean, sodium_mean) in enumerate(people, start=1):
            recalls = [
                (energy_mean - 100, fiber_mean - 2, sodium_mean + 150),
                (energy_mean + 100, fiber_mean + 2, sodium_mean - 150),
            ]
            energy = sum(row[0] for row in recalls) / len(recalls)
            fiber = sum(row[1] for row in recalls) / len(recalls)
            sodium = sum(row[2] for row in recalls) / len(recalls)
            person_rows.append(
                {
                    "participant_id": f"{group[0]}{index:02d}",
                    "group": group,
                    "completed_recalls": len(recalls),
                    "mean_energy_kcal": energy,
                    "fiber_g_per_1000_kcal": nutrient_density(fiber, energy),
                    "sodium_mg_per_1000_kcal": nutrient_density(sodium, energy),
                }
            )

    summaries: list[dict[str, object]] = []
    for group in NUTRITION_PEOPLE:
        group_rows = [row for row in person_rows if row["group"] == group]
        summaries.append(
            {
                "group": group,
                "participants": len(group_rows),
                "complete_two_recall_percent": 100.0,
                "mean_energy_kcal": round(
                    sum(float(row["mean_energy_kcal"]) for row in group_rows)
                    / len(group_rows),
                    1,
                ),
                "mean_fiber_g_per_1000_kcal": round(
                    sum(float(row["fiber_g_per_1000_kcal"]) for row in group_rows)
                    / len(group_rows),
                    2,
                ),
                "mean_sodium_mg_per_1000_kcal": round(
                    sum(float(row["sodium_mg_per_1000_kcal"]) for row in group_rows)
                    / len(group_rows),
                    1,
                ),
            }
        )

    contrasts: list[dict[str, object]] = []
    for field, label in (
        ("fiber_g_per_1000_kcal", "Fiber (g per 1,000 kcal)"),
        ("sodium_mg_per_1000_kcal", "Sodium (mg per 1,000 kcal)"),
    ):
        group_a = [
            float(row[field])
            for row in person_rows
            if row["group"] == "Nutrition education"
        ]
        group_b = [
            float(row[field])
            for row in person_rows
            if row["group"] == "Comparison"
        ]
        estimate = mean_difference(group_a, group_b)
        contrasts.append(
            {
                "measure": label,
                "contrast": "Nutrition education minus comparison",
                **{key: round(value, 3) for key, value in estimate.items()},
            }
        )
    return summaries, contrasts


def write_rate_svg(rows: list[dict[str, object]]) -> None:
    width, height = 760, 420
    chart_left, chart_bottom, chart_height = 95, 345, 265
    max_rate = max(float(row["upper_95"]) for row in rows) * 1.10
    bar_width = 92
    gap = 55
    colors = ["#0f766e", "#2563eb", "#dc2626", "#7c3aed"]
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="36" y="42" font-family="Arial" font-size="22" font-weight="700" fill="#0f172a">Age-standardized surveillance rates</text>',
        '<text x="36" y="67" font-family="Arial" font-size="13" fill="#475569">Synthetic cases per 100,000 person-weeks; bars show approximate 95% CIs</text>',
        f'<line x1="{chart_left}" y1="{chart_bottom}" x2="700" y2="{chart_bottom}" stroke="#94a3b8"/>',
    ]
    for tick in range(0, int(max_rate) + 1, 50):
        y = chart_bottom - (tick / max_rate) * chart_height
        pieces.extend(
            [
                f'<line x1="{chart_left}" y1="{y:.1f}" x2="700" y2="{y:.1f}" stroke="#e2e8f0"/>',
                f'<text x="82" y="{y + 4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="#64748b">{tick}</text>',
            ]
        )
    for index, row in enumerate(rows):
        x = chart_left + 38 + index * (bar_width + gap)
        rate = float(row["standardized_rate"])
        lower = float(row["lower_95"])
        upper = float(row["upper_95"])
        y = chart_bottom - (rate / max_rate) * chart_height
        bar_height = chart_bottom - y
        y_low = chart_bottom - (lower / max_rate) * chart_height
        y_high = chart_bottom - (upper / max_rate) * chart_height
        pieces.extend(
            [
                f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" rx="5" fill="{colors[index]}"/>',
                f'<line x1="{x + bar_width / 2}" y1="{y_high:.1f}" x2="{x + bar_width / 2}" y2="{y_low:.1f}" stroke="#0f172a" stroke-width="2"/>',
                f'<line x1="{x + 30}" y1="{y_high:.1f}" x2="{x + 62}" y2="{y_high:.1f}" stroke="#0f172a" stroke-width="2"/>',
                f'<line x1="{x + 30}" y1="{y_low:.1f}" x2="{x + 62}" y2="{y_low:.1f}" stroke="#0f172a" stroke-width="2"/>',
                f'<text x="{x + bar_width / 2}" y="{y - 9:.1f}" text-anchor="middle" font-family="Arial" font-size="12" font-weight="700" fill="#0f172a">{rate:.1f}</text>',
                f'<text x="{x + bar_width / 2}" y="371" text-anchor="middle" font-family="Arial" font-size="12" fill="#334155">{row["district"]}</text>',
            ]
        )
    pieces.append('</svg>')
    (ASSETS / "age-standardized-rates.svg").write_text(
        "\n".join(pieces), encoding="utf-8", newline="\n"
    )


def write_km_svg(rows: list[dict[str, object]]) -> None:
    width, height = 760, 420
    left, bottom, plot_width, plot_height = 90, 345, 610, 255
    colors = {"Enhanced outreach": "#0f766e", "Standard outreach": "#dc2626"}
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="36" y="42" font-family="Arial" font-size="22" font-weight="700" fill="#0f172a">Retention in care</text>',
        '<text x="36" y="67" font-family="Arial" font-size="13" fill="#475569">Kaplan-Meier estimate; event is disengagement from a synthetic care program</text>',
        f'<line x1="{left}" y1="{bottom}" x2="{left + plot_width}" y2="{bottom}" stroke="#94a3b8"/>',
        f'<line x1="{left}" y1="{bottom - plot_height}" x2="{left}" y2="{bottom}" stroke="#94a3b8"/>',
    ]
    for tick in (0, 0.25, 0.5, 0.75, 1.0):
        y = bottom - tick * plot_height
        pieces.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" stroke="#e2e8f0"/>',
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="#64748b">{tick:.2f}</text>',
            ]
        )
    for tick in (0, 30, 60, 90):
        x = left + tick / 90 * plot_width
        pieces.append(f'<text x="{x:.1f}" y="368" text-anchor="middle" font-family="Arial" font-size="11" fill="#64748b">{tick}</text>')

    for group, color in colors.items():
        group_rows = [row for row in rows if row["group"] == group]
        path_parts = [f'M {left} {bottom - plot_height}']
        previous_survival = 1.0
        for row in group_rows[1:]:
            x = left + float(row["time"]) / 90 * plot_width
            current_survival = float(row["survival"])
            old_y = bottom - previous_survival * plot_height
            new_y = bottom - current_survival * plot_height
            path_parts.extend([f'H {x:.1f}', f'V {new_y:.1f}'])
            previous_survival = current_survival
        path_parts.append(f'H {left + plot_width}')
        pieces.append(f'<path d="{" ".join(path_parts)}" fill="none" stroke="{color}" stroke-width="3"/>')

    pieces.extend(
        [
            '<line x1="438" y1="105" x2="470" y2="105" stroke="#0f766e" stroke-width="3"/><text x="478" y="110" font-family="Arial" font-size="12" fill="#334155">Enhanced outreach</text>',
            '<line x1="438" y1="128" x2="470" y2="128" stroke="#dc2626" stroke-width="3"/><text x="478" y="133" font-family="Arial" font-size="12" fill="#334155">Standard outreach</text>',
            '<text x="395" y="402" text-anchor="middle" font-family="Arial" font-size="12" fill="#334155">Days since enrollment</text>',
            '<text x="20" y="225" transform="rotate(-90 20 225)" text-anchor="middle" font-family="Arial" font-size="12" fill="#334155">Probability retained</text>',
            '</svg>',
        ]
    )
    (ASSETS / "retention-curves.svg").write_text(
        "\n".join(pieces), encoding="utf-8", newline="\n"
    )


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    rates = rate_results()
    write_csv(OUTPUTS / "age_standardized_rates.csv", rates)

    signals = weekly_z_signals(WEEKLY_COUNTS)
    signal_rows = [
        {
            "week": row["week"],
            "count": row["count"],
            "z_score": "" if row["z_score"] is None else round(float(row["z_score"]), 3),
            "signal": row["signal"],
        }
        for row in signals
    ]
    write_csv(OUTPUTS / "weekly_surveillance_signals.csv", signal_rows)

    outbreak = risk_ratio(29, 58, 9, 72)
    write_csv(
        OUTPUTS / "outbreak_risk_ratio.csv",
        [{key: round(value, 4) for key, value in outbreak.items()}],
    )

    retention, medians = retention_results()
    write_csv(OUTPUTS / "retention_curve.csv", retention)

    nutrition_summaries, nutrition_contrasts = nutrition_results()
    write_csv(OUTPUTS / "nutrition_density_summary.csv", nutrition_summaries)
    write_csv(OUTPUTS / "nutrition_group_contrasts.csv", nutrition_contrasts)
    write_rate_svg(rates)
    write_km_svg(retention)

    highest = max(rates, key=lambda row: float(row["standardized_rate"]))
    flagged_weeks = [row["week"] for row in signals if row["signal"]]
    enhanced_median = medians["Enhanced outreach"]
    standard_median = medians["Standard outreach"]
    fiber_contrast = next(
        row for row in nutrition_contrasts if str(row["measure"]).startswith("Fiber")
    )
    sodium_contrast = next(
        row for row in nutrition_contrasts if str(row["measure"]).startswith("Sodium")
    )
    summary = f"""# Reproducible reference results

These outputs are generated from deterministic synthetic data.

- **Highest age-standardized rate:** {highest['district']} at {float(highest['standardized_rate']):.1f} cases per 100,000 person-weeks (95% CI {float(highest['lower_95']):.1f}–{float(highest['upper_95']):.1f}).
- **Surveillance signal:** week {', '.join(str(week) for week in flagged_weeks)} crossed the illustrative rolling z-score threshold.
- **Outbreak association:** shared-meal exposure was associated with a risk ratio of {outbreak['risk_ratio']:.2f} (95% CI {outbreak['lower_95']:.2f}–{outbreak['upper_95']:.2f}).
- **Median time to disengagement:** {enhanced_median if enhanced_median is not None else 'not reached'} days with enhanced outreach and {standard_median if standard_median is not None else 'not reached'} days with standard outreach.
- **Nutrition epidemiology:** the synthetic nutrition-education group had {float(fiber_contrast['difference']):.2f} more grams of fiber and {abs(float(sodium_contrast['difference'])):.1f} fewer milligrams of sodium per 1,000 kcal than the comparison group.

These results demonstrate implementation, not real-world evidence. The data are synthetic, the surveillance threshold is illustrative, and the outreach comparison is descriptive rather than causal.
"""
    (OUTPUTS / "summary.md").write_text(summary, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
