"""
PHYS 551 — Monte Carlo Methods Project
Istanbul Power Grid Cascading Failure — IMPORTANCE SAMPLING.

The rare driver of a city-wide blackout is a large systemic demand surge S
(VOL_SYS). Crude Monte Carlo almost never draws a large S, so it cannot estimate
the tail. We instead sample S from a tilted proposal g (mean shifted up by theta
standard deviations) and reweight every draw by the 1-D likelihood ratio

        W = f(S)/g(S) = exp(-theta * z_s + theta^2 / 2),   z_s = (S-1)/VOL_SYS.

Only S is biased; the per-district noise eps_i and the cascade coin-flips are
drawn from their true distributions, so they need no reweighting. A small ladder
of theta values is run — each makes a different population-impact threshold
"typical" — and the exceedance curve is stitched from whichever run estimates
each threshold most precisely. This is a clean, low-dimensional tilt: the weight
spread grows like |theta|, not sqrt(38)*|theta|, so the ESS stays healthy.
"""

import os
import numpy as np
import pandas as pd

from city_config import ISTANBUL_ALL_LAND_NODES, ADJACENCY, GAMMA, VOL_SYS, VOL_IDIO
from cascade import simulate_cascade
from naive import EXCEEDANCE_THRESHOLDS, OUTPUT_DIR, CONVERGENCE_THRESHOLD

SEED = 42

# Tilt ladder (shift of the systemic surge S, in std units). Small theta resolves
# moderate events; large theta reaches the catastrophic tail.
THETA_LADDER = [2.0, 2.5, 3.0, 3.5, 4.0]
SAMPLES_PER_THETA = 80_000

# theta used for the per-district heat-map estimate (moderate: good ESS, still
# exercises every realistically-failing district).
DISTRICT_THETA = 3.5

# theta whose tilt best targets the rarest (convergence-demo) threshold.
CONV_THETA = 3.0


def run_one_theta(theta, n_samples, names, mu, pop, K, track_threshold=None):
    """One tilted run. Returns weighted exceedance estimates + per-district + ESS.

    If track_threshold is given, also records a running-estimate trace for that
    threshold (used for the convergence plot).
    """
    np.random.seed(SEED + int(round(theta * 100)))

    sum_w = 0.0
    sum_w2 = 0.0
    exc_w = {t: 0.0 for t in EXCEEDANCE_THRESHOLDS}
    exc_w2 = {t: 0.0 for t in EXCEEDANCE_THRESHOLDS}
    blackout_w = {n: 0.0 for n in names}

    conv_rows = []
    conv_checkpoints = set(np.unique(
        np.linspace(n_samples / 200, n_samples, 200).astype(int))) if track_threshold else set()
    tw = 0.0      # running weighted hits for the tracked threshold
    tw2 = 0.0

    half_t2 = 0.5 * theta * theta
    for i in range(n_samples):
        z_s = np.random.normal(theta, 1.0)          # S drawn from the tilted proposal
        S = 1.0 + VOL_SYS * z_s
        W = np.exp(-theta * z_s + half_t2)          # 1-D likelihood ratio f/g

        eps = np.random.normal(0.0, VOL_IDIO, size=K)
        loads = dict(zip(names, mu * (S + eps)))
        status = simulate_cascade(loads, ISTANBUL_ALL_LAND_NODES, ADJACENCY, GAMMA)

        affected = 0
        for j, n in enumerate(names):
            if status[n] == 0:
                blackout_w[n] += W
                affected += pop[j]

        sum_w += W
        sum_w2 += W * W
        for t in EXCEEDANCE_THRESHOLDS:
            if affected >= t:
                exc_w[t] += W
                exc_w2[t] += W * W

        if track_threshold is not None:
            if affected >= track_threshold:
                tw += W
                tw2 += W * W
            if (i + 1) in conv_checkpoints:
                n_so = i + 1
                m1 = tw / n_so
                m2 = tw2 / n_so
                se = np.sqrt(max(0.0, (m2 - m1 * m1) / n_so))
                conv_rows.append({"n": n_so, "estimate": m1, "ci95": 1.96 * se})

    ess = (sum_w ** 2) / sum_w2 if sum_w2 > 0 else 0.0

    ep = {}
    for t in EXCEEDANCE_THRESHOLDS:
        m1 = exc_w[t] / n_samples                   # = P_hat
        m2 = exc_w2[t] / n_samples
        var = max(0.0, (m2 - m1 * m1) / n_samples)  # Var of the IS estimator
        ep[t] = {"P": m1, "SE": np.sqrt(var), "hits_w": exc_w[t]}

    return {"theta": theta, "ess": ess, "n": n_samples, "ep": ep,
            "blackout_w": blackout_w, "conv": conv_rows}


def run_importance_sampling():
    print("=" * 80)
    print("IMPORTANCE SAMPLING — systemic-surge tilt (1-D)")
    print(f"VOL_SYS={VOL_SYS}  VOL_IDIO={VOL_IDIO}  ladder={THETA_LADDER}  "
          f"M/theta={SAMPLES_PER_THETA:,}")
    print("=" * 80)

    names = list(ISTANBUL_ALL_LAND_NODES.keys())
    mu = np.array([ISTANBUL_ALL_LAND_NODES[n]["initial_load"] for n in names])
    pop = np.array([ISTANBUL_ALL_LAND_NODES[n]["population"] for n in names])
    K = len(names)

    runs = []
    for theta in THETA_LADDER:
        # track the convergence trace on the run whose tilt best targets the
        # rarest (convergence-demo) threshold
        track = CONVERGENCE_THRESHOLD if abs(theta - CONV_THETA) < 1e-9 else None
        r = run_one_theta(theta, SAMPLES_PER_THETA, names, mu, pop, K,
                          track_threshold=track)
        print(f"  theta={theta:<4}  ESS={r['ess']:>9.1f} / {r['n']:,} "
              f"({100 * r['ess'] / r['n']:5.2f}%)")
        runs.append(r)

    # ---- stitch the exceedance curve: per threshold, take the most precise run
    #      (smallest SE) that actually observed the event ----
    ep_rows = []
    for t in EXCEEDANCE_THRESHOLDS:
        best = None
        for r in runs:
            e = r["ep"][t]
            if e["P"] > 0 and (best is None or e["SE"] < best["SE"]):
                best = {"P": e["P"], "SE": e["SE"], "theta": r["theta"],
                        "ess": r["ess"]}
        if best is None:                            # never observed at any tilt
            best = {"P": 0.0, "SE": 0.0, "theta": np.nan, "ess": np.nan}
        ep_rows.append({
            "Threshold_People": t,
            "Exceedance_Probability": best["P"],
            "SE": best["SE"],
            "CI_95": 1.96 * best["SE"] if best["P"] > 0 else np.nan,
            "Theta_Used": best["theta"],
            "ESS": best["ess"],
        })
    df_ep = pd.DataFrame(ep_rows)

    # ---- per-district blackout probabilities from the moderate-theta run ----
    dr = next(r for r in runs if abs(r["theta"] - DISTRICT_THETA) < 1e-9)
    rows = []
    for j, n in enumerate(names):
        p = dr["blackout_w"][n] / dr["n"]
        rows.append({
            "District": n,
            "Side": ISTANBUL_ALL_LAND_NODES[n]["side"],
            "Alpha": round(ISTANBUL_ALL_LAND_NODES[n]["alpha"], 4),
            "Population": int(pop[j]),
            "True_Blackout_Probability": p,
            "Expected_People_Affected": p * pop[j],
            "Theta_Used": DISTRICT_THETA,
        })
    df_dist = pd.DataFrame(rows).sort_values("True_Blackout_Probability",
                                             ascending=False)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_dist.to_csv(os.path.join(OUTPUT_DIR, "is_results.csv"), index=False)
    df_ep.to_csv(os.path.join(OUTPUT_DIR, "is_population_impact.csv"), index=False)

    cr = next(r for r in runs if abs(r["theta"] - CONV_THETA) < 1e-9)
    pd.DataFrame(cr["conv"]).to_csv(
        os.path.join(OUTPUT_DIR, "is_convergence.csv"), index=False)

    # ---- report ----
    print("\nPOPULATION EXCEEDANCE CURVE  P(affected >= X)   [Importance Sampling]")
    print(f"{'>= people':>12}{'probability':>16}{'± 95% CI':>14}{'theta':>8}")
    print("-" * 52)
    for _, r in df_ep.iterrows():
        p = r["Exceedance_Probability"]
        shown = f"{p:.3e}" if p > 0 else "not reached"
        ci = f"{r['CI_95']:.2e}" if p > 0 else "--"
        th = f"{r['Theta_Used']:.1f}" if p > 0 else "--"
        print(f"{int(r['Threshold_People']):>12,}{shown:>16}{ci:>14}{th:>8}")

    print(f"\nPer-district estimates written from theta={DISTRICT_THETA} run.")
    print("=" * 80)
    return df_dist, df_ep


if __name__ == "__main__":
    run_importance_sampling()
