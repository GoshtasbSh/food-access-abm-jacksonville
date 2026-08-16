"""
Sobol Sensitivity Analysis Engine for GeoMesa Food Access Model
===============================================================
Global sensitivity analysis using the Saltelli sampling scheme.
Does NOT import from live_enhanced_mesa_dash.py (one-way dependency only).

Dependency: pip install SALib
"""

import glob
import os
import io
import sys
import contextlib
import json
import random
import numpy as np
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# SALib for Sobol analysis (sobol.sample replaces deprecated saltelli in SALib 1.5+)
from SALib.sample import sobol as sobol_sampler
from SALib.analyze import sobol

# Sobol outputs live under ABM/results/sa_results/ (cwd-independent, restructure).
_SA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "sa_results")

# Model imports - each run loads its own data
# (imports inside run_single_model to keep worker process clean)

OUTPUT_NAMES = [
    'avg_spend_low', 'avg_spend_med', 'avg_spend_high',
    'corner_share', 'food_insecurity_share',
    'avg_dist_car', 'avg_dist_nocar', 'total_trips'
]

PARAM_NAMES = [
    'alpha_distance', 'beta_price_budget', 'gamma_quality_variety',
    'delta_convenience', 'go_shop_threshold_low', 'go_shop_threshold_medium',
    'go_shop_threshold_high'
]


def load_calibration_center(glob_pattern: str = None):
    """
    Load most recent calibration params JSON.
    Priority: Phase 2 (FINAL_CALIBRATED_PARAMS) > Phase 1 (BEST_PHASE1/MEMORY_OPTIMIZED).
    Uses most recent by mtime across all found files.
    
    Returns:
        (params_dict, file_path, calibration_error) or (None, None, None) if not found.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs = ['.', 'extra_Files', script_dir, os.path.join(script_dir, 'extra_Files')]
    # Phase 2 output first (best validation); fallback to Phase 1
    patterns = (
        [p.strip() for p in glob_pattern.split('|')] if glob_pattern and '|' in glob_pattern
        else [glob_pattern] if glob_pattern
        else ['FINAL_CALIBRATED_PARAMS_*.json', 'BEST_PHASE1_PARAMS_*.json', 'BEST_MEMORY_OPTIMIZED_PARAMS_*.json']
    )
    files = []
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for p in patterns:
            files.extend(glob.glob(os.path.join(d, p)))
    
    if not files:
        return (None, None, None)
    
    # Most recent by mtime
    latest = max(files, key=lambda f: os.path.getmtime(f))
    
    try:
        with open(latest, 'r') as f:
            data = json.load(f)
        params = data.get('best_parameters', data.get('final_parameters', {}))
        # Ensure we have the 7 params we need
        center = {k: params[k] for k in PARAM_NAMES if k in params}
        if len(center) < 7:
            return (None, None, None)
        cal_error = data.get('calibration_error', data.get('calibration_error_full', None))
        return (center, latest, cal_error)
    except Exception:
        return (None, None, None)


def build_sa_problem(center_params: dict, pct: float = 0.30):
    """
    Build SALib problem dict and summary DataFrame.
    
    Returns:
        problem: dict with num_vars, names, bounds
        summary_df: DataFrame for controls table (param, center, lower, upper)
    """
    names = list(center_params.keys())
    bounds = [[v * (1 - pct), v * (1 + pct)] for v in center_params.values()]
    problem = {
        'num_vars': len(names),
        'names': names,
        'bounds': bounds
    }
    rows = []
    for n, v in zip(names, center_params.values()):
        rows.append({
            'param': n,
            'center': v,
            'lower': v * (1 - pct),
            'upper': v * (1 + pct)
        })
    summary_df = pd.DataFrame(rows)
    return problem, summary_df


@contextlib.contextmanager
def _quiet():
    """Suppress stdout/stderr during model setup and stepping."""
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
        yield
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def _run_single_model_impl(args_tuple):
    """
    Worker function: run one model evaluation.
    Uses _quiet() to suppress verbose model setup output.
    """
    run_index, param_array, param_names, n_steps, seed = args_tuple
    
    random.seed(seed)
    np.random.seed(seed)
    
    try:
        from enhanced_mesa_geo_model import SimulationConfig, IncomeLevel, EnhancedHouseholdAgent
        from baseline_scenario import create_baseline_scenario
    except ImportError:
        return {k: np.nan for k in OUTPUT_NAMES}
    
    try:
        config = SimulationConfig(
            num_consumers=200,               # Sufficient for stable income distribution; 2.5× faster than 500
            enable_spatial_analytics=False,   # Not needed for SA metrics
        )
        for i, name in enumerate(param_names):
            if i < len(param_array):
                setattr(config, name, param_array[i])
        
        with _quiet():
            model = create_baseline_scenario(config=config)
            # Seed Mesa's per-model activation RNG (model.random) — the global
            # random/np seeds above do NOT control it, so without this the
            # same (sample, seed) gave different Sobol outputs on every run
            # (see run_journal_50seeds.py for the same ritual).
            if hasattr(model, "reset_randomizer"):
                model.reset_randomizer(seed)
            for _ in range(n_steps):
                model.step()
        
        households = [a for a in model.schedule.agents if isinstance(a, EnhancedHouseholdAgent)]
        
        spend_by_income = {IncomeLevel.LOW: [], IncomeLevel.MEDIUM: [], IncomeLevel.HIGH: []}
        for hh in households:
            if len(hh.shopping_history) > 0:
                total_spend = sum(trip.get('basket_cost', trip.get('basket_size', 0))
                                 for trip in hh.shopping_history)
                spend_by_income[hh.income].append(total_spend)
        
        avg_spend_low = np.mean(spend_by_income[IncomeLevel.LOW]) if spend_by_income[IncomeLevel.LOW] else 0
        avg_spend_med = np.mean(spend_by_income[IncomeLevel.MEDIUM]) if spend_by_income[IncomeLevel.MEDIUM] else 0
        avg_spend_high = np.mean(spend_by_income[IncomeLevel.HIGH]) if spend_by_income[IncomeLevel.HIGH] else 0
        
        corner_trips = sum(1 for hh in households for trip in hh.shopping_history
                          if trip.get('is_corner_shop', False))
        total_trip_count = sum(len(hh.shopping_history) for hh in households)
        corner_share = corner_trips / total_trip_count if total_trip_count > 0 else 0
        total_trips_per_hh = total_trip_count / len(households) if households else 0

        # Food insecurity (same definition as Phase 2 — core calibration target)
        food_insecure = sum(1 for hh in households
                           if hh.unmet_need > 0
                           or any(trip.get('unmet_need', 0) > 0 for trip in hh.shopping_history))
        food_insecurity_share = food_insecure / len(households) if households else 0
        
        car_distances = []
        nocar_distances = []
        for hh in households:
            for trip in hh.shopping_history:
                if trip.get('travel_distance', 0) > 0:
                    if hh.vehicle_available:
                        car_distances.append(trip['travel_distance'])
                    else:
                        nocar_distances.append(trip['travel_distance'])
        
        avg_dist_car = np.mean(car_distances) if car_distances else 0
        avg_dist_nocar = np.mean(nocar_distances) if nocar_distances else 0
        
        return {
            'avg_spend_low': avg_spend_low,
            'avg_spend_med': avg_spend_med,
            'avg_spend_high': avg_spend_high,
            'corner_share': corner_share,
            'food_insecurity_share': food_insecurity_share,
            'avg_dist_car': avg_dist_car,
            'avg_dist_nocar': avg_dist_nocar,
            'total_trips': total_trips_per_hh
        }
    except Exception:
        return {k: np.nan for k in OUTPUT_NAMES}


def run_single_model(args_tuple):
    """Public wrapper for _run_single_model_impl (handles any edge cases)."""
    return _run_single_model_impl(args_tuple)


def run_sa_sweep(N: int, pct: float, n_steps: int = 90,
                 progress_callback=None,
                 cancel_event=None):
    """
    Run full Sobol sensitivity analysis sweep.
    
    Args:
        N: Saltelli sample size
        pct: Bounds percentage (e.g. 0.30 for ±30%)
        n_steps: Simulation steps per run
        progress_callback: (completed, total, done=False, result_path=None)
        cancel_event: threading.Event to signal cancel
    
    Returns:
        (raw_df, tidy_df, indices_dict)
    """
    center_params, cal_path, _ = load_calibration_center()
    if not center_params:
        print("SA: No calibration file found.", flush=True)
        if progress_callback:
            progress_callback(0, 1, done=True, result_path=None)
        return (None, None, None)

    print(f"SA: Using {os.path.basename(cal_path or '?')}", flush=True)
    problem, _ = build_sa_problem(center_params, pct)
    param_values = sobol_sampler.sample(problem, N=N, calc_second_order=True)
    n_runs = param_values.shape[0]
    param_names = problem['names']
    print(f"SA: {n_runs} runs (N={N}, 7 params, ±{pct*100:.0f}%, {n_steps} days)", flush=True)

    if progress_callback:
        progress_callback(0, n_runs, done=False, result_path=None)
    
    os.makedirs(_SA_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    Y_matrix = np.full((n_runs, len(OUTPUT_NAMES)), np.nan)
    batch_size = 10
    completed = 0

    # Fixed seed: all Sobol evaluations use the same random seed so
    # stochastic noise is identical across parameter configurations
    # and cancels in Sobol index computation (Saltelli et al. 2010;
    # Ligmann-Zielinska et al. 2025).
    FIXED_SEED = 42
    args_list = [
        (i, param_values[i], param_names, n_steps, FIXED_SEED)
        for i in range(n_runs)
    ]

    # ThreadPoolExecutor avoids macOS spawn overhead (ProcessPoolExecutor
    # re-imports everything per worker, adding 30-60s startup each).
    n_workers = min(4, max(1, n_runs // 100))
    executor = ThreadPoolExecutor(max_workers=n_workers)
    try:
        futures = {executor.submit(run_single_model, args): args[0]
                   for args in args_list}
        
        for future in as_completed(futures):
            if cancel_event and cancel_event.is_set():
                break
            idx = futures[future]
            try:
                result = future.result()
                for j, k in enumerate(OUTPUT_NAMES):
                    Y_matrix[idx, j] = result.get(k, np.nan)
            except Exception:
                pass
            completed += 1
            if progress_callback:
                progress_callback(completed, n_runs, done=False, result_path=None)
            if completed % 200 == 0 and completed > 0:
                ckpt_path = os.path.join(_SA_DIR, f"checkpoint_{timestamp}_{completed}.csv")
                raw = pd.DataFrame(param_values, columns=param_names)
                for j, k in enumerate(OUTPUT_NAMES):
                    raw[k] = Y_matrix[:, j]
                raw.to_csv(ckpt_path, index=False)
    finally:
        executor.shutdown(wait=False)
    
    if cancel_event and cancel_event.is_set():
        return (None, None, None)
    
    # Compute Sobol indices per output
    indices_dict = {}
    tidy_rows = []
    
    for j, out_name in enumerate(OUTPUT_NAMES):
        Y = Y_matrix[:, j]
        valid = ~np.isnan(Y)
        if np.sum(valid) < 0.9 * len(Y):
            print(f"Warning: {out_name} has {np.sum(~valid)} NaN runs — skipping", flush=True)
            continue
        Y_imputed = Y.copy()
        Y_imputed[~valid] = np.nanmedian(Y[valid]) if np.any(valid) else 0.0
        try:
            Si = sobol.analyze(problem, Y_imputed, calc_second_order=True)
            indices_dict[out_name] = {
                'S1': Si['S1'].tolist(),
                'ST': Si['ST'].tolist(),
                'S1_conf': Si['S1_conf'].tolist() if 'S1_conf' in Si else [0]*len(Si['S1']),
                'ST_conf': Si['ST_conf'].tolist() if 'ST_conf' in Si else [0]*len(Si['ST']),
                'S2': Si['S2'].tolist() if 'S2' in Si else [],
                'names': problem['names']
            }
            for i, pname in enumerate(problem['names']):
                tidy_rows.append({
                    'output': out_name,
                    'parameter': pname,
                    'S1': float(Si['S1'][i]),
                    'ST': float(Si['ST'][i]),
                    'S1_conf': float(Si['S1_conf'][i]) if 'S1_conf' in Si else 0,
                    'ST_conf': float(Si['ST_conf'][i]) if 'ST_conf' in Si else 0
                })
        except Exception:
            pass
    
    tidy_df = pd.DataFrame(tidy_rows) if tidy_rows else None
    
    raw_df = pd.DataFrame(param_values, columns=param_names)
    for j, k in enumerate(OUTPUT_NAMES):
        raw_df[k] = Y_matrix[:, j]
    
    if progress_callback:
        result_path = f"sa_results/sobol_{timestamp}"
        progress_callback(n_runs, n_runs, done=True, result_path=result_path)
    
    raw_path = os.path.join(_SA_DIR, f"sobol_raw_{timestamp}.csv")
    tidy_path = os.path.join(_SA_DIR, f"sobol_tidy_{timestamp}.csv")
    indices_path = os.path.join(_SA_DIR, f"sobol_indices_{timestamp}.json")
    
    raw_df.to_csv(raw_path, index=False)
    if tidy_df is not None:
        tidy_df.to_csv(tidy_path, index=False)
    with open(indices_path, 'w') as f:
        json.dump(indices_dict, f, indent=2)
    
    return (raw_df, tidy_df, indices_dict)


def compute_budget_table(tidy_df: pd.DataFrame, indices_dict: dict = None) -> pd.DataFrame:
    """
    columns: output, dominant_param, dominant_S1, strongest_pair, S2_value, interaction_ratio
    interaction_ratio = (sum(ST) - sum(S1)) / sum(ST) per output
    """
    if tidy_df is None or tidy_df.empty:
        return pd.DataFrame()
    
    param_names = tidy_df['parameter'].unique().tolist()
    rows = []
    for out_name in tidy_df['output'].unique():
        sub = tidy_df[tidy_df['output'] == out_name]
        if sub.empty:
            continue
        dom_idx = sub['ST'].idxmax()
        dom_row = sub.loc[dom_idx]
        dominant_param = dom_row['parameter']
        dominant_S1 = dom_row['S1']
        
        sum_s1 = sub['S1'].sum()
        sum_st = sub['ST'].sum()
        interaction_ratio = (sum_st - sum_s1) / sum_st if sum_st > 0 else 0
        
        strongest_pair = ""
        s2_value = np.nan
        if indices_dict and out_name in indices_dict and indices_dict[out_name].get('S2'):
            S2_matrix = np.array(indices_dict[out_name]['S2'])
            pnames = indices_dict[out_name].get('names', param_names)
            np.fill_diagonal(S2_matrix, -np.inf)
            i, j = np.unravel_index(np.argmax(S2_matrix), S2_matrix.shape)
            if i < len(pnames) and j < len(pnames) and S2_matrix[i, j] > -np.inf:
                strongest_pair = f"{pnames[i]} × {pnames[j]}"
                s2_value = float(S2_matrix[i, j])
        rows.append({
            'output': out_name,
            'dominant_param': dominant_param,
            'dominant_S1': float(dominant_S1),
            'strongest_pair': strongest_pair,
            'S2_value': s2_value,
            'interaction_ratio': float(interaction_ratio)
        })
    return pd.DataFrame(rows)


def load_latest_sa_results():
    """
    Load most recent sobol_tidy_*.csv and sobol_indices_*.json from ./sa_results/
    Returns (raw_df, tidy_df, indices_dict) or (None, None, None)
    """
    d = _SA_DIR
    if not os.path.isdir(d):
        return (None, None, None)
    
    tidy_files = glob.glob(os.path.join(d, 'sobol_tidy_*.csv'))
    if not tidy_files:
        return (None, None, None)
    
    latest_tidy = max(tidy_files, key=os.path.getmtime)
    base = os.path.basename(latest_tidy)
    ts = base.replace('sobol_tidy_', '').replace('.csv', '')
    
    raw_path = os.path.join(d, f'sobol_raw_{ts}.csv')
    indices_path = os.path.join(d, f'sobol_indices_{ts}.json')
    
    try:
        tidy_df = pd.read_csv(latest_tidy)
    except Exception:
        return (None, None, None)
    
    raw_df = None
    if os.path.isfile(raw_path):
        try:
            raw_df = pd.read_csv(raw_path)
        except Exception:
            pass
    
    indices_dict = {}
    if os.path.isfile(indices_path):
        try:
            with open(indices_path, 'r') as f:
                indices_dict = json.load(f)
        except Exception:
            pass
    
    return (raw_df, tidy_df, indices_dict)


def build_heatmap_figure(tidy_df: pd.DataFrame, index_type: str = 'ST'):
    import plotly.graph_objects as go
    
    if tidy_df is None or tidy_df.empty:
        return go.Figure()
    
    outputs = tidy_df['output'].unique().tolist()
    params = tidy_df['parameter'].unique().tolist()
    
    col = index_type
    if col not in tidy_df.columns:
        col = 'ST'
    
    pivot = tidy_df.pivot(index='parameter', columns='output', values=col)
    pivot = pivot.reindex(params)
    pivot = pivot[outputs]
    
    fig = go.Figure(data=go.Heatmap(
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        z=pivot.values.tolist(),
        colorscale='Viridis',
        zmin=0,
        zmax=1,
        text=[[f"{v:.2f}" if not np.isnan(v) else "" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont={"size": 11},
        hovertemplate="%{y} × %{x}<br>%{z:.3f}<extra></extra>"
    ))
    fig.update_layout(
        title=f"Sobol {index_type} Sensitivity Indices",
        xaxis_title="Output Metric",
        yaxis_title="Parameter",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='Inter'),
        margin=dict(l=100, r=50, t=50, b=100)
    )
    return fig


def build_bar_figure(tidy_df: pd.DataFrame, output_name: str, sort_by: str = 'ST'):
    import plotly.graph_objects as go
    
    if tidy_df is None or tidy_df.empty:
        return go.Figure()
    
    sub = tidy_df[tidy_df['output'] == output_name]
    if sub.empty:
        return go.Figure()
    
    sub = sub.sort_values(sort_by, ascending=True)
    params = sub['parameter'].tolist()
    s1_vals = sub['S1'].tolist()
    st_vals = sub['ST'].tolist()
    s1_conf = sub['S1_conf'].tolist() if 'S1_conf' in sub.columns else [0]*len(params)
    st_conf = sub['ST_conf'].tolist() if 'ST_conf' in sub.columns else [0]*len(params)
    
    colors = []
    for s1, st in zip(s1_vals, st_vals):
        diff = st - s1 if not np.isnan(st) else 0
        if diff < 0.1:
            colors.append('#27ae60')
        elif diff < 0.3:
            colors.append('#f39c12')
        else:
            colors.append('#e74c3c')
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=params,
        x=s1_vals,
        name='S1',
        orientation='h',
        marker_color='#667eea',
        error_x=dict(type='data', array=s1_conf)
    ))
    fig.add_trace(go.Bar(
        y=params,
        x=st_vals,
        name='ST',
        orientation='h',
        marker_color='rgba(118, 75, 162, 0.5)',
        error_x=dict(type='data', array=st_conf)
    ))
    
    fig.update_layout(
        title=f"Sobol Indices — {output_name}",
        barmode='overlay',
        xaxis_title="Sensitivity Index",
        yaxis_title="Parameter",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='Inter'),
        legend=dict(orientation='h'),
        margin=dict(l=120)
    )
    return fig


def build_scatter_figure(raw_df: pd.DataFrame, x_param: str, y_output: str):
    import plotly.graph_objects as go
    
    if raw_df is None or raw_df.empty or x_param not in raw_df.columns or y_output not in raw_df.columns:
        return go.Figure()
    
    x = raw_df[x_param].values
    y = raw_df[y_output].values
    valid = ~np.isnan(x) & ~np.isnan(y)
    x, y = x[valid], y[valid]
    if len(x) < 5:
        return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode='markers',
        marker=dict(size=6, color='#667eea', opacity=0.6),
        name='Data'
    ))
    
    try:
        from statsmodels.nonparametric.smoothers_lowess import lowess
        smooth = lowess(y, x, frac=0.3)
        fig.add_trace(go.Scatter(
            x=smooth[:, 0], y=smooth[:, 1],
            mode='lines',
            line=dict(color='#764ba2', width=2),
            name='LOWESS'
        ))
    except ImportError:
        try:
            z = np.polyfit(x, y, 2)
            p = np.poly1d(z)
            x_sorted = np.sort(x)
            fig.add_trace(go.Scatter(
                x=x_sorted, y=p(x_sorted),
                mode='lines',
                line=dict(color='#764ba2', width=2),
                name='Poly fit'
            ))
        except Exception:
            pass
    
    fig.update_layout(
        title=f"{y_output} vs {x_param}",
        xaxis_title=x_param,
        yaxis_title=y_output,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='Inter')
    )
    return fig


def _problem_from_raw_df(raw_df: pd.DataFrame) -> dict:
    """Reconstruct problem dict from raw_df columns when loading from file."""
    if raw_df is None or raw_df.empty:
        return None
    param_cols = [c for c in raw_df.columns if c in PARAM_NAMES]
    if not param_cols:
        return None
    bounds = []
    for c in param_cols:
        mn, mx = raw_df[c].min(), raw_df[c].max()
        bounds.append([float(mn), float(mx)])
    return {'num_vars': len(param_cols), 'names': param_cols, 'bounds': bounds}


def build_convergence_figure(raw_df: pd.DataFrame, problem: dict, output_col: str):
    import plotly.graph_objects as go
    
    if raw_df is None or raw_df.empty or output_col not in raw_df.columns:
        return go.Figure()
    if problem is None:
        problem = _problem_from_raw_df(raw_df)
    if problem is None:
        return go.Figure()
    
    param_names = problem.get('names', [])
    D = len(param_names)
    base_unit = D + 2
    n = len(raw_df)
    if n < base_unit * 2:
        return go.Figure()
    
    fractions = [0.125, 0.25, 0.5, 0.75, 1.0]
    x_vals = []
    st_by_param = {p: [] for p in param_names}
    
    for frac in fractions:
        subset_n = int(n * frac)
        valid_n = (subset_n // base_unit) * base_unit
        if valid_n < base_unit * 2:
            continue
        sub = raw_df.head(valid_n)
        Y = sub[output_col].values.copy()
        median_val = np.nanmedian(Y)
        Y = np.where(np.isnan(Y), median_val, Y)
        try:
            Si = sobol.analyze(problem, Y, calc_second_order=False)
            x_vals.append(valid_n)
            for i, p in enumerate(param_names):
                st_by_param[p].append(float(Si['ST'][i]))
        except Exception:
            continue
    
    if not x_vals:
        return go.Figure()
    
    fig = go.Figure()
    for p in param_names:
        if st_by_param[p]:
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=st_by_param[p],
                mode='lines+markers',
                name=p
            ))
    
    fig.update_layout(
        title=f"ST Convergence — {output_col}",
        xaxis_title="Number of Runs",
        yaxis_title="ST Index",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='Inter'),
        legend=dict(orientation='h')
    )
    return fig


# ═══════════════════════════════════════════════════════════════
# COMPLEMENTARY SENSITIVITY METHODS
# Computed from the same N raw model evaluations (no new runs).
# ═══════════════════════════════════════════════════════════════

_PARAM_LABELS = {
    'alpha_distance':           'α — Distance decay',
    'beta_price_budget':        'β — Price/budget weight',
    'gamma_quality_variety':    'γ — Quality/variety weight',
    'delta_convenience':        'δ — Convenience weight',
    'go_shop_threshold_low':    'θ_low — Shopping freq. (low)',
    'go_shop_threshold_medium': 'θ_med — Shopping freq. (med)',
    'go_shop_threshold_high':   'θ_high — Shopping freq. (high)',
}

_OUTPUT_LABELS = {
    'avg_spend_low':        'Low-Inc.\nSpend',
    'avg_spend_med':        'Med-Inc.\nSpend',
    'avg_spend_high':       'High-Inc.\nSpend',
    'corner_share':         'Corner\nStore %',
    'food_insecurity_share': 'Food\nInsecurity',
    'avg_dist_car':         'Dist.\n(Car)',
    'avg_dist_nocar':       'Dist.\n(No Car)',
    'total_trips':          'Total\nTrips',
}


def compute_pearson_correlation(raw_df):
    """
    Pearson r with bootstrapped 95% CI for every parameter–output pair.
    Returns DataFrame: parameter, output, r, ci_low, ci_high, p_value
    """
    from scipy import stats as sp_stats
    done = raw_df.dropna()
    rng = np.random.RandomState(42)
    rows = []
    params = [c for c in PARAM_NAMES if c in done.columns]
    outputs = [c for c in OUTPUT_NAMES if c in done.columns]
    for p in params:
        x = done[p].values
        for o in outputs:
            y = done[o].values
            r, pval = sp_stats.pearsonr(x, y)
            boot_r = np.empty(2000)
            for b in range(2000):
                idx = rng.randint(0, len(x), len(x))
                boot_r[b] = np.corrcoef(x[idx], y[idx])[0, 1]
            ci_lo, ci_hi = np.nanpercentile(boot_r, [2.5, 97.5])
            rows.append({
                'parameter': p, 'output': o,
                'r': r, 'ci_low': ci_lo, 'ci_high': ci_hi, 'p_value': pval
            })
    return pd.DataFrame(rows)


def compute_src(raw_df):
    """
    Standardized Regression Coefficients (SRC) with R² per output.
    Returns DataFrame: parameter, output, src, r_squared
    """
    done = raw_df.dropna()
    params = [c for c in PARAM_NAMES if c in done.columns]
    outputs = [c for c in OUTPUT_NAMES if c in done.columns]
    X = done[params].values
    X_std = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-12)
    X_aug = np.column_stack([np.ones(len(X_std)), X_std])
    rows = []
    for o in outputs:
        y = done[o].values
        y_std = (y - y.mean()) / (y.std() + 1e-12)
        beta, _, _, _ = np.linalg.lstsq(X_aug, y_std, rcond=None)
        y_hat = X_aug @ beta
        ss_res = np.sum((y_std - y_hat) ** 2)
        ss_tot = np.sum((y_std - y_std.mean()) ** 2)
        r2 = max(0.0, 1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0
        for i, p in enumerate(params):
            rows.append({
                'parameter': p, 'output': o,
                'src': float(beta[i + 1]), 'r_squared': r2
            })
    return pd.DataFrame(rows)


def compute_prcc(raw_df):
    """
    Partial Rank Correlation Coefficients (PRCC).
    Rank-transform → OLS residualize → Pearson on residuals.
    Returns DataFrame: parameter, output, prcc, p_value
    """
    from scipy import stats as sp_stats
    done = raw_df.dropna()
    params = [c for c in PARAM_NAMES if c in done.columns]
    outputs = [c for c in OUTPUT_NAMES if c in done.columns]
    ranks = {}
    for c in params + outputs:
        ranks[c] = sp_stats.rankdata(done[c].values).astype(float)
    rows = []
    for o in outputs:
        y_rank = ranks[o]
        for p in params:
            others = [c for c in params if c != p]
            X_others = np.column_stack([ranks[c] for c in others])
            X_aug = np.column_stack([np.ones(len(X_others)), X_others])
            bp, _, _, _ = np.linalg.lstsq(X_aug, ranks[p], rcond=None)
            bo, _, _, _ = np.linalg.lstsq(X_aug, y_rank, rcond=None)
            res_p = ranks[p] - X_aug @ bp
            res_o = y_rank - X_aug @ bo
            r, pval = sp_stats.pearsonr(res_p, res_o)
            rows.append({
                'parameter': p, 'output': o, 'prcc': r, 'p_value': pval
            })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════
# DISSERTATION FIGURE GENERATION (matplotlib, saved to PNG)
# ═══════════════════════════════════════════════════════════════

def _sig_stars(p):
    if p < 0.001:
        return '***'
    if p < 0.01:
        return '**'
    if p < 0.05:
        return '*'
    return 'ns'


def generate_dissertation_figures(raw_df, sobol_indices_dict, output_dir):
    """
    Generate 5 publication-quality figures and save as PNG files.
    Also saves sensitivity_pearson_results.csv and sensitivity_prcc_results.csv.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from scipy import stats as sp_stats

    os.makedirs(output_dir, exist_ok=True)
    done = raw_df.dropna()
    N = len(done)

    params = [c for c in PARAM_NAMES if c in done.columns]
    outputs = [c for c in OUTPUT_NAMES if c in done.columns]
    p_labels = [_PARAM_LABELS.get(p, p) for p in params]
    o_labels = [_OUTPUT_LABELS.get(o, o) for o in outputs]

    # ── Compute complementary methods ────────────────────────
    print("SA: Computing Pearson correlations...", flush=True)
    pearson_df = compute_pearson_correlation(raw_df)
    print("SA: Computing SRC...", flush=True)
    src_df = compute_src(raw_df)
    print("SA: Computing PRCC...", flush=True)
    prcc_df = compute_prcc(raw_df)

    # ── Save CSV results ─────────────────────────────────────
    pearson_df.to_csv(os.path.join(output_dir, 'sensitivity_pearson_results.csv'), index=False)
    prcc_df.to_csv(os.path.join(output_dir, 'sensitivity_prcc_results.csv'), index=False)
    print(f"SA: Saved sensitivity_pearson_results.csv and sensitivity_prcc_results.csv", flush=True)

    # ── Shared style ─────────────────────────────────────────
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'figure.dpi': 300,
    })

    # ════════════════════════════════════════════════════════════
    # FIGURE 1 — Pearson Heatmap (7 params × 8 outputs)
    # ════════════════════════════════════════════════════════════
    r_matrix = np.full((len(params), len(outputs)), np.nan)
    p_matrix = np.full_like(r_matrix, np.nan)
    for _, row in pearson_df.iterrows():
        pi = params.index(row['parameter']) if row['parameter'] in params else -1
        oi = outputs.index(row['output']) if row['output'] in outputs else -1
        if pi >= 0 and oi >= 0:
            r_matrix[pi, oi] = row['r']
            p_matrix[pi, oi] = row['p_value']

    fig1, ax1 = plt.subplots(figsize=(12, 5.5))
    im = ax1.imshow(r_matrix, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    for i in range(len(params)):
        for j in range(len(outputs)):
            rv = r_matrix[i, j]
            pv = p_matrix[i, j]
            if np.isnan(rv):
                continue
            color = 'white' if abs(rv) > 0.5 else 'black'
            ax1.text(j, i, f"{rv:.2f}\n{_sig_stars(pv)}",
                     ha='center', va='center', fontsize=8, color=color)
    ax1.set_xticks(range(len(outputs)))
    ax1.set_xticklabels(o_labels, fontsize=8)
    ax1.set_yticks(range(len(params)))
    ax1.set_yticklabels(p_labels, fontsize=9)
    ax1.set_xlabel('Output Metric')
    ax1.set_ylabel('Parameter')
    ax1.set_title(f'Sensitivity Screening — Pearson Correlation Matrix (N={N:,})',
                  fontweight='bold', pad=12)
    fig1.colorbar(im, ax=ax1, label='Pearson r', shrink=0.85)
    fig1.tight_layout()
    fig1.savefig(os.path.join(output_dir, 'fig1_pearson_heatmap.png'), bbox_inches='tight')
    plt.close(fig1)
    print("SA: Saved fig1_pearson_heatmap.png", flush=True)

    # ════════════════════════════════════════════════════════════
    # FIGURE 2 — Ranked Bar Charts (1×4 subplot)
    # ════════════════════════════════════════════════════════════
    bar_outputs = ['avg_spend_low', 'corner_share', 'avg_dist_car', 'avg_spend_med']
    bar_colors_map = {
        'avg_spend_low': '#1F4E79',
        'corner_share':  '#2E75B6',
        'avg_dist_car':  '#375623',
        'avg_spend_med': '#C9A227',
    }

    fig2, axes2 = plt.subplots(1, 4, figsize=(18, 5), sharey=False)
    for ax, oname in zip(axes2, bar_outputs):
        sub = pearson_df[pearson_df['output'] == oname].copy()
        if sub.empty:
            ax.set_visible(False)
            continue
        sub['abs_r'] = sub['r'].abs()
        sub = sub.sort_values('abs_r', ascending=True)
        y_pos = range(len(sub))
        labels = [_PARAM_LABELS.get(p, p) for p in sub['parameter']]
        r_vals = sub['r'].values
        ci_lo = sub['ci_low'].values
        ci_hi = sub['ci_high'].values
        xerr_lo = np.abs(r_vals - ci_lo)
        xerr_hi = np.abs(ci_hi - r_vals)
        base_color = bar_colors_map.get(oname, '#2E75B6')
        colors = [base_color if abs(r) > 0.05 else '#AAAAAA' for r in r_vals]
        ax.barh(y_pos, r_vals, xerr=[xerr_lo, xerr_hi],
                color=colors, edgecolor='none', capsize=3, error_kw={'linewidth': 1})
        ax.axvline(x=0, color='black', linestyle='--', linewidth=0.8, alpha=0.6)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(labels, fontsize=7.5)
        ax.set_xlabel('Pearson r', fontsize=9)
        ax.set_xlim(-1.05, 1.05)
        o_label = _OUTPUT_LABELS.get(oname, oname).replace('\n', ' ')
        ax.set_title(o_label, fontweight='bold', fontsize=10)
    fig2.suptitle(f'Parameter Sensitivity Ranking — Pearson r with 95% CI (N={N:,})',
                  fontweight='bold', fontsize=12, y=1.02)
    fig2.tight_layout()
    fig2.savefig(os.path.join(output_dir, 'fig2_ranked_bars.png'), bbox_inches='tight')
    plt.close(fig2)
    print("SA: Saved fig2_ranked_bars.png", flush=True)

    # ════════════════════════════════════════════════════════════
    # FIGURE 3 — Sobol S1 for avg_spend_low only
    # ════════════════════════════════════════════════════════════
    fig3, ax3 = plt.subplots(figsize=(8, 5))
    target_output = 'avg_spend_low'
    if target_output in sobol_indices_dict:
        si = sobol_indices_dict[target_output]
        s1_vals = np.array(si['S1'])
        s1_conf = np.array(si.get('S1_conf', [0] * len(s1_vals)))
        names_si = si.get('names', params)
        order = np.argsort(s1_vals)
        s1_sorted = s1_vals[order]
        conf_sorted = s1_conf[order]
        labels_sorted = [_PARAM_LABELS.get(names_si[i], names_si[i]) for i in order]
        y_pos = range(len(s1_sorted))
        colors = ['#C00000' if v == s1_sorted.max() else '#2E75B6' for v in s1_sorted]
        ax3.barh(y_pos, s1_sorted, xerr=conf_sorted,
                 color=colors, edgecolor='none', capsize=3, error_kw={'linewidth': 1})
        ax3.axvline(x=0, color='black', linestyle='--', linewidth=0.8, alpha=0.6)
        ax3.set_yticks(list(y_pos))
        ax3.set_yticklabels(labels_sorted, fontsize=9)
        ax3.set_xlabel('Sobol S1 Index', fontsize=10)
        dom_idx = np.argmax(s1_sorted)
        dom_val = s1_sorted[dom_idx]
        dom_name = labels_sorted[dom_idx]
        ax3.annotate(f'S1 = {dom_val:.3f} (explains {dom_val*100:.1f}% of variance)',
                     xy=(dom_val, dom_idx), xytext=(dom_val * 0.5, dom_idx - 1.8),
                     fontsize=9, fontweight='bold', color='#C00000',
                     arrowprops=dict(arrowstyle='->', color='#C00000', lw=1.5))
        sum_s1 = float(np.sum(s1_vals))
        ax3.text(0.98, 0.05, f'SumS1 = {sum_s1:.3f} ✓  Valid Sobol decomposition',
                 transform=ax3.transAxes, fontsize=9, ha='right', va='bottom',
                 bbox=dict(boxstyle='round,pad=0.4', facecolor='#E2EFDA',
                           edgecolor='#375623', alpha=0.9))
    else:
        ax3.text(0.5, 0.5, 'No Sobol indices for avg_spend_low',
                 transform=ax3.transAxes, ha='center', va='center')
    ax3.set_title(f'Sobol S1 Indices — Low-Income Annual Spending (N={N:,} Saltelli evaluations)',
                  fontweight='bold', fontsize=11, pad=12)
    fig3.tight_layout()
    fig3.savefig(os.path.join(output_dir, 'fig3_sobol_spend_low.png'), bbox_inches='tight')
    plt.close(fig3)
    print("SA: Saved fig3_sobol_spend_low.png", flush=True)

    # ════════════════════════════════════════════════════════════
    # FIGURE 4 — PRCC Heatmap (7 params × 4 key outputs)
    # ════════════════════════════════════════════════════════════
    prcc_outputs = ['avg_spend_low', 'corner_share', 'avg_dist_car', 'avg_spend_med']
    prcc_o_labels = [_OUTPUT_LABELS.get(o, o) for o in prcc_outputs]
    prcc_matrix = np.full((len(params), len(prcc_outputs)), np.nan)
    prcc_pmat = np.full_like(prcc_matrix, np.nan)
    for _, row in prcc_df.iterrows():
        pi = params.index(row['parameter']) if row['parameter'] in params else -1
        oi = prcc_outputs.index(row['output']) if row['output'] in prcc_outputs else -1
        if pi >= 0 and oi >= 0:
            prcc_matrix[pi, oi] = row['prcc']
            prcc_pmat[pi, oi] = row['p_value']

    fig4, ax4 = plt.subplots(figsize=(8, 5.5))
    im4 = ax4.imshow(prcc_matrix, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    for i in range(len(params)):
        for j in range(len(prcc_outputs)):
            rv = prcc_matrix[i, j]
            pv = prcc_pmat[i, j]
            if np.isnan(rv):
                continue
            color = 'white' if abs(rv) > 0.5 else 'black'
            ax4.text(j, i, f"{rv:.2f}\n{_sig_stars(pv)}",
                     ha='center', va='center', fontsize=9, color=color)
    ax4.set_xticks(range(len(prcc_outputs)))
    ax4.set_xticklabels(prcc_o_labels, fontsize=9)
    ax4.set_yticks(range(len(params)))
    ax4.set_yticklabels(p_labels, fontsize=9)
    ax4.set_xlabel('Output Metric')
    ax4.set_ylabel('Parameter')
    ax4.set_title('Partial Rank Correlation Coefficients (PRCC)\n'
                  '— Controls for all other parameters simultaneously',
                  fontweight='bold', fontsize=11, pad=12)
    fig4.colorbar(im4, ax=ax4, label='PRCC', shrink=0.85)
    fig4.tight_layout()
    fig4.savefig(os.path.join(output_dir, 'fig4_prcc_heatmap.png'), bbox_inches='tight')
    plt.close(fig4)
    print("SA: Saved fig4_prcc_heatmap.png", flush=True)

    # ════════════════════════════════════════════════════════════
    # FIGURE 5 — Convergence of Pearson r (1×2 subplots)
    #   Bootstrapped CI band that narrows with increasing N
    # ════════════════════════════════════════════════════════════
    conv_pairs = [
        ('go_shop_threshold_low', 'avg_spend_low', 'Low-Income Spending'),
        ('go_shop_threshold_low', 'corner_share', 'Corner Store Share'),
    ]
    fig5, axes5 = plt.subplots(1, 2, figsize=(14, 5))
    sample_sizes = list(range(200, N + 1, 100))
    if N not in sample_sizes:
        sample_sizes.append(N)
    n_boot_conv = 500
    rng_conv = np.random.RandomState(42)

    for ax, (cparam, coutput, olabel) in zip(axes5, conv_pairs):
        if cparam not in done.columns or coutput not in done.columns:
            ax.set_visible(False)
            continue
        x_full = done[cparam].values
        y_full = done[coutput].values

        r_trace, ci_lo_trace, ci_hi_trace = [], [], []
        for ss in sample_sizes:
            xs, ys = x_full[:ss], y_full[:ss]
            r, _ = sp_stats.pearsonr(xs, ys)
            r_trace.append(r)
            boot_r = np.empty(n_boot_conv)
            for b in range(n_boot_conv):
                idx = rng_conv.randint(0, ss, ss)
                boot_r[b] = np.corrcoef(xs[idx], ys[idx])[0, 1]
            ci_lo_trace.append(np.nanpercentile(boot_r, 2.5))
            ci_hi_trace.append(np.nanpercentile(boot_r, 97.5))

        final_r = r_trace[-1]
        r_trace = np.array(r_trace)
        ci_lo_trace = np.array(ci_lo_trace)
        ci_hi_trace = np.array(ci_hi_trace)

        ax.fill_between(sample_sizes, ci_lo_trace, ci_hi_trace,
                        color='#4A90D9', alpha=0.18, linewidth=0)
        ax.plot(sample_sizes, r_trace, color='#1F4E79', linewidth=2.2, zorder=3)
        ax.axhline(y=final_r, color='#888888', linestyle='--', linewidth=1, alpha=0.7,
                   label=f'Final r = {final_r:.3f}')
        ax.legend(loc='upper right', fontsize=9, framealpha=0.9,
                  edgecolor='#cccccc', fancybox=True)
        ax.set_xlabel('Number of Simulation Runs', fontsize=10)
        ax.set_ylabel('Pearson r', fontsize=10)
        pl = _PARAM_LABELS.get(cparam, cparam).split('—')[0].strip()
        ax.set_title(f'Convergence: {pl} → {olabel}\n(demonstrates result stability)',
                     fontweight='bold', fontsize=10)
        ax.tick_params(labelsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    fig5.tight_layout()
    fig5.savefig(os.path.join(output_dir, 'fig5_convergence.png'), bbox_inches='tight')
    plt.close(fig5)
    print("SA: Saved fig5_convergence.png", flush=True)

    print(f"SA: All 5 dissertation figures saved to {output_dir}/", flush=True)
    return pearson_df, src_df, prcc_df


# ═══════════════════════════════════════════════════════════════
# STANDALONE EXECUTION
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    raw_df, tidy_df, indices_dict = load_latest_sa_results()
    if raw_df is None or raw_df.empty:
        print("No SA results found. Run sensitivity analysis from the dashboard first.")
        sys.exit(1)

    print(f"Loaded {len(raw_df)} rows from latest SA results.", flush=True)
    output_dir = _SA_DIR
    generate_dissertation_figures(raw_df, indices_dict, output_dir)
    print("Done.", flush=True)