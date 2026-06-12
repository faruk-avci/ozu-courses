"""
PHYS 551 — Monte Carlo Methods Project
Where should we build new relief substations to minimise blackout impact?

We add NEW relief substations to the grid and re-run the Monte Carlo to measure
how many fewer people lose power. Each new station:
  * connects to up to MAX_CONNECTIONS districts (default 3),
  * takes over RELIEF_FRACTION of each connected district's demand, so those
    districts sit further below their breaker limit and trip far less often,
  * has a healthy average margin (STATION_ALPHA) and zero population of its own,
    and acts as a high-headroom sink that soaks up cascade spillover.

The objective is the EXPECTED daily population without power. We greedily pick
two placements (anchored on the highest-risk districts and their neighbours),
then report the before/after impact with a refreshed heat-map, an exceedance
curve, and the rare-tail probabilities estimated by Importance Sampling.

Run after importance_sampling.py.  Usage:  python station_placement.py
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cascade import simulate_cascade
from city_config import (ISTANBUL_ALL_LAND_NODES as BASE, ADJACENCY as BASE_ADJ,
                         GAMMA as BASE_GAMMA, VOL_SYS, VOL_IDIO)
from naive import EXCEEDANCE_THRESHOLDS, OUTPUT_DIR
from importance_sampling import THETA_LADDER, mis_run
from visualize_heatmap import draw_heatmap

# ---- new-station model parameters ("average values") ----
RELIEF_FRACTION = 0.30     # share of each connected district's demand the station takes
STATION_ALPHA   = 0.20     # healthy margin of the new station
MAX_CONNECTIONS = 3        # a station may connect to at most this many districts
GAMMA_STATION   = 1.0

EXPECTED_N      = 30_000   # naive samples for the expected-affected objective (search)
IS_SAMPLES      = 80_000   # IS samples per theta for the final before/after curves
SEED            = 7


# ----------------------------------------------------------------------------
# Grid construction
# ----------------------------------------------------------------------------
def make_grid(stations):
    """stations: list of (station_name, [connected district names]). Returns a grid."""
    nodes = {n: {"capacity": BASE[n]["capacity"], "alpha": BASE[n]["alpha"]} for n in BASE}
    adjacency = {n: list(BASE_ADJ[n]) for n in BASE}
    gamma = dict(BASE_GAMMA)
    mu = {n: BASE[n]["initial_load"] for n in BASE}
    scale = {n: 1.0 for n in BASE}
    pop = {n: BASE[n]["population"] for n in BASE}
    coords = {n: (BASE[n]["lon"], BASE[n]["lat"]) for n in BASE}

    for name, conns in stations:
        absorbed = 0.0
        for d in conns:
            absorbed += RELIEF_FRACTION * mu[d]          # demand handed to the station
            scale[d] *= (1.0 - RELIEF_FRACTION)          # district keeps less demand
        nodes[name] = {"capacity": absorbed * (1.0 + STATION_ALPHA), "alpha": STATION_ALPHA}
        mu[name] = absorbed
        scale[name] = 1.0
        pop[name] = 0
        gamma[name] = GAMMA_STATION
        adjacency[name] = list(conns)
        for d in conns:
            adjacency[d] = adjacency[d] + [name]
        coords[name] = (float(np.mean([BASE[d]["lon"] for d in conns])),
                        float(np.mean([BASE[d]["lat"] for d in conns])))

    names = list(nodes)
    return {
        "names": names, "nodes": nodes, "adjacency": adjacency, "gamma": gamma,
        "mu": np.array([mu[n] for n in names]),
        "scale": np.array([scale[n] for n in names]),
        "pop": np.array([pop[n] for n in names]),
        "coords": coords,
    }


def _sample_loads(grid, S, eps):
    return dict(zip(grid["names"], grid["mu"] * grid["scale"] * (S + eps)))


# ----------------------------------------------------------------------------
# Evaluators
# ----------------------------------------------------------------------------
def eval_naive(grid, n=EXPECTED_N, seed=SEED):
    """Returns (expected_affected_per_day, {district: blackout_prob})."""
    np.random.seed(seed)
    names = grid["names"]
    pop = grid["pop"]
    K = len(names)
    total_affected = 0.0
    counts = {nm: 0 for nm in names}
    for _ in range(n):
        S = np.random.normal(1.0, VOL_SYS)
        eps = np.random.normal(0.0, VOL_IDIO, size=K)
        status = simulate_cascade(_sample_loads(grid, S, eps),
                                  grid["nodes"], grid["adjacency"], grid["gamma"])
        affected = 0
        for j, nm in enumerate(names):
            if status[nm] == 0:
                counts[nm] += 1
                affected += pop[j]
        total_affected += affected
    exp_affected = total_affected / n
    pdist = {nm: counts[nm] / n for j, nm in enumerate(names) if pop[j] > 0}
    return exp_affected, pdist


def eval_is_ep(grid, n=IS_SAMPLES):
    """Multiple-importance-sampling exceedance curve for the grid (same estimator
    as importance_sampling.py). Returns {threshold: (P, SE)}."""
    res = mis_run(grid["names"], grid["mu"], grid["scale"], grid["pop"],
                  grid["nodes"], grid["adjacency"], grid["gamma"], n_per=n)
    return {t: (res["ep"][t]["P"], res["ep"][t]["SE"]) for t in EXCEEDANCE_THRESHOLDS}


# ----------------------------------------------------------------------------
# Greedy placement
# ----------------------------------------------------------------------------
def candidate_connection_sets(risk, used, adjacency, n_seeds=6):
    """Build candidate district-sets: a high-risk seed + its highest-risk neighbours."""
    seeds = [d for d in sorted(risk, key=risk.get, reverse=True) if d not in used][:n_seeds]
    cands = []
    seen = set()
    for seed in seeds:
        neigh = [nb for nb in adjacency[seed]
                 if nb in BASE and nb not in used and nb != seed]
        neigh.sort(key=lambda d: risk.get(d, 0), reverse=True)
        conns = tuple([seed] + neigh[:MAX_CONNECTIONS - 1])
        key = frozenset(conns)
        if key not in seen:
            seen.add(key)
            cands.append(conns)
    return cands


def greedy_place(n_stations=2):
    base_grid = make_grid([])
    E0, pdist0 = eval_naive(base_grid)
    risk = {d: pdist0[d] * BASE[d]["population"] for d in BASE}
    print(f"Baseline expected daily affected: {E0:,.0f} people\n")

    chosen = []
    used = set()
    cur_E = E0
    for k in range(n_stations):
        cands = candidate_connection_sets(risk, used, BASE_ADJ)
        print(f"--- Selecting station {k + 1} ({len(cands)} candidates) ---")
        best = None
        for conns in cands:
            trial = chosen + [(f"NEW-{k + 1}", conns)]
            E, _ = eval_naive(make_grid(trial))
            print(f"   connect {', '.join(conns):<45} -> {E:,.0f} affected")
            if best is None or E < best[0]:
                best = (E, conns)
        chosen.append((f"NEW-{k + 1}", best[1]))
        used.update(best[1])
        print(f"  => station {k + 1} at [{', '.join(best[1])}]  ({best[0]:,.0f} affected)\n")
        cur_E = best[0]

    return base_grid, E0, chosen, cur_E


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------
def ep_overlay(base_ep, new_ep, path):
    fig, ax = plt.subplots(figsize=(9, 6))
    for ep, color, label in [(base_ep, "#2c3e50", "Baseline grid"),
                             (new_ep, "#27ae60", "With 2 relief stations")]:
        xs, ps, ses = [], [], []
        for t in EXCEEDANCE_THRESHOLDS:
            P, SE = ep[t]
            if P > 0:
                xs.append(t / 1e6); ps.append(P); ses.append(SE)
        xs, ps, ses = np.array(xs), np.array(ps), np.array(ses)
        ax.plot(xs, ps, "-o", color=color, lw=2, label=label)
        ax.fill_between(xs, np.maximum(ps - 1.96 * ses, 1e-12), ps + 1.96 * ses,
                        color=color, alpha=0.2)
    ax.set_yscale("log")
    ax.set_xlabel("People without power  X  (millions)", fontsize=12)
    ax.set_ylabel("Exceedance probability  P(affected ≥ X)  per day", fontsize=12)
    ax.set_title("Effect of two new relief substations on blackout risk",
                 fontsize=13, fontweight="bold")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"✓ {os.path.relpath(path)}")


def main():
    base_grid, E0, chosen, E_final = greedy_place(n_stations=2)
    new_grid = make_grid(chosen)

    # higher-resolution final estimates
    E_base, pdist_base = eval_naive(base_grid, n=100_000)
    E_new, pdist_new = eval_naive(new_grid, n=100_000)
    reduction = 100 * (E_base - E_new) / E_base
    baseline_vmax = max(pdist_base.values())   # shared colour scale for before/after

    print("=" * 70)
    print("RESULT — TWO NEW RELIEF SUBSTATIONS")
    for name, conns in chosen:
        print(f"  {name}: serves {', '.join(conns)}")
    print(f"\n  Expected daily affected  : {E_base:,.0f}  ->  {E_new:,.0f} people")
    print(f"  Reduction                : {reduction:.1f}%")
    print("=" * 70)

    print("\nEstimating rare-tail effect with Importance Sampling...")
    base_ep = eval_is_ep(base_grid)
    new_ep = eval_is_ep(new_grid)

    station_names = [name for name, _ in chosen]

    # heat-map of the improved grid (per-district probs from a moderate-theta run)
    # reuse the naive per-district probs at higher resolution for the map colours
    prob_map = pdist_new
    coords = {n: new_grid["coords"][n] for n in new_grid["names"]}
    pop = {new_grid["names"][i]: int(new_grid["pop"][i]) for i in range(len(new_grid["names"]))}
    title = (f"Istanbul Grid Risk AFTER 2 Relief Stations\n"
             f"Expected Daily Affected: {E_new:,.0f} (was {E_base:,.0f}, -{reduction:.0f}%)")
    draw_heatmap(prob_map, coords, pop, new_grid["adjacency"],
                 os.path.join(OUTPUT_DIR, "heatmap_with_stations.png"),
                 title, stations=station_names, vmax=baseline_vmax)

    ep_overlay(base_ep, new_ep, os.path.join(OUTPUT_DIR, "placement_ep_curve.png"))

    # summary CSV
    rows = []
    for t in EXCEEDANCE_THRESHOLDS:
        rows.append({
            "Threshold_People": t,
            "Baseline_P": base_ep[t][0],
            "WithStations_P": new_ep[t][0],
            "Reduction_factor": (base_ep[t][0] / new_ep[t][0])
                if new_ep[t][0] > 0 else np.nan,
        })
    df = pd.DataFrame(rows)
    df.loc[len(df)] = {"Threshold_People": "EXPECTED_AFFECTED",
                       "Baseline_P": E_base, "WithStations_P": E_new,
                       "Reduction_factor": E_base / E_new if E_new > 0 else np.nan}
    df.to_csv(os.path.join(OUTPUT_DIR, "placement_summary.csv"), index=False)
    print(f"✓ {os.path.relpath(os.path.join(OUTPUT_DIR, 'placement_summary.csv'))}")

    print("\nTAIL EFFECT (Importance Sampling):")
    print(f"{'>= people':>12}{'baseline P':>14}{'with stations':>16}{'x safer':>10}")
    print("-" * 52)
    for t in EXCEEDANCE_THRESHOLDS:
        bp, npb = base_ep[t][0], new_ep[t][0]
        fac = f"{bp / npb:.1f}x" if npb > 0 and bp > 0 else "--"
        print(f"{t:>12,}{bp:>14.2e}{npb:>16.2e}{fac:>10}")


if __name__ == "__main__":
    main()
