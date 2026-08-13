"""Regression tests for the Public Health Methods Lab."""

from __future__ import annotations

import math
import sys
import unittest
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


class TestEpidemiologyMethods(unittest.TestCase):
    def test_standardized_rate_matches_common_stratum_rate(self) -> None:
        strata = [
            {"age_group": "younger", "cases": 10, "person_time": 10_000},
            {"age_group": "older", "cases": 20, "person_time": 20_000},
        ]
        result = direct_standardized_rate(strata, {"younger": 3, "older": 2})
        self.assertAlmostEqual(result["crude_rate"], 100.0)
        self.assertAlmostEqual(result["standardized_rate"], 100.0)

    def test_risk_ratio_and_interval(self) -> None:
        result = risk_ratio(29, 58, 9, 72)
        self.assertAlmostEqual(result["risk_ratio"], 4.0)
        self.assertLess(result["lower_95"], 4.0)
        self.assertGreater(result["upper_95"], 4.0)

    def test_nutrient_density(self) -> None:
        self.assertAlmostEqual(nutrient_density(24, 2_000), 12.0)
        with self.assertRaises(ValueError):
            nutrient_density(24, 0)

    def test_mean_difference(self) -> None:
        result = mean_difference([2.0, 3.0, 4.0], [1.0, 2.0, 3.0])
        self.assertAlmostEqual(result["difference"], 1.0)
        self.assertLess(result["lower_95"], 1.0)
        self.assertGreater(result["upper_95"], 1.0)

    def test_surveillance_flags_large_increase(self) -> None:
        results = weekly_z_signals([8, 9, 7, 10, 9, 11, 8, 10, 29])
        self.assertTrue(results[-1]["signal"])
        self.assertIsNone(results[0]["z_score"])

    def test_kaplan_meier_is_monotone(self) -> None:
        curve = kaplan_meier([(1, 1), (2, 0), (3, 1), (4, 1)])
        survival = [float(row["survival"]) for row in curve]
        self.assertTrue(all(left >= right for left, right in zip(survival, survival[1:])))
        self.assertTrue(all(0 <= value <= 1 for value in survival))
        self.assertEqual(median_event_time(curve), 3.0)
        self.assertTrue(math.isclose(survival[2], survival[1]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
