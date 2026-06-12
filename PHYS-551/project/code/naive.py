"""
PHYS 551 — Monte Carlo Methods Project
Istanbul Power Grid Cascading Failure — NAIVE (crude) Monte Carlo baseline.

Samples the true demand model directly (no biasing) and measures how often a
cascade blacks out at least X people. This is the honest baseline: it nails the
common, small events but is blind to the rare city-wide catastrophes, which is
exactly what Importance Sampling is for. Run importance_sampling.py for those.
"""

import os
import sys
import numpy as np
import pandas as pd

from city_config import ISTANBUL_ALL_LAND_NODES, ADJACENCY, GAMMA, VOL_SYS, VOL_IDIO
from cascade import simulate_cascade

SEED = 42

# Exceedance thresholds for the population-impact (EP) curve: P(people affected >= t).
# Shared by importance_sampling.py and compare.py (imported from here).
EXCEEDANCE_THRESHOLDS = [
    100_000, 250_000, 500_000, 1_000_000, 2_000_000,
    3_000_000, 4_000_000, 6_000_000, 8_000_000,
]

# Bucket the convergence demo tracks: the rarest one, which naive cannot resolve
# (it sees ~0 hits) but importance sampling estimates cleanly.
CONVERGENCE_THRESHOLD = 8_000_000

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))


def _wald_ci(p, n):
    """95% half-width; for p=0 fall back to the rule-of-three upper bound (3/n)."""
    if p <= 0:
        return 3.0 / n
    return 1.96 * np.sqrt(p * (1 - p) / n)


def run_naive_monte_carlo(total_simulations=100_000):
    print("=" * 80)
    print("NAIVE (CRUDE) MONTE CARLO — direct sampling of the true demand model")
    print(f"Iterations: {total_simulations:,}   VOL_SYS={VOL_SYS}  VOL_IDIO={VOL_IDIO}")
    print("=" * 80)

    names = list(ISTANBUL_ALL_LAND_NODES.keys())
    mu = np.array([ISTANBUL_ALL_LAND_NODES[n]["initial_load"] for n in names])
    pop = np.array([ISTANBUL_ALL_LAND_NODES[n]["population"] for n in names])
    K = len(names)

    np.random.seed(SEED)

    blackout_counts = {n: 0 for n in names}
    exceed_counts = {t: 0 for t in EXCEEDANCE_THRESHOLDS}

    # convergence trace for one rare threshold
    conv_checkpoints = np.unique(np.linspace(total_simulations / 200,
                                             total_simulations, 200).astype(int))
    conv_running = 0
    conv_rows = []
    cp_idx = 0

    for i in range(total_simulations):
        S = np.random.normal(1.0, VOL_SYS)                 # city-wide surge
        eps = np.random.normal(0.0, VOL_IDIO, size=K)      # per-district noise
        loads = dict(zip(names, mu * (S + eps)))

        status = simulate_cascade(loads, ISTANBUL_ALL_LAND_NODES, ADJACENCY, GAMMA)

        affected = 0
        for j, n in enumerate(names):
            if status[n] == 0:
                blackout_counts[n] += 1
                affected += pop[j]

        for t in EXCEEDANCE_THRESHOLDS:
            if affected >= t:
                exceed_counts[t] += 1

        if affected >= CONVERGENCE_THRESHOLD:
            conv_running += 1
        if cp_idx < len(conv_checkpoints) and (i + 1) == conv_checkpoints[cp_idx]:
            n_so_far = i + 1
            p = conv_running / n_so_far
            conv_rows.append({"n": n_so_far, "estimate": p, "ci95": _wald_ci(p, n_so_far)})
            cp_idx += 1

        if (i + 1) % 25_000 == 0:
            print(f"  -> {i + 1:,} / {total_simulations:,} days simulated")

    # ---- per-district results ----
    rows = []
    for j, n in enumerate(names):
        p = blackout_counts[n] / total_simulations
        rows.append({
            "District": n,
            "Side": ISTANBUL_ALL_LAND_NODES[n]["side"],
            "Population": int(pop[j]),
            "Alpha": round(ISTANBUL_ALL_LAND_NODES[n]["alpha"], 4),
            "Blackout_Probability": p,
            "SE": np.sqrt(p * (1 - p) / total_simulations),
            "CI_95": _wald_ci(p, total_simulations),
        })
    df_dist = pd.DataFrame(rows).sort_values("Blackout_Probability", ascending=False)

    # ---- population exceedance (EP) curve ----
    ep_rows = []
    for t in EXCEEDANCE_THRESHOLDS:
        c = exceed_counts[t]
        p = c / total_simulations
        ep_rows.append({
            "Threshold_People": t,
            "Exceedance_Probability": p,
            "Hits": c,
            "SE": np.sqrt(p * (1 - p) / total_simulations),
            "CI_95": _wald_ci(p, total_simulations),
        })
    df_ep = pd.DataFrame(ep_rows)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_dist.to_csv(os.path.join(OUTPUT_DIR, "naive_results.csv"), index=False)
    df_ep.to_csv(os.path.join(OUTPUT_DIR, "naive_population_impact.csv"), index=False)
    pd.DataFrame(conv_rows).to_csv(
        os.path.join(OUTPUT_DIR, "naive_convergence.csv"), index=False)

    # ---- report ----
    print("\nTOP-10 DISTRICTS BY BLACKOUT PROBABILITY")
    print(f"{'District':<16}{'Side':<8}{'P(blackout)':>14}{'± 95% CI':>14}")
    print("-" * 52)
    for _, r in df_dist.head(10).iterrows():
        print(f"{r['District']:<16}{r['Side']:<8}{r['Blackout_Probability']:>14.3e}"
              f"{r['CI_95']:>14.3e}")

    print("\nPOPULATION EXCEEDANCE CURVE  P(affected >= X)")
    print(f"{'>= people':>12}{'hits':>8}{'probability':>16}{'± 95% CI':>14}")
    print("-" * 52)
    for _, r in df_ep.iterrows():
        p = r["Exceedance_Probability"]
        shown = f"{p:.3e}" if p > 0 else "0 (none seen)"
        print(f"{int(r['Threshold_People']):>12,}{int(r['Hits']):>8}{shown:>16}"
              f"{r['CI_95']:>14.3e}")

    print("\nNote: empty top buckets are the rare-event blind spot — see "
          "importance_sampling.py.")
    print("=" * 80)
    return df_dist, df_ep


if __name__ == "__main__":
    n = int(float(sys.argv[1])) if len(sys.argv) > 1 else 100_000
    run_naive_monte_carlo(total_simulations=n)
