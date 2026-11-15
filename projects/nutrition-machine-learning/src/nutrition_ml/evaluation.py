"""Fixed-model evaluation; approximate stratified PSU-bootstrap intervals."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .modeling import metrics


def bootstrap_weights(frame, repeats=1000, seed=4217):
    """Rao-Wu-style n_h-1 resampling, with n_h/(n_h-1) rescaling.

    For the two masked PSUs per stratum this chooses one and doubles its weight.
    Models are held fixed: these intervals exclude training/selection uncertainty.
    """
    rng = np.random.default_rng(seed)
    factor = np.zeros((repeats, len(frame)))
    for _, block in frame.groupby("SDMVSTRA", sort=True):
        psus = sorted(block.SDMVPSU.unique())
        n = len(psus)
        if n < 2:
            raise ValueError("Cannot resample a singleton stratum; review cohort design")
        draws = rng.choice(psus, size=(repeats, n - 1), replace=True)
        for psu in psus:
            mask = ((frame.SDMVSTRA == block.SDMVSTRA.iloc[0]) & (frame.SDMVPSU == psu)).to_numpy()
            factor[:, mask] = ((draws == psu).sum(axis=1) * n / (n - 1))[:, None]
    return factor * frame.WTDR2D.to_numpy()[None, :]


def replicate_rmse(y, prediction, replicate_w):
    return np.sqrt((replicate_w @ ((prediction - y) ** 2)) / replicate_w.sum(axis=1))


def interval(values):
    return [float(x) for x in np.quantile(values, [0.025, 0.975])]


def evaluate(frame, predictions, selection, plan):
    if set(frame.cycle) != {plan["test_cycle"]}:
        raise ValueError("Test evaluation received an unexpected cycle")
    y, w = frame.LBXGH.to_numpy(), frame.WTDR2D.to_numpy()
    rw = bootstrap_weights(frame, plan["bootstrap_replicates"], plan["seed"])
    rows, rep = [], {}
    for key, pred in predictions.items():
        rep[key] = replicate_rmse(y, pred, rw)
        low, high = interval(rep[key])
        rows.append({"model": key, "n": len(frame), **metrics(y, pred, w),
                     "rmse_lower": low, "rmse_upper": high,
                     "unweighted_rmse": metrics(y, pred, np.ones(len(y)))["rmse"]})
    result = pd.DataFrame(rows)
    pairs = [("Selected pipelines", selection["champions"]["base"], selection["champions"]["diet"])]
    pairs += [(family, "base:" + family, "diet:" + family) for family in ["elastic", "forest", "boost"]]
    comparisons = []
    for name, base, diet in pairs:
        low, high = interval(rep[diet] - rep[base])
        point = metrics(y, predictions[diet], w)["rmse"] - metrics(y, predictions[base], w)["rmse"]
        comparisons.append({"comparison": name, "base_model": base, "diet_model": diet,
                            "rmse_difference": point, "lower": low, "upper": high})
    chosen = selection["champions"]["diet"]
    groups = []
    for dimension in ["age_group", "sex_group", "race_group"]:
        for group, indices in frame.groupby(dimension, observed=True).groups.items():
            mask = frame.index.isin(indices)
            n = int(mask.sum())
            row = {"dimension": dimension, "group": str(group), "n": n, "model": chosen}
            if n < plan["minimum_published_group_n"]:
                row["status"] = "suppressed"
            else:
                sub_rw = rw[:, mask]
                valid = sub_rw.sum(axis=1) > 0
                low, high = interval(replicate_rmse(y[mask], predictions[chosen][mask], sub_rw[valid]))
                row.update({"status": "reported", **metrics(y[mask], predictions[chosen][mask], w[mask]),
                            "rmse_lower": low, "rmse_upper": high})
            groups.append(row)
    sensitivity = []
    # Evaluation restriction only; models and preprocessing are not refit.
    for label, mask in [("Reports no diabetes diagnosis (DIQ010=2)", (frame.DIQ010 == 2).to_numpy()),
                        ("Complete base predictors", frame[plan["features_base"]].notna().all(axis=1).to_numpy())]:
        for fs in ["base", "diet"]:
            key = selection["champions"][fs]
            sensitivity.append({"subset": label, "feature_set": fs, "model": key, "n": int(mask.sum()),
                                **metrics(y[mask], predictions[key][mask], w[mask])})
    return result, pd.DataFrame(comparisons), pd.DataFrame(groups), pd.DataFrame(sensitivity)


def binned_diagnostics(frame, predictions, minimum=30):
    d = pd.DataFrame({"predicted": predictions, "observed": frame.LBXGH.to_numpy(), "weight": frame.WTDR2D.to_numpy()})
    d["bin"] = pd.qcut(d.predicted, 10, duplicates="drop")
    rows = []
    for _, group in d.groupby("bin", observed=True):
        if len(group) >= minimum:
            pred = np.average(group.predicted, weights=group.weight)
            obs = np.average(group.observed, weights=group.weight)
            rows.append({"n": len(group), "predicted": pred, "observed": obs, "residual": obs - pred})
    return pd.DataFrame(rows)


def ale_curve(model, dev, columns, variable, bins=10):
    """Weighted first-order accumulated local effects over development support."""
    valid = dev[variable].notna()
    x = dev.loc[valid, columns].copy()
    w = dev.loc[valid, "WTDR2D"].to_numpy()
    values = x[variable].to_numpy()
    edges = np.unique(np.quantile(values, np.linspace(0.05, 0.95, bins + 1)))
    assignment = np.searchsorted(edges, values, side="right") - 1
    assignment[values == edges[-1]] = len(edges) - 2
    effects, centers, weights, counts = [], [], [], []
    for k in range(len(edges) - 1):
        mask = (assignment == k) & (values >= edges[0]) & (values <= edges[-1])
        if mask.sum() == 0:
            continue
        low, high = x.loc[mask].copy(), x.loc[mask].copy()
        low[variable], high[variable] = edges[k], edges[k + 1]
        delta = model.predict(high) - model.predict(low)
        effects.append(np.average(delta, weights=w[mask]))
        centers.append((edges[k] + edges[k + 1]) / 2)
        weights.append(w[mask].sum())
        counts.append(int(mask.sum()))
    accumulated = np.cumsum(effects) - np.asarray(effects) / 2
    accumulated -= np.average(accumulated, weights=weights)
    return pd.DataFrame({"variable": variable, "value": centers, "effect": accumulated, "n": counts})
