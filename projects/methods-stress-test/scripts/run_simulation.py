"""Run the fixed stress-test design; publish aggregate evidence only."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from methods import LABELS, simulate_one, summarize
from figures import make_figures


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: f"{v:.10f}" if isinstance(v, (float, np.floating)) else v for k,v in row.items()})


def run(design, repetitions):
    summary, paired = [], []
    for c in design["scenarios"]:
        results, fractions = {}, []
        for repetition in range(repetitions):
            estimates, extra = simulate_one(c, repetition, design["seed"])
            fractions.append(extra["observed_fraction"])
            for method, values in estimates.items():
                results.setdefault(method, []).append(values)
        for method, values in results.items():
            row = dict(scenario=c["id"],family=c["family"],method=method,truth=c["truth"],
                       n=c.get("n", c.get("schools",0)*c.get("pupils_per_school",0)),
                       error_sd=c.get("error_sd",""),error_correlation=c.get("error_correlation",""),
                       mechanism=c.get("mechanism",""),schools=c.get("schools",""),icc=c.get("icc",""),
                       observed_fraction=float(np.mean(fractions)))
            row.update(summarize(values, c["truth"], repetitions))
            summary.append(row)
        first = next(iter(results))
        base = np.asarray(results[first])
        bc = (base[:,2] <= c["truth"]) & (c["truth"] <= base[:,3])
        for method, values in results.items():
            if method == first:
                continue
            a = np.asarray(values)
            d = a[:,0]-base[:,0]
            dc = ((a[:,2] <= c["truth"]) & (c["truth"] <= a[:,3])).astype(float)-bc
            paired.append(dict(scenario=c["id"],reference=first,method=method,
                mean_estimate_difference=float(d.mean()),difference_mcse=float(d.std(ddof=1)/np.sqrt(repetitions)),
                coverage_difference=float(dc.mean()),coverage_difference_mcse=float(dc.std(ddof=1)/np.sqrt(repetitions))))
        print(f"Scenario {c['id']} {c['family']}: {repetitions} repetitions", flush=True)
    return summary, paired


def report(rows, reps, digest):
    lines = ["# When methods fail: executed simulation",
             "",f"**{reps:,} repetitions per scenario; 23 scenarios.** Fixed seed streams. All observations are synthetic.",
             "", "Three controlled experiments isolate measurement error, selective missingness, and clustering. They are not a factorial reconstruction of any published study.",
             "", "## Measurement error", "", "![Measurement error](../assets/measurement-error.svg)",
             "", "Calibration uses a known error variance and assumes independent recall errors. It is a favorable benchmark, not a validated real-data correction. Latent exposure is an unavailable-in-practice oracle.",
             "", "## Missing outcomes", "", "![Missing outcomes](../assets/missingness.svg)",
             "", "IPW receives known MAR probabilities under MCAR/MAR but the same incorrectly assumed MAR model under MNAR. Regression standardization models observed outcomes using X. Neither method is given the unobserved outcome errors. The full-data comparator is an oracle.",
             "", "## Clustered assignment", "", "![Clustering](../assets/clustering.svg)",
             "", "School-mean t intervals match the independent assignment units under this balanced, equal-size, Gaussian design. This does not establish validity for unequal, informative, or few-cluster designs in general.",
             "", "## Full results", "",
             "| Scenario | Method | Truth | Bias (MCSE) | 95% coverage (MCSE) | Reject zero | Failures |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['scenario']} | {LABELS[r['method']]} | {r['truth']:.2f} | {r['bias']:+.3f} ({r['bias_mcse']:.3f}) | {r['coverage']:.3f} ({r['coverage_mcse']:.3f}) | {r['reject_zero']:.3f} | {r['failed']} |")
    lines += ["", "Reject-zero is a false-positive rate only where truth = 0; otherwise it is power. Coverage targets the generating parameter, not the attenuated observed-exposure slope.",
              "", "Coverage and rejection MCSE use sqrt[p(1-p)/R]. Bias MCSE uses empirical SD / sqrt(R). Worst-case binomial MCSE at R=2,000 is 0.0112; near 95% coverage it is 0.0049. These are simulation errors, not participant-level confidence intervals.",
              "", "Wilson Monte Carlo intervals for coverage and rejection are included in the CSV and figures. A zero plug-in MCSE after zero events is not evidence of zero uncertainty.",
              "", "Same simulated data feed competing methods. [Paired comparisons](paired-comparisons.csv) report within-repetition differences and their MCSE. No failed fit is silently removed: an unexpected estimator exception stops the run; the summary also reports nonfinite-result failures.",
              "", f"Design SHA-256: {digest}. [Design](../config/design.json) · [Methods and formulas](../docs/methods.md) · [Machine-readable summary](summary.csv).",
              "", "This fixed computational plan is not an externally preregistered protocol. Results apply to the supplied generating mechanisms, not all dietary research. No findings from TX Sprouts or NHANES are reestimated by this simulation.",
              ""]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--smoke", action="store_true", help="20 repetitions to ignored artifacts; never replace published results")
    p.add_argument("--check", action="store_true", help="rerun full plan and compare accepted aggregates without replacing them")
    args = p.parse_args()
    if args.smoke and args.check:
        p.error("Choose smoke or full reference check")
    raw = (ROOT/"config/design.json").read_bytes()
    design = json.loads(raw)
    reps = 20 if args.smoke else design["replicates"]
    rows, paired = run(design, reps)
    out = ROOT/("artifacts/smoke" if args.smoke else "outputs")
    if args.check:
        for filename, actual in [("summary.csv",rows),("paired-comparisons.csv",paired)]:
            with (out/filename).open(newline="") as f:
                reference = list(csv.DictReader(f))
            if len(actual) != len(reference):
                raise AssertionError("Reference row count differs")
            for a,e in zip(actual,reference):
                if set(a) != set(e):
                    raise AssertionError("Reference columns differ")
                for k,v in a.items():
                    if isinstance(v,(int,float,np.floating)):
                        if not np.isclose(float(e[k]),v,rtol=2e-6,atol=2e-6):
                            raise AssertionError(f"{filename} {a.get('scenario')} {k}: {v} != {e[k]}")
                    elif str(v) != e[k]:
                        raise AssertionError(f"Reference differs: {k}")
        print("Both full-run aggregate tables reproduce within 2e-6.")
        return
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out/"summary.csv", rows)
    write_csv(out/"paired-comparisons.csv", paired)
    if not args.smoke:
        (out/"report.md").write_text(report(rows,reps,hashlib.sha256(raw).hexdigest()),encoding="utf-8",newline="\n")
        make_figures(ROOT, rows)
    print(f"Saved aggregate outputs: {out}")


if __name__ == "__main__":
    main()
