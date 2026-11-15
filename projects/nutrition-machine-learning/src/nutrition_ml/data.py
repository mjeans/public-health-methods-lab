"""Fetch only CDC public-use XPTs; enforce provenance and one-to-one joins."""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

CYCLES = {"2015-2016": (2015, "I"), "2017-2018": (2017, "J")}
NUTRIENTS = {"energy_kcal": "KCAL", "fiber_density": "FIBE", "sugar_density": "SUGR",
             "saturated_fat_density": "SFAT", "protein_density": "PROT", "sodium_density": "SODI"}


def sources():
    return [{"cycle": cycle, "file": f"{component}_{suffix}.XPT",
             "url": f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{component}_{suffix}.XPT"}
            for cycle, (year, suffix) in CYCLES.items()
            for component in ["DEMO", "DR1TOT", "DR2TOT", "BMX", "GHB", "DIQ"]]


def fetch_all(root: Path):
    raw = root / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    lock_path = root / "data/source-manifest.json"
    locked = {r["file"]: r["sha256"] for r in json.loads(lock_path.read_text())["sources"]} if lock_path.exists() else {}
    manifest = []
    for source in sources():
        path = raw / source["file"]
        if not path.exists():
            for attempt in range(3):
                try:
                    req = urllib.request.Request(source["url"], headers={"User-Agent": "mjeans-nutrition-ml/1.0"})
                    with urllib.request.urlopen(req, timeout=45) as response:
                        payload = response.read(50_000_001)
                    if len(payload) > 50_000_000 or not payload.startswith(b"HEADER RECORD"):
                        raise ValueError("Expected SAS XPORT, not an HTML error or oversized file")
                    path.write_bytes(payload)
                    break
                except (OSError, ValueError):
                    if attempt == 2:
                        raise
                    time.sleep(1 + attempt)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if locked and locked.get(source["file"]) != digest:
            raise ValueError(f"Source checksum changed: {source['file']}; review upstream before updating manifest")
        manifest.append({**source, "sha256": digest, "bytes": path.stat().st_size})
        print(f"Verified {source['file']}", flush=True)
    return {"sources": manifest}


def join_sources(frames):
    result = frames[0]
    for f in frames:
        if f.SEQN.isna().any() or not f.SEQN.is_unique:
            raise ValueError("Source SEQN must be unique and nonmissing")
    for frame in frames[1:]:
        result = result.merge(frame, on="SEQN", how="left", validate="one_to_one")
    return result


def build_cohort(root: Path, cycle: str):
    suffix = CYCLES[cycle][1]
    fields = {
        "DEMO": ["SEQN", "RIDAGEYR", "RIAGENDR", "RIDEXPRG", "INDFMPIR", "RIDRETH3", "SDMVSTRA", "SDMVPSU"],
        "DR1TOT": ["SEQN", "WTDR2D", "DR1DRSTZ"] + [f"DR1T{x}" for x in NUTRIENTS.values()],
        "DR2TOT": ["SEQN", "DR2DRSTZ"] + [f"DR2T{x}" for x in NUTRIENTS.values()],
        "BMX": ["SEQN", "BMXBMI", "BMXWAIST"], "GHB": ["SEQN", "LBXGH"], "DIQ": ["SEQN", "DIQ010"]}
    frames = [pd.read_sas(root / f"data/raw/{component}_{suffix}.XPT", format="xport")[cols]
              for component, cols in fields.items()]
    return derive_cohort(join_sources(frames), cycle)


def derive_cohort(frame, cycle):
    d = frame.copy()
    flow = []
    def retain(mask, name):
        nonlocal d
        before = len(d)
        d = d.loc[mask].copy()
        flow.append({"cycle": cycle, "step": name, "remaining": len(d), "excluded": before - len(d)})
    flow.append({"cycle": cycle, "step": "Source demographics", "remaining": len(d), "excluded": 0})
    retain(d.RIDAGEYR >= 20, "Age 20 or older")
    retain(d.RIDEXPRG != 1, "Not known pregnant (unknown retained)")
    retain((d.DR1DRSTZ == 1) & (d.DR2DRSTZ == 1) & (d.WTDR2D > 0), "Two reliable recalls and positive WTDR2D")
    missing = [{"cycle": cycle, "variable": col, "missing_n": int(d[col].isna().sum()), "denominator_n": len(d)}
               for col in ["LBXGH", "BMXBMI", "BMXWAIST", "INDFMPIR", "DIQ010"]]
    retain(d.LBXGH.notna() & np.isfinite(d.LBXGH), "Measured HbA1c available (never imputed)")
    retain(d.SDMVSTRA.notna() & d.SDMVPSU.notna(), "Survey design fields available")
    for name, suffix in NUTRIENTS.items():
        a, b = d[f"DR1T{suffix}"], d[f"DR2T{suffix}"]
        # Arithmetic mean of both recalls; do not replace a missing recall with one day.
        d[name] = (a + b) / 2
    retain((d.energy_kcal > 0) & np.isfinite(d.energy_kcal), "Positive two-day energy")
    for name in NUTRIENTS:
        if name != "energy_kcal":
            d[name] = 1000 * d[name] / d.energy_kcal
    d = d.rename(columns={"RIDAGEYR": "age", "INDFMPIR": "income_ratio", "BMXBMI": "bmi", "BMXWAIST": "waist_cm"})
    if not d.RIAGENDR.isin([1, 2]).all():
        raise ValueError("Unexpected sex code")
    d["female"] = (d.RIAGENDR == 2).astype(float)
    d["cycle"] = cycle
    d["psu_group"] = d.SDMVSTRA.astype(int).astype(str) + ":" + d.SDMVPSU.astype(int).astype(str)
    d["age_group"] = pd.cut(d.age, [19, 39, 59, np.inf], labels=["20-39", "40-59", "60+"]).astype(str)
    d["sex_group"] = d.RIAGENDR.map({1: "Male", 2: "Female"})
    d["race_group"] = d.RIDRETH3.map({1: "Mexican American", 2: "Other Hispanic", 3: "Non-Hispanic White", 4: "Non-Hispanic Black", 6: "Non-Hispanic Asian", 7: "Other / multiracial"})
    return d.sort_values("SEQN").reset_index(drop=True), flow, missing
