#!/usr/bin/env python
"""
Sobol sensitivity analysis reported in the manuscript (Fig. 8).
================================================================

DESIGN
  centre   : the calibrated parameters in PAPER_PARAMS_FoodSecurity.json
  bounds   : +/- 30% around each centre value, 7 parameters
  sampler  : SALib Saltelli, N = 256 base sample, calc_second_order=True, seed 42
             -> 256 * (2*7 + 2) = 4,096 model runs
  model    : baseline scenario, 500 households x 365 days, store inventory
             store_FINAL_6g_11c.csv, model rng seed 42 + reset_randomizer(42)
  indices  : total-order S_T and first-order S_1 with SALib bootstrap 95% CIs

OUTPUTS (indices are computed for each)
  fi_final_day   share of households unsatisfied on the final day
                 (the food-insecurity rate of Tables 4-5; shown in Fig. 8)
  fi_day_union   share insecure on >= 1 day of the year (annual prevalence,
                 the calibration target)
  corner_share   corner-store share of all trips
  fi_unmet_proxy, spend_low, spend_med, trips_per_hh  (supplementary)

The output of the run reported in the manuscript is shipped as
sobol_indices_paper.json, with the raw model outputs in
sensitivity/sobol_Y_500hh.csv (one row per design point).

RUN
  python run_sobol_paper.py                     # full run, resumable (Ctrl+C, rerun)
  python run_sobol_paper.py --workers 8         # worker processes (default: cores-1)
  python run_sobol_paper.py --status            # progress only
  python run_sobol_paper.py --smoke             # tiny end-to-end check (N=2, 20 hh, 3 days)
  python run_sobol_paper.py --out sensitivity --analyze-only
        # recompute the indices from the shipped raw outputs in seconds

Writes to --out (default results/sobol_rerun/): sobol_Y_500hh.csv,
sobol_indices_500hh.json, SOBOL_500HH_REPORT.md, sobol_matrix.hash.
"""

import argparse
import contextlib
import csv
import hashlib
import io
import json
import multiprocessing as mp
import os
import random
import sys
import time
from datetime import datetime

# ---------------------------------------------------------------- paths
_THIS = os.path.abspath(__file__)
ABM_DIR = os.path.dirname(_THIS)              # project root (flat layout)
SMOKE = "--smoke" in sys.argv


def _out_dir():
    if "--out" in sys.argv:
        i = sys.argv.index("--out")
        if i + 1 < len(sys.argv):
            return os.path.abspath(sys.argv[i + 1])
    return os.path.join(ABM_DIR, "results", "sobol_rerun" + ("_SMOKE" if SMOKE else ""))


OUT_DIR = _out_dir()
Y_CSV = os.path.join(OUT_DIR, "sobol_Y_500hh.csv")
IDX_JSON = os.path.join(OUT_DIR, "sobol_indices_500hh.json")
REPORT = os.path.join(OUT_DIR, "SOBOL_500HH_REPORT.md")
HASH_FILE = os.path.join(OUT_DIR, "sobol_matrix.hash")

PARAMS_JSON = os.path.join(ABM_DIR, "PAPER_PARAMS_FoodSecurity.json")
STORE_CSV = os.path.join(ABM_DIR, "store_FINAL_6g_11c.csv")
if not os.path.isfile(STORE_CSV):
    raise SystemExit(f"ABORT: store CSV not found: {STORE_CSV}")
os.environ["GEOMESA_SUPERMARKET_CSV"] = STORE_CSV
# The 7 parameters are set explicitly per run; never inherit a params file.
os.environ.pop("GEOMESA_CALIBRATED_PARAMS", None)

PARAM7 = ["alpha_distance", "beta_price_budget", "gamma_quality_variety",
          "delta_convenience", "go_shop_threshold_low",
          "go_shop_threshold_medium", "go_shop_threshold_high"]

# Design
SA_N = 256 if not SMOKE else 2
SA_PCT = 0.30
HH = 500 if not SMOKE else 20
DAYS = 365 if not SMOKE else 3
SA_SEED = 42
N_RUNS = SA_N * (2 * len(PARAM7) + 2)

OUTPUTS = ["fi_unmet_proxy", "fi_day_union", "fi_final_day",
           "spend_low", "spend_med", "corner_share", "trips_per_hh"]
CSV_COLS = ["run_index"] + OUTPUTS + ["status"]

PY = sys.executable


def log(msg):
    print(f"[{datetime.now().strftime('%m-%d %H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- worker
def _winit(abm_dir):
    os.chdir(abm_dir)
    if abm_dir not in sys.path:
        sys.path.insert(0, abm_dir)
    os.environ.pop("GEOMESA_CALIBRATED_PARAMS", None)
    os.environ["GEOMESA_SUPERMARKET_CSV"] = STORE_CSV


def _one(task):
    """Run ONE design point. Returns a dict of the outputs (or status=error)."""
    run_index, param_row, names, hh, days, seed = task
    import numpy as np
    try:
        from enhanced_mesa_geo_model import (SimulationConfig, IncomeLevel,
                                             EnhancedHouseholdAgent)
        from baseline_scenario import create_baseline_scenario

        random.seed(seed)
        np.random.seed(seed)

        # SAFE PATTERN: construct first, then setattr — __post_init__ would
        # otherwise clobber constructor kwargs with the discovered params file.
        config = SimulationConfig(num_consumers=hh, simulation_days=days,
                                  enable_spatial_analytics=False)
        for i, name in enumerate(names):
            setattr(config, name, float(param_row[i]))

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            model = create_baseline_scenario(config=config)
            if hasattr(model, "reset_randomizer"):
                model.reset_randomizer(seed)
            households = [a for a in model.schedule.agents
                          if isinstance(a, EnhancedHouseholdAgent)]
            insec_days = {id(h): 0 for h in households}
            for _ in range(days):
                model.step()
                for h in households:                      # daily poll -> fi_day_union
                    if getattr(h, "unsatisfied", False):
                        insec_days[id(h)] += 1

        n = len(households)
        # (1) ever carried unmet need
        fi_unmet = sum(1 for h in households
                       if getattr(h, "unmet_need", 0) > 0
                       or any(t.get("unmet_need", 0) > 0 for t in h.shopping_history)) / n
        # (2) calibration construct: insecure on >= 1 day, unioned over the year
        fi_union = sum(1 for v in insec_days.values() if v >= 1) / n
        # (3) scenario metric: unsatisfied on the final day
        fi_final = sum(1 for h in households if getattr(h, "unsatisfied", False)) / n

        spend = {IncomeLevel.LOW: [], IncomeLevel.MEDIUM: []}
        trips = corner = 0
        for h in households:
            hist = h.shopping_history or []
            if hist and h.income in spend:
                spend[h.income].append(
                    sum(t.get("basket_cost", t.get("basket_size", 0)) for t in hist))
            trips += len(hist)
            corner += sum(1 for t in hist if t.get("is_corner_shop", False))

        return {"run_index": run_index,
                "fi_unmet_proxy": fi_unmet,
                "fi_day_union": fi_union,
                "fi_final_day": fi_final,
                "spend_low": float(np.mean(spend[IncomeLevel.LOW])) if spend[IncomeLevel.LOW] else 0.0,
                "spend_med": float(np.mean(spend[IncomeLevel.MEDIUM])) if spend[IncomeLevel.MEDIUM] else 0.0,
                "corner_share": corner / trips if trips else 0.0,
                "trips_per_hh": trips / n if n else 0.0,
                "status": "ok"}
    except Exception as exc:
        return {"run_index": run_index, "status": f"error:{type(exc).__name__}:{exc}",
                **{k: float("nan") for k in OUTPUTS}}


# ---------------------------------------------------------------- design
def build_design():
    """Saltelli matrix, identical to the manuscript run (same bounds, N, seed)."""
    import numpy as np
    center = json.load(open(PARAMS_JSON))["final_parameters"]
    center = {k: float(center[k]) for k in PARAM7}      # fixed order
    cwd0 = os.getcwd()
    os.chdir(ABM_DIR)
    if ABM_DIR not in sys.path:
        sys.path.insert(0, ABM_DIR)
    try:
        import sensitivity_analysis_sobol as sam
        problem, _ = sam.build_sa_problem(center, SA_PCT)
        try:
            pv = sam.sobol_sampler.sample(problem, N=SA_N, calc_second_order=True,
                                          seed=SA_SEED)
        except TypeError:                                # older SALib
            np.random.seed(SA_SEED)
            pv = sam.sobol_sampler.sample(problem, N=SA_N, calc_second_order=True)
    finally:
        os.chdir(cwd0)
    assert pv.shape == (N_RUNS, len(PARAM7)), f"unexpected sample shape {pv.shape}"
    h = hashlib.sha256(pv.tobytes()).hexdigest()[:16]
    if os.path.exists(HASH_FILE):
        assert open(HASH_FILE).read().strip() == h, (
            "Sobol matrix changed between sessions — delete sobol_Y_500hh.csv "
            "and sobol_matrix.hash to restart")
    else:
        os.makedirs(OUT_DIR, exist_ok=True)
        open(HASH_FILE, "w").write(h)
    return center, problem, pv, h


# ---------------------------------------------------------------- state
def done_indices():
    if not os.path.exists(Y_CSV):
        return set()
    out = set()
    with open(Y_CSV, newline="") as f:
        for r in csv.DictReader(f):
            if str(r.get("status", "")) == "ok":
                try:
                    out.add(int(float(r["run_index"])))
                except (TypeError, ValueError):
                    pass
    return out


def append_row(row):
    new = not os.path.exists(Y_CSV)
    with open(Y_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


# ---------------------------------------------------------------- sweep
def sweep(workers):
    center, problem, pv, mat_hash = build_design()
    os.makedirs(OUT_DIR, exist_ok=True)
    done = done_indices()
    todo = [i for i in range(N_RUNS) if i not in done]
    log(f"design: N={SA_N} -> {N_RUNS} runs @ {HH}hh/{DAYS}d, +/-{SA_PCT:.0%}, "
        f"matrix {mat_hash}")
    log(f"centre: " + ", ".join(f"{k}={v}" for k, v in center.items()))
    log(f"{len(done)} done, {len(todo)} to go")
    if not todo:
        return
    tasks = [(i, pv[i], PARAM7, HH, DAYS, SA_SEED) for i in todo]
    ctx = mp.get_context("spawn")
    t0, n_done, n_err = time.time(), 0, 0
    with ctx.Pool(processes=workers, maxtasksperchild=25,
                  initializer=_winit, initargs=(ABM_DIR,)) as pool:
        for row in pool.imap_unordered(_one, tasks):
            append_row(row)
            n_done += 1
            if str(row.get("status")) != "ok":
                n_err += 1
                log(f"  ERROR run {row.get('run_index')}: {row.get('status')}")
            if n_done % 25 == 0 or n_done == len(todo):
                rate = n_done / max(time.time() - t0, 1)
                eta = (len(todo) - n_done) / max(rate, 1e-9) / 3600
                log(f"  {n_done}/{len(todo)} ({(time.time()-t0)/60:.0f} min)  "
                    f"ETA {eta:.1f} h")
    if n_err:
        log(f"WARNING {n_err} run(s) errored; re-run to retry them")


# ---------------------------------------------------------------- analysis
def analyze():
    import numpy as np
    center, problem, pv, mat_hash = build_design()
    rows = {}
    with open(Y_CSV, newline="") as f:
        for r in csv.DictReader(f):
            if str(r.get("status", "")) == "ok":
                rows[int(float(r["run_index"]))] = r
    missing = [i for i in range(N_RUNS) if i not in rows]
    if missing:
        raise SystemExit(f"incomplete: {len(missing)} runs missing — re-run to resume")

    cwd0 = os.getcwd()
    os.chdir(ABM_DIR)
    if ABM_DIR not in sys.path:
        sys.path.insert(0, ABM_DIR)
    try:
        import sensitivity_analysis_sobol as sam
        result = {"design": {"N": SA_N, "n_runs": N_RUNS, "pct": SA_PCT,
                             "households": HH, "days": DAYS, "seed": SA_SEED,
                             "calc_second_order": True, "matrix_sha": mat_hash,
                             "store_csv": STORE_CSV, "centre": center},
                  "outputs": {}}
        for name in OUTPUTS:
            Y = np.array([float(rows[i][name]) for i in range(N_RUNS)], float)
            nan_n = int(np.isnan(Y).sum())
            if nan_n:
                Y = np.where(np.isnan(Y), np.nanmean(Y), Y)
            Si = sam.sobol.analyze(problem, Y, calc_second_order=True,
                                   print_to_console=False)
            result["outputs"][name] = {
                "min": float(Y.min()), "max": float(Y.max()),
                "mean": float(Y.mean()), "sd": float(Y.std()),
                "range": float(Y.max() - Y.min()),
                "n_distinct": int(len(np.unique(np.round(Y, 6)))),
                "nan_imputed": nan_n,
                "ST": {k: float(v) for k, v in zip(problem["names"], Si["ST"])},
                "ST_conf": {k: float(v) for k, v in zip(problem["names"], Si["ST_conf"])},
                "S1": {k: float(v) for k, v in zip(problem["names"], Si["S1"])},
                "S1_conf": {k: float(v) for k, v in zip(problem["names"], Si["S1_conf"])},
            }
    finally:
        os.chdir(cwd0)
    result["written"] = datetime.now().isoformat()
    with open(IDX_JSON, "w") as f:
        json.dump(result, f, indent=1)
    write_report(result)
    return result


def write_report(res):
    d = res["design"]
    L = []
    L.append("# Sobol sensitivity analysis at full scale (500 households, 365 days)\n")
    L.append(f"Generated: {res['written']}\n")
    L.append(f"Design: N = {d['N']} -> **{d['n_runs']} model runs**, Saltelli sampling with "
             f"second-order terms, +/-{d['pct']:.0%} around the calibrated centre, "
             f"{d['households']} households x {d['days']} days, seed {d['seed']}, "
             f"sample matrix `{d['matrix_sha']}`.\n")
    L.append(f"Store inventory: `{os.path.basename(d['store_csv'])}` "
             f"(6 supermarkets + 11 small-format grocery stores).\n")
    L.append("Centre (the calibrated parameters): "
             + ", ".join(f"{k} = {v}" for k, v in d["centre"].items()) + "\n")
    L.append("\n## How much does the model actually move?\n")
    L.append("| Output | min | max | range | SD | distinct values |")
    L.append("|---|--:|--:|--:|--:|--:|")
    for k, o in res["outputs"].items():
        L.append(f"| {k} | {o['min']:.4f} | {o['max']:.4f} | **{o['range']:.4f}** | "
                 f"{o['sd']:.4f} | {o['n_distinct']} |")
    L.append("\nA Sobol decomposition is only meaningful when the output varies "
             "materially across the design. Read the range column before the indices.\n")
    for k, o in res["outputs"].items():
        L.append(f"\n## {k}\n")
        unit = (f"{o['range']*100:.2f} percentage points" if k.startswith(("fi_", "corner_"))
                else f"{o['range']:.2f} in the output's own units")
        L.append(f"Output range {o['range']:.4f} ({unit}), SD {o['sd']:.4f}, "
                 f"{o['n_distinct']} distinct values, {o['nan_imputed']} NaN imputed.\n")
        L.append("| Parameter | ST | 95% CI | S1 | 95% CI | ST distinguishable from 0? |")
        L.append("|---|--:|--:|--:|--:|:--|")
        for p in sorted(o["ST"], key=lambda p: -o["ST"][p]):
            st, stc = o["ST"][p], o["ST_conf"][p]
            s1, s1c = o["S1"][p], o["S1_conf"][p]
            verdict = "yes" if st - stc > 0 else "**no**"
            L.append(f"| {p} | {st:.3f} | +/-{stc:.3f} | {s1:.3f} | +/-{s1c:.3f} | {verdict} |")
        L.append(f"\nsum ST = {sum(o['ST'].values()):.2f}, sum S1 = {sum(o['S1'].values()):.2f}. "
                 "For an additive model sum S1 = 1 and sum ST = 1; sum ST well above 1 "
                 "indicates either strong interactions or that the indices are "
                 "decomposing numerical noise.\n")
    L.append("\n## Construct note\n")
    L.append("The three food-insecurity outputs are different constructs and are NOT "
             "interchangeable:\n")
    L.append("* `fi_unmet_proxy` — household ever carried unmet need "
             "(the construct used by `sensitivity_analysis_sobol.py` in the live dashboard).\n")
    L.append("* `fi_day_union` — household insecure on at least one day, unioned over the "
             "year. This is the **calibration target** (0.33).\n")
    L.append("* `fi_final_day` — household unsatisfied on the final day. This is the "
             "metric reported in **Tables 4 and 5** and in every scenario comparison.\n")
    L.append("\nReport the sensitivity analysis on the construct the surrounding text "
             "uses, and say which one it is.\n")
    with open(REPORT, "w") as f:
        f.write("\n".join(L) + "\n")
    log(f"report -> {REPORT}")


def status():
    done = done_indices()
    print("=== SOBOL 500hh STATUS ===")
    print(f" design : N={SA_N} -> {N_RUNS} runs @ {HH}hh/{DAYS}d")
    print(f" runs   : {len(done)}/{N_RUNS} ok")
    print(f" indices: {'DONE -> ' + IDX_JSON if os.path.exists(IDX_JSON) else 'pending'}")
    print(f" report : {'DONE -> ' + REPORT if os.path.exists(REPORT) else 'pending'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", default=None, help="output folder (default results/sobol_rerun/)")
    args = ap.parse_args()
    if args.status:
        status()
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    if not args.analyze_only:
        log(f"SOBOL 500hh start (workers={args.workers})"
            + ("  [SMOKE]" if SMOKE else ""))
        try:
            sweep(args.workers)
        except KeyboardInterrupt:
            log("INTERRUPTED — state saved; re-run the same command to resume")
            sys.exit(130)
    res = analyze()
    print()
    for name in ("fi_unmet_proxy", "fi_day_union", "fi_final_day"):
        o = res["outputs"][name]
        log(f"{name}: range {o['range']:.4f} ({o['n_distinct']} distinct)  ST: "
            + ", ".join(f"{k}={o['ST'][k]:.3f}+/-{o['ST_conf'][k]:.3f}"
                        for k in sorted(o["ST"], key=lambda p: -o["ST"][p])[:3]))
    log("DONE")


if __name__ == "__main__":
    main()
