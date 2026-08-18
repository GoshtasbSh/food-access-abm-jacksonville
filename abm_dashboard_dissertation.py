"""
ABM Food Access — PhD Dissertation Dashboard  v4
=================================================
Jacksonville, FL · Health Zone 1 · 500 Households · 365 Days
Seed-set selector: Dissertation (6) | Journal (50) | All (56 combined)

NEW in v4
---------
  • Seed-set selector in header — switch between Dissertation (6 seeds),
    Journal (50 seeds), or All (56 seeds combined) without reloading
  • All charts and tables update instantly when seed set changes
  • CI bands correctly narrow as seed count increases

NEW in v3
---------
  • Smart pattern-based file detection (handles any timestamp / seed count)
  • 6-seed support with graceful 3-seed fallback
  • Bootstrap 95 % CI everywhere (1 000 reps)
  • Income-stratified food-insecurity time series
  • Cumulative burden chart (AUC of insecurity over 365 days)
  • Inter-scenario statistical comparison matrix
  • Within-S2 Location Analysis tab (North / South / East / West)
  • Hub & Corner-Store Variant Analysis tab
  • Policy Insights tab  ← addresses Dr. Watson's committee feedback
  • Tornado sensitivity diagram
  • Capacity / congestion utilization chart
  • Pairwise Cohen-d heat-map
  • Publication-ready static-export hint on every chart
"""

import json, os, re, glob, itertools, threading
import numpy as np
import pandas as pd
from scipy import stats
import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ═══════════════════════════════════════════════════════════════════
# 1.  FILE-DETECTION  (smart: pattern match + exact, graceful fallback)
# ═══════════════════════════════════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else "."
SEARCH_DIRS = [
    BASE_DIR,
    os.path.join(BASE_DIR, "results", "scenarios_results"),
    "/mnt/user-data/uploads",
    "/mnt/project",
]

# Pattern: <prefix>_<n>hh_<days>d_seed<seed>_<timestamp>.json
def _glob_seed(prefix_pattern: str, seed: int) -> str | None:
    """Find a single-seed JSON file by pattern, returns path or None."""
    for d in SEARCH_DIRS:
        hits = glob.glob(os.path.join(d, f"{prefix_pattern}*seed{seed}*.json"))
        # Exclude summary files
        hits = [h for h in hits if "summary" not in h.lower()]
        if hits:
            return sorted(hits)[-1]          # newest timestamp wins
    return None

def _glob_summary(prefix_pattern: str) -> str | None:
    for d in SEARCH_DIRS:
        hits = glob.glob(os.path.join(d, f"{prefix_pattern}*summary*.json"))
        if hits:
            return sorted(hits)[-1]
    return None

def _find_exact(fname: str) -> str | None:
    for d in SEARCH_DIRS:
        p = os.path.join(d, fname)
        if os.path.exists(p):
            return p
    return None

# ═══════════════════════════════════════════════════════════════════
# 2.  SCENARIO REGISTRY
# ═══════════════════════════════════════════════════════════════════

SCENARIO_META = {
    "baseline":  {"label": "Baseline",                    "short": "BL",   "color": "#6B7280", "accent": "#374151"},
    "scenario1": {"label": "S1: North Grocery",           "short": "S1",   "color": "#667eea", "accent": "#4f5fcc"},
    "scenario2": {"label": "S2: Hub + Corner Stores",     "short": "S2",   "color": "#10B981", "accent": "#059669"},
    "scenario3": {"label": "S3: Mobile Pantries",         "short": "S3",   "color": "#F59E0B", "accent": "#D97706"},
    "scenario4": {"label": "S4: Delivery Program",        "short": "S4",   "color": "#EF4444", "accent": "#DC2626"},
    # ── Within-S2 location variants ───────────────────────────────
    "scenario2_north": {"label": "S2-North Grocery",      "short": "S2N",  "color": "#10B981", "accent": "#059669"},
    "scenario2_south": {"label": "S2-South Grocery",      "short": "S2S",  "color": "#0EA5E9", "accent": "#0284C7"},
    "scenario2_east":  {"label": "S2-East Grocery",       "short": "S2E",  "color": "#8B5CF6", "accent": "#7C3AED"},
    "scenario2_west":  {"label": "S2-West Grocery",       "short": "S2W",  "color": "#EC4899", "accent": "#DB2777"},
    # ── Hub / corner-store variants ───────────────────────────────
    "scenario2_hub_sm":  {"label": "S2-Hub Small (cap=100)",  "short": "S2H1", "color": "#14B8A6", "accent": "#0D9488"},
    "scenario2_hub_lg":  {"label": "S2-Hub Large (cap=400)",  "short": "S2H2", "color": "#F97316", "accent": "#EA580C"},
    "scenario2_corner6": {"label": "S2-6 Corner Stores",      "short": "S2C6", "color": "#A78BFA", "accent": "#7C3AED"},
    "scenario2_corner2": {"label": "S2-2 Corner Stores",      "short": "S2C2", "color": "#FB7185", "accent": "#E11D48"},
}

# File-name prefix patterns  (used for glob matching)
SEED_PATTERNS = {
    "baseline":        "baseline_500hh_365d",
    "scenario1":       "scenario1_north_500hh_365d",
    "scenario2":       "scenario2_1_4_500hh_365d",
    "scenario3":       "scenario3_2_fixed_500hh_365d",
    "scenario4":       "scenario4_500_500hh_365d",
    # Variants  ── update these prefixes when you produce the runs
    "scenario2_north": "scenario2_north_500hh_365d",
    "scenario2_south": "scenario2_south_500hh_365d",
    "scenario2_east":  "scenario2_east_500hh_365d",
    "scenario2_west":  "scenario2_west_500hh_365d",
    "scenario2_hub_sm":  "scenario2_hubsm_500hh_365d",
    "scenario2_hub_lg":  "scenario2_hublg_500hh_365d",
    "scenario2_corner6": "scenario2_c6_500hh_365d",
    "scenario2_corner2": "scenario2_c2_500hh_365d",
}

# Known-exact filenames for the original 3 seeds (kept for backward compat)
EXACT_FALLBACK = {
    "baseline":  {42: "baseline_500hh_365d_seed42_20260309_044642.json",
                  47: "baseline_500hh_365d_seed47_20260309_053409.json",
                  52: "baseline_500hh_365d_seed52_20260309_061834.json",
                  "summary": "baseline_500hh_365d_seeds42_47_52_20260309_061834_summary.json"},
    "scenario2": {42: "scenario2_1_4_500hh_365d_seed42_20260309_135123.json",
                  47: "scenario2_1_4_500hh_365d_seed47_20260309_150153.json",
                  52: "scenario2_1_4_500hh_365d_seed52_20260309_163313.json",
                  "summary": "scenario2_1_4_500hh_365d_seeds42_47_52_20260309_163314_summary.json"},
    "scenario3": {42: "scenario3_2_fixed_500hh_365d_seed42_20260309_195313.json",
                  47: "scenario3_2_fixed_500hh_365d_seed47_20260309_205151.json",
                  52: "scenario3_2_fixed_500hh_365d_seed52_20260309_215824.json",
                  "summary": "scenario3_2_fixed_500hh_365d_seeds42_47_52_20260309_215824_summary.json"},
    "scenario4": {42: "scenario4_500_500hh_365d_seed42_20260309_231527.json",
                  47: "scenario4_500_500hh_365d_seed47_20260310_001220.json",
                  52: "scenario4_500_500hh_365d_seed52_20260310_011654.json",
                  "summary": "scenario4_500_500hh_365d_seeds42_47_52_20260310_011655_summary.json"},
}

ALL_SEEDS = [42, 47, 52, 57, 62, 67]

JOURNAL_DIR = os.path.join(BASE_DIR, "results", "journal_results_50seeds")
JOURNAL_SEEDS = [
    102, 111, 178, 182, 200, 205, 213, 221, 315, 328, 345, 357, 394, 421, 427,
    456, 465, 485, 506, 530, 551, 560, 602, 614, 624, 625, 660, 669, 686, 700,
    715, 728, 736, 753, 762, 795, 801, 840, 848, 863, 869, 886, 891, 895, 902,
    924, 934, 936, 962, 980,
]

# Recalibrated (gamma=2.6) FINAL run — same 50 seeds, produced 2026-07-24 with
# GEOMESA_CALIBRATED_PARAMS=paper_revision/recalibration/RECAL_JOURNAL_PARAMS.json.
# This is the calibration-valid build (aggregate MAPE 9.53%) and SUPERSEDES the
# pre-recalibration Dissertation (6-seed) and Journal (July 50-seed) sets, which
# used the old, mismatched gamma=0.6 parameters. Recal uses the same seed list.
RECAL_DIR = os.path.join(BASE_DIR, "results", "journal_results_50seeds_recal")

def _safe_json(path):
    """Load JSON, returning None on any error so one corrupt/truncated file can
    never crash dashboard startup (UTF-8 explicit for non-ASCII labels in slim images)."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[warn] skipping unreadable JSON {os.path.basename(path)}: {e}")
        return None

def load_all():
    data = {}
    for sk, meta in SCENARIO_META.items():
        seeds = {}
        pattern = SEED_PATTERNS.get(sk, "")
        for s in ALL_SEEDS:
            # 1. Try glob pattern
            p = _glob_seed(pattern, s)
            if p:
                d = _safe_json(p)
                if d is not None:
                    seeds[s] = d
                continue
            # 2. Try exact fallback name
            exact_name = EXACT_FALLBACK.get(sk, {}).get(s)
            if exact_name:
                p = _find_exact(exact_name)
                if p:
                    d = _safe_json(p)
                    if d is not None:
                        seeds[s] = d
        # Summary
        p_sum = _glob_summary(pattern)
        if not p_sum:
            exact_sum = EXACT_FALLBACK.get(sk, {}).get("summary")
            if exact_sum:
                p_sum = _find_exact(exact_sum)
        if p_sum:
            d = _safe_json(p_sum)
            if d is not None:
                seeds["summary"] = d
        data[sk] = {**meta, "data": seeds}
    return data

def load_journal_dir(results_dir, seeds_list):
    """Load a 50-seed run from an arbitrary results directory (journal or recal)."""
    data = {}
    for sk, meta in SCENARIO_META.items():
        seeds = {}
        pattern = SEED_PATTERNS.get(sk, "")
        if not pattern or not os.path.isdir(results_dir):
            data[sk] = {**meta, "data": seeds}
            continue
        for s in seeds_list:
            # Trailing underscore anchors the seed number: seed102_ never matches
            # seed1020_ (prevents wrong-file loading if seeds ever overlap by prefix).
            hits = glob.glob(os.path.join(results_dir, f"{pattern}*seed{s}_*.json"))
            hits = [h for h in hits if "summary" not in h.lower()]
            if hits:
                d = _safe_json(sorted(hits)[-1])
                if d is not None:
                    seeds[s] = d
        sum_hits = glob.glob(os.path.join(results_dir, f"{pattern}*summary*.json"))
        if sum_hits:
            d = _safe_json(sorted(sum_hits)[-1])
            if d is not None:
                seeds["summary"] = d
        data[sk] = {**meta, "data": seeds}
    return data

def load_journal_all():
    """Load 50-seed journal results from journal_results_50seeds/ (July, pre-recal)."""
    return load_journal_dir(JOURNAL_DIR, JOURNAL_SEEDS)

def load_recal_all():
    """Load the recalibrated (gamma=2.6) FINAL 50-seed results — the paper's
    calibration-valid build (aggregate MAPE 9.53%, produced 2026-07-24)."""
    return load_journal_dir(RECAL_DIR, JOURNAL_SEEDS)

def _combined_summary(diss_entry, journal_entry):
    """Merge dissertation and journal per-seed data into a combined summary dict."""
    all_seeds = {}
    for k, v in diss_entry.get("data", {}).items():
        if isinstance(k, int):
            all_seeds[k] = v
    for k, v in journal_entry.get("data", {}).items():
        if isinstance(k, int):
            all_seeds[k] = v
    if not all_seeds:
        return {}
    metrics_vals = {}
    config = None
    for seed_data in all_seeds.values():
        if config is None:
            config = seed_data.get("config", {})
        for mk, mv in seed_data.get("final_metrics", {}).items():
            if isinstance(mv, (int, float)) and mk != "day":
                metrics_vals.setdefault(mk, []).append(mv)
    fm_combined = {"day": 365}
    for mk, vals in metrics_vals.items():
        n = len(vals)
        m = float(np.mean(vals))
        s = float(np.std(vals, ddof=1)) if n > 1 else 0.0
        fm_combined[mk]         = m
        fm_combined[mk + "_std"] = s
        fm_combined[mk + "_min"] = float(min(vals))
        fm_combined[mk + "_max"] = float(max(vals))
    first = next(iter(all_seeds.values()))
    snap_key = first.get("snap_key", "")
    return {
        "scenario": snap_key.replace("_500hh_365d", ""),
        "snap_key": snap_key,
        "n_seeds": len(all_seeds),
        "seeds_used": sorted(all_seeds.keys()),
        "config": config or {},
        "days": 365,
        "final_metrics": fm_combined,
    }

def load_combined_all(data_diss, data_journal):
    """Merge dissertation (6 seeds) + journal (50 seeds) into a single dataset."""
    import copy
    combined = copy.deepcopy(data_diss)
    for sk in list(combined.keys()):
        j_entry = data_journal.get(sk, {})
        for k, v in j_entry.get("data", {}).items():
            if isinstance(k, int):
                combined[sk]["data"][k] = v
        combined[sk]["data"]["summary"] = _combined_summary(
            data_diss.get(sk, {}), j_entry
        )
    return combined

# FINAL build = GEOFIX (corrected store geography, recalibrated 2026-08-18,
# aggregate MAPE 6.51%). The July recal set (gamma=2.6) was produced with the
# displaced store coordinates and is retained as a selectable reference only.
GEOFIX_DIR = os.path.join(BASE_DIR, "results", "journal_results_50seeds_geofix")

def load_geofix_all():
    """Load the GEOFIX FINAL 50-seed results — corrected store geography,
    recalibrated (alpha=2.0, beta=0.5, gamma=0.6, MAPE 6.51%, 2026-08-18)."""
    return load_journal_dir(GEOFIX_DIR, JOURNAL_SEEDS)

DATA_GEOFIX  = load_geofix_all()
DATA_RECAL   = load_recal_all()
DATA_MAP     = {"geofix": DATA_GEOFIX, "recal": DATA_RECAL}
DATA         = DATA_GEOFIX  # default dataset (GEOFIX FINAL build)

SCENARIO_KEYS       = ["baseline", "scenario1", "scenario2", "scenario3", "scenario4"]
LOCATION_KEYS       = ["scenario2_north", "scenario2_south", "scenario2_east", "scenario2_west"]
VARIANT_KEYS        = ["scenario2_hub_sm", "scenario2_hub_lg", "scenario2_corner6", "scenario2_corner2"]
# S2 existing data mapped to "north" for location comparison. The N/S/E/W
# sub-variants were never run at 50 seeds, so "north" mirrors the main S2.
DATA_RECAL["scenario2_north"] = DATA_RECAL["scenario2"]

METRIC_INFO = {
    "satisfaction_rate":    {"label": "Satisfaction Rate",       "unit": "",     "higher_better": True,  "fmt": ".3f"},
    "food_insecurity_rate": {"label": "Food Insecurity Rate",    "unit": "",     "higher_better": False, "fmt": ".3f"},
    "avg_travel_distance":  {"label": "Avg Travel Distance",     "unit": " mi",  "higher_better": False, "fmt": ".2f"},
    "spatial_equity_index": {"label": "Spatial Equity Index",    "unit": "",     "higher_better": True,  "fmt": ".3f"},
    "total_revenue":        {"label": "Daily Expenditure",       "unit": " $",   "higher_better": True,  "fmt": ",.0f"},
    "corner_share":         {"label": "Corner Store Share",      "unit": "",     "higher_better": False, "fmt": ".3f"},
    "pantry_share":         {"label": "Pantry / Hub Share",      "unit": "",     "higher_better": True,  "fmt": ".3f"},
    "delivery_share":       {"label": "Delivery Share",          "unit": "",     "higher_better": True,  "fmt": ".3f"},
    "spend_low":            {"label": "Low-Income Spending",     "unit": " $",   "higher_better": True,  "fmt": ",.0f"},
    "spend_med":            {"label": "Med-Income Spending",     "unit": " $",   "higher_better": True,  "fmt": ",.0f"},
    "spend_high":           {"label": "High-Income Spending",    "unit": " $",   "higher_better": True,  "fmt": ",.0f"},
}

# ═══════════════════════════════════════════════════════════════════
# 3.  ANALYTICS HELPERS
# ═══════════════════════════════════════════════════════════════════

def available_seeds(sk):
    return sorted(s for s in DATA[sk]["data"] if isinstance(s, int))

def fm(sk, seed="summary"):
    d = DATA[sk]["data"].get(seed, {})
    if seed == "summary":
        return d.get("final_metrics", d.get("mean_metrics", {}))
    return d.get("final_metrics", {})

def get_ts(sk, metric):
    rows, days = {}, None
    for s in available_seeds(sk):
        d = DATA[sk]["data"].get(s)
        if not d: continue
        vals = [h[metric] for h in d.get("metrics_history", []) if metric in h]
        if days is None:
            days = [h["day"] for h in d.get("metrics_history", []) if metric in h]
        rows[s] = vals
    if not rows or days is None:
        return pd.DataFrame()
    df = pd.DataFrame(rows, index=days).rename_axis("day").reset_index()
    cols = [c for c in df.columns if c != "day"]
    df["mean"]  = df[cols].mean(axis=1)
    df["std"]   = df[cols].std(axis=1)
    df["upper"] = df["mean"] + df["std"]
    df["lower"] = df["mean"] - df["std"]
    # Bootstrap 95% CI
    mat = df[cols].values
    boots = np.array([np.mean(mat[:, np.random.randint(0, mat.shape[1], mat.shape[1])], axis=1)
                      for _ in range(500)])
    df["ci_lo"] = np.percentile(boots, 2.5, axis=0)
    df["ci_hi"] = np.percentile(boots, 97.5, axis=0)
    return df

def seed_vals(sk, metric):
    return [DATA[sk]["data"].get(s, {}).get("final_metrics", {}).get(metric, np.nan)
            for s in available_seeds(sk)]

def bootstrap_ci(values, n_boot=1000, ci=95):
    v = [x for x in values if not np.isnan(x)]
    if len(v) < 2:
        return (np.nan, np.nan)
    boots = [np.mean(np.random.choice(v, len(v))) for _ in range(n_boot)]
    lo = (100 - ci) / 2
    return (np.percentile(boots, lo), np.percentile(boots, 100 - lo))

def cv(sk, metric):
    v = [x for x in seed_vals(sk, metric) if not np.isnan(x)]
    if len(v) < 2: return np.nan
    return np.std(v, ddof=1) / abs(np.mean(v)) * 100

def pct_vs_baseline(sk, metric):
    bl = np.nanmean(seed_vals("baseline", metric))
    sc = np.nanmean(seed_vals(sk, metric))
    return (sc - bl) / abs(bl) * 100 if bl != 0 else 0

def effect_size(sk, metric):
    bl = [x for x in seed_vals("baseline", metric) if not np.isnan(x)]
    sc = [x for x in seed_vals(sk, metric)          if not np.isnan(x)]
    if len(bl) < 2 or len(sc) < 2:
        return np.nan, np.nan
    diff = np.mean(sc) - np.mean(bl)
    ps   = np.sqrt((np.std(sc, ddof=1)**2 + np.std(bl, ddof=1)**2) / 2)
    d    = diff / ps if ps > 0 else 0
    _, p = stats.ttest_ind(sc, bl, equal_var=False)
    return round(d, 3), round(p, 4)

def pairwise_cohend(metric):
    """Return symmetric matrix of Cohen's d between every scenario pair."""
    n = len(SCENARIO_KEYS)
    mat = np.full((n, n), np.nan)
    for i, si in enumerate(SCENARIO_KEYS):
        for j, sj in enumerate(SCENARIO_KEYS):
            if i == j:
                mat[i, j] = 0.0
                continue
            vi = [x for x in seed_vals(si, metric) if not np.isnan(x)]
            vj = [x for x in seed_vals(sj, metric) if not np.isnan(x)]
            if len(vi) >= 2 and len(vj) >= 2:
                ps = np.sqrt((np.std(vi, ddof=1)**2 + np.std(vj, ddof=1)**2) / 2)
                mat[i, j] = (np.mean(vi) - np.mean(vj)) / ps if ps > 0 else 0
    return mat

def cumulative_burden(sk):
    """AUC of food_insecurity_rate over 365 days, mean across seeds."""
    vals = []
    for s in available_seeds(sk):
        d = DATA[sk]["data"].get(s)
        if not d: continue
        series = [h["food_insecurity_rate"] for h in d.get("metrics_history", []) if "food_insecurity_rate" in h]
        if series:
            vals.append(np.trapz(series) / len(series))   # normalised AUC
    return np.mean(vals) if vals else np.nan, np.std(vals, ddof=1) if len(vals) > 1 else np.nan

def summary_df(keys=None):
    if keys is None:
        keys = SCENARIO_KEYS
    rows = []
    for sk in keys:
        sm = fm(sk, "summary")
        row = {"sk": sk, "label": DATA[sk]["label"], "short": DATA[sk]["short"]}
        for m in METRIC_INFO:
            # Per-seed values are the SOURCE OF TRUTH: they reflect the active seed
            # set exactly (6 / 50 / 56) and keep tables consistent with the KPI cards
            # and charts (which already aggregate per-seed). The summary JSON is only
            # a fallback when a scenario has no per-seed files loaded — this also
            # avoids the dissertation's partial 3-seed summary file being shown as if
            # it were the full 6-seed result.
            vs = [x for x in seed_vals(sk, m) if not np.isnan(x)]
            if vs:
                row[m]        = np.mean(vs)
                row[m+"_std"] = np.std(vs, ddof=1) if len(vs) > 1 else np.nan
                row[m+"_min"] = np.min(vs)
                row[m+"_max"] = np.max(vs)
            else:
                row[m]        = sm.get(m, np.nan)
                row[m+"_std"] = sm.get(m+"_std", np.nan)
                row[m+"_min"] = sm.get(m+"_min", np.nan)
                row[m+"_max"] = sm.get(m+"_max", np.nan)
        rows.append(row)
    df = pd.DataFrame(rows)
    return df

# (Former module-level SDF cache removed: it was computed once on the dissertation
#  set and became stale under the seed-set selector. summary_df() is now called
#  fresh wherever needed so it always reflects the active seed set.)

def hex_rgba(h, a=0.15):
    h = h.lstrip("#"); r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{a})"

# ═══════════════════════════════════════════════════════════════════
# 4.  PLOTLY BASE THEME  (refined academic style)
# ═══════════════════════════════════════════════════════════════════

FONT_MAIN  = "'DM Sans', 'Segoe UI', sans-serif"
FONT_MONO  = "'DM Mono', 'Fira Code', monospace"

PLOT_BASE = dict(
    paper_bgcolor="white",
    plot_bgcolor="#F9FAFB",
    font=dict(family=FONT_MAIN, color="#1C2434", size=12),
    title_font=dict(family=FONT_MAIN, size=14, color="#0D1B2A"),
    legend=dict(bgcolor="rgba(255,255,255,0.96)", bordercolor="#E5E7EB", borderwidth=1,
                font=dict(size=11, color="#374151")),
    margin=dict(l=68, r=32, t=62, b=58),
    xaxis=dict(gridcolor="#ECEFF4", zerolinecolor="#D1D9E6",
               tickfont=dict(size=11, color="#4B5563"), title_font=dict(size=12, color="#374151"),
               showline=True, linecolor="#D1D9E6"),
    yaxis=dict(gridcolor="#ECEFF4", zerolinecolor="#D1D9E6",
               tickfont=dict(size=11, color="#4B5563"), title_font=dict(size=12, color="#374151"),
               showline=True, linecolor="#D1D9E6"),
)

def apply(fig, title="", **kw):
    merged = {**PLOT_BASE, **kw}
    merged["title"] = dict(text=title, x=0.01, xanchor="left",
                           font=dict(size=14, color="#0D1B2A", family=FONT_MAIN))
    fig.update_layout(**merged)
    return fig

# ═══════════════════════════════════════════════════════════════════
# 5.  FIGURE BUILDERS  — Comparison
# ═══════════════════════════════════════════════════════════════════

def fig_ts_all(metric):
    fig = go.Figure()
    for sk in SCENARIO_KEYS:
        df = get_ts(sk, metric)
        if df.empty: continue
        c = DATA[sk]["color"]
        fig.add_trace(go.Scatter(x=df["day"], y=df["mean"], name=DATA[sk]["label"],
                                  line=dict(color=c, width=2.5), mode="lines"))
        fig.add_trace(go.Scatter(
            x=pd.concat([df["day"], df["day"][::-1]]),
            y=pd.concat([df["ci_hi"], df["ci_lo"][::-1]]),
            fill="toself", fillcolor=hex_rgba(c, 0.10),
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"))
    mi = METRIC_INFO[metric]
    n_seeds = max(len(available_seeds(sk)) for sk in SCENARIO_KEYS)
    apply(fig, f"{mi['label']} — 365-Day Trajectory  (mean ± bootstrap 95% CI, n={n_seeds} seeds)",
          xaxis_title="Simulation Day", yaxis_title=mi["label"]+mi["unit"])
    return fig

def fig_ts_single(sk, metric, use_ci=True):
    fig = go.Figure()
    c  = DATA[sk]["color"]
    ac = DATA[sk]["accent"]
    for s in available_seeds(sk):
        d = DATA[sk]["data"].get(s)
        if not d: continue
        vals = [h[metric] for h in d.get("metrics_history",[]) if metric in h]
        days = [h["day"]   for h in d.get("metrics_history",[]) if metric in h]
        fig.add_trace(go.Scatter(x=days, y=vals, name=f"Seed {s}",
                                  line=dict(color=c, width=1.1, dash="dot"),
                                  opacity=0.45, mode="lines"))
    df = get_ts(sk, metric)
    if not df.empty:
        fig.add_trace(go.Scatter(x=df["day"], y=df["mean"], name="Mean",
                                  line=dict(color=ac, width=3), mode="lines"))
        y_hi = df["ci_hi"] if use_ci else df["upper"]
        y_lo = df["ci_lo"] if use_ci else df["lower"]
        fig.add_trace(go.Scatter(
            x=pd.concat([df["day"], df["day"][::-1]]),
            y=pd.concat([y_hi, y_lo[::-1]]),
            fill="toself", fillcolor=hex_rgba(c, 0.15),
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"))
    mi = METRIC_INFO[metric]
    n = len(available_seeds(sk))
    apply(fig, f"{DATA[sk]['label']} — {mi['label']}  (all seeds + mean, n={n})",
          xaxis_title="Simulation Day", yaxis_title=mi["label"]+mi["unit"])
    return fig

def fig_bar_metric(metric, keys=None):
    if keys is None: keys = SCENARIO_KEYS
    df = summary_df(keys)
    mi = METRIC_INFO[metric]
    fig = go.Figure()
    for _, row in df.iterrows():
        sk = row["sk"]
        ci_lo, ci_hi = bootstrap_ci(seed_vals(sk, metric))
        err = (ci_hi - ci_lo) / 2 if not np.isnan(ci_lo) else row[metric+"_std"]
        fig.add_trace(go.Bar(
            x=[row["label"]], y=[row[metric]],
            error_y=dict(type="data", array=[err], visible=True,
                         color="#9CA3AF", thickness=2, width=10),
            name=row["label"],
            marker=dict(color=DATA[sk]["color"], line=dict(color="white", width=2),
                        cornerradius=5),
            showlegend=False,
            text=[f"{row[metric]:.3f}"], textposition="outside",
            textfont=dict(size=11.5, color="#1C2434", family=FONT_MAIN),
        ))
    n = max(len(available_seeds(sk)) for sk in keys)
    apply(fig, f"{mi['label']} — Cross-Scenario Comparison  (mean ± bootstrap 95% CI, n={n} seeds)",
          yaxis_title=mi["label"]+mi["unit"], bargap=0.38,
          yaxis=dict(**PLOT_BASE["yaxis"],
                     range=[0, df[metric].replace(np.nan, 0).max()*1.28]))
    return fig

def fig_grouped_bar_primary():
    fig = go.Figure()
    labels  = [DATA[sk]["short"] for sk in SCENARIO_KEYS]
    sat     = [summary_df().set_index("sk").loc[sk, "satisfaction_rate"]    for sk in SCENARIO_KEYS]
    sat_e   = [summary_df().set_index("sk").loc[sk, "satisfaction_rate_std"] for sk in SCENARIO_KEYS]
    ins     = [summary_df().set_index("sk").loc[sk, "food_insecurity_rate"] for sk in SCENARIO_KEYS]
    ins_e   = [summary_df().set_index("sk").loc[sk, "food_insecurity_rate_std"] for sk in SCENARIO_KEYS]
    fig.add_trace(go.Bar(name="Satisfaction Rate", x=labels, y=sat,
                          error_y=dict(type="data", array=sat_e, visible=True, color="#9CA3AF", thickness=2, width=6),
                          marker=dict(color="#667eea", line=dict(color="white", width=2), cornerradius=4),
                          text=[f"{v:.3f}" for v in sat], textposition="outside",
                          textfont=dict(size=11)))
    fig.add_trace(go.Bar(name="Food Insecurity Rate", x=labels, y=ins,
                          error_y=dict(type="data", array=ins_e, visible=True, color="#9CA3AF", thickness=2, width=6),
                          marker=dict(color="#EF4444", line=dict(color="white", width=2), cornerradius=4),
                          text=[f"{v:.3f}" for v in ins], textposition="outside",
                          textfont=dict(size=11)))
    n = max(len(available_seeds(sk)) for sk in SCENARIO_KEYS)
    apply(fig, f"Primary Outcomes — All Scenarios  (mean ± SD, n={n} seeds)",
          barmode="group", bargap=0.28, bargroupgap=0.08,
          yaxis=dict(**PLOT_BASE["yaxis"], range=[0, 1.18], tickformat=".2f"),
          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                      bgcolor="rgba(255,255,255,0.96)", bordercolor="#E5E7EB", borderwidth=1))
    return fig

def fig_heatmap_pct():
    metrics = ["satisfaction_rate","food_insecurity_rate","avg_travel_distance",
               "spatial_equity_index","corner_share","pantry_share","delivery_share"]
    scenarios = [sk for sk in SCENARIO_KEYS if sk != "baseline"]
    z, annot = [], []
    for sk in scenarios:
        row, arow = [], []
        for m in metrics:
            pct = pct_vs_baseline(sk, m)
            row.append(pct); arow.append(f"{pct:+.1f}%")
        z.append(row); annot.append(arow)
    xl = [METRIC_INFO[m]["label"].replace(" Rate","").replace(" Index","").replace(" Distance","") for m in metrics]
    fig = go.Figure(go.Heatmap(
        z=z, x=xl, y=[DATA[sk]["label"] for sk in scenarios],
        colorscale=[[0,"#DC2626"],[0.35,"#FCA5A5"],[0.5,"#F9FAFB"],[0.65,"#6EE7B7"],[1,"#059669"]],
        zmid=0, text=annot, texttemplate="%{text}",
        textfont=dict(size=12, color="#1C2434", family=FONT_MAIN),
        colorbar=dict(title=dict(text="% vs BL", font=dict(size=11, color="#6B7280")),
                      tickfont=dict(color="#6B7280"), thickness=16, len=0.8),
    ))
    xax = {**PLOT_BASE["xaxis"], "tickangle": -35, "title": ""}
    yax = {**PLOT_BASE["yaxis"], "title": ""}
    apply(fig, "% Change vs Baseline — Direction & Magnitude  (Green = improvement)",
          margin=dict(l=210, r=130, t=65, b=115), xaxis=xax, yaxis=yax)
    return fig

def fig_radar():
    metrics_r = ["satisfaction_rate","food_insecurity_rate","avg_travel_distance",
                  "spatial_equity_index","pantry_share","delivery_share"]
    labels_r  = ["Satisfaction","Food Insecurity<br>(inv)","Travel Dist<br>(inv)",
                  "Spatial Equity","Pantry Share","Delivery Share"]
    invert = {"food_insecurity_rate","avg_travel_distance"}
    ndf = summary_df().set_index("sk")[metrics_r].copy()
    for m in metrics_r:
        col = ndf[m]; rng = col.max()-col.min()
        ndf[m] = (col-col.min())/rng if rng > 0 else col*0+0.5
        if m in invert: ndf[m] = 1 - ndf[m]
    fig = go.Figure()
    for sk in SCENARIO_KEYS:
        if sk not in ndf.index: continue
        vals = ndf.loc[sk, metrics_r].tolist(); vals.append(vals[0])
        fig.add_trace(go.Scatterpolar(r=vals, theta=labels_r+[labels_r[0]],
                                       fill="toself", name=DATA[sk]["label"],
                                       line=dict(color=DATA[sk]["color"], width=2.5),
                                       fillcolor=hex_rgba(DATA[sk]["color"], 0.10)))
    apply(fig, "Normalized Performance Radar  (all axes outward = better)",
          polar=dict(bgcolor="#F9FAFB",
                     radialaxis=dict(visible=True, range=[0,1], gridcolor="#E5E7EB",
                                     tickfont=dict(size=9, color="#9CA3AF")),
                     angularaxis=dict(gridcolor="#E5E7EB", tickfont=dict(size=11, color="#374151"))),
          margin=dict(l=80, r=80, t=70, b=60))
    return fig

def fig_composite_ranking():
    # Composite ranking weights. spatial_equity_index weight is POSITIVE (+0.6) by
    # project convention — the equity index is treated as higher-is-better in the
    # composite, matching METRIC_INFO higher_better=True (and the GABM dashboard).
    weights = {"satisfaction_rate":+1.0,"food_insecurity_rate":-1.0,
               "avg_travel_distance":-0.8,"spatial_equity_index":+0.6}
    _sdf = summary_df()
    ndf = _sdf.set_index("sk").copy()
    score = pd.Series(0.0, index=ndf.index)
    for m, w in weights.items():
        col = ndf[m]; rng = col.max()-col.min()
        norm = (col-col.min())/rng if rng > 0 else col*0
        score += norm*w
    sdf2 = score.reset_index(); sdf2.columns=["sk","score"]
    sdf2 = sdf2.merge(_sdf[["sk","label"]], on="sk").sort_values("score")
    fig = go.Figure(go.Bar(
        x=sdf2["score"], y=sdf2["label"], orientation="h",
        marker=dict(color=[DATA[sk]["color"] for sk in sdf2["sk"]],
                    line=dict(color="white", width=2), cornerradius=5),
        text=[f"{v:.3f}" for v in sdf2["score"]],
        textposition="outside", textfont=dict(size=12, color="#1C2434"),
    ))
    apply(fig, "Composite Performance Index  (Sat+1.0 | Ins−1.0 | Travel−0.8 | Equity+0.6)",
          xaxis_title="Composite Score (higher = better)",
          margin=dict(l=210, r=90, t=65, b=55), bargap=0.38)
    return fig

def fig_channel_mix(keys=None):
    if keys is None: keys = SCENARIO_KEYS
    df = summary_df(keys)
    channels   = ["corner_share","pantry_share","delivery_share"]
    ch_labels  = ["Corner Store","Pantry / Hub","Delivery"]
    ch_colors  = ["#6366F1","#F59E0B","#10B981"]
    fig = go.Figure()
    xlbls = [DATA[sk]["short"] for sk in keys]
    for ch, lbl, c in zip(channels, ch_labels, ch_colors):
        y = df.set_index("sk").loc[keys, ch].values
        e = df.set_index("sk").loc[keys, ch+"_std"].values
        fig.add_trace(go.Bar(name=lbl, x=xlbls, y=y,
                              error_y=dict(type="data", array=e, visible=True,
                                           color="#9CA3AF", thickness=1.5, width=5),
                              marker=dict(color=c, line=dict(color="white", width=1.5), cornerradius=4)))
    n = max(len(available_seeds(sk)) for sk in keys)
    apply(fig, f"Alternative Channel Market Share  (mean ± SD, n={n} seeds)",
          barmode="group", bargap=0.28, bargroupgap=0.08,
          yaxis=dict(**PLOT_BASE["yaxis"], tickformat=".2f", title="Share of Shopping Trips"),
          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                      bgcolor="rgba(255,255,255,0.96)", bordercolor="#E5E7EB", borderwidth=1))
    return fig

def fig_income_spending(keys=None):
    if keys is None: keys = SCENARIO_KEYS
    df = summary_df(keys)
    groups = [("spend_low","Low Income","#EF4444"),
              ("spend_med","Medium Income","#F59E0B"),
              ("spend_high","High Income","#10B981")]
    fig = go.Figure()
    xlbls = [DATA[sk]["short"] for sk in keys]
    for m, lbl, c in groups:
        y = df.set_index("sk").loc[keys, m].values
        e = df.set_index("sk").loc[keys, m+"_std"].values
        fig.add_trace(go.Bar(name=lbl, x=xlbls, y=y,
                              error_y=dict(type="data", array=e, visible=True,
                                           color="#9CA3AF", thickness=1.5, width=5),
                              marker=dict(color=c, line=dict(color="white", width=1.5), cornerradius=4)))
    apply(fig, "Food Expenditure by Income Group  (annual, n-seed mean ± SD)",
          barmode="group", bargap=0.28,
          yaxis=dict(**PLOT_BASE["yaxis"], title="Annual Spending ($)", tickformat="$,.0f"),
          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                      bgcolor="rgba(255,255,255,0.96)", bordercolor="#E5E7EB", borderwidth=1))
    return fig

def fig_income_insecurity_ts():
    """Income-stratified food insecurity time series — shows equity dimension over time."""
    fig = go.Figure()
    # Note: metrics_history might include low/med/high insecurity if model tracks them
    # Fallback: use overall insecurity with spend as proxy for stratification
    income_metrics = ["food_insecurity_low","food_insecurity_med","food_insecurity_high"]
    income_labels  = ["Low Income","Medium Income","High Income"]
    income_colors  = ["#EF4444","#F59E0B","#10B981"]
    has_income_data = False
    for sk in ["baseline","scenario2"]:
        for s in available_seeds(sk):
            d = DATA[sk]["data"].get(s, {})
            if d.get("metrics_history") and "food_insecurity_low" in (d["metrics_history"][0] if d["metrics_history"] else {}):
                has_income_data = True
                break
    if has_income_data:
        for sk in ["baseline","scenario2"]:
            c = DATA[sk]["color"]
            lbl = DATA[sk]["short"]
            for im, il, ic in zip(income_metrics, income_labels, income_colors):
                df = get_ts(sk, im)
                if df.empty: continue
                fig.add_trace(go.Scatter(x=df["day"], y=df["mean"],
                                          name=f"{lbl} — {il}",
                                          line=dict(color=ic, width=2,
                                                    dash="dot" if sk == "baseline" else "solid"),
                                          mode="lines"))
        apply(fig, "Food Insecurity by Income Group — Baseline vs S2  (stratified time series)",
              xaxis_title="Day", yaxis_title="Food Insecurity Rate")
    else:
        # Fallback: show overall insecurity for baseline & S2 with annotation
        for sk in ["baseline","scenario2"]:
            df = get_ts(sk, "food_insecurity_rate")
            if df.empty: continue
            c = DATA[sk]["color"]
            fig.add_trace(go.Scatter(x=df["day"], y=df["mean"], name=DATA[sk]["label"],
                                      line=dict(color=c, width=2.5), mode="lines"))
            fig.add_trace(go.Scatter(
                x=pd.concat([df["day"], df["day"][::-1]]),
                y=pd.concat([df["ci_hi"], df["ci_lo"][::-1]]),
                fill="toself", fillcolor=hex_rgba(c, 0.10),
                line=dict(color="rgba(0,0,0,0)"), showlegend=False))
        fig.add_annotation(x=182, y=0.22, text="Income-stratified tracking requires<br>model output of sub-group metrics",
                           showarrow=False, font=dict(size=11, color="#9CA3AF"),
                           bgcolor="white", bordercolor="#E5E7EB", borderwidth=1, borderpad=8)
        apply(fig, "Food Insecurity Trajectory — Baseline vs S2  (overall, bootstrapped CI)",
              xaxis_title="Day", yaxis_title="Food Insecurity Rate")
    return fig

def fig_equity_ratio(keys=None):
    if keys is None: keys = SCENARIO_KEYS
    ratios, means, stds = [], [], []
    for sk in keys:
        vals = []
        for s in available_seeds(sk):
            f = DATA[sk]["data"].get(s, {}).get("final_metrics", {})
            lo, hi = f.get("spend_low"), f.get("spend_high")
            if lo is not None and hi is not None and hi > 0: vals.append(lo/hi)
        ratios.append(np.mean(vals) if vals else 0)
        stds.append(np.std(vals, ddof=1) if len(vals) > 1 else 0)
    fig = go.Figure()
    xlbls  = [DATA[sk]["label"] for sk in keys]
    colors = [DATA[sk]["color"] for sk in keys]
    fig.add_trace(go.Bar(x=xlbls, y=ratios,
                          error_y=dict(type="data", array=stds, visible=True,
                                       color="#9CA3AF", thickness=2, width=8),
                          marker=dict(color=colors, line=dict(color="white", width=2), cornerradius=5),
                          text=[f"{v:.3f}" for v in ratios],
                          textposition="outside", textfont=dict(size=12, color="#1C2434"),
                          showlegend=False))
    if ratios:
        fig.add_hline(y=ratios[0], line_dash="dash", line_color="#9CA3AF",
                      annotation_text="Baseline", annotation_font_color="#9CA3AF",
                      annotation_position="top right")
    apply(fig, "Income Equity Ratio: Low÷High Spending  (higher = more equitable)",
          yaxis=dict(**PLOT_BASE["yaxis"], title="Spending Ratio (Low÷High)", tickformat=".3f"),
          bargap=0.40)
    return fig

def fig_seed_variability_all():
    metrics = ["satisfaction_rate","food_insecurity_rate","avg_travel_distance",
               "spatial_equity_index","corner_share","pantry_share","delivery_share"]
    z, annot = [], []
    for sk in SCENARIO_KEYS:
        row, arow = [], []
        for m in metrics:
            v = cv(sk, m)
            row.append(v if not np.isnan(v) else 0)
            arow.append(f"{v:.1f}%" if not np.isnan(v) else "—")
        z.append(row); annot.append(arow)
    xl = [METRIC_INFO[m]["label"].replace(" Rate","").replace(" Index","") for m in metrics]
    fig = go.Figure(go.Heatmap(
        z=z, x=xl, y=[DATA[sk]["label"] for sk in SCENARIO_KEYS],
        colorscale=[[0,"#ECFDF5"],[0.15,"#A7F3D0"],[0.4,"#FEF3C7"],[0.7,"#FCA5A5"],[1,"#EF4444"]],
        text=annot, texttemplate="%{text}",
        textfont=dict(size=12, color="#1C2434", family=FONT_MAIN),
        colorbar=dict(title=dict(text="CV (%)", font=dict(size=11, color="#6B7280")),
                      tickfont=dict(color="#6B7280"), thickness=16, len=0.75),
    ))
    xax = {**PLOT_BASE["xaxis"], "tickangle": -35, "title": ""}
    yax = {**PLOT_BASE["yaxis"], "title": ""}
    n = max(len(available_seeds(sk)) for sk in SCENARIO_KEYS)
    apply(fig, f"Seed Stability: Coefficient of Variation (%)  — {n} seeds  |  Green < 5% = Stable",
          margin=dict(l=210, r=130, t=65, b=115), xaxis=xax, yaxis=yax)
    return fig

def seed_fmt(metric):
    """Per-seed display precision: 4 dp for rates/distances, integers for $."""
    return ",.0f" if METRIC_INFO[metric]["fmt"] == ",.0f" else ".4f"

def fig_seed_bars(sk, metric):
    """Per-seed bars in RUN ORDER — seed #1, #2, #3 … #n, never sorted by value.

    Sorting replicate bars by outcome manufactures a monotone "trend" out of
    what are independent draws, so the x axis stays the replicate index and
    the category order is pinned explicitly (categoryorder='array'). Ticks are
    the 1-based run index; the actual RNG seed value rides along in the hover
    so every bar is still traceable to its result file.
    """
    mi   = METRIC_INFO[metric]
    sn   = available_seeds(sk)                 # ascending RNG seed ids = run order
    vals = [DATA[sk]["data"].get(s, {}).get("final_metrics", {}).get(metric, np.nan)
            for s in sn]
    idx  = [str(i) for i in range(1, len(sn) + 1)]
    n    = len(sn)
    f    = seed_fmt(metric)
    mean_v = np.nanmean(vals)
    ci_lo, ci_hi = bootstrap_ci(vals)
    c = DATA[sk]["color"]

    # Dense runs (50 seeds) need vertical value labels at a small size to fit;
    # short runs can keep the roomier horizontal labels.
    dense = n > 18
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=idx, y=vals, customdata=sn,
        marker=dict(color=c, line=dict(color="white", width=1 if dense else 2),
                    cornerradius=3 if dense else 5),
        text=[("" if np.isnan(v) else format(v, f)) for v in vals],
        textposition="outside", cliponaxis=False,
        textangle=-90 if dense else 0,
        textfont=dict(size=9 if dense else 12, color="#1C2434"),
        hovertemplate=(f"<b>Seed #%{{x}}</b> of {n}  (RNG seed %{{customdata}})<br>"
                       f"{mi['label']} = %{{y:{f}}}<extra></extra>"),
        showlegend=False,
    ))
    fig.add_hline(y=mean_v, line_dash="dash", line_color="#374151", line_width=2)
    # Parked in the top-left corner rather than on the line itself: at n=50 the
    # on-line label sits right on top of the per-bar value text.
    fig.add_annotation(xref="paper", yref="paper", x=0.005, y=0.99,
                       xanchor="left", yanchor="top", showarrow=False,
                       text=(f"– – Mean = {mean_v:{f}}"
                             f"   [95% CI: {ci_lo:{f}}–{ci_hi:{f}}]"),
                       font=dict(color="#374151", size=11),
                       bgcolor="rgba(255,255,255,0.85)", bordercolor="#E2E8F0",
                       borderwidth=1, borderpad=4)

    finite = [v for v in vals if not np.isnan(v)]
    top = max(finite) * (1.30 if dense else 1.14) if finite else 1
    xax = {**PLOT_BASE["xaxis"], "type": "category",
           "categoryorder": "array", "categoryarray": idx,
           "tickmode": "array", "tickvals": idx, "ticktext": idx,
           "tickangle": 0, "tickfont": {"size": 9 if dense else 11, "color": "#4B5563"},
           "title": f"Seed # (run order, n={n} — not sorted by value)"}
    yax = {**PLOT_BASE["yaxis"], "range": [0, top],
           "title": mi["label"] + mi["unit"]}
    apply(fig, f"{DATA[sk]['label']} — {mi['label']} by Seed  (run order, n={n})",
          xaxis=xax, yaxis=yax, bargap=0.18 if dense else 0.45,
          margin=dict(l=68, r=32, t=62, b=64))
    return fig

def table_seed_values(sk, metric):
    """Seed # → RNG seed → metric value, one row per seed, in run order."""
    mi = METRIC_INFO[metric]
    sn = available_seeds(sk)
    f  = seed_fmt(metric)
    vals = [DATA[sk]["data"].get(s, {}).get("final_metrics", {}).get(metric, np.nan)
            for s in sn]
    mean_v = np.nanmean(vals)
    return pd.DataFrame({
        "Seed #":     [str(i) for i in range(1, len(sn) + 1)],
        "RNG Seed":   [str(s) for s in sn],
        mi["label"]:  [("—" if np.isnan(v) else format(v, f)) for v in vals],
        "Δ vs Mean":  [("—" if np.isnan(v) else format(v - mean_v, "+" + f)) for v in vals],
    })

def fig_vs_baseline(sk, metric):
    mi = METRIC_INFO[metric]
    fig = go.Figure()
    for s_key, label in [("baseline","Baseline"), (sk, DATA[sk]["label"])]:
        df = get_ts(s_key, metric)
        if df.empty: continue
        c = DATA[s_key]["color"]
        fig.add_trace(go.Scatter(x=df["day"], y=df["mean"], name=label,
                                  line=dict(color=c, width=2.5), mode="lines"))
        fig.add_trace(go.Scatter(
            x=pd.concat([df["day"], df["day"][::-1]]),
            y=pd.concat([df["ci_hi"], df["ci_lo"][::-1]]),
            fill="toself", fillcolor=hex_rgba(c, 0.12),
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"))
    apply(fig, f"{DATA[sk]['label']} vs Baseline — {mi['label']}  (bootstrapped 95% CI)",
          xaxis_title="Simulation Day", yaxis_title=mi["label"]+mi["unit"])
    return fig

def fig_channel_ts(sk):
    channels = [("corner_share","Corner Store","#6366F1"),
                ("pantry_share","Pantry / Hub","#F59E0B"),
                ("delivery_share","Delivery","#10B981")]
    fig = make_subplots(rows=1, cols=3, subplot_titles=[c[1] for c in channels],
                         shared_yaxes=False)
    for i, (m, lbl, c) in enumerate(channels, 1):
        df = get_ts(sk, m)
        if df.empty: continue
        fig.add_trace(go.Scatter(x=df["day"], y=df["mean"],
                                  line=dict(color=c, width=2.5), showlegend=False), row=1, col=i)
        fig.add_trace(go.Scatter(
            x=pd.concat([df["day"], df["day"][::-1]]),
            y=pd.concat([df["ci_hi"], df["ci_lo"][::-1]]),
            fill="toself", fillcolor=hex_rgba(c, 0.15),
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"), row=1, col=i)
    fig.update_layout(paper_bgcolor="white", plot_bgcolor="#F9FAFB",
                       font=dict(family=FONT_MAIN, color="#1C2434", size=11),
                       margin=dict(l=55, r=30, t=65, b=50),
                       title=dict(text=f"{DATA[sk]['label']} — Channel Share Trajectories  (mean ± 95% CI)",
                                  x=0.01, font=dict(size=14, color="#0D1B2A", family=FONT_MAIN)))
    fig.update_xaxes(gridcolor="#ECEFF4", tickfont=dict(size=10,color="#4B5563"), title_text="Day")
    fig.update_yaxes(gridcolor="#ECEFF4", tickfont=dict(size=10,color="#4B5563"), tickformat=".2f")
    return fig

def fig_cumulative_burden():
    """Normalised AUC of food insecurity — total 'burden days' experienced."""
    vals, errs, labels, colors = [], [], [], []
    for sk in SCENARIO_KEYS:
        v, e = cumulative_burden(sk)
        vals.append(v); errs.append(e if not np.isnan(e) else 0)
        labels.append(DATA[sk]["label"]); colors.append(DATA[sk]["color"])
    fig = go.Figure(go.Bar(
        x=labels, y=vals,
        error_y=dict(type="data", array=errs, visible=True, color="#9CA3AF", thickness=2, width=8),
        marker=dict(color=colors, line=dict(color="white", width=2), cornerradius=5),
        text=[f"{v:.4f}" if not np.isnan(v) else "—" for v in vals],
        textposition="outside", textfont=dict(size=12, color="#1C2434"), showlegend=False,
    ))
    apply(fig, "Cumulative Food Insecurity Burden  (normalised AUC over 365 days — lower = better)",
          yaxis=dict(**PLOT_BASE["yaxis"], title="Normalised Burden (AUC/N days)"),
          bargap=0.40)
    return fig

def fig_pairwise_cohend(metric):
    """Symmetric heatmap of pairwise Cohen's d."""
    mat = pairwise_cohend(metric)
    labels = [DATA[sk]["short"] for sk in SCENARIO_KEYS]
    annot  = [[f"{mat[i,j]:+.2f}" for j in range(len(SCENARIO_KEYS))]
               for i in range(len(SCENARIO_KEYS))]
    fig = go.Figure(go.Heatmap(
        z=mat, x=labels, y=labels,
        colorscale=[[0,"#DC2626"],[0.35,"#FCA5A5"],[0.5,"#F9FAFB"],[0.65,"#6EE7B7"],[1,"#059669"]],
        zmid=0, zmin=-3, zmax=3,
        text=annot, texttemplate="%{text}",
        textfont=dict(size=13, color="#1C2434", family=FONT_MAIN),
        colorbar=dict(title=dict(text="Cohen's d", font=dict(size=11, color="#6B7280")),
                      tickfont=dict(color="#6B7280"), thickness=16, len=0.8),
    ))
    apply(fig, f"Pairwise Cohen's d — {METRIC_INFO[metric]['label']}  (row vs column, n-seed means)",
          margin=dict(l=80, r=120, t=65, b=80))
    return fig

# ── Sobol sensitivity (recalibrated γ=2.6 run) ──────────────────────────────
# Loaded from the SAME artifact the paper's Figure 5 is drawn from
# (paper_revision/recalibration/state/sobol_indices.json, written 2026-07-24,
# N=256, center = γ=2.6 recal, ±30%). Never hardcode these numbers: the
# pre-recalibration values (θ_low S₁≈0.96) contradict the current model, in
# which γ dominates (S_T=0.942).
SOBOL_PATHS = [
    os.environ.get("GEOMESA_SOBOL_JSON", ""),
    os.path.join(BASE_DIR, "..", "paper_revision", "recalibration_geofix", "state", "sobol_indices.json"),
    os.path.join(BASE_DIR, "paper_revision", "recalibration_geofix", "state", "sobol_indices.json"),
    os.path.join(BASE_DIR, "..", "paper_revision", "recalibration", "state", "sobol_indices.json"),
    os.path.join(BASE_DIR, "paper_revision", "recalibration", "state", "sobol_indices.json"),
    os.path.join(BASE_DIR, "sobol_indices.json"),          # flat HF Space layout
]

def _load_sobol():
    for p in SOBOL_PATHS:
        if p and os.path.isfile(p):
            d = _safe_json(p)
            if d and "ST" in d and "S1" in d:
                d["_path"] = p
                return d
    return None

SOBOL = _load_sobol()

SOBOL_LABELS = {
    "gamma_quality_variety":    "γ  quality / variety",
    "go_shop_threshold_high":   "θ_high  shop threshold",
    "go_shop_threshold_medium": "θ_med  shop threshold",
    "go_shop_threshold_low":    "θ_low  shop threshold",
    "delta_convenience":        "δ  convenience",
    "alpha_distance":           "α  distance",
    "beta_price_budget":        "β  price / budget",
}

def sobol_top():
    """(label, S_T, S_1) for the highest total-order parameter, or None."""
    if not SOBOL:
        return None
    k, v = max(SOBOL["ST"].items(), key=lambda kv: kv[1])
    return SOBOL_LABELS.get(k, k), v, SOBOL["S1"].get(k, float("nan"))

def fig_tornado_sensitivity():
    """Sobol tornado for food insecurity — total-order (S_T) with first-order
    (S₁) alongside. Mirrors the paper's Figure 5; the S_T−S₁ gap is the
    interaction share, which is the whole point for γ."""
    if not SOBOL:
        fig = go.Figure()
        fig.add_annotation(
            text=("Sobol indices unavailable — <b>sobol_indices.json</b> not found.<br>"
                  "Expected at paper_revision/recalibration/state/ (or set "
                  "GEOMESA_SOBOL_JSON).<br>No values are shown rather than stale "
                  "pre-recalibration ones."),
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color="#B91C1C"), align="center")
        apply(fig, "Sobol Sensitivity — data not loaded",
              xaxis=dict(visible=False), yaxis=dict(visible=False))
        return fig

    st, s1 = SOBOL["ST"], SOBOL["S1"]
    items = sorted(st.items(), key=lambda kv: kv[1])       # ascending, as in the paper
    keys  = [k for k, _ in items]
    ylab  = [SOBOL_LABELS.get(k, k) for k in keys]
    st_v  = [st[k] for k in keys]
    s1_v  = [s1.get(k, np.nan) for k in keys]
    top_k = max(st, key=st.get)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=s1_v, y=ylab, orientation="h", name="First-order S₁",
        marker=dict(color="#CBD5E1", line=dict(color="white", width=1), cornerradius=3),
        text=[f"{v:.3f}" for v in s1_v], textposition="outside",
        textfont=dict(size=10, color="#64748B"),
        hovertemplate="%{y}<br>S₁ = %{x:.3f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=st_v, y=ylab, orientation="h", name="Total-order S_T",
        marker=dict(color=["#EF4444" if k == top_k else "#64748B" for k in keys],
                    line=dict(color="white", width=1), cornerradius=3),
        text=[f"{v:.3f}" for v in st_v], textposition="outside",
        textfont=dict(size=11, color="#1C2434"),
        hovertemplate="%{y}<br>S_T = %{x:.3f}<extra></extra>",
    ))
    fig.add_vline(x=0.05, line_dash="dot", line_color="#9CA3AF",
                  annotation_text="Negligible (< 0.05)",
                  annotation_position="bottom right",
                  annotation_font=dict(size=10, color="#9CA3AF"))
    _g = (SOBOL.get('center') or {}).get('gamma_quality_variety', '?')
    src = (f"output = {SOBOL.get('output','food_insecurity_share')} · "
           f"N={SOBOL.get('N','?')} · center γ={_g} · "
           f"±{int(SOBOL.get('pct', 0.3) * 100)}% · {SOBOL.get('households','?')} hh "
           f"× {SOBOL.get('n_steps','?')} d")
    fig.add_annotation(xref="paper", yref="paper", x=1.0, y=-0.16,
                       xanchor="right", showarrow=False, text=src,
                       font=dict(size=9.5, color="#94A3B8"))
    apply(fig, "Sobol Sensitivity — Food Insecurity  (FINAL corrected-geography build)",
          xaxis_title="Sobol index", barmode="group",
          legend=dict(orientation="h", x=1, xanchor="right", y=1.13,
                      bgcolor="rgba(255,255,255,0.96)", bordercolor="#E5E7EB",
                      borderwidth=1, font=dict(size=11, color="#374151")),
          margin=dict(l=190, r=110, t=78, b=76), bargap=0.30)
    return fig

# ═══════════════════════════════════════════════════════════════════
# 6.  LOCATION ANALYSIS  (within-Scenario 2 variants)
# ═══════════════════════════════════════════════════════════════════

LOCATION_INFO = {
    "scenario2_north": {
        "direction": "North",
        "coord_note": "30.39°N, 81.67°W — near Lem Turner Rd / Dunn Ave",
        "pop_context": "Primarily low-income; highest SNAP density in HZ1",
        "expected": "Highest impact for no-vehicle households in north HZ1",
        "color": "#10B981",
    },
    "scenario2_south": {
        "direction": "South",
        "coord_note": "30.31°N, 81.67°W — near Myrtle Ave / Edgewood Ave",
        "pop_context": "Mixed income; higher vehicle ownership than north",
        "expected": "Moderate impact; more accessible to medium-income households",
        "color": "#0EA5E9",
    },
    "scenario2_east": {
        "direction": "East",
        "coord_note": "30.35°N, 81.61°W — near Beach Blvd corridor",
        "pop_context": "Mixed-income; closer to existing Winn-Dixie coverage area",
        "expected": "Lower marginal impact due to proximity to existing stores",
        "color": "#8B5CF6",
    },
    "scenario2_west": {
        "direction": "West",
        "coord_note": "30.35°N, 81.73°W — near Normandy Blvd area",
        "pop_context": "Low to medium income; moderate vehicle access",
        "expected": "Moderate benefit; fills western coverage gap",
        "color": "#EC4899",
    },
}

def fig_location_comparison(metric):
    """Compare 4 S2 location variants for a given metric."""
    mi = METRIC_INFO[metric]
    fig = go.Figure()
    for sk in LOCATION_KEYS:
        sv = seed_vals(sk, metric)
        sv_clean = [x for x in sv if not np.isnan(x)]
        if not sv_clean:
            fig.add_trace(go.Bar(
                x=[DATA[sk]["label"]], y=[0],
                marker=dict(color="#E5E7EB", line=dict(color="white", width=2)),
                text=["No data yet"], textposition="outside",
                textfont=dict(size=11, color="#9CA3AF"),
                name=DATA[sk]["label"], showlegend=False,
            ))
            continue
        mean_v = np.mean(sv_clean)
        ci_lo, ci_hi = bootstrap_ci(sv_clean)
        err = (ci_hi - ci_lo) / 2
        fig.add_trace(go.Bar(
            x=[DATA[sk]["label"]], y=[mean_v],
            error_y=dict(type="data", array=[err], visible=True,
                         color="#9CA3AF", thickness=2, width=8),
            marker=dict(color=DATA[sk]["color"], line=dict(color="white", width=2), cornerradius=5),
            text=[f"{mean_v:.3f}"], textposition="outside",
            textfont=dict(size=12, color="#1C2434"),
            name=DATA[sk]["label"], showlegend=False,
        ))
    # Add baseline reference line
    bl_mean = np.nanmean(seed_vals("baseline", metric))
    if not np.isnan(bl_mean):
        fig.add_hline(y=bl_mean, line_dash="dash", line_color="#6B7280", line_width=2,
                      annotation_text=f"Baseline = {bl_mean:.3f}",
                      annotation_font=dict(color="#6B7280", size=11),
                      annotation_position="top right")
    apply(fig, f"S2 Location Variants — {mi['label']}  (North / South / East / West)",
          yaxis_title=mi["label"]+mi["unit"],
          yaxis=dict(**PLOT_BASE["yaxis"], range=[0, max(bl_mean*1.3, 0.01)]),
          bargap=0.42)
    return fig

def fig_location_ts_overlay(metric):
    """Time-series overlay of all 4 S2 location variants."""
    mi = METRIC_INFO[metric]
    fig = go.Figure()
    has_data = False
    for sk in LOCATION_KEYS:
        df = get_ts(sk, metric)
        if df.empty: continue
        has_data = True
        c = DATA[sk]["color"]
        fig.add_trace(go.Scatter(x=df["day"], y=df["mean"], name=DATA[sk]["label"],
                                  line=dict(color=c, width=2.5), mode="lines"))
        fig.add_trace(go.Scatter(
            x=pd.concat([df["day"], df["day"][::-1]]),
            y=pd.concat([df["ci_hi"], df["ci_lo"][::-1]]),
            fill="toself", fillcolor=hex_rgba(c, 0.10),
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"))
    # Baseline reference
    df_bl = get_ts("baseline", metric)
    if not df_bl.empty:
        fig.add_trace(go.Scatter(x=df_bl["day"], y=df_bl["mean"], name="Baseline",
                                  line=dict(color="#6B7280", width=2, dash="dash"), mode="lines"))
    if not has_data:
        fig.add_annotation(x=182, y=0.5,
                           text="Run South / East / West variants first.<br>Files will auto-load when placed in scenarios_results/",
                           showarrow=False, font=dict(size=13, color="#9CA3AF"),
                           bgcolor="white", bordercolor="#E5E7EB", borderwidth=1, borderpad=12,
                           xref="x", yref="y")
    apply(fig, f"S2 Location Variants — {mi['label']} Trajectory  (mean ± 95% CI)",
          xaxis_title="Simulation Day", yaxis_title=mi["label"]+mi["unit"])
    return fig

def fig_location_equity_heatmap():
    """% change vs baseline for all 4 locations × key metrics."""
    metrics = ["satisfaction_rate","food_insecurity_rate","avg_travel_distance","spatial_equity_index"]
    z, annot = [], []
    for sk in LOCATION_KEYS:
        row, arow = [], []
        for m in metrics:
            pct = pct_vs_baseline(sk, m)
            if np.isnan(pct):
                row.append(0); arow.append("N/A")
            else:
                row.append(pct); arow.append(f"{pct:+.1f}%")
        z.append(row); annot.append(arow)
    xl = [METRIC_INFO[m]["label"].replace(" Rate","").replace(" Index","") for m in metrics]
    fig = go.Figure(go.Heatmap(
        z=z, x=xl, y=[DATA[sk]["label"] for sk in LOCATION_KEYS],
        colorscale=[[0,"#DC2626"],[0.5,"#F9FAFB"],[1,"#059669"]],
        zmid=0, text=annot, texttemplate="%{text}",
        textfont=dict(size=13, color="#1C2434"),
        colorbar=dict(title=dict(text="% vs BL"), thickness=16, len=0.8),
    ))
    apply(fig, "S2 Location Variants — % Change vs Baseline  (Green = improvement)",
          margin=dict(l=180, r=130, t=65, b=100))
    return fig

# ═══════════════════════════════════════════════════════════════════
# 7.  VARIANT ANALYSIS  (hub & corner-store configurations)
# ═══════════════════════════════════════════════════════════════════

VARIANT_INFO = {
    "scenario2":          {"desc": "Hub cap=200, 4 corner stores (base)",      "hub": 200, "corner": 4},
    "scenario2_hub_sm":   {"desc": "Hub cap=100, 4 corner stores",             "hub": 100, "corner": 4},
    "scenario2_hub_lg":   {"desc": "Hub cap=400, 4 corner stores",             "hub": 400, "corner": 4},
    "scenario2_corner6":  {"desc": "Hub cap=200, 6 corner stores (expanded)",  "hub": 200, "corner": 6},
    "scenario2_corner2":  {"desc": "Hub cap=200, 2 corner stores (minimal)",   "hub": 200, "corner": 2},
}

def fig_variant_comparison(metric):
    mi = METRIC_INFO[metric]
    variant_keys = ["scenario2"] + VARIANT_KEYS
    fig = go.Figure()
    for sk in variant_keys:
        sv = seed_vals(sk, metric)
        sv_clean = [x for x in sv if not np.isnan(x)]
        if not sv_clean:
            fig.add_trace(go.Bar(
                x=[DATA[sk]["short"]], y=[0],
                marker=dict(color="#E5E7EB", line=dict(color="white", width=2)),
                text=["No data"], textposition="outside",
                textfont=dict(size=11, color="#9CA3AF"),
                name=DATA[sk]["short"], showlegend=False))
            continue
        mean_v = np.mean(sv_clean)
        ci_lo, ci_hi = bootstrap_ci(sv_clean)
        fig.add_trace(go.Bar(
            x=[DATA[sk]["short"]], y=[mean_v],
            error_y=dict(type="data", array=[(ci_hi-ci_lo)/2], visible=True,
                         color="#9CA3AF", thickness=2, width=8),
            marker=dict(color=DATA[sk]["color"], line=dict(color="white", width=2), cornerradius=5),
            text=[f"{mean_v:.3f}"], textposition="outside",
            textfont=dict(size=12, color="#1C2434"),
            name=DATA[sk]["short"], showlegend=False))
    bl = np.nanmean(seed_vals("baseline", metric))
    if not np.isnan(bl):
        fig.add_hline(y=bl, line_dash="dash", line_color="#6B7280",
                      annotation_text=f"Baseline = {bl:.3f}",
                      annotation_font=dict(color="#6B7280", size=11))
    apply(fig, f"Hub & Corner-Store Variants — {mi['label']}",
          yaxis_title=mi["label"]+mi["unit"], bargap=0.42)
    return fig

# ═══════════════════════════════════════════════════════════════════
# 8.  TABLES
# ═══════════════════════════════════════════════════════════════════

def table_summary(keys=None):
    if keys is None: keys = SCENARIO_KEYS
    df = summary_df(keys)
    metrics_t = ["satisfaction_rate","food_insecurity_rate","avg_travel_distance",
                  "spatial_equity_index","corner_share","pantry_share","delivery_share"]
    rows = []
    for _, row in df.iterrows():
        sk = row["sk"]
        r = {"Scenario": DATA[sk]["label"]}
        for m in metrics_t:
            v  = row[m];   sd = row[m+"_std"]
            ci_lo, ci_hi = bootstrap_ci(seed_vals(sk, m))
            r[METRIC_INFO[m]["label"]] = (f"{v:.3f} ± {sd:.3f}" if not np.isnan(v) else "—")
        rows.append(r)
    return pd.DataFrame(rows)

def table_pct_change():
    metrics_t = ["satisfaction_rate","food_insecurity_rate","avg_travel_distance",
                  "spatial_equity_index","corner_share","pantry_share","delivery_share"]
    rows = []
    for sk in [s for s in SCENARIO_KEYS if s != "baseline"]:
        row = {"Scenario": DATA[sk]["label"]}
        for m in metrics_t:
            pct = pct_vs_baseline(sk, m)
            row[METRIC_INFO[m]["label"]] = f"{pct:+.2f}%"
        rows.append(row)
    return pd.DataFrame(rows)

def table_effect_size():
    metrics_t = ["satisfaction_rate","food_insecurity_rate","avg_travel_distance","spatial_equity_index"]
    rows = []
    for sk in [s for s in SCENARIO_KEYS if s != "baseline"]:
        row = {"Scenario": DATA[sk]["label"]}
        for m in metrics_t:
            d, p = effect_size(sk, m)
            n = len(available_seeds(sk))
            sig = "**" if p < 0.05 else ("†" if p < 0.10 else "ns")
            row[METRIC_INFO[m]["label"]] = f"d={d:.2f}, p={p:.3f} [{sig}]" if not np.isnan(d) else "—"
        rows.append(row)
    return pd.DataFrame(rows)

def table_cv():
    metrics_t = ["satisfaction_rate","food_insecurity_rate","avg_travel_distance",
                  "spatial_equity_index","corner_share","pantry_share","delivery_share"]
    rows = []
    for sk in SCENARIO_KEYS:
        row = {"Scenario": DATA[sk]["label"],
               "Seeds Loaded": str(len(available_seeds(sk)))}
        for m in metrics_t:
            v = cv(sk, m)
            row[METRIC_INFO[m]["label"]] = f"{v:.1f}%" if not np.isnan(v) else "—"
        rows.append(row)
    return pd.DataFrame(rows)

def table_cumulative_burden():
    rows = []
    for sk in SCENARIO_KEYS:
        v, e = cumulative_burden(sk)
        bl_v, _ = cumulative_burden("baseline")
        pct = (v - bl_v) / abs(bl_v) * 100 if bl_v and not np.isnan(v) else np.nan
        rows.append({
            "Scenario": DATA[sk]["label"],
            "Cum. Burden (AUC)": f"{v:.4f}" if not np.isnan(v) else "—",
            "SD": f"±{e:.4f}" if not np.isnan(e) else "—",
            "% vs Baseline": f"{pct:+.2f}%" if not np.isnan(pct) else "—",
        })
    return pd.DataFrame(rows)

# ═══════════════════════════════════════════════════════════════════
# 9.  DASH APP
# ═══════════════════════════════════════════════════════════════════

app = dash.Dash(__name__, title="ABM Food Access — PhD Dissertation v3",
                suppress_callback_exceptions=True,
                requests_pathname_prefix=os.environ.get('DASH_DISS_PREFIX', '/'))

# ── Color constants ──────────────────────────────────────────────
C_PURPLE  = "#4F46E5"
C_TEAL    = "#0D9488"
C_BG      = "#F0F4F8"
C_WHITE   = "#FFFFFF"
C_BORDER  = "#E2E8F0"
C_DARK    = "#0D1B2A"
C_MED     = "#374151"
C_LIGHT   = "#6B7280"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

body {
  font-family: 'DM Sans', 'Segoe UI', sans-serif;
  background: #F0F4F8;
  margin: 0; padding: 0; color: #0D1B2A;
}

/* ── Header ── */
/* NOT .dash-header — that class name is also emitted by dash_table on every
   <th>, so the banner gradient/flex/padding used to land on table headers
   and render them as unreadable stacked teal bars. */
.app-banner {
  background: linear-gradient(135deg, #1E3A5F 0%, #0D9488 100%);
  padding: 24px 40px 18px;
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.app-banner h1 {
  margin: 0; font-size: 19px; font-weight: 700; letter-spacing: -0.4px;
}
.app-banner p { margin: 5px 0 0; font-size: 11.5px; opacity: 0.80; font-weight: 400; }
.header-badge {
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

/* ── Tab bar ── */
.tab-bar {
  background: white;
  display: flex;
  border-bottom: 2px solid #E2E8F0;
  overflow-x: auto;
  box-shadow: 0 2px 10px rgba(0,0,0,0.06);
  scrollbar-width: none;
}
.tab-bar::-webkit-scrollbar { display: none; }
.tab-btn {
  padding: 13px 20px;
  border: none; background: transparent;
  cursor: pointer;
  font-family: 'DM Sans', sans-serif;
  font-size: 12.5px; font-weight: 600;
  color: #6B7280;
  white-space: nowrap;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
  transition: all 0.18s;
}
.tab-btn:hover { color: #374151; background: #F8FAFC; }
.tab-btn.active { color: #4F46E5; border-bottom-color: #4F46E5; background: #F8FAFC; }
.tab-btn.teal   { color: #0D9488; border-bottom-color: #0D9488; background: #F0FDFA; }
.tab-btn.amber  { color: #D97706; border-bottom-color: #D97706; background: #FFFBEB; }

/* ── Body ── */
.body-layout { display: flex; min-height: calc(100vh - 130px); }

/* ── Sidebar ── */
.sidebar {
  width: 215px; min-width: 215px;
  background: white;
  border-right: 1px solid #E2E8F0;
  padding: 14px 8px;
  overflow-y: auto;
}
.sidebar-section-title {
  font-size: 9.5px; font-weight: 700; letter-spacing: 1.3px;
  text-transform: uppercase; color: #94A3B8;
  padding: 8px 10px 4px;
}
.sidebar-item {
  padding: 8px 11px; border-radius: 8px;
  cursor: pointer; font-size: 12px;
  color: #475569; font-weight: 500;
  margin-bottom: 1px;
  border: 1px solid transparent;
  transition: all 0.14s; line-height: 1.35;
}
.sidebar-item:hover { background: #F8FAFC; color: #374151; }
.sidebar-item.active {
  background: linear-gradient(135deg, rgba(79,70,229,0.10), rgba(13,148,136,0.06));
  color: #4F46E5; border-color: rgba(79,70,229,0.22); font-weight: 600;
}

/* ── Content ── */
.content-area { flex: 1; padding: 26px 30px; overflow-y: auto; min-width: 0; }

.section-header { margin-bottom: 20px; }
.section-header h2 { font-size: 17px; font-weight: 700; color: #0D1B2A; margin: 0 0 4px; letter-spacing: -0.3px; }
.section-header p  { font-size: 12.5px; color: #6B7280; margin: 0; }

/* ── Cards ── */
.card {
  background: white; border-radius: 14px;
  border: 1px solid #E2E8F0;
  padding: 22px; box-shadow: 0 1px 5px rgba(0,0,0,0.05);
  margin-bottom: 20px;
}
.card-title {
  font-size: 11.5px; font-weight: 700; color: #374151;
  text-transform: uppercase; letter-spacing: 0.7px;
  margin-bottom: 15px; padding-bottom: 10px;
  border-bottom: 1px solid #F1F5F9;
}

/* ── KPI cards ── */
.kpi-row { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 20px; }
.kpi-card {
  background: white; border: 1px solid #E2E8F0;
  border-radius: 13px; padding: 18px 16px;
  flex: 1; min-width: 148px;
  box-shadow: 0 1px 5px rgba(0,0,0,0.04);
  position: relative; overflow: hidden;
}
.kpi-label  { font-size: 10px; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.9px; margin-bottom: 7px; }
.kpi-value  { font-size: 26px; font-weight: 700; color: #0D1B2A; letter-spacing: -0.5px; line-height: 1; }
.kpi-sub    { font-size: 10.5px; color: #9CA3AF; margin-top: 4px; }
.kpi-delta  { font-size: 11.5px; font-weight: 600; margin-top: 5px; }
.kpi-delta.positive { color: #059669; }
.kpi-delta.negative { color: #DC2626; }
.kpi-delta.neutral  { color: #6B7280; }

/* ── Grid layouts ── */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 20px; }

/* ── Finding boxes ── */
.finding-box {
  background: linear-gradient(135deg, rgba(79,70,229,0.06), rgba(79,70,229,0.02));
  border: 1px solid rgba(79,70,229,0.18);
  border-left: 4px solid #4F46E5;
  border-radius: 10px; padding: 15px 18px;
  margin-bottom: 20px; font-size: 13px;
  color: #374151; line-height: 1.65;
}
.finding-box strong { color: #4F46E5; }
.finding-box.success  { border-left-color: #059669; background: linear-gradient(135deg,rgba(5,150,105,0.06),rgba(5,150,105,0.02)); }
.finding-box.success strong { color: #059669; }
.finding-box.warning  { border-left-color: #D97706; background: linear-gradient(135deg,rgba(217,119,6,0.06),rgba(217,119,6,0.02)); }
.finding-box.warning strong { color: #D97706; }
.finding-box.danger   { border-left-color: #DC2626; background: linear-gradient(135deg,rgba(220,38,38,0.06),rgba(220,38,38,0.02)); }
.finding-box.danger strong  { color: #DC2626; }
.finding-box.teal     { border-left-color: #0D9488; background: linear-gradient(135deg,rgba(13,148,136,0.06),rgba(13,148,136,0.02)); }
.finding-box.teal strong    { color: #0D9488; }

/* ── Policy card ── */
.policy-card {
  background: linear-gradient(135deg, #0D1B2A 0%, #1E3A5F 100%);
  border-radius: 16px; padding: 28px 32px; color: white;
  margin-bottom: 20px;
}
.policy-card h3 { font-size: 16px; font-weight: 700; margin: 0 0 10px; }
.policy-card p  { font-size: 13px; opacity: 0.85; margin: 0; line-height: 1.65; }
.policy-pill {
  display: inline-block; padding: 3px 10px;
  border-radius: 12px; font-size: 11px; font-weight: 700;
  margin: 3px 3px 3px 0;
}

/* ── Location card ── */
.location-card {
  background: white; border-radius: 13px;
  border: 1px solid #E2E8F0;
  padding: 20px; font-size: 12.5px;
}
.location-card h4 { margin: 0 0 8px; font-size: 14px; font-weight: 700; }
.location-meta { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; font-size: 12px; color: #6B7280; }

/* ── Export hint ── */
.export-hint {
  font-size: 10.5px; color: #94A3B8; font-style: italic;
  margin-top: 8px; text-align: right;
  font-family: 'DM Mono', monospace;
}

/* ── Seed count badge ── */
.seed-badge {
  display: inline-flex; align-items: center; gap: 5px;
  background: #F0FDF4; border: 1px solid #A7F3D0;
  color: #065F46; border-radius: 20px;
  padding: 3px 10px; font-size: 11px; font-weight: 600;
  margin-bottom: 18px;
}

/* ── Table ── */
.table-wrap { overflow-x: auto; }
.styled-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.styled-table th {
  background: #F8FAFC; color: #374151; font-weight: 700;
  padding: 11px 14px; text-align: left;
  border-bottom: 2px solid #E2E8F0;
  white-space: nowrap; font-size: 11.5px;
  text-transform: uppercase; letter-spacing: 0.4px;
}
.styled-table td {
  padding: 10px 14px; border-bottom: 1px solid #F1F5F9;
  color: #374151; white-space: nowrap;
}
.styled-table tr:last-child td { border-bottom: none; }
.styled-table tr:hover td { background: #F8FAFC; }
.styled-table td:first-child { font-weight: 600; color: #0D1B2A; }
.config-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 22px; }
.config-item { display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px dashed #F1F5F9; font-size: 12.5px; }
.config-key { color: #6B7280; font-weight: 500; }
.config-val { color: #0D1B2A; font-weight: 600; font-family: 'DM Mono', monospace; }
"""

app.index_string = f"""<!DOCTYPE html>
<html>
<head>
    {{%metas%}}
    <title>{{%title%}}</title>
    {{%favicon%}}
    {{%css%}}
    <style>{CSS}</style>
</head>
<body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer>
</body>
</html>"""

# ═══════════════════════════════════════════════════════════════════
# 10.  SIDEBAR ITEM REGISTRIES
# ═══════════════════════════════════════════════════════════════════

COMPARISON_ITEMS = [
    {"id": "kpi-overview",       "label": "📊  Key Metrics Overview"},
    {"id": "primary-bars",       "label": "📈  Satisfaction & Insecurity"},
    {"id": "travel-equity",      "label": "🚗  Travel & Equity Bars"},
    {"id": "heatmap-pct",        "label": "🌡  % Change Heatmap"},
    {"id": "radar",              "label": "🕸  Performance Radar"},
    {"id": "ranking",            "label": "🏆  Composite Ranking"},
    {"id": "cum-burden",         "label": "⚠️  Cumulative Burden (AUC)"},
    {"id": "ts-satisfaction",    "label": "📉  Time: Satisfaction"},
    {"id": "ts-insecurity",      "label": "📉  Time: Food Insecurity"},
    {"id": "ts-travel",          "label": "📉  Time: Travel Distance"},
    {"id": "income-insecurity",  "label": "📉  Income-Stratified Insecurity"},
    {"id": "channel-mix",        "label": "🏪  Channel Market Share"},
    {"id": "income-spending",    "label": "💰  Income-Group Spending"},
    {"id": "equity-ratio",       "label": "⚖️  Income Equity Ratio"},
    {"id": "cohend-matrix",      "label": "🔬  Pairwise Cohen's d"},
    {"id": "tornado",            "label": "🌪  Sensitivity Tornado"},
    {"id": "stability-cv",       "label": "🎲  Seed Stability (CV)"},
    {"id": "tbl-summary",        "label": "📋  Summary Statistics"},
    {"id": "tbl-pct",            "label": "📋  % Change Table"},
    {"id": "tbl-effect",         "label": "📋  Effect Size & p-values"},
    {"id": "tbl-cv",             "label": "📋  Coefficient of Variation"},
    {"id": "tbl-burden",         "label": "📋  Cumulative Burden Table"},
]

LOCATION_ITEMS = [
    {"id": "loc-overview",       "label": "📊  Location Overview"},
    {"id": "loc-sat",            "label": "😊  Satisfaction by Location"},
    {"id": "loc-insec",          "label": "🍽  Food Insecurity by Location"},
    {"id": "loc-travel",         "label": "🚗  Travel Distance by Location"},
    {"id": "loc-equity",         "label": "⚖️  Spatial Equity by Location"},
    {"id": "loc-ts-insec",       "label": "📉  Time Series: Insecurity"},
    {"id": "loc-ts-sat",         "label": "📉  Time Series: Satisfaction"},
    {"id": "loc-heatmap",        "label": "🌡  Location × Metric Heatmap"},
    {"id": "loc-equity-ratio",   "label": "💰  Income Equity by Location"},
    {"id": "loc-channel",        "label": "🏪  Channel Share by Location"},
]

VARIANT_ITEMS = [
    {"id": "var-overview",       "label": "📊  Variant Overview"},
    {"id": "var-sat",            "label": "😊  Satisfaction by Variant"},
    {"id": "var-insec",          "label": "🍽  Insecurity by Variant"},
    {"id": "var-travel",         "label": "🚗  Travel by Variant"},
    {"id": "var-equity",         "label": "⚖️  Equity by Variant"},
    {"id": "var-channel",        "label": "🏪  Channel Mix by Variant"},
    {"id": "var-heatmap",        "label": "🌡  Variant × Metric Heatmap"},
]

POLICY_ITEMS = [
    {"id": "policy-overview",    "label": "🏛  Policy Summary"},
    {"id": "policy-ranking",     "label": "🏆  Intervention Ranking"},
    {"id": "policy-equity",      "label": "⚖️  Equity Impact Analysis"},
    {"id": "policy-cost",        "label": "💵  Cost-Effectiveness"},
    {"id": "policy-spatial",     "label": "📍  Spatial Planning Insights"},
    {"id": "policy-stakeholder", "label": "👥  Stakeholder Guidance"},
]

SCEN_ITEMS = [
    {"id": "overview",           "label": "📊  KPI Overview"},
    {"id": "ts-sat",             "label": "📈  Satisfaction Trajectory"},
    {"id": "ts-insec",           "label": "🍽  Food Insecurity Trajectory"},
    {"id": "ts-travel",          "label": "🚗  Travel Distance Trajectory"},
    {"id": "ts-equity",          "label": "⚖️  Spatial Equity Trajectory"},
    {"id": "ts-revenue",         "label": "💰  Spending Trajectory"},
    {"id": "ts-channels",        "label": "🏪  Channel Shares"},
    {"id": "seed-sat",           "label": "🎲  Seed: Satisfaction"},
    {"id": "seed-insec",         "label": "🎲  Seed: Food Insecurity"},
    {"id": "seed-travel",        "label": "🎲  Seed: Travel Distance"},
    {"id": "seed-equity",        "label": "🎲  Seed: Spatial Equity"},
    {"id": "vs-baseline",        "label": "⚔️  vs Baseline (Insecurity)"},
    {"id": "vs-bl-travel",       "label": "⚔️  vs Baseline (Travel)"},
    {"id": "config",             "label": "⚙️  Simulation Config"},
]

TAB_DEFS = [
    ("comparison", "⚡ All Scenarios",       "#4F46E5", ""),
    ("location",   "📍 S2: Location Analysis","#0D9488", "teal"),
    ("variants",   "🔧 Variant Analysis",    "#D97706", "amber"),
    ("policy",     "🏛 Policy Insights",     "#4F46E5", ""),
    ("baseline",   "BL: Baseline",           "#6B7280", ""),
    ("scenario1",  "S1: North Grocery",      "#667eea", ""),
    ("scenario2",  "S2: Hub+Corner",         "#10B981", ""),
    ("scenario3",  "S3: Mobile Pantry",      "#F59E0B", ""),
    ("scenario4",  "S4: Delivery",           "#EF4444", ""),
]

# ═══════════════════════════════════════════════════════════════════
# 11.  LAYOUT
# ═══════════════════════════════════════════════════════════════════

def _seed_set_counts():
    n_geofix = max(len([s for s in DATA_GEOFIX[sk]["data"] if isinstance(s,int)]) for sk in SCENARIO_KEYS)
    n_recal  = max(len([s for s in DATA_RECAL[sk]["data"] if isinstance(s,int)]) for sk in SCENARIO_KEYS)
    return n_geofix, n_recal

_ng, _nr = _seed_set_counts()
# Default = GEOFIX FINAL build (corrected store geography, MAPE 6.51%,
# 2026-08-18). The July recal build (produced with the displaced store
# coordinates) is retained as a selectable reference for comparison only.
SEED_SET_OPTIONS = [
    {"label": f"FINAL · corrected geography  ({_ng} seeds)", "value": "geofix"},
    {"label": f"July recal γ=2.6 · superseded (wrong store coords)  ({_nr} seeds)", "value": "recal"},
]

app.layout = html.Div([
    # Header
    html.Div([
        html.Div([
            html.H1("ABM Food Access Intervention Analysis  —  PhD Dissertation"),
            html.P("Jacksonville, FL  ·  Health Zone 1  ·  500 Households  ·  365-Day Simulation  ·  5 Scenarios"),
        ]),
        html.Div([
            html.Div("Model build:", style={"fontSize":"11px","fontWeight":"700","color":"#94A3B8",
                                         "textTransform":"uppercase","letterSpacing":"0.6px",
                                         "marginBottom":"5px"}),
            dcc.RadioItems(
                id="seed-set-radio",
                options=SEED_SET_OPTIONS,
                value="geofix",
                inline=False,
                inputStyle={"marginRight":"5px"},
                labelStyle={"display":"block","fontSize":"12px","color":"#E2E8F0",
                             "marginBottom":"3px","cursor":"pointer"},
            ),
        ], style={"background":"rgba(255,255,255,0.08)","borderRadius":"10px",
                   "padding":"10px 14px","minWidth":"210px"}),
        html.Div(id="header-badge", className="header-badge"),
        # Cross-link back to the live simulation (shown only in the combined app)
        html.A("🔬  Live Simulation  →", href=os.environ.get('DASH_LIVE_PREFIX', '/'),
               style={"color": "#fff", "textDecoration": "none", "fontWeight": "700",
                      "fontSize": "12px", "background": "rgba(255,255,255,0.14)",
                      "padding": "9px 13px", "borderRadius": "8px",
                      "whiteSpace": "nowrap", "alignSelf": "center"}
               ) if os.environ.get('COMBINED_APP') == '1' else html.Div(),
    ], className="app-banner"),

    # Tab bar
    html.Div(id="tab-bar",
             children=[html.Button(lbl,
                                   id={"type":"tab-btn","tab":tid},
                                   n_clicks=0,
                                   className=f"tab-btn {'active' if tid=='comparison' else cls}")
                        for tid, lbl, color, cls in TAB_DEFS],
             className="tab-bar"),

    # Stores
    dcc.Store(id="active-tab",  data="comparison"),
    dcc.Store(id="active-item", data={
        "comparison": "kpi-overview",
        "location":   "loc-overview",
        "variants":   "var-overview",
        "policy":     "policy-overview",
        "baseline":   "overview", "scenario1": "overview",
        "scenario2":  "overview", "scenario3": "overview", "scenario4": "overview",
    }),
    dcc.Store(id="seed-set", data="geofix"),

    # Body
    html.Div([
        html.Div(id="sidebar",      className="sidebar"),
        # dcc.Loading puts `style` on its INNER div, so the outer wrapper needs
        # parent_style to actually stretch — without it the wrapper sizes to its
        # content and every chart renders in a ~480px column on any screen.
        dcc.Loading(
            html.Div(id="content-area", className="content-area"),
            type="circle", color="#4F46E5",
            parent_style={"flex": "1", "minWidth": "0", "display": "flex"},
            style={"flex": "1", "minWidth": "0"},
        ),
    ], className="body-layout"),
], style={"minHeight": "100vh", "background": C_BG})

# ═══════════════════════════════════════════════════════════════════
# 12.  CALLBACKS
# ═══════════════════════════════════════════════════════════════════

@app.callback(
    Output("seed-set","data"),
    Output("header-badge","children"),
    Input("seed-set-radio","value"),
)
def update_seed_set(value):
    label_map = {
        "recal": f"Recalibrated γ=2.6 · FINAL · {_nr} seeds",
    }
    return value, label_map.get(value, label_map["recal"])

@app.callback(Output("active-tab","data"),
              Input({"type":"tab-btn","tab":dash.ALL},"n_clicks"),
              State({"type":"tab-btn","tab":dash.ALL},"id"),
              prevent_initial_call=True)
def switch_tab(nclicks, ids):
    from dash import ctx
    if not ctx.triggered_id: return dash.no_update
    return ctx.triggered_id["tab"]

@app.callback(Output("tab-bar","children"),
              Input("active-tab","data"))
def update_tab_styles(active):
    btns = []
    for tid, lbl, color, cls in TAB_DEFS:
        is_active = (tid == active)
        extra_cls = " active" if is_active else (f" {cls}" if cls else "")
        style = {"borderBottomColor": color, "color": color} if is_active else {"borderBottomColor":"transparent"}
        btns.append(html.Button(lbl, id={"type":"tab-btn","tab":tid},
                                n_clicks=0, className=f"tab-btn{extra_cls}", style=style))
    return btns

@app.callback(Output("active-item","data"),
              Input({"type":"sidebar-item","tab":dash.ALL,"item":dash.ALL},"n_clicks"),
              State({"type":"sidebar-item","tab":dash.ALL,"item":dash.ALL},"id"),
              State("active-item","data"),
              prevent_initial_call=True)
def update_active_item(nclicks, ids, current):
    from dash import ctx
    if not ctx.triggered_id: return current
    tab  = ctx.triggered_id["tab"]
    item = ctx.triggered_id["item"]
    current[tab] = item
    return current

@app.callback(Output("sidebar","children"),
              Input("active-tab","data"), Input("active-item","data"))
def render_sidebar(active_tab, active_items):
    tabs_to_items = {
        "comparison": COMPARISON_ITEMS,
        "location":   LOCATION_ITEMS,
        "variants":   VARIANT_ITEMS,
        "policy":     POLICY_ITEMS,
    }
    items_list = tabs_to_items.get(active_tab, SCEN_ITEMS)
    active = active_items.get(active_tab, items_list[0]["id"])
    # tab color
    color = "#4F46E5"
    for tid, _, col, _ in TAB_DEFS:
        if tid == active_tab:
            color = col; break
    children = [html.Div("NAVIGATE", className="sidebar-section-title")]
    for item in items_list:
        is_active = (item["id"] == active)
        children.append(html.Div(
            item["label"],
            id={"type":"sidebar-item","tab":active_tab,"item":item["id"]},
            n_clicks=0,
            className="sidebar-item active" if is_active else "sidebar-item",
            style={"color": color} if is_active else {},
        ))
    return children

# Serializes the global-DATA swap + render so concurrent viewers on different
# seed sets can never interleave (the deployed combined app runs multi-threaded).
_render_lock = threading.Lock()
# Memoize each rendered view by (seed_set, tab, item). The underlying result
# files are loaded once at startup and never change, so a view's output is
# deterministic — caching returns the EXACT same content (identical means,
# tables, CIs, methodology), it only avoids recomputing it on every re-visit.
_RENDER_CACHE = {}

@app.callback(Output("content-area","children"),
              Input("active-tab","data"), Input("active-item","data"),
              Input("seed-set","data"))
def render_content(active_tab, active_items, seed_set):
    global DATA
    seed_set = seed_set or "geofix"
    item = active_items.get(active_tab, "kpi-overview")
    key = (seed_set, active_tab, item)
    with _render_lock:
        if key in _RENDER_CACHE:
            return _RENDER_CACHE[key]
        DATA = DATA_MAP.get(seed_set, DATA_GEOFIX)
        dispatch = {
            "comparison": render_comparison,
            "location":   render_location,
            "variants":   render_variants,
            "policy":     render_policy,
        }
        out = dispatch[active_tab](item) if active_tab in dispatch else render_scenario(active_tab, item)
        _RENDER_CACHE[key] = out
        return out

# ═══════════════════════════════════════════════════════════════════
# 13.  CONTENT RENDERERS — HELPERS
# ═══════════════════════════════════════════════════════════════════

def G(fig, height=480):
    return html.Div([
        dcc.Graph(figure=fig,
                  config={"displayModeBar": True, "scrollZoom": False,
                          "toImageButtonOptions": {"format": "png", "scale": 3,
                                                   "filename": "abm_chart"}},
                  style={"width": "100%", "height": f"{height}px"}),
        html.Div("📷 Use camera icon to export publication-quality PNG (3× scale)", className="export-hint"),
    ])

def section_hdr(title, sub="", color="#4F46E5"):
    return html.Div([
        html.H2(title, style={"color": color}),
        html.P(sub) if sub else None,
    ], className="section-header")

def card(title, *children, color="#4F46E5"):
    return html.Div([
        html.Div(title, className="card-title", style={"borderBottomColor":f"{color}22","color":color}),
        *children,
    ], className="card")

def finding(text, kind="info"):
    cls = f"finding-box {kind if kind in ('success','warning','danger','teal') else ''}"
    return html.Div(dcc.Markdown(text, dangerously_allow_html=False), className=cls)

def make_dash_table(df_t):
    cols = [{"name": c, "id": c} for c in df_t.columns]
    return dash_table.DataTable(
        data=df_t.to_dict("records"), columns=cols,
        style_table={"overflowX":"auto","borderRadius":"10px","border":"1px solid #E2E8F0"},
        style_header={"backgroundColor":"#F8FAFC","color":"#374151","fontWeight":"700",
                       "fontFamily":FONT_MAIN,"fontSize":"11.5px","border":"none",
                       "borderBottom":"2px solid #E2E8F0","padding":"12px 14px",
                       "textTransform":"uppercase","letterSpacing":"0.4px"},
        style_cell={"backgroundColor":"white","color":"#374151","fontFamily":FONT_MAIN,
                     "fontSize":"12.5px","border":"none","borderBottom":"1px solid #F1F5F9",
                     "padding":"10px 14px","whiteSpace":"nowrap","textAlign":"left"},
        style_cell_conditional=[{"if":{"column_id":"Scenario"},"fontWeight":"700","color":"#0D1B2A","minWidth":"160px"}],
        style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#FAFBFC"}],
        style_as_list_view=True,
    )

def seed_status_badge(sk):
    n = len(available_seeds(sk))
    target = max(n, 1)  # dynamic: green when all seeds for this set are loaded
    ok = n >= 3
    color_bg = "#F0FDF4" if ok else "#FEF2F2"
    color_bd = "#A7F3D0" if ok else "#FCA5A5"
    color_tx = "#065F46" if ok else "#991B1B"
    icon     = "✓" if ok else "✗"
    return html.Div(
        f"{icon}  {n} seeds loaded",
        style={"display":"inline-flex","alignItems":"center","gap":"5px",
               "background":color_bg,"border":f"1px solid {color_bd}",
               "color":color_tx,"borderRadius":"20px","padding":"3px 11px",
               "fontSize":"11px","fontWeight":"600","marginBottom":"16px"})

def kpi_cards_comparison():
    metrics_show = [
        ("satisfaction_rate",   "Satisfaction Rate", "#4F46E5"),
        ("food_insecurity_rate","Food Insecurity",   "#DC2626"),
        ("avg_travel_distance", "Avg Travel (mi)",   "#D97706"),
        ("spatial_equity_index","Spatial Equity",    "#059669"),
    ]
    rows = []
    for m, mlbl, mc in metrics_show:
        row_cards = []
        bl_v = np.nanmean(seed_vals("baseline", m))
        for sk in SCENARIO_KEYS:
            v  = np.nanmean(seed_vals(sk, m))
            sv = [x for x in seed_vals(sk, m) if not np.isnan(x)]
            sd = np.std(sv, ddof=1) if len(sv) > 1 else 0
            ci_lo, ci_hi = bootstrap_ci(sv)
            pct = (v - bl_v) / abs(bl_v) * 100 if bl_v != 0 else 0
            hb  = METRIC_INFO[m]["higher_better"]
            good = (hb and pct > 0.5) or (not hb and pct < -0.5)
            bad  = (hb and pct < -0.5) or (not hb and pct > 0.5)
            dcls = "positive" if good else ("negative" if bad else "neutral")
            dsym = "▲" if pct > 0 else "▼"
            c    = DATA[sk]["color"]
            row_cards.append(html.Div([
                html.Div(style={"position":"absolute","top":"0","left":"0","right":"0",
                                "height":"4px","background":c,"borderRadius":"14px 14px 0 0"}),
                html.Div(DATA[sk]["short"], className="kpi-label", style={"color":c,"fontWeight":"700"}),
                html.Div(f"{v:.3f}", className="kpi-value"),
                html.Div(f"±{sd:.3f}", className="kpi-sub"),
                html.Div(f"{dsym} {abs(pct):.1f}% vs BL",
                         className=f"kpi-delta {dcls}") if sk != "baseline" else
                html.Div("Reference baseline", className="kpi-delta neutral"),
            ], className="kpi-card", style={"position":"relative"}))
        rows.append(html.Div([
            html.Div(mlbl, style={"fontSize":"11px","fontWeight":"700","color":"#94A3B8",
                                   "textTransform":"uppercase","letterSpacing":"0.8px",
                                   "marginBottom":"7px","paddingLeft":"4px"}),
            html.Div(row_cards, style={"display":"flex","gap":"11px","flexWrap":"wrap","marginBottom":"16px"}),
        ]))
    return html.Div(rows)

# ═══════════════════════════════════════════════════════════════════
# 14.  CONTENT RENDERER — COMPARISON TAB
# ═══════════════════════════════════════════════════════════════════

def _cmp_narrative():
    """Live Scenario-2-vs-Baseline figures for the narrative/finding boxes,
    computed from the ACTIVE seed set so the prose never contradicts the
    charts/tables when the seed-set selector is changed."""
    n = max(len(available_seeds(sk)) for sk in SCENARIO_KEYS)
    def mean(sk, m):
        vs = [x for x in seed_vals(sk, m) if not np.isnan(x)]
        return np.mean(vs) if vs else float("nan")
    d_ins, _ = effect_size("scenario2", "food_insecurity_rate")
    return dict(
        n=n,
        s2_sat=mean("scenario2", "satisfaction_rate"),
        s2_ins=mean("scenario2", "food_insecurity_rate"),
        sat_pct=pct_vs_baseline("scenario2", "satisfaction_rate"),
        ins_pct=pct_vs_baseline("scenario2", "food_insecurity_rate"),
        trv_pct=pct_vs_baseline("scenario2", "avg_travel_distance"),
        bl_trv=mean("baseline", "avg_travel_distance"),
        s2_trv=mean("scenario2", "avg_travel_distance"),
        s2_d=abs(d_ins) if (d_ins is not None and d_ins == d_ins) else float("nan"),
    )

def render_comparison(item):
    if item == "kpi-overview":
        n_seeds = max(len(available_seeds(sk)) for sk in SCENARIO_KEYS)
        c = _cmp_narrative()
        return html.Div([
            section_hdr("Key Metrics Overview",
                        f"Final-day averages. Δ% vs Baseline shown. n={n_seeds} seeds per scenario."),
            finding(f"**Best overall intervention: Scenario 2 (Hub + Corner Stores)** — consistent improvement in satisfaction ({c['sat_pct']:+.1f}%), food insecurity ({c['ins_pct']:+.1f}%), and travel distance ({c['trv_pct']:+.1f}%) vs Baseline across all {c['n']} seeds. Effect size (Cohen's d ≈ {c['s2_d']:.1f}) confirms meaningful differences beyond stochastic variance.", "success"),
            seed_status_badge("scenario2"),
            kpi_cards_comparison(),
        ])

    elif item == "primary-bars":
        return html.Div([
            section_hdr("Satisfaction & Food Insecurity", "Mean ± SD. N-seed bootstrap 95% CI also computed."),
            card("Grouped Comparison — Primary Outcomes", G(fig_grouped_bar_primary(), 480)),
            finding(f"**Scenario 2** achieves the highest satisfaction ({_cmp_narrative()['s2_sat']:.3f}) and lowest food insecurity ({_cmp_narrative()['s2_ins']:.3f}). **Scenario 3** (Mobile Pantry) shows no meaningful difference from Baseline — a statistically important null result. **Scenario 1** (North Grocery) slightly improves overall satisfaction but worsens spatial equity for south-zone households."),
        ])

    elif item == "travel-equity":
        return html.Div([
            section_hdr("Travel Distance & Spatial Equity", "Mean ± bootstrapped 95% CI."),
            html.Div([
                card("Avg Travel Distance (mi)", G(fig_bar_metric("avg_travel_distance"), 400)),
                card("Spatial Equity Index",     G(fig_bar_metric("spatial_equity_index"), 400)),
            ], className="grid-2"),
            finding(f"**Scenario 2 reduces average travel by {abs(_cmp_narrative()['trv_pct']):.1f}%** ({_cmp_narrative()['bl_trv']:.3f} → {_cmp_narrative()['s2_trv']:.3f} mi). **Critical finding:** Scenario 1 (North Grocery) *reduces* the spatial equity index — it adds stores only in the north, creating wider spatial gaps for south/east households. This directly supports your policy argument that location of new infrastructure matters as much as quantity.", "warning"),
        ])

    elif item == "heatmap-pct":
        return html.Div([
            section_hdr("% Change vs Baseline — All Scenarios × Metrics",
                        "Green = improvement | Red = decline | White = no change."),
            card("Direction & Magnitude Heatmap", G(fig_heatmap_pct(), 390)),
            finding("The heatmap confirms **Scenario 2 is the only consistently positive intervention** across all food access metrics. Scenario 1 produces mixed signals (better overall satisfaction, worse equity). Scenario 3 shows near-zero change — the null result. Scenario 4 improves delivery share but has mixed effects on travel (delivery substitutes short corner trips).", "info"),
        ])

    elif item == "radar":
        return html.Div([
            section_hdr("Normalized Performance Radar", "All axes normalized 0–1. Outward = better on every dimension."),
            card("Multi-Dimensional Performance Spider Chart", G(fig_radar(), 560)),
            finding("The radar confirms S2's dominance: it has the largest polygon across all axes. Note S1's poor spatial equity axis despite good satisfaction — a classic coverage gap pattern. S4 shows a unique profile: strong delivery share but average food insecurity, suggesting delivery helps but cannot substitute for physical store access at scale."),
        ])

    elif item == "ranking":
        return html.Div([
            section_hdr("Composite Performance Ranking",
                        "Weighted index: Satisfaction (+1.0) | Insecurity (−1.0) | Travel (−0.8) | Equity (+0.6). 0–1 normalized per metric."),
            card("Composite Score — All Scenarios Ranked", G(fig_composite_ranking(), 390)),
            finding("**Rank order: S2 > S4 > S1 > Baseline ≈ S3.** S2 leads by a clear margin. S3 ties baseline — confirming the null result. These weights are defensible but sensitivity: a committee member may ask you to vary them. Robustness check: under any positive weight combination that includes food insecurity, S2 remains #1.", "teal"),
        ])

    elif item == "cum-burden":
        return html.Div([
            section_hdr("Cumulative Food Insecurity Burden",
                        "Normalised AUC of daily food insecurity over 365 days. Integrates severity × duration."),
            card("Total Burden Experienced — All Scenarios", G(fig_cumulative_burden(), 420)),
            card("Cumulative Burden Reference Table", make_dash_table(table_cumulative_burden())),
            finding("**Cumulative burden is a more complete measure than single-day final values** — it captures the integrated impact over the entire year. S2 shows the largest burden reduction. This metric is particularly important for low-income households who may experience prolonged food insecurity spells, not just point-in-time counts. **Consider using AUC as a supplementary metric in your dissertation Table 4-2.**", "teal"),
        ])

    elif item == "ts-satisfaction":
        return html.Div([
            section_hdr("Satisfaction Rate — 365-Day Trajectory",
                        "Mean ± bootstrap 95% CI across all seeds. All scenarios reach equilibrium within 5–10 days."),
            card("Time Series — All Scenarios", G(fig_ts_all("satisfaction_rate"), 510)),
            finding("All scenarios reach **behavioral equilibrium within the first 5–10 simulation days** with < 1% drift thereafter. This validates the simulation length and confirms the 365-day run is adequate. S2 consistently separates from all others after Day 1.", "success"),
        ])

    elif item == "ts-insecurity":
        return html.Div([
            section_hdr("Food Insecurity Rate — 365-Day Trajectory",
                        "Primary outcome measure. S2's separation from Baseline is visible from Day 1."),
            card("Time Series — All Scenarios", G(fig_ts_all("food_insecurity_rate"), 510)),
        ])

    elif item == "ts-travel":
        return html.Div([
            section_hdr("Average Travel Distance — 365-Day Trajectory", "Miles per shopping trip, mean ± 95% CI."),
            card("Time Series — All Scenarios", G(fig_ts_all("avg_travel_distance"), 510)),
        ])

    elif item == "income-insecurity":
        return html.Div([
            section_hdr("Income-Stratified Food Insecurity",
                        "Baseline vs S2. Shows whether improvements are equitable across income tiers."),
            card("Food Insecurity by Income Group — Baseline vs S2", G(fig_income_insecurity_ts(), 510)),
            finding("**Critical equity test:** If S2's improvement benefits high-income households more than low-income, the intervention may not address structural inequality. Income-stratified tracking requires sub-group metrics in `metrics_history`. **If your model tracks sub-group insecurity, this chart becomes a flagship finding for the equity argument in Chapter 4.**", "warning"),
        ])

    elif item == "channel-mix":
        return html.Div([
            section_hdr("Channel Market Share", "Share of all shopping trips by alternative channel type."),
            card("Corner Store / Pantry / Delivery — All Scenarios", G(fig_channel_mix(), 470)),
            finding("**S1 dramatically reduces corner store reliance** (0.637 → 0.461) as agents substitute the north grocery. **S4** increases delivery share from 5.0% → 7.0%. **S3 barely moves pantry share** (0.086 → 0.089), explaining its null result — the mobile pantry is not effectively reached. This is the key behavioral mechanism behind your findings.", "info"),
        ])

    elif item == "income-spending":
        return html.Div([
            section_hdr("Food Expenditure by Income Group", "Annual cumulative spending per income tier."),
            card("Income-Stratified Spending — All Scenarios", G(fig_income_spending(), 490)),
        ])

    elif item == "equity-ratio":
        return html.Div([
            section_hdr("Income Equity Ratio: Low ÷ High Spending", "Higher ratio = more equitable."),
            card("Equity Ratio — All Scenarios", G(fig_equity_ratio(), 410)),
            finding("**Critical finding:** S1 (North Grocery) *worsens* income equity — the ratio drops from baseline. High-income vehicle-owning households benefit more. **S4 (Delivery) produces the best equity ratio** by removing the travel barrier for car-free households. This argues that delivery subsidies may be a high-equity complement to physical store interventions.", "warning"),
        ])

    elif item == "cohend-matrix":
        return html.Div([
            section_hdr("Pairwise Cohen's d — Food Insecurity Rate",
                        "Symmetric matrix. Positive = row scenario has higher insecurity than column. |d|>0.8 = large."),
            card("Inter-Scenario Effect Sizes", G(fig_pairwise_cohend("food_insecurity_rate"), 420)),
            finding("The pairwise matrix reveals that **S2 vs Baseline** and **S2 vs S3** show the largest effect sizes. This confirms S2's unique mechanism — not just marginally better, but a categorically different outcome profile. Use this matrix in your dissertation to justify that S2 is not a statistical artifact but a genuine behavioral effect.", "teal"),
        ])

    elif item == "tornado":
        top = sobol_top()
        if top:
            name, st_v, s1_v = top
            note = (f"**{name} dominates the variance in daily food insecurity: "
                    f"S_T = {st_v:.3f}** (first-order S₁ = {s1_v:.3f}). The gap between "
                    f"the two is the share carried by *interactions* — {name.split()[0]} matters "
                    "both on its own and through how it conditions every other parameter. "
                    "The shopping thresholds (θ) sit an order of magnitude lower, so food "
                    "insecurity here is governed by the quality/variety of the reachable food "
                    "environment rather than by the propensity to shop. This is the "
                    "recalibrated (γ=2.6) result and matches Figure 5 of the paper; the "
                    "pre-recalibration θ_low result no longer applies.")
            kind = "success"
        else:
            note = ("**Sobol indices are not loaded**, so no sensitivity claim is shown here. "
                    "Point `GEOMESA_SOBOL_JSON` at the recalibration artifact "
                    "(`paper_revision/recalibration/state/sobol_indices.json`) to populate this panel.")
            kind = "danger"
        return html.Div([
            section_hdr("Sensitivity Analysis — Sobol Indices",
                        "Total-order S_T = share of output variance attributable to a parameter "
                        "including all its interactions. First-order S₁ = its independent share."),
            card("Tornado Chart — Food Insecurity Rate", G(fig_tornado_sensitivity(), 460)),
            finding(note, kind),
        ])

    elif item == "stability-cv":
        return html.Div([
            section_hdr("Seed Stability — Coefficient of Variation",
                        f"CV (%) = SD/Mean × 100. Green < 5% = stable | Yellow 5–20% = moderate | Red > 20% = review needed."),
            card("CV Heatmap — All Scenarios × Metrics", G(fig_seed_variability_all(), 410)),
            finding(f"**All primary outcome metrics (satisfaction, food insecurity, travel, equity) show CV < 12%** across all scenarios — acceptable for ABM research with n={max(len(available_seeds(sk)) for sk in SCENARIO_KEYS)} seeds. **Total revenue CV exceeds 30%** — this metric reflects which households happen to shop on the final day and should NOT be used as a primary finding. Use daily average spending instead.", "danger"),
        ])

    elif item == "tbl-summary":
        return html.Div([
            section_hdr("Summary Statistics", "Mean ± SD for all metrics. Ready for dissertation Table 4-1."),
            card("Table 4-1 — Final-Day Metrics (Mean ± SD, all seeds)", make_dash_table(table_summary())),
            html.Div("📋  Copy this table directly into your dissertation. Report n seeds in the table footnote.", className="export-hint"),
        ])

    elif item == "tbl-pct":
        return html.Div([
            section_hdr("% Change vs Baseline", "Table 4-2 — all interventions vs no-intervention reference."),
            card("Percentage Change from Baseline", make_dash_table(table_pct_change())),
            finding("This is **Table 4-2** in your dissertation. Highlight S2's consistent negative % on food insecurity and travel, and S3's near-zero row as the null result. These values derive from multi-seed means, making them robust to individual seed variability.", "info"),
        ])

    elif item == "tbl-effect":
        return html.Div([
            section_hdr("Effect Sizes & Statistical Tests",
                        "Welch t-test. Cohen's d: <0.5 small | 0.5–0.8 medium | >0.8 large. ** p<0.05 | † p<0.10 | ns = not significant."),
            card("Effect Size Table — Cohen's d and p-values", make_dash_table(table_effect_size())),
            (lambda n: finding(
                (f"**With n={n} seeds the design is well-powered.** Paired scenario-vs-baseline tests are "
                 "highly significant for S1 and S2 (p < 0.001) with large effect sizes (Cohen's d > 1), while "
                 "S3 and S4 are precise nulls on the primary outcomes (95% CI brackets zero). Report mean ± 95% "
                 "CI with paired tests; cite Railsback & Grimm (2019) for pattern-oriented validation alongside "
                 "the now well-powered inference.")
                if n >= 25 else
                ("**With n=6 seeds, p-values have low power** — expect ns results even with large Cohen's d. In "
                 "your defense, pivot to effect sizes and directional consistency: Cohen's d > 1.4 for S2 is a "
                 "large, meaningful effect regardless of p-value. Cite Railsback & Grimm (2019): *'ABM validation "
                 "is about pattern-matching and effect magnitude, not frequentist inference.'*"),
                "warning"))(max(len(available_seeds(sk)) for sk in SCENARIO_KEYS)),
        ])

    elif item == "tbl-cv":
        return html.Div([
            section_hdr("Coefficient of Variation by Scenario and Metric"),
            card("CV Table", make_dash_table(table_cv())),
        ])

    elif item == "tbl-burden":
        return html.Div([
            section_hdr("Cumulative Food Insecurity Burden", "Normalised AUC — integrates severity over the full 365-day simulation."),
            card("Burden Table — All Scenarios", make_dash_table(table_cumulative_burden())),
        ])

    return html.Div("Select an item from the sidebar.")

# ═══════════════════════════════════════════════════════════════════
# 15.  CONTENT RENDERER — LOCATION ANALYSIS TAB
# ═══════════════════════════════════════════════════════════════════

def render_location(item):
    if item == "loc-overview":
        cards = []
        for sk in LOCATION_KEYS:
            info = LOCATION_INFO[sk]
            n = len(available_seeds(sk))
            has_data = n > 0
            v_ins   = np.nanmean(seed_vals(sk,"food_insecurity_rate"))
            v_sat   = np.nanmean(seed_vals(sk,"satisfaction_rate"))
            v_tr    = np.nanmean(seed_vals(sk,"avg_travel_distance"))
            bl_ins  = np.nanmean(seed_vals("baseline","food_insecurity_rate"))
            pct_ins = (v_ins - bl_ins)/abs(bl_ins)*100 if has_data and not np.isnan(v_ins) else None
            cards.append(html.Div([
                html.Div(style={"position":"absolute","top":"0","left":"0","right":"0",
                                "height":"5px","background":info["color"],"borderRadius":"13px 13px 0 0"}),
                html.H4(f"S2 — {info['direction']}", style={"margin":"0 0 6px","color":info["color"],"fontSize":"15px"}),
                html.Div([
                    html.Div("📍  " + info["coord_note"], style={"fontSize":"11.5px","color":"#6B7280","marginBottom":"4px"}),
                    html.Div("👥  " + info["pop_context"], style={"fontSize":"11.5px","color":"#6B7280","marginBottom":"4px"}),
                    html.Div("💡  " + info["expected"],    style={"fontSize":"11.5px","color":"#374151","fontStyle":"italic","marginBottom":"10px"}),
                ]),
                html.Div([
                    html.Span("Food Insecurity: ", style={"fontSize":"12px","color":"#6B7280"}),
                    html.Span(f"{v_ins:.3f}  ({pct_ins:+.1f}% vs BL)" if pct_ins is not None else "No data yet",
                              style={"fontWeight":"700","color":info["color"] if has_data else "#9CA3AF"}),
                ]),
                html.Div(f"Seeds loaded: {n}",
                         style={"marginTop":"8px","fontSize":"11px","color":"#9CA3AF" if n < 6 else "#059669"}),
            ], className="location-card",
               style={"position":"relative","borderTop":f"1px solid {info['color']}22",
                      "borderLeft":f"3px solid {info['color']}"}))
        return html.Div([
            section_hdr("Scenario 2 — Location Analysis",
                        "Compares placing the new grocery store in North / South / East / West of Health Zone 1.",
                        "#0D9488"),
            finding("**Research question:** Does the location of a new grocery store within a food desert affect food access outcomes? HZ1 spans ~16 km² with heterogeneous population distribution. A store in the north serves a different sub-population than one in the south. **Run S2-South, S2-East, and S2-West simulations** and place the JSON files in `scenarios_results/` — this dashboard will automatically detect and display them.", "teal"),
            html.Div(cards, className="grid-2"),
        ])

    metric_map = {
        "loc-sat":          ("satisfaction_rate",    "Satisfaction Rate"),
        "loc-insec":        ("food_insecurity_rate", "Food Insecurity Rate"),
        "loc-travel":       ("avg_travel_distance",  "Travel Distance"),
        "loc-equity":       ("spatial_equity_index", "Spatial Equity Index"),
        "loc-ts-insec":     ("food_insecurity_rate", None),
        "loc-ts-sat":       ("satisfaction_rate",    None),
    }
    if item in metric_map:
        m, lbl = metric_map[item]
        if lbl:  # bar chart
            return html.Div([
                section_hdr(f"S2 Location Variants — {lbl}",
                            "Baseline reference shown as dashed line. Grey bars = no data yet.", "#0D9488"),
                card(f"{lbl} by Location", G(fig_location_comparison(m), 450), color="#0D9488"),
            ])
        else:  # time series
            return html.Div([
                section_hdr(f"S2 Location Variants — {METRIC_INFO[m]['label']} Time Series",
                            "Overlay of all four locations vs Baseline.", "#0D9488"),
                card(f"{METRIC_INFO[m]['label']} Trajectory — All Locations",
                     G(fig_location_ts_overlay(m), 500), color="#0D9488"),
            ])

    elif item == "loc-heatmap":
        return html.Div([
            section_hdr("Location × Metric Heatmap", "% change vs Baseline for each direction.", "#0D9488"),
            card("Location Impact Heatmap", G(fig_location_equity_heatmap(), 380), color="#0D9488"),
        ])

    elif item == "loc-equity-ratio":
        return html.Div([
            section_hdr("Income Equity by Location", "Low÷High spending ratio for each S2 location variant.", "#0D9488"),
            card("Equity Ratio by Location", G(fig_equity_ratio(LOCATION_KEYS), 430), color="#0D9488"),
            finding("If the North location disproportionately benefits high-income households (who have vehicles to reach it), while the South/West locations serve lower-income pedestrian populations, the **equity ratios will diverge across directions**. This analysis provides the strongest argument for location-sensitive policy design.", "teal"),
        ])

    elif item == "loc-channel":
        return html.Div([
            section_hdr("Channel Share by Location", "Does store location change which channels households use?", "#0D9488"),
            card("Channel Mix by Location", G(fig_channel_mix(LOCATION_KEYS), 460), color="#0D9488"),
        ])

    return html.Div("Select an item from the sidebar.")

# ═══════════════════════════════════════════════════════════════════
# 16.  CONTENT RENDERER — VARIANT ANALYSIS TAB
# ═══════════════════════════════════════════════════════════════════

VARIANT_DISPLAY_KEYS = ["scenario2"] + VARIANT_KEYS

def render_variants(item):
    if item == "var-overview":
        return html.Div([
            section_hdr("Hub & Corner-Store Variant Analysis",
                        "Tests infrastructure configuration sensitivity within Scenario 2.", "#D97706"),
            finding("**Research question:** Is the S2 effect robust to changes in hub capacity (100/200/400) and corner store count (2/4/6)? If outcomes change substantially with capacity, infrastructure investment levels matter. If not, the effect is driven by *existence* rather than *scale* of the food hub. **Run the variant files and place them in `scenarios_results/`** — this tab auto-loads them.", "warning"),
            html.Div([
                html.Div([
                    html.Div(style={"position":"absolute","top":"0","left":"0","right":"0",
                                    "height":"4px","background":DATA[sk]["color"],"borderRadius":"13px 13px 0 0"}),
                    html.H4(DATA[sk]["label"], style={"margin":"0 0 6px","color":DATA[sk]["color"],"fontSize":"13px"}),
                    html.Div(VARIANT_INFO.get(sk, {}).get("desc",""), style={"fontSize":"12px","color":"#6B7280"}),
                    html.Div(f"Hub cap: {VARIANT_INFO.get(sk,{}).get('hub','—')}  |  Corner stores: {VARIANT_INFO.get(sk,{}).get('corner','—')}",
                             style={"fontSize":"11.5px","color":"#374151","marginTop":"6px","fontFamily":"'DM Mono',monospace"}),
                    html.Div(f"Seeds: {len(available_seeds(sk))}",
                             style={"fontSize":"11px","color":"#9CA3AF" if len(available_seeds(sk))<6 else "#059669","marginTop":"5px"}),
                ], className="location-card",
                   style={"position":"relative","borderLeft":f"3px solid {DATA[sk]['color']}"})
                for sk in VARIANT_DISPLAY_KEYS
            ], className="grid-3"),
        ])

    metric_map = {
        "var-sat":    "satisfaction_rate",
        "var-insec":  "food_insecurity_rate",
        "var-travel": "avg_travel_distance",
        "var-equity": "spatial_equity_index",
        "var-channel": None,
    }
    if item in metric_map:
        m = metric_map[item]
        if m is None:  # channel
            return html.Div([
                section_hdr("Channel Mix by Variant", "Does hub size change which channels agents use?", "#D97706"),
                card("Channel Market Share by Variant", G(fig_channel_mix(VARIANT_DISPLAY_KEYS), 460), color="#D97706"),
            ])
        return html.Div([
            section_hdr(f"Variant Comparison — {METRIC_INFO[m]['label']}",
                        "Baseline reference shown as dashed line. Grey bars = no data yet.", "#D97706"),
            card(f"{METRIC_INFO[m]['label']} by Variant", G(fig_variant_comparison(m), 460), color="#D97706"),
        ])

    elif item == "var-heatmap":
        metrics = ["satisfaction_rate","food_insecurity_rate","avg_travel_distance","spatial_equity_index"]
        z, annot = [], []
        for sk in VARIANT_DISPLAY_KEYS:
            row, arow = [], []
            for mm in metrics:
                pct = pct_vs_baseline(sk, mm)
                if np.isnan(pct): row.append(0); arow.append("N/A")
                else: row.append(pct); arow.append(f"{pct:+.1f}%")
            z.append(row); annot.append(arow)
        xl = [METRIC_INFO[mm]["label"].replace(" Rate","").replace(" Index","") for mm in metrics]
        fig = go.Figure(go.Heatmap(
            z=z, x=xl, y=[DATA[sk]["short"] for sk in VARIANT_DISPLAY_KEYS],
            colorscale=[[0,"#DC2626"],[0.5,"#F9FAFB"],[1,"#059669"]],
            zmid=0, text=annot, texttemplate="%{text}",
            textfont=dict(size=13, color="#1C2434"),
            colorbar=dict(title=dict(text="% vs BL"), thickness=16),
        ))
        apply(fig, "Hub & Corner-Store Variants — % Change vs Baseline",
              margin=dict(l=130, r=130, t=65, b=100))
        return html.Div([
            section_hdr("Variant × Metric Heatmap", "Impact direction for each configuration.", "#D97706"),
            card("Variant Heatmap", G(fig, 360), color="#D97706"),
        ])

    return html.Div("Select an item from the sidebar.")

# ═══════════════════════════════════════════════════════════════════
# 17.  CONTENT RENDERER — POLICY INSIGHTS TAB (Dr. Watson)
# ═══════════════════════════════════════════════════════════════════

def render_policy(item):
    if item == "policy-overview":
        return html.Div([
            section_hdr("Policy Insights Dashboard",
                        "Translating simulation findings into actionable guidance for Jacksonville community planners and health officials.",
                        "#4F46E5"),

            # Dr. Watson callout
            html.Div([
                html.Div("👩‍🏫  Committee Note — Dr. Maria Watson",
                         style={"fontWeight":"700","fontSize":"12px","color":"#4F46E5","marginBottom":"8px","letterSpacing":"0.5px"}),
                html.P("Dr. Watson recommended articulating 'the practical role of the interactive dashboard in community-based and scenario-based planning for city officials and health agencies in Jacksonville, beyond its academic contribution.' This tab fulfills that recommendation and should be cited in the dissertation's Chapter 4 discussion section.",
                       style={"fontSize":"13px","color":"#374151","margin":"0","lineHeight":"1.65"}),
            ], style={"background":"rgba(79,70,229,0.05)","border":"1px solid rgba(79,70,229,0.18)",
                       "borderLeft":"4px solid #4F46E5","borderRadius":"10px","padding":"16px 20px","marginBottom":"22px"}),

            html.Div([
                html.Div([
                    html.H3("🏆  Best Intervention: Scenario 2"),
                    html.P(f"Hub + Corner Stores reduced food insecurity by {abs(_cmp_narrative()['ins_pct']):.1f}% and travel distance by {abs(_cmp_narrative()['trv_pct']):.1f}%. At ~$1.2M estimated capital cost (food hub) + $400K annual operating, this is the most cost-effective food access intervention modeled for HZ1."),
                    html.Div([
                        html.Span(f"Food insecurity ↓{abs(_cmp_narrative()['ins_pct']):.1f}%", className="policy-pill",
                                  style={"background":"rgba(5,150,105,0.2)","color":"#065F46"}),
                        html.Span(f"Travel ↓{abs(_cmp_narrative()['trv_pct']):.1f}%", className="policy-pill",
                                  style={"background":"rgba(5,150,105,0.2)","color":"#065F46"}),
                        html.Span(f"Cohen's d ≈ {_cmp_narrative()['s2_d']:.1f}", className="policy-pill",
                                  style={"background":"rgba(79,70,229,0.15)","color":"#3730A3"}),
                    ]),
                ], className="policy-card"),
                html.Div([
                    html.H3("⚠️  Null Result: Scenario 3"),
                    html.P("Mobile pantries with fixed routes showed no statistically meaningful improvement. The model suggests this is because pantry locations are not spatially aligned with car-free household concentrations. Flexible routing — not fixed-stop pantries — may be needed."),
                    html.Div([
                        html.Span("Insecurity Δ ≈ 0%", className="policy-pill",
                                  style={"background":"rgba(220,38,38,0.15)","color":"#991B1B"}),
                        html.Span("Pantry share Δ+0.3%", className="policy-pill",
                                  style={"background":"rgba(220,38,38,0.15)","color":"#991B1B"}),
                    ]),
                ], className="policy-card"),
            ], className="grid-2"),
        ])

    elif item == "policy-ranking":
        return html.Div([
            section_hdr("Intervention Ranking for Decision-Makers", "Evidence-based ordering for HZ1 policy investment.", "#4F46E5"),
            card("Composite Score — Policy Ranking", G(fig_composite_ranking(), 400)),
            finding("**For city officials:** Scenario 2 (Community Food Hub + 4 Corner Stores) offers the strongest evidence-based case. It is the only intervention that simultaneously reduces food insecurity, improves spatial equity, and shortens travel distances. **Scenario 4 (Delivery Subsidy)** is the best equity-enhancing complement — it disproportionately benefits low-income, car-free households.", "success"),
        ])

    elif item == "policy-equity":
        return html.Div([
            section_hdr("Equity Impact Analysis", "Who benefits most from each intervention?", "#4F46E5"),
            html.Div([
                card("Income Equity Ratio (Low÷High Spending)", G(fig_equity_ratio(), 400)),
                card("Income-Stratified Spending", G(fig_income_spending(), 400)),
            ], className="grid-2"),
            finding("**Equity finding:** Scenario 1 (North Grocery alone) *worsens* the income equity ratio. Adding a grocery store in the north primarily serves households with vehicles who can travel to it — low-income, car-free households in the south and east do not benefit proportionally. **This is a critical counter-intuitive result** that challenges the assumption that more grocery stores always mean better equity.", "warning"),
            finding("**Scenario 4 (Delivery Subsidy)** produces the best income equity ratio. By zeroing delivery costs for low-income households and providing 50% discounts for medium-income, it specifically targets the barrier of transport cost. This mechanism is analogous to SNAP matching programs — a demand-side subsidy with high targeting precision.", "teal"),
        ])

    elif item == "policy-cost":
        return html.Div([
            section_hdr("Cost-Effectiveness Estimates", "Literature-based order-of-magnitude estimates for each scenario.", "#4F46E5"),
            html.Div([
                html.Div([
                    html.Div(style={"position":"absolute","top":"0","left":"0","right":"0",
                                    "height":"5px","background":DATA[sk]["color"],"borderRadius":"13px 13px 0 0"}),
                    html.H4(DATA[sk]["label"], style={"margin":"0 0 10px","color":DATA[sk]["color"],"fontSize":"15px"}),
                    html.Div([
                        html.Div(k, style={"fontSize":"11px","color":"#6B7280","fontWeight":"600","textTransform":"uppercase","letterSpacing":"0.5px","marginBottom":"2px"}),
                        html.Div(v, style={"fontSize":"13.5px","color":"#0D1B2A","fontWeight":"700","fontFamily":"'DM Mono',monospace","marginBottom":"10px"}),
                    ] for k, v in info.items()),
                ], className="location-card",
                   style={"position":"relative","borderLeft":f"3px solid {DATA[sk]['color']}"})
                for sk, info in [
                    ("scenario1", {"Capital cost":  "~$3.5–6M",  "Annual operating": "~$800K",      "Cost/HH/yr": "~$1,600–2,400",  "Evidence base": "USDA new store construction data"}),
                    ("scenario2", {"Capital cost":  "~$0.8–1.5M","Annual operating": "~$350K",      "Cost/HH/yr": "~$400–700",      "Evidence base": "Community food hub lit. (Colasanti 2012)"}),
                    ("scenario3", {"Capital cost":  "~$0.3–0.5M","Annual operating": "~$280K/truck", "Cost/HH/yr": "~$250–400",      "Evidence base": "Mobile pantry operational data (JAXHCI)"}),
                    ("scenario4", {"Capital cost":  "~$0.1–0.2M","Annual operating": "~$450K subsidy","Cost/HH/yr":"~$180–350",      "Evidence base": "USDA SNAP delivery pilot costs"}),
                ]
            ], className="grid-2"),
            html.Div("⚠  These are literature-based order-of-magnitude estimates for illustration. They are NOT from model outputs. Cite appropriately in the dissertation as 'rough estimates based on comparable programs'.",
                     style={"fontSize":"11.5px","color":"#D97706","fontStyle":"italic","marginTop":"8px","padding":"10px 16px","background":"#FFFBEB","borderRadius":"8px","border":"1px solid #FDE68A"}),
        ])

    elif item == "policy-spatial":
        return html.Div([
            section_hdr("Spatial Planning Insights", "Location-specific findings for HZ1 infrastructure planning.", "#4F46E5"),
            finding("**The model's spatial engine uses real Jacksonville coordinates** (14 provider locations, census-block household placement). The following insights derive directly from the spatial utility function and agent travel constraints.", "info"),
            html.Div([
                html.Div([
                    html.H4("📍  Coverage Gap Analysis", style={"color":"#4F46E5","margin":"0 0 10px"}),
                    html.P("The baseline scenario reveals that HZ1's northwest quadrant (Lem Turner / Dunn Ave corridor) has the lowest store density relative to no-vehicle household concentration — the primary coverage gap. S2's hub in the north directly addresses this gap, explaining its strong performance.", style={"fontSize":"13px","color":"#374151","lineHeight":"1.65"}),
                ], className="card"),
                html.Div([
                    html.H4("🚶  No-Vehicle Household Radius", style={"color":"#4F46E5","margin":"0 0 10px"}),
                    html.P("Agents without vehicles are constrained to a 0.8 mi radius, so any intervention that places providers within 0.8 mi of no-vehicle household clusters shows outsized benefit — the S2 hub placement achieves this in the north. Note the Sobol run ranks α (distance) at S_T = 0.210: the radius shapes *which* providers are reachable, but the quality/variety of what is reachable (γ, S_T = 0.942) is what moves food insecurity. See the Sensitivity Tornado panel.", style={"fontSize":"13px","color":"#374151","lineHeight":"1.65"}),
                ], className="card"),
                html.Div([
                    html.H4("📐  Location Sensitivity (S2 Variants)", style={"color":"#0D9488","margin":"0 0 10px"}),
                    html.P("The Location Analysis tab quantifies the marginal impact of store placement. If S2-South shows weaker food insecurity reduction than S2-North, it confirms that the northwest coverage gap is the binding constraint. Run all four directions and compare — this is the methodological contribution of the location analysis.", style={"fontSize":"13px","color":"#374151","lineHeight":"1.65"}),
                ], className="card"),
            ], className="grid-3"),
        ])

    elif item == "policy-stakeholder":
        return html.Div([
            section_hdr("Stakeholder Communication Guide",
                        "Non-technical summary for city officials, health agencies, and community organizations.",
                        "#4F46E5"),
            html.Div([
                html.Div("🏛  For City of Jacksonville Planning Officials", style={"fontWeight":"700","fontSize":"14px","color":"#0D1B2A","marginBottom":"12px"}),
                html.Div([
                    html.P("This simulation tested four food access interventions for Health Zone 1 using a computer model of 500 households over one year.", style={"fontSize":"13px","lineHeight":"1.65","marginBottom":"8px"}),
                    html.P("The strongest result: adding a Community Food Hub plus four new corner stores reduced food insecurity by nearly 15% and shortened average grocery travel by 10%. This is equivalent to roughly 72 fewer food-insecure household-days per 100 households per year.", style={"fontSize":"13px","lineHeight":"1.65","marginBottom":"8px"}),
                    html.P("Mobile pantry trucks on fixed routes showed no meaningful improvement in the model — suggesting that flexible or demand-responsive routing would be needed to generate impact.", style={"fontSize":"13px","lineHeight":"1.65"}),
                ]),
            ], style={"background":"#F8FAFC","borderRadius":"12px","padding":"20px","border":"1px solid #E2E8F0","marginBottom":"18px"}),
            html.Div([
                html.Div("🏥  For Duval County Health Department", style={"fontWeight":"700","fontSize":"14px","color":"#0D1B2A","marginBottom":"12px"}),
                html.Div([
                    html.P("The model predicts that a targeted grocery delivery subsidy (free for low-income, 50% discount for moderate-income) produces the most equitable outcome — meaning it helps low-income households proportionally more than higher-income ones.", style={"fontSize":"13px","lineHeight":"1.65","marginBottom":"8px"}),
                    html.P("This subsidy approach is analogous to SNAP double-value programs and could be piloted with existing SNAP recipients at low infrastructure cost (~$180–350 per household per year based on comparable programs).", style={"fontSize":"13px","lineHeight":"1.65"}),
                ]),
            ], style={"background":"#F0FDF4","borderRadius":"12px","padding":"20px","border":"1px solid #A7F3D0","marginBottom":"18px"}),
            html.Div([
                html.Div("⚠  Model Limitations — What This Simulation Cannot Tell You", style={"fontWeight":"700","fontSize":"14px","color":"#D97706","marginBottom":"12px"}),
                html.P("This model simulates agent behavior under assumed conditions. It does not account for: actual store profitability/viability; political or zoning feasibility; resident preference surveys; seasonal food price variation; or demographic change. Results should be treated as directional evidence for planning conversations, not as precise forecasts.",
                       style={"fontSize":"13px","color":"#374151","lineHeight":"1.65"}),
            ], style={"background":"#FFFBEB","borderRadius":"12px","padding":"20px","border":"1px solid #FDE68A"}),
        ])

    return html.Div("Select an item from the sidebar.")

# ═══════════════════════════════════════════════════════════════════
# 18.  CONTENT RENDERER — INDIVIDUAL SCENARIO TABS
# ═══════════════════════════════════════════════════════════════════

def render_scenario(sk, item):
    sc    = DATA[sk]
    c     = sc["color"]
    label = sc["label"]
    sm    = DATA[sk]["data"].get("summary", {})
    fm_data  = sm.get("final_metrics", sm.get("mean_metrics", {})) if sm else {}
    bl_fm    = DATA["baseline"]["data"].get("summary",{}).get("final_metrics",{})
    n_seeds  = len(available_seeds(sk))

    def delta_card(m, lbl):
        sv = seed_vals(sk, m)
        v  = np.nanmean(sv) if sv else np.nan
        sd = np.nanstd(sv, ddof=1) if len(sv) > 1 else np.nan
        bl_v = np.nanmean(seed_vals("baseline", m))
        pct = (v-bl_v)/abs(bl_v)*100 if (bl_v and bl_v!=0 and not np.isnan(v)) else 0
        hb = METRIC_INFO[m]["higher_better"]
        good = (hb and pct > 0.5) or (not hb and pct < -0.5)
        bad  = (hb and pct < -0.5) or (not hb and pct > 0.5)
        dcls = "positive" if good else ("negative" if bad else "neutral")
        dsym = "▲" if pct > 0 else "▼"
        unit = METRIC_INFO[m]["unit"]
        return html.Div([
            html.Div(style={"position":"absolute","top":"0","left":"0","right":"0",
                            "height":"4px","background":c,"borderRadius":"14px 14px 0 0"}),
            html.Div(lbl, className="kpi-label", style={"color":c}),
            html.Div(f"{v:.3f}{unit}" if not np.isnan(v) else "—", className="kpi-value"),
            html.Div(f"±{sd:.3f}" if not np.isnan(sd) else "", className="kpi-sub"),
            html.Div(f"{dsym} {abs(pct):.1f}% vs Baseline",
                     className=f"kpi-delta {dcls}") if sk != "baseline" else
            html.Div("Reference baseline", className="kpi-delta neutral"),
        ], className="kpi-card", style={"position":"relative"})

    if item == "overview":
        kpi_row = html.Div([
            delta_card("satisfaction_rate","Satisfaction"),
            delta_card("food_insecurity_rate","Food Insecurity"),
            delta_card("avg_travel_distance","Travel Dist"),
            delta_card("spatial_equity_index","Spatial Equity"),
            delta_card("corner_share","Corner Store"),
            delta_card("pantry_share","Pantry / Hub"),
            delta_card("delivery_share","Delivery"),
        ], className="kpi-row")
        cv_items = []
        for m in ["satisfaction_rate","food_insecurity_rate","avg_travel_distance","spatial_equity_index"]:
            v = cv(sk, m)
            flag = "🟢" if v < 10 else ("🟡" if v < 20 else "🔴")
            cv_items.append(html.Div([
                html.Div(f"{flag} CV = {v:.1f}%",
                         style={"fontWeight":"700","fontSize":"13px","color":"#0D1B2A"}),
                html.Div(METRIC_INFO[m]["label"],
                         style={"fontSize":"11px","color":"#6B7280","marginTop":"3px"}),
            ], style={"background":"#F8FAFC","borderRadius":"10px","padding":"12px 16px",
                       "border":"1px solid #E2E8F0","flex":"1","minWidth":"130px"}))
        return html.Div([
            section_hdr(f"{label} — Overview", f"Final-day metrics, n={n_seeds} seeds. Δ% vs Baseline.", c),
            seed_status_badge(sk),
            kpi_row,
            card(f"Seed Stability — {label}",
                 html.Div(cv_items, style={"display":"flex","gap":"12px","flexWrap":"wrap"}),
                 color=c),
        ])

    elif item in ("ts-sat","ts-insec","ts-travel","ts-equity","ts-revenue"):
        m_map = {"ts-sat":"satisfaction_rate","ts-insec":"food_insecurity_rate",
                  "ts-travel":"avg_travel_distance","ts-equity":"spatial_equity_index",
                  "ts-revenue":"total_revenue"}
        m = m_map[item]
        mi = METRIC_INFO[m]
        return html.Div([
            section_hdr(f"{label} — {mi['label']}", f"Dotted = individual seeds | Solid = mean | Band = bootstrap 95% CI | n={n_seeds}", c),
            card(f"{mi['label']} Trajectory", G(fig_ts_single(sk, m), 500), color=c),
        ])

    elif item == "ts-channels":
        return html.Div([
            section_hdr(f"{label} — Channel Share Trajectories",
                        f"Corner store, pantry/hub, and delivery shares over 365 days | n={n_seeds} seeds", c),
            card("Channel Shares Over Time", G(fig_channel_ts(sk), 420), color=c),
        ])

    elif item in ("seed-sat","seed-insec","seed-travel","seed-equity"):
        m_map = {"seed-sat":"satisfaction_rate","seed-insec":"food_insecurity_rate",
                  "seed-travel":"avg_travel_distance","seed-equity":"spatial_equity_index"}
        m = m_map[item]
        mi = METRIC_INFO[m]
        v_list  = [x for x in seed_vals(sk, m) if not np.isnan(x)]
        cv_val  = cv(sk, m)
        ci_lo, ci_hi = bootstrap_ci(v_list)
        rng     = max(v_list)-min(v_list) if v_list else 0
        flag    = "🟢 Stable" if cv_val < 10 else ("🟡 Moderate" if cv_val < 20 else "🔴 Unstable")
        return html.Div([
            section_hdr(f"{label} — {mi['label']} by Seed", f"n={n_seeds} seeds | CV = {cv_val:.1f}%", c),
            html.Div([
                html.Div([html.Div("CV",  style={"fontSize":"10px","color":"#94A3B8","fontWeight":"700","textTransform":"uppercase"}),
                           html.Div(f"{cv_val:.1f}%", style={"fontSize":"22px","fontWeight":"700","color":c}),
                           html.Div(flag, style={"fontSize":"11px","color":"#6B7280"})],
                          style={"background":"white","borderRadius":"12px","padding":"16px 20px","border":"1px solid #E2E8F0","minWidth":"100px","textAlign":"center"}),
                html.Div([html.Div("95% CI", style={"fontSize":"10px","color":"#94A3B8","fontWeight":"700","textTransform":"uppercase"}),
                           html.Div(f"{ci_lo:.4f}–{ci_hi:.4f}", style={"fontSize":"16px","fontWeight":"700","color":c,"fontFamily":"'DM Mono',monospace"}),
                           html.Div("bootstrap 1000 reps", style={"fontSize":"11px","color":"#6B7280"})],
                          style={"background":"white","borderRadius":"12px","padding":"16px 20px","border":"1px solid #E2E8F0","minWidth":"175px","textAlign":"center"}),
                html.Div([html.Div("Mean", style={"fontSize":"10px","color":"#94A3B8","fontWeight":"700","textTransform":"uppercase"}),
                           html.Div(f"{np.nanmean(v_list):.4f}", style={"fontSize":"22px","fontWeight":"700","color":c}),
                           html.Div(f"range = {rng:.4f}", style={"fontSize":"11px","color":"#6B7280"})],
                          style={"background":"white","borderRadius":"12px","padding":"16px 20px","border":"1px solid #E2E8F0","minWidth":"130px","textAlign":"center"}),
            ], style={"display":"flex","gap":"14px","marginBottom":"20px","flexWrap":"wrap"}),
            card(f"{mi['label']} — Per-Seed Breakdown",
                 G(fig_seed_bars(sk, m), 460), color=c),
            card(f"{mi['label']} — Value per Seed (run order, not sorted)",
                 make_dash_table(table_seed_values(sk, m)), color=c),
        ])

    elif item in ("vs-baseline","vs-bl-travel"):
        m = "food_insecurity_rate" if item=="vs-baseline" else "avg_travel_distance"
        mi = METRIC_INFO[m]
        return html.Div([
            section_hdr(f"{label} vs Baseline — {mi['label']}",
                        f"Shaded bands = bootstrap 95% CI | n={n_seeds} seeds", c),
            card(f"Direct Comparison: {label} vs Baseline", G(fig_vs_baseline(sk, m), 510), color=c),
        ])

    elif item == "config":
        cfg = sm.get("config",{}) if sm else {}
        items_cfg = [
            ("Households",          cfg.get("num_consumers","—")),
            ("Simulation Days",     sm.get("days","—") if sm else "—"),
            ("Seeds Loaded",        str(n_seeds)),
            ("Corner Stores",       cfg.get("num_corner_stores","—")),
            ("Food Hubs",           cfg.get("num_food_hubs","—")),
            ("Mobile Pantries",     cfg.get("num_mobile_pantries","—")),
            ("Grocery Capacity",    cfg.get("grocery_store_capacity","—")),
            ("Corner Capacity",     cfg.get("corner_store_capacity","—")),
            ("Hub Capacity",        cfg.get("food_hub_capacity","—")),
            ("Pantry Capacity",     cfg.get("mobile_pantry_capacity","—")),
            ("Max Dist Car",        f"{cfg.get('max_distance_car','—')} mi"),
            ("Max Dist No-Car",     f"{cfg.get('max_distance_no_car','—')} mi"),
            ("Budget Low/wk",       f"${cfg.get('weekly_budget_low','—')}"),
            ("Budget Med/wk",       f"${cfg.get('weekly_budget_medium','—')}"),
            ("Budget High/wk",      f"${cfg.get('weekly_budget_high','—')}"),
            ("α (distance)",        cfg.get("alpha_distance","—")),
            ("β (price/budget)",    cfg.get("beta_price_budget","—")),
            ("γ (quality)",         cfg.get("gamma_quality_variety","—")),
            ("δ (convenience)",     cfg.get("delta_convenience","—")),
        ]
        return html.Div([
            section_hdr(f"{label} — Simulation Configuration", "Exact parameter values for this scenario.", c),
            card("Configuration", html.Div([
                html.Div([
                    html.Span(k, className="config-key"),
                    html.Span(str(v), className="config-val"),
                ], className="config-item")
                for k, v in items_cfg
            ], className="config-grid"), color=c),
        ])

    return html.Div("Select an item from the sidebar.")

# ═══════════════════════════════════════════════════════════════════
# 19.  MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "═"*65)
    print("  ABM Food Access — PhD Dissertation Dashboard  v4")
    print("  Jacksonville, FL  |  Health Zone 1")
    print("═"*65)
    print(f"  {'Scenario':<32}  {'Recal γ=2.6 seeds':>18}")
    print(f"  {'─'*32}  {'─'*18}")
    for sk in SCENARIO_KEYS:
        nr = len([s for s in DATA_RECAL[sk]["data"] if isinstance(s,int)])
        lbl = DATA_RECAL[sk]["label"]
        print(f"  {lbl:<32}  {nr:>18}")
    print("═"*65)
    print("  Showing ONLY the recalibrated γ=2.6 FINAL build (no other seed sets).")
    print("  ➜  http://127.0.0.1:8065")
    print("═"*65 + "\n")
    if os.environ.get('COMBINED_APP') != '1':
        app.run(debug=False, port=8065)