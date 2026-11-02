# Food-access ABM — Health Zone 1, Jacksonville, FL

Code, input data and results for the manuscript

> Shahriari-Mehr, G., von Meding, J., Watson, M., & Tepe, E. *A literature-calibrated
> spatial agent-based model for comparing food-access interventions in a data-scarce
> urban food desert: a case study of Health Zone 1, Jacksonville, FL.* Submitted to
> *Food Security*.

The release tagged **`v1.0-foodsecurity`** is the exact build reported in the
manuscript (Tables 3–5, Figs. 3–8). Interactive dashboard:
**https://goshtasb-food-access-abm-jacksonville.hf.space/** (live simulation at `/`,
manuscript results at `/results/`).

## What the model does

A spatial agent-based model (Mesa / Mesa-Geo) of 500 households in Health Zone 1
(HZ1), Jacksonville, FL, simulated for 365 days. Each household decides each day
whether to shop (a go-shop threshold in days since its last trip, by income group)
and, if it shops, chooses a provider with a discrete-choice utility over distance,
price relative to budget, quality/variety and convenience, within a travel radius
of 5.5 km (vehicle) or 0.8 km (car-free). The model compares a baseline with four
interventions:

| Scenario | Intervention |
|---|---|
| Baseline | 6 grocery stores, 11 corner stores, 19 existing food pantries, market-rate grocery delivery |
| S1 North Grocery | one new grocery store in the north of HZ1 |
| S2 Hub + Corner | one community food hub and four new corner stores, sited by a maximal-covering rule (Church & ReVelle 1974) |
| S3 Mobile Pantries | two additional mobile pantries on fixed stops |
| S4 Delivery | subsidised delivery (free for low-income, half price for medium-income households) |

**Calibration.** The model is calibrated against published literature targets
(pattern-oriented modelling); no household survey data were used. Three targets are
scored — annual food-at-home spending of low-income ($3,707) and medium-income
($4,672) households and annual food-insecurity prevalence (33.0%); the corner-store
trip share is reported but not scored.

## Software

| | Version |
|---|---|
| Python | 3.10.16 |
| Mesa | 3.0.3 |
| Mesa-Geo | 0.9.1 |
| all other packages | pinned in [`requirements-lock.txt`](requirements-lock.txt) |

```bash
git clone https://github.com/GoshtasbSh/food-access-abm-jacksonville.git
cd food-access-abm-jacksonville
git checkout v1.0-foodsecurity

conda create -n foodabm python=3.10.16
conda activate foodabm
pip install -r requirements-lock.txt
```

All inputs ship with the repository; no external data or environment variables are
needed.

## Files that define the manuscript build

| File | Content |
|---|---|
| [`PAPER_PARAMS_FoodSecurity.json`](PAPER_PARAMS_FoodSecurity.json) | **The calibrated parameters (manuscript Table 2)** and the Table 3 calibration record: α = 2.0, β = 0.5, γ = 0.6, δ = 0.4 (fixed); go-shop thresholds 4 / 5 / 14 days (low / medium / high income; high fixed). Loaded by default (`enhanced_mesa_geo_model.py`); `GEOMESA_CALIBRATED_PARAMS=<file>` overrides it. |
| [`store_FINAL_6g_11c.csv`](store_FINAL_6g_11c.csv) | **Baseline store inventory**: 6 grocery stores and 11 corner stores (see below). Loaded by default (`config.py`); `GEOMESA_SUPERMARKET_CSV=<file>` overrides it. |
| [`baseline_scenario.py`](baseline_scenario.py) | the 19 existing HZ1 food pantries and the baseline delivery service |
| [`journal_seeds.txt`](journal_seeds.txt) | the 50 random seeds used for every scenario run |
| [`census_data/`](census_data/), [`hz1_household_data_CORRECTED.csv`](hz1_household_data_CORRECTED.csv), [`health_zone_1_census_tracts.txt`](health_zone_1_census_tracts.txt) | ACS 2023 inputs for the synthetic household population |
| [`geodata/HealthZones1and4/`](geodata/HealthZones1and4/) | Health Zone 1 boundary |

Fixed model inputs (in `SimulationConfig`, `enhanced_mesa_geo_model.py`): weekly food
budgets $75 / $90 / $327 (low / medium / high income); travel radius 5.5 km with a
vehicle and 0.8 km without; quality 0.80 for grocery stores and 0.30 for corner
stores; price level 1.0 for grocery stores and the food hub and 1.16 for corner stores.

**Store inventory.** The 17 outlets are taken from the USDA SNAP Retailer Locator and
clipped to HZ1. The 6 grocery stores are the supermarkets in the list; small-format
outlets were kept as corner stores only where Google Maps classifies them as grocery
stores, so dollar stores, gas stations and other non-grocery retailers are excluded.
`SourceStoreType` is the USDA store type; `ProviderType` is the type used in the model.

## Reproducing the manuscript

Run every command from the repository root. Run times are for a desktop with 8 cores.

### Table 3 — calibration (five seeds)

```bash
python reproduce_table3.py
```

Runs the baseline with `PAPER_PARAMS_FoodSecurity.json` for seeds 0–4 (500
households, 365 days; about 4 minutes in parallel) and prints Table 3: low-income
spending $3,618.72 ± 57.70 (MAPE 2.38%), medium-income $4,644.66 ± 115.68 (0.59%),
annual food-insecurity prevalence 0.328 ± 0.017 (0.61%), corner-store trip share
0.242 ± 0.018; aggregate MAPE 2.93% averaged per seed and 1.19% on the five-seed
means. It also compares each seed with the archived run in
[`calibration/table3_calibration_seeds.csv`](calibration/table3_calibration_seeds.csv)
(difference 0).

### Tables 4–5 and Figs. 3–7 — scenario comparison (50 seeds)

```bash
python run_journal_50seeds.py --seeds-file journal_seeds.txt \
    --households 500 --days 365 --out results/my_rerun
python summarize_results.py --results results/my_rerun
```

The first command runs the five scenarios for the 50 seeds (250 runs, about 1.5 hours
with 7 workers; `--workers N` sets the number of processes, and an interrupted run
resumes when the same command is repeated). The second prints Table 4 (final-day
means ± SD and cumulative burden) and Table 5 (Cohen's d, Welch p, Holm correction).
`python summarize_results.py` without arguments summarises the shipped manuscript
results:

| | Food insecurity | Travel (km) | Spatial equity | Corner share | Delivery share | Cumulative burden |
|---|---|---|---|---|---|---|
| Baseline | 0.166 | 2.275 | 0.471 | 0.230 | 0.027 | 0.1544 |
| S1 North Grocery | 0.162 | 2.176 | 0.467 | 0.229 | 0.027 | 0.1520 |
| S2 Hub + Corner | 0.128 | 2.124 | 0.456 | 0.259 | 0.020 | 0.1153 |
| S3 Mobile Pantries | 0.163 | 2.260 | 0.464 | 0.229 | 0.027 | 0.1543 |
| S4 Delivery | 0.140 | 2.205 | 0.471 | 0.209 | 0.092 | 0.1303 |

Runs are deterministic: the same seed gives bit-identical output. Each per-seed file
records the full configuration of its run, so the parameters behind every number can
be checked.

### Fig. 8 — Sobol sensitivity analysis

```bash
python run_sobol_paper.py --workers 7
```

Saltelli design, N = 256 base sample, 7 parameters, 4,096 runs of the baseline (500
households, 365 days), ±30% around the calibrated values, bootstrap 95% CIs (about
22 hours with 7 workers; resumable). Indices are written for the final-day
food-insecurity rate (Fig. 8: total-order θ_med 0.630, θ_low 0.588, θ_high 0.314,
α 0.151, δ 0.087, γ 0.081, β 0.010), annual prevalence and corner-store share. The
output of the manuscript run is shipped as
[`sobol_indices_paper.json`](sobol_indices_paper.json), with the raw model outputs of
all 4,096 runs in [`sensitivity/sobol_Y_500hh.csv`](sensitivity/sobol_Y_500hh.csv). To
recompute the indices from those outputs in a few seconds:

```bash
python run_sobol_paper.py --out sensitivity --analyze-only
```

The point estimates are reproduced exactly; the bootstrap confidence intervals vary
slightly between runs because SALib's bootstrap is not seeded.

## Where results are

| Path | Content |
|---|---|
| `results/journal_results_50seeds_paper/` | the 250 per-seed result files behind Tables 4–5 and Figs. 3–7, plus one summary file per scenario |
| `calibration/table3_calibration_seeds.csv` | the five calibration runs behind Table 3 |
| `sobol_indices_paper.json`, `sensitivity/` | Fig. 8 indices and raw outputs |
| `results/my_rerun/`, `results/sobol_rerun/` | default locations for your own reruns |
| `archive/` | superseded development builds, kept for the record; not used by the code |

## Dashboards

```bash
python abm_dashboard_dissertation.py      # manuscript results   -> http://127.0.0.1:8065
python live_enhanced_mesa_dash.py         # live simulation      -> http://127.0.0.1:8050
python app.py                             # both, as on Hugging Face -> http://127.0.0.1:10000
```

The results dashboard reads `results/journal_results_50seeds_paper/` and
`sobol_indices_paper.json`. The live dashboard runs new simulations with the
manuscript parameters as defaults (500 households, 365 days, calibrated choice
model, S1 in the north, S2 with a 200-capacity hub and four corner stores); a full
365-day run takes a few minutes per scenario. The same app runs on the Hugging Face
Space above, built from this repository's `Dockerfile`.

## Repository layout

```
enhanced_mesa_geo_model.py   model core: SimulationConfig, agents, choice model
baseline_scenario.py         baseline (stores, pantries, delivery)
enhanced_scenario_1..4.py    the four interventions
config.py                    input paths (defaults point at files in this repository)
run_journal_50seeds.py       multi-seed scenario runner (Tables 4-5)
summarize_results.py         Tables 4-5 from a results folder
reproduce_table3.py          Table 3
run_sobol_paper.py           Fig. 8
sensitivity_analysis_sobol.py  Sobol helpers and the live dashboard's quick sensitivity tab
abm_dashboard_dissertation.py  results dashboard
live_enhanced_mesa_dash.py   live dashboard (+ dashboard_parameters.py, dashboard_config_builder.py)
app.py, Dockerfile           combined app for the Hugging Face Space
```

## Citation and license

Please cite the manuscript above; citation metadata for this software is in
[`CITATION.cff`](CITATION.cff). The code is released under the MIT License
([`LICENSE`](LICENSE)).
