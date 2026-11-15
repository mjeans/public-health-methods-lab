"""Development-only model selection with PSU-grouped cross-validation."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FAMILY_NAMES = {"mean": "Weighted mean", "elastic": "Elastic net", "forest": "Random forest", "boost": "Gradient boosting"}


def make_pipeline(candidate, seed):
    family, params = candidate["family"], candidate["params"]
    if family == "mean":
        estimator = DummyRegressor(strategy="mean")
    elif family == "elastic":
        estimator = ElasticNet(**params, max_iter=20000, tol=1e-7)
    elif family == "forest":
        estimator = RandomForestRegressor(**params, random_state=seed, n_jobs=1)
    elif family == "boost":
        estimator = HistGradientBoostingRegressor(**params, early_stopping=False, random_state=seed)
    else:
        raise ValueError(f"Unknown model family: {family}")
    return Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
                     ("scale", StandardScaler()), ("model", estimator)])


def features(plan, feature_set):
    if feature_set not in {"base", "diet"}:
        raise ValueError("Unknown feature set")
    return plan["features_base"] + (plan["features_diet"] if feature_set == "diet" else [])


def fit_model(model, data, columns):
    w = data.WTDR2D.to_numpy(float)
    # Normalize training weights for stable regularization; preserve relative weights.
    model.fit(data[columns], data.LBXGH, model__sample_weight=w / w.mean())
    return model


def metrics(y, pred, w):
    y, pred, w = (np.asarray(v, float) for v in (y, pred, w))
    if not (y.shape == pred.shape == w.shape) or y.ndim != 1:
        raise ValueError("Outcome, prediction and weight vectors must have matching one-dimensional shapes")
    if not all(np.isfinite(v).all() for v in (y, pred, w)) or np.any(w < 0) or w.sum() <= 0:
        raise ValueError("Finite values and nonnegative weights with positive total required")
    err = pred - y
    mse = np.average(err ** 2, weights=w)
    var = np.average((y - np.average(y, weights=w)) ** 2, weights=w)
    return {"rmse": float(np.sqrt(mse)), "mae": float(np.average(abs(err), weights=w)),
            "bias": float(np.average(err, weights=w)), "r2": float(1 - mse / var) if var > 0 else None}


def development_fit(dev, plan):
    if set(dev.cycle) != {plan["development_cycle"]}:
        raise ValueError("Model selection must only receive the development cycle")
    splitter = GroupKFold(n_splits=plan["cv_folds"])
    folds = list(splitter.split(dev, groups=dev.psu_group))
    oof_rows, folds_audit, bundles = [], [], {}
    for fold, (a, b) in enumerate(folds):
        if set(dev.iloc[a].psu_group) & set(dev.iloc[b].psu_group):
            raise ValueError("PSU leaks across a CV fold")
        folds_audit.append({"fold": fold + 1, "train_n": len(a), "validation_n": len(b),
                            "train_psus": int(dev.iloc[a].psu_group.nunique()),
                            "validation_psus": int(dev.iloc[b].psu_group.nunique()), "overlapping_psus": 0})
    for feature_set in ["base", "diet"]:
        cols = features(plan, feature_set)
        for order, candidate in enumerate(plan["candidates"]):
            if feature_set == "diet" and candidate["family"] == "mean":
                continue
            predictions = np.full(len(dev), np.nan)
            for a, b in folds:
                model = fit_model(make_pipeline(candidate, plan["seed"]), dev.iloc[a], cols)
                predictions[b] = model.predict(dev.iloc[b][cols])
            result = metrics(dev.LBXGH, predictions, dev.WTDR2D)
            oof_rows.append({"feature_set": feature_set, "candidate": candidate["id"],
                             "family": candidate["family"], "order": order, **result})
            print(f"Development CV: {feature_set} / {candidate['id']} RMSE={result['rmse']:.4f}", flush=True)
    cv = pd.DataFrame(oof_rows)
    chosen = []
    for (fs, family), rows in cv.groupby(["feature_set", "family"], sort=True):
        row = rows.sort_values(["rmse", "order"]).iloc[0]
        candidate = next(c for c in plan["candidates"] if c["id"] == row.candidate)
        key = fs + ":" + family
        bundles[key] = fit_model(make_pipeline(candidate, plan["seed"]), dev, features(plan, fs))
        chosen.append({"key": key, "candidate": candidate, "cv_rmse": float(row.rmse)})
    champions = {fs: min([c for c in chosen if c["key"].startswith(fs + ":")],
                         key=lambda c: (c["cv_rmse"], c["key"]))["key"] for fs in ["base", "diet"]}
    # The mean baseline is shared and must remain eligible for both comparisons.
    mean = next(c for c in chosen if c["key"] == "base:mean")
    if mean["cv_rmse"] < next(c["cv_rmse"] for c in chosen if c["key"] == champions["diet"]):
        champions["diet"] = "base:mean"
    selection = {"development_cycle": plan["development_cycle"], "test_cycle": plan["test_cycle"],
                 "plan_sha256": hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(),
                 "selection_uses_test_outcomes": False, "selected": chosen, "champions": champions,
                 "development_n": len(dev), "development_psus": int(dev.psu_group.nunique())}
    return bundles, selection, cv, pd.DataFrame(folds_audit)
