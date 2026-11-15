import copy
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nutrition_ml.data import join_sources, derive_cohort, NUTRIENTS
from nutrition_ml.modeling import metrics, make_pipeline, fit_model, development_fit, features
from nutrition_ml.evaluation import bootstrap_weights, replicate_rmse, evaluate, ale_curve


def fixture(n=48):
    rng = np.random.default_rng(3)
    d = pd.DataFrame({"SEQN": np.arange(n), "age": rng.integers(20, 75, n), "female": np.arange(n) % 2,
                      "income_ratio": rng.uniform(0, 5, n), "bmi": rng.uniform(20, 35, n),
                      "waist_cm": rng.uniform(75, 115, n), "WTDR2D": rng.uniform(1, 10, n),
                      "LBXGH": rng.uniform(4, 7, n), "SDMVSTRA": np.arange(n) % 2,
                      "SDMVPSU": (np.arange(n) // 2) % 2 + 1, "cycle": "2015-2016"})
    d["psu_group"] = d.SDMVSTRA.astype(str) + ":" + d.SDMVPSU.astype(str)
    for variable in NUTRIENTS:
        d[variable] = rng.uniform(1, 10, n)
    return d


class MetricsTests(unittest.TestCase):
    def test_weighted_metrics(self):
        m = metrics([1, 3], [2, 2], [1, 3])
        self.assertAlmostEqual(m["rmse"], 1)
        self.assertAlmostEqual(m["mae"], 1)
        self.assertAlmostEqual(m["bias"], -.5)

    def test_weight_scale_invariance(self):
        self.assertEqual(metrics([1, 3], [2, 4], [1, 3]), metrics([1, 3], [2, 4], [10, 30]))

    def test_reject_bad_weights(self):
        for w in [[0, 0], [-1, 2], [1, np.nan]]:
            with self.assertRaises(ValueError):
                metrics([1, 2], [1, 2], w)

    def test_reject_missing_target(self):
        with self.assertRaises(ValueError):
            metrics([1, np.nan], [1, 2], [1, 1])

    def test_zero_variance_r2(self):
        self.assertIsNone(metrics([1, 1], [2, 2], [1, 1])["r2"])


class BootstrapTests(unittest.TestCase):
    def test_cluster_and_stratum_structure(self):
        d = fixture()
        rw = bootstrap_weights(d, 20, 10)
        factor = rw / d.WTDR2D.to_numpy()
        self.assertEqual(set(np.unique(factor)), {0., 2.})
        for _, g in d.groupby("psu_group"):
            self.assertTrue(np.all(factor[:, g.index] == factor[:, g.index[0]][:, None]))
        for _, g in d.groupby("SDMVSTRA"):
            one, two = g[g.SDMVPSU == 1].index[0], g[g.SDMVPSU == 2].index[0]
            np.testing.assert_array_equal(factor[:, one] + factor[:, two], np.full(20, 2.))

    def test_reproducible(self):
        d = fixture()
        np.testing.assert_array_equal(bootstrap_weights(d, 10), bootstrap_weights(d, 10))

    def test_singleton_rejected(self):
        d = fixture()
        with self.assertRaises(ValueError):
            bootstrap_weights(d[d.SDMVPSU == 1], 10)

    def test_identical_paired_models_have_zero_difference(self):
        d = fixture()
        rw = bootstrap_weights(d, 10)
        a = replicate_rmse(d.LBXGH.to_numpy(), np.full(len(d), 5), rw)
        np.testing.assert_array_equal(a - a, np.zeros(10))


class DataTests(unittest.TestCase):
    def test_duplicate_join_keys_rejected(self):
        with self.assertRaises(ValueError):
            join_sources([pd.DataFrame({"SEQN": [1, 1]})])

    def test_left_join_preserves_denominator(self):
        out = join_sources([pd.DataFrame({"SEQN": [1, 2]}), pd.DataFrame({"SEQN": [1], "x": [4]})])
        self.assertEqual(len(out), 2)
        self.assertTrue(pd.isna(out.loc[1, "x"]))

    def test_density_and_outcome_exclusion(self):
        d = pd.DataFrame({"SEQN": [1, 2, 3, 4], "RIDAGEYR": [25] * 4, "RIAGENDR": [2] * 4,
                          "RIDEXPRG": [np.nan] * 4, "INDFMPIR": [2] * 4, "BMXBMI": [25] * 4,
                          "BMXWAIST": [80] * 4, "RIDRETH3": [3] * 4, "DIQ010": [2] * 4,
                          "SDMVSTRA": [1] * 4, "SDMVPSU": [1, 2, 1, 2], "WTDR2D": [1] * 4,
                          "DR1DRSTZ": [1] * 4, "DR2DRSTZ": [1, 1, 1, 5], "LBXGH": [5, 5, np.nan, 5]})
        for suffix in NUTRIENTS.values():
            d["DR1T" + suffix] = 10
            d["DR2T" + suffix] = 30
        d["DR1TKCAL"], d["DR2TKCAL"] = 1000, 3000
        d.loc[1, "DR2TFIBE"] = np.nan
        cohort, _, _ = derive_cohort(d, "2015-2016")
        self.assertEqual(len(cohort), 2)
        self.assertEqual(cohort.loc[0, "fiber_density"], 10)
        self.assertTrue(pd.isna(cohort.loc[1, "fiber_density"]))


class LeakageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads((ROOT / "config/analysis-plan.json").read_text())

    def test_predictor_allowlist(self):
        for fs in ["base", "diet"]:
            self.assertFalse(set(features(self.plan, fs)) & set(self.plan["excluded_from_predictors"]))

    def test_imputer_uses_training_only(self):
        d = fixture()
        d.loc[0, "bmi"] = np.nan
        model = fit_model(make_pipeline(self.plan["candidates"][1], 1), d, ["bmi"])
        before = model.named_steps["impute"].statistics_.copy()
        model.predict(pd.DataFrame({"bmi": [10000., np.nan]}))
        np.testing.assert_array_equal(before, model.named_steps["impute"].statistics_)
        self.assertAlmostEqual(before[0], d.bmi.median())

    def test_selection_rejects_test_cycle(self):
        d = fixture()
        d["cycle"] = "2017-2018"
        with self.assertRaises(ValueError):
            development_fit(d, self.plan)

    def test_cv_has_no_shared_psus(self):
        plan = copy.deepcopy(self.plan)
        plan["candidates"] = self.plan["candidates"][:2]
        _, selection, _, audit = development_fit(fixture(), plan)
        self.assertTrue((audit.overlapping_psus == 0).all())
        self.assertFalse(selection["selection_uses_test_outcomes"])

    def test_evaluation_rejects_development_cycle(self):
        with self.assertRaises(ValueError):
            evaluate(fixture(), {}, {}, self.plan)

    def test_unknown_model_fails(self):
        with self.assertRaises(ValueError):
            make_pipeline({"family": "unknown", "params": {}}, 1)

    def test_constant_model_ale_is_zero(self):
        d = fixture()
        m = fit_model(make_pipeline(self.plan["candidates"][0], 1), d, ["bmi"])
        curve = ale_curve(m, d, ["bmi"], "bmi")
        np.testing.assert_allclose(curve.effect, 0)


if __name__ == "__main__":
    unittest.main()
