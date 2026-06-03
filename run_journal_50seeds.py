#!/usr/bin/env python3
"""
run_journal_50seeds.py
======================
Headless, parallel, RESUMABLE, memory-light multi-seed batch runner for the
journal paper.

WHAT THIS DOES
  * Runs all 5 scenarios (baseline + scenario1..4) for a block of NEW seeds
    (default 1000-1049 = 50 seeds), at 500 households x 365 days.
  * Uses the SAME calibrated parameters and the SAME scenario configurations as
    the dissertation runs (verified against the saved dissertation result JSONs),
    so the only thing that changes between dissertation and journal runs is the
    random seed -- exactly what you want for Monte-Carlo replication.
  * FULLY REPRODUCIBLE: seeds python `random`, numpy, AND the mesa model RNG
    (model.reset_randomizer) so the same seed always gives byte-identical results.
  * PARALLEL across CPU cores, and MEMORY-LIGHT: each seed runs in a FRESH worker
    process that is destroyed when the seed finishes (maxtasksperchild=1), so no
    model/agent memory ever accumulates across runs. The parent never holds all
    results in memory -- workers write each seed to disk and the summary is
    computed by streaming one file at a time.
  * RESUMABLE: writes one file per (scenario, seed) as it finishes (atomically).
    Stop anytime (Ctrl-C, or `kill <pid>`); re-run the SAME command later and it
    SKIPS everything already done and continues with only the missing seeds.
  * Writes to a SEPARATE directory (default journal_results_50seeds/) so the
    dissertation's 6 seeds in scenarios_results/ are never touched.

WHAT THIS DOES *NOT* DO
  * It does NOT modify the model / scenarios / dashboards -- it only imports their
    public factory functions and calls them.
  * It does NOT drop seeds for being "unfavorable" (that would bias the paper).
    It only auto-excludes TECHNICALLY INVALID runs (crash / NaN / empty /
    degenerate); every run's status is logged in the manifest.

USAGE  (run from the project root, with the abm310 interpreter)
  PY=/Users/goshtasbshahriari/opt/anaconda3/envs/abm310/bin/python
  $PY run_journal_50seeds.py                      # all 5 scenarios, seeds 1000-1049
  $PY run_journal_50seeds.py                      # <- run AGAIN to RESUME (skips done seeds)
  $PY run_journal_50seeds.py --workers 8          # cap parallel workers
  $PY run_journal_50seeds.py --max-tasks-per-child 5   # reuse a worker for 5 seeds (faster, more RAM)
  $PY run_journal_50seeds.py --fresh              # delete existing files and re-run everything
  $PY run_journal_50seeds.py --scenarios baseline # subset

  # background (close terminal; laptop stays awake). Stop with: kill <pid>. Resume: re-run.
  nohup $PY run_journal_50seeds.py > journal_run.log 2>&1 &

STOP & CONTINUE
  * Stop:    Ctrl-C (foreground) or `kill <pid>` (background). Finished seeds are
             saved; the in-flight one is simply re-done later.
  * Continue: run the exact same command again -> resumes, never restarting from
             the first seed.
"""

from __future__ import annotations

import argparse
import contextlib
import gc
import glob
import json
import math
import multiprocessing as mp
import os
import signal
import sys
import time
from dataclasses import asdict
from datetime import datetime

# --- Make imports work no matter where the script is launched from ----------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
os.chdir(_SCRIPT_DIR)

import numpy as np  # noqa: E402

import warnings  # noqa: E402
# Mesa 3.0.3 emits a DeprecationWarning for RandomActivation on every model build;
# with 250 fresh-process runs that would flood the log. Silence just that noise.
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Model + scenario factories (public entry points; nothing here is modified) ---
from enhanced_mesa_geo_model import SimulationConfig            # noqa: E402
from baseline_scenario import create_baseline_scenario          # noqa: E402
from enhanced_scenario_1 import create_enhanced_scenario_1      # noqa: E402
from enhanced_scenario_2 import create_enhanced_scenario_2      # noqa: E402
from enhanced_scenario_3 import create_enhanced_scenario_3      # noqa: E402
from enhanced_scenario_4 import create_enhanced_scenario_4      # noqa: E402

_FACTORIES = {
    "baseline":  create_baseline_scenario,
    "scenario1": create_enhanced_scenario_1,
    "scenario2": create_enhanced_scenario_2,
    "scenario3": create_enhanced_scenario_3,
    "scenario4": create_enhanced_scenario_4,
}

# Scenario definitions -- ground-truthed from the dissertation result JSONs.
SCENARIOS = {
    "baseline": dict(
        snap_key="baseline",
        label="Baseline",
        overrides={},
        factory_kwargs=dict(use_real_data=True),
    ),
    "scenario1": dict(
        snap_key="scenario1_north",
        label="S1: New grocery store (north)",
        overrides=dict(scenario1_store_region="north"),
        factory_kwargs=dict(include_baseline=True, use_real_data=True),
    ),
    "scenario2": dict(
        snap_key="scenario2_1_4",
        label="S2: Food hub + corner stores (1 hub, 4 corners)",
        overrides=dict(food_hub_capacity=200, num_corner_stores=4),
        factory_kwargs=dict(include_baseline=True, use_real_data=True),
    ),
    "scenario3": dict(
        snap_key="scenario3_2_fixed",
        label="S3: Mobile pantries (2, fixed)",
        overrides=dict(num_mobile_pantries=2, mobile_pantry_strategy="fixed"),
        factory_kwargs=dict(include_baseline=True, use_real_data=True),
    ),
    "scenario4": dict(
        snap_key="scenario4_500",
        label="S4: Subsidized delivery (cap 500, fee $2.00)",
        overrides={},
        factory_kwargs=dict(
            use_real_data=True,
            delivery_capacity=500,
            base_service_fee=2.0,
            distance_fee_per_km=0.75,
            delivery_area_km=20.0,
        ),
    ),
}

METRIC_KEYS = [
    "satisfaction_rate", "food_insecurity_rate", "avg_travel_distance",
    "spatial_equity_index", "total_revenue",
    "spend_low", "spend_med", "spend_high",
    "corner_share", "pantry_share", "delivery_share",
]


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def _is_valid(history, n_days):
    """Technical validity only (NOT favorability). Returns (ok: bool, reason: str)."""
    if not history:
        return False, "empty metrics_history"
    if len(history) < n_days:
        return False, f"history length {len(history)} < requested {n_days} days"
    fm = history[-1]
    for k in ("satisfaction_rate", "food_insecurity_rate", "avg_travel_distance"):
        v = fm.get(k, None)
        try:
            if v is None or not math.isfinite(float(v)):
                return False, f"final {k} not finite ({v!r})"
        except (TypeError, ValueError):
            return False, f"final {k} not numeric ({v!r})"
    sat = float(fm["satisfaction_rate"])
    if not (-1e-6 <= sat <= 1.0 + 1e-6):
        return False, f"final satisfaction_rate out of [0,1]: {sat}"
    try:
        max_sat = max(float(h.get("satisfaction_rate", 0) or 0) for h in history)
    except (TypeError, ValueError):
        return False, "non-numeric satisfaction_rate in history"
    if max_sat <= 0.0:
        return False, "satisfaction_rate == 0 across all days (degenerate run)"
    return True, "ok"


def _seed_glob(out_dir, snap_key, seed, n_hh, n_days):
    """All per-seed files for this exact (scenario, seed, size); excludes summaries/tmp."""
    pat = os.path.join(out_dir, f"{snap_key}_{n_hh}hh_{n_days}d_seed{seed}_*.json")
    return [p for p in glob.glob(pat) if "summary" not in os.path.basename(p)]


def _existing_valid(out_dir, snap_key, seed, n_hh, n_days):
    """Return a valid existing file path for this (scenario, seed), else None (for RESUME)."""
    for p in sorted(_seed_glob(out_dir, snap_key, seed, n_hh, n_days)):
        try:
            with open(p) as f:
                d = json.load(f)
            ok, _ = _is_valid(d.get("metrics_history", []), n_days)
            keep = ok and int(d.get("seed", -1)) == int(seed)
            del d
            if keep:
                return p
        except Exception:
            continue
    return None


def run_one_task(task):
    """
    Worker: run ONE (scenario, seed). Top-level + picklable (works with 'spawn').
    Writes a per-seed JSON ATOMICALLY on success (tmp file + os.replace), so a
    kill mid-run can never leave a corrupt/partial file behind. The whole worker
    process is recycled after this returns (maxtasksperchild=1), so no memory
    from the model/agents survives to the next seed.
    """
    scenario = task["scenario"]
    seed = int(task["seed"])
    n_hh = int(task["households"])
    n_days = int(task["days"])
    out_dir = task["out_dir"]
    spec = SCENARIOS[scenario]
    snap_key = spec["snap_key"]

    result = {"scenario": scenario, "snap_key": snap_key, "seed": seed,
              "status": "error", "reason": "", "file": None, "final_metrics": {},
              "pid": os.getpid()}
    model = None
    history = None
    try:
        import random as _random
        _random.seed(seed)
        np.random.seed(seed)

        cfg = SimulationConfig(num_consumers=n_hh, simulation_days=n_days,
                               **spec["overrides"])
        factory = _FACTORIES[scenario]

        with open(os.devnull, "w") as _dn, contextlib.redirect_stdout(_dn):
            model = factory(cfg, **spec["factory_kwargs"])
            # CRITICAL for reproducibility: the model uses mesa's RandomActivation,
            # whose per-step agent shuffle draws from `model.random` -- a per-model
            # RNG that random.seed()/np.random.seed() do NOT control. Without this,
            # the SAME seed produces DIFFERENT results. Seeding it here (after agents
            # are placed via the global/numpy RNGs, before stepping) makes every run
            # byte-for-byte reproducible. Verified 2026-06-02.
            _seeded = False
            try:
                model.reset_randomizer(seed)
                _seeded = True
            except Exception:
                try:
                    model.random.seed(seed)
                    _seeded = True
                except Exception:
                    _seeded = False
            if not _seeded:
                # Fail LOUD: proceeding would silently produce a NON-reproducible
                # run that still looks "ok". Mark this seed as an error instead.
                raise RuntimeError("could not seed model RNG (reset_randomizer / "
                                   "model.random unavailable) -> run would be non-reproducible")
            for _ in range(n_days):
                model.step()
            history = list(getattr(model, "metrics_history", []) or [])

        ok, reason = _is_valid(history, n_days)
        if not ok:
            result.update(status="invalid", reason=reason)
            return result

        # Record exactly how the model was built (provenance), incl. scenario4
        # delivery params, so each file is self-describing.
        cfg_dict = asdict(cfg)
        for k, v in spec["factory_kwargs"].items():
            if k not in ("use_real_data", "include_baseline"):
                cfg_dict.setdefault(k, v)

        final_metrics = dict(history[-1]) if history else {}
        now = datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S_%f")
        fname = f"{snap_key}_{n_hh}hh_{n_days}d_seed{seed}_{ts}.json"
        fpath = os.path.join(out_dir, fname)
        tmp = fpath + ".tmp"
        payload = {
            "snap_key": snap_key, "seed": seed, "days": n_days,
            "n_households": n_hh,
            "timestamp": now.isoformat(timespec="seconds"),
            "scenario": scenario,
            "scenario_factory_kwargs": dict(spec["factory_kwargs"]),
            "config": cfg_dict,
            "metrics_history": history,
            "final_metrics": final_metrics,
        }
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2, default=_json_default)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, fpath)  # atomic: the .json only ever appears complete

        result.update(status="ok", reason="ok", file=os.path.basename(fpath),
                      final_metrics={k: final_metrics.get(k) for k in METRIC_KEYS
                                     if k in final_metrics})
        return result
    except Exception as exc:
        import traceback
        result.update(status="error",
                      reason=f"{type(exc).__name__}: {exc}",
                      traceback=traceback.format_exc()[-1500:])
        return result
    finally:
        # Explicit release (belt-and-suspenders; the process is recycled anyway).
        try:
            del model, history
        except Exception:
            pass
        gc.collect()


def _write_summary(scenario, n_hh, n_days, out_dir):
    """
    Aggregate ALL valid per-seed files for this scenario into a dashboard-format
    summary (mean/std/min/max per day). STREAMING: reads one file at a time and
    keeps only O(days x metrics) running accumulators -- never all seeds at once.
    Scanning the whole folder (not just this session) keeps the summary correct
    after a resume. Stable filename -> overwritten, not piled up.
    """
    spec = SCENARIOS[scenario]
    snap_key, label = spec["snap_key"], spec["label"]
    files = [p for p in glob.glob(os.path.join(out_dir, f"{snap_key}_{n_hh}hh_{n_days}d_seed*_*.json"))
             if "summary" not in os.path.basename(p)]

    seeds_seen = set()
    cfg_example = None
    acc = None  # list over days; each entry: {metric: [n, mean, M2, min, max]} (Welford)

    for p in sorted(files):
        try:
            with open(p) as f:
                d = json.load(f)
        except Exception:
            continue
        hist = d.get("metrics_history", [])
        ok, _ = _is_valid(hist, n_days)
        seed = int(d.get("seed", -1))
        if not ok or seed in seeds_seen:
            del d
            continue
        seeds_seen.add(seed)
        if cfg_example is None:
            cfg_example = d.get("config", {})
        if acc is None:
            acc = [dict() for _ in range(len(hist))]
        ndays = min(len(acc), len(hist))
        for di in range(ndays):
            row = hist[di]
            cell = acc[di]
            for k in METRIC_KEYS:
                v = row.get(k)
                if v is None:
                    continue
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(fv):
                    continue
                a = cell.get(k)
                if a is None:
                    # Welford accumulator [n, mean, M2, min, max] — numerically
                    # stable std even for large-dollar metrics (total_revenue, spend_*).
                    cell[k] = [1, fv, 0.0, fv, fv]
                else:
                    a[0] += 1
                    delta = fv - a[1]
                    a[1] += delta / a[0]
                    a[2] += delta * (fv - a[1])
                    if fv < a[3]:
                        a[3] = fv
                    if fv > a[4]:
                        a[4] = fv
        del d, hist
    if not seeds_seen or acc is None:
        return None, 0

    mean_history = []
    for di in range(len(acc)):
        rowout = {"day": di + 1}
        for k in METRIC_KEYS:
            a = acc[di].get(k)
            if not a:
                continue
            n, mean, m2, mn, mx = a
            var = m2 / (n - 1) if n > 1 else 0.0
            rowout[k] = float(mean)
            # max(0, var) guards the tiny-negative-epsilon Welford can hit on
            # near-identical values (math.sqrt would otherwise raise).
            rowout[k + "_std"] = float(math.sqrt(max(0.0, var)))
            rowout[k + "_min"] = float(mn)
            rowout[k + "_max"] = float(mx)
        mean_history.append(rowout)

    seeds_used = sorted(seeds_seen)
    snap = {
        "scenario": scenario, "display_label": label, "snap_key": snap_key,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "days": n_days, "n_seeds": len(seeds_used), "seeds_used": seeds_used,
        "config": cfg_example or {},
        "metrics_history": mean_history,
        "final_metrics": mean_history[-1] if mean_history else {},
    }
    fname = f"{snap_key}_{n_hh}hh_{n_days}d_journal_summary.json"  # stable -> overwritten
    tmp = os.path.join(out_dir, fname + ".tmp")
    with open(tmp, "w") as f:
        json.dump(snap, f, indent=2, default=_json_default)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, os.path.join(out_dir, fname))
    return fname, len(seeds_used)


def main():
    ap = argparse.ArgumentParser(description="Parallel, resumable, memory-light multi-seed runner (journal).")
    ap.add_argument("--seeds-start", type=int, default=1000)
    ap.add_argument("--n-seeds", type=int, default=50)
    ap.add_argument("--seeds", nargs="+", type=int, default=None,
                    help="Explicit seed list (overrides --seeds-start/--n-seeds).")
    ap.add_argument("--seeds-file", default=None,
                    help="File of seeds (whitespace/newline separated; '#' comments allowed). "
                         "Overrides --seeds-start/--n-seeds.")
    ap.add_argument("--households", type=int, default=500)
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--scenarios", nargs="+", default=list(SCENARIOS.keys()),
                    choices=list(SCENARIOS.keys()))
    ap.add_argument("--out", default=os.path.join(_SCRIPT_DIR, "journal_results_50seeds"))
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--max-tasks-per-child", type=int, default=1,
                    help="Seeds a worker runs before it is recycled (default 1 = fresh process per "
                         "seed, no memory accumulation). Raise for a bit more speed at more RAM.")
    ap.add_argument("--fresh", action="store_true",
                    help="Delete existing files for the targeted scenarios and re-run everything.")
    args = ap.parse_args()

    if args.seeds:
        seeds = sorted(set(int(s) for s in args.seeds))
    elif args.seeds_file:
        toks = []
        with open(args.seeds_file) as _sf:
            for line in _sf:
                toks += line.split("#", 1)[0].split()
        seeds = sorted(set(int(t) for t in toks))
        if not seeds:
            raise SystemExit(f"--seeds-file '{args.seeds_file}' contained no seeds")
    else:
        seeds = list(range(args.seeds_start, args.seeds_start + args.n_seeds))
    os.makedirs(args.out, exist_ok=True)
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Remove any stray .tmp from a previous hard kill (never valid output).
    for t in glob.glob(os.path.join(args.out, "*.json.tmp")):
        try:
            os.remove(t)
        except OSError:
            pass

    # --fresh: delete existing per-seed files for the targeted scenarios+size.
    if args.fresh:
        for s in args.scenarios:
            sk = SCENARIOS[s]["snap_key"]
            for p in glob.glob(os.path.join(args.out, f"{sk}_{args.households}hh_{args.days}d_seed*_*.json")):
                if "summary" not in os.path.basename(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass

    all_tasks = [
        {"scenario": s, "seed": seed, "households": args.households,
         "days": args.days, "out_dir": args.out}
        for s in args.scenarios for seed in seeds
    ]

    # RESUME: drop tasks that already have a valid result file.
    already = 0
    to_run = []
    for t in all_tasks:
        sk = SCENARIOS[t["scenario"]]["snap_key"]
        if (not args.fresh) and _existing_valid(args.out, sk, t["seed"], args.households, args.days):
            already += 1
        else:
            to_run.append(t)

    print("=" * 72)
    print("JOURNAL MULTI-SEED BATCH RUNNER  (resumable, memory-light; model untouched)")
    print("=" * 72)
    print(f"  scenarios : {', '.join(args.scenarios)}")
    print(f"  seeds     : {seeds[0]}..{seeds[-1]}  ({len(seeds)} seeds)")
    print(f"  size      : {args.households} households x {args.days} days")
    print(f"  total     : {len(all_tasks)} runs  |  already done: {already}  |  to run now: {len(to_run)}")
    print(f"  workers   : {args.workers}   (fresh process every {args.max_tasks_per_child} seed[s])")
    print(f"  output    : {args.out}")
    if already and not args.fresh:
        print(f"  RESUMING — skipping {already} completed runs.")
    print("=" * 72, flush=True)

    t0 = time.time()
    results = []
    interrupted = False
    pool_exc = None

    if to_run:
        # `kill <pid>` (SIGTERM) -> behave like Ctrl-C: stop cleanly, stay resumable.
        def _graceful(_signum, _frame):
            raise KeyboardInterrupt()
        try:
            signal.signal(signal.SIGTERM, _graceful)
        except Exception:
            pass

        ctx = mp.get_context("spawn")  # safe with numpy/heavy libs; isolates each worker
        pool = ctx.Pool(processes=args.workers,
                        maxtasksperchild=max(1, args.max_tasks_per_child))
        done = 0
        try:
            for r in pool.imap_unordered(run_one_task, to_run):
                results.append(r)
                done += 1
                tag = {"ok": "OK ", "invalid": "SKIP", "error": "ERR "}.get(r["status"], "??? ")
                extra = "" if r["status"] == "ok" else f"  <- {r['reason']}"
                print(f"  [{done:>4}/{len(to_run)}] {tag} {r['scenario']:<10} seed {r['seed']}{extra}",
                      flush=True)
            pool.close()
        except KeyboardInterrupt:
            interrupted = True
            pool.terminate()
            print("\n  [STOPPED] Completed seeds are saved on disk.")
            print("      Re-run the SAME command to CONTINUE from where it left off.", flush=True)
        except Exception as exc:
            # Don't lose the manifest/summaries: record and re-raise AFTER they're written.
            pool_exc = exc
            pool.terminate()
        finally:
            pool.join()
    else:
        print("  Nothing to run — all requested seeds are already complete.", flush=True)

    # Always (re)build per-scenario summaries by STREAMING the files on disk.
    print("-" * 72)
    summaries = {}
    for s in args.scenarios:
        fn, n_valid = _write_summary(s, args.households, args.days, args.out)
        summaries[s] = {"n_valid_on_disk": n_valid, "summary_file": fn}

    manifest = {
        "run_timestamp": run_ts, "interrupted": interrupted,
        "seeds_requested": seeds, "households": args.households, "days": args.days,
        "scenarios": args.scenarios, "already_done_at_start": already,
        "ran_this_session": len(results),
        "elapsed_seconds": round(time.time() - t0, 1),
        "per_scenario": summaries,
        "runs_this_session": sorted(results, key=lambda r: (r["scenario"], r["seed"])),
    }
    man_path = os.path.join(args.out, f"_manifest_{run_ts}.json")
    man_tmp = man_path + ".tmp"
    with open(man_tmp, "w") as f:
        json.dump(manifest, f, indent=2, default=_json_default)
        f.flush()
        os.fsync(f.fileno())
    os.replace(man_tmp, man_path)  # atomic + durable, like the per-seed/summary writes

    n_ok = sum(1 for r in results if r["status"] == "ok")
    n_skip = sum(1 for r in results if r["status"] == "invalid")
    n_err = sum(1 for r in results if r["status"] == "error")
    total_target = len(seeds)
    print("=" * 72)
    state = "STOPPED (resumable)" if interrupted else "DONE"
    print(f"{state} in {manifest['elapsed_seconds']}s   "
          f"this session: valid={n_ok} skipped={n_skip} errors={n_err}")
    complete = True
    for s in args.scenarios:
        nv = summaries[s]["n_valid_on_disk"]
        if nv < total_target:
            complete = False
        bar = "complete" if nv >= total_target else f"{total_target - nv} remaining"
        print(f"    {s:<10} {nv}/{total_target} valid seeds on disk  ({bar})")
    print(f"  manifest: {os.path.basename(man_path)}")
    if interrupted or not complete:
        print("  -> To CONTINUE: re-run the exact same command (it skips finished seeds).")
    else:
        print("  -> All scenarios complete. Summaries written (journal_summary.json per scenario).")
    if n_skip or n_err:
        print("  NOTE: skipped/errored = TECHNICAL failures (crash/NaN/empty), not 'unfavorable'")
        print(f"        results. To replace them, run with a higher --seeds-start (e.g. {seeds[-1]+1}).")
    print("=" * 72, flush=True)

    # Re-raise any unexpected pool exception now that the manifest/summaries are safely written.
    if pool_exc is not None:
        raise pool_exc


if __name__ == "__main__":
    main()
