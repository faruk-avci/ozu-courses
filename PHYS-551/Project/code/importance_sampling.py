"""
PHYS 551 — Monte Carlo Methods Project
Istanbul Power Grid Cascading Failure — IMPORTANCE SAMPLING.

The rare driver of a city-wide blackout is a large systemic demand surge S
(VOL_SYS). Crude Monte Carlo almost never draws a large S, so it cannot estimate
the tail. We instead sample S from tilted proposals g_l (mean shifted up by
theta_l standard deviations) and reweight.

A single tilt is only well matched to one part of the tail, so we run a *ladder*
of tilts and combine them with MULTIPLE IMPORTANCE SAMPLING (the balance
heuristic). Every draw — whichever tilt produced it — is weighted by

        w(S) = f(S) / gbar(S),   gbar(S) = (1/K) sum_l g_l(S),

where f is the true density and gbar is the equal-mixture of the K proposals.
All K*N draws are pooled into a single unbiased estimator
        P_hat(>=t) = (1/Ntot) sum 1{affected>=t} * w(S),
which avoids the selection bias of picking the "best" run per threshold and gives
one honest effective sample size for the whole pool. Only S is biased; the
per-district noise eps_i is drawn from its true distribution, and the cascade is
a deterministic function of the demand, so neither needs reweighting.
"""

import os
import numpy as np
import pandas as pd

from city_config import ISTANBUL_ALL_LAND_NODES, ADJACENCY, GAMMA, VOL_SYS, VOL_IDIO
from cascade import simulate_cascade
from naive import EXCEEDANCE_THRESHOLDS, OUTPUT_DIR, CONVERGENCE_THRESHOLD

SEED = 42

# Tilt ladder (shift of the systemic surge S, in std units): low tilts resolve
# moderate events, high tilts reach the rare tail. The ladder is combined by MIS.
THETA_LADDER = [2.0, 2.5, 3.0, 3.5, 4.0]
SAMPLES_PER_THETA = 80_000


def mis_weight(z, ladder):
    """Balance-heuristic MIS weight  w = K*phi(z) / sum_l phi(z - theta_l),
    where z = (S-1)/sigma_sys and phi is the standard normal density.
    Computed via log-sum-exp for numerical stability in the deep tail."""
    a0 = -0.5 * z * z
    others = -0.5 * (z - ladder) ** 2
    m = others.max()
    lse = m + np.log(np.exp(others - m).sum())
    return np.exp(np.log(len(ladder)) + a0 - lse)


def mis_run(names, mu, scale, pop, nodes, adjacency, gamma,
            ladder=THETA_LADDER, n_per=SAMPLES_PER_THETA, track_threshold=None):
    """Multiple-importance-sampling sweep. Pools K*n_per draws (round-robin across
    the ladder so a running estimate stays ~unbiased) into one estimator.

    Returns ep {t: {P, SE}}, per-name weighted blackout prob, pooled ESS, n_tot,
    and (if track_threshold given) a running-estimate trace for that threshold.
    """
    ladder_arr = np.asarray(ladder, dtype=float)
    K = len(names)
    n_tot = len(ladder) * n_per

    exc_w = {t: 0.0 for t in EXCEEDANCE_THRESHOLDS}
    exc_w2 = {t: 0.0 for t in EXCEEDANCE_THRESHOLDS}
    blackout_w = {n: 0.0 for n in names}
    sum_w = 0.0
    sum_w2 = 0.0

    conv_rows = []
    checkpoints = (set(np.unique(np.linspace(n_tot / 200, n_tot, 200).astype(int)))
                   if track_threshold is not None else set())
    tw = tw2 = 0.0
    seen = 0

    np.random.seed(SEED)
    for _ in range(n_per):                       # round-robin: one draw per tilt
        for theta in ladder:
            z = np.random.normal(theta, 1.0)
            S = 1.0 + VOL_SYS * z
            w = mis_weight(z, ladder_arr)

            eps = np.random.normal(0.0, VOL_IDIO, size=K)
            loads = dict(zip(names, mu * scale * (S + eps)))
            status = simulate_cascade(loads, nodes, adjacency, gamma)

            affected = 0
            for k, nm in enumerate(names):
                if status[nm] == 0:
                    blackout_w[nm] += w
                    affected += pop[k]

            sum_w += w
            sum_w2 += w * w
            for t in EXCEEDANCE_THRESHOLDS:
                if affected >= t:
                    exc_w[t] += w
                    exc_w2[t] += w * w

            seen += 1
            if track_threshold is not None:
                if affected >= track_threshold:
                    tw += w
                    tw2 += w * w
                if seen in checkpoints:
                    m1 = tw / seen
                    m2 = tw2 / seen
                    se = np.sqrt(max(0.0, (m2 - m1 * m1) / seen))
                    conv_rows.append({"n": seen, "estimate": m1, "ci95": 1.96 * se})

    ep = {}
    for t in EXCEEDANCE_THRESHOLDS:
        m1 = exc_w[t] / n_tot
        m2 = exc_w2[t] / n_tot
        ep[t] = {"P": m1, "SE": np.sqrt(max(0.0, (m2 - m1 * m1) / n_tot))}
    ess = (sum_w ** 2) / sum_w2 if sum_w2 > 0 else 0.0
    return {"ep": ep, "blackout_w": blackout_w, "ess": ess,
            "n_tot": n_tot, "conv": conv_rows}


def run_importance_sampling():
    print("=" * 80)
    print("IMPORTANCE SAMPLING — systemic-surge tilt, multiple importance sampling")
    print(f"VOL_SYS={VOL_SYS}  VOL_IDIO={VOL_IDIO}  ladder={THETA_LADDER}  "
          f"M/theta={SAMPLES_PER_THETA:,}")
    print("=" * 80)

    names = list(ISTANBUL_ALL_LAND_NODES.keys())
    mu = np.array([ISTANBUL_ALL_LAND_NODES[n]["initial_load"] for n in names])
    pop = np.array([ISTANBUL_ALL_LAND_NODES[n]["population"] for n in names])
    K = len(names)

    res = mis_run(names, mu, np.ones(K), pop,
                  ISTANBUL_ALL_LAND_NODES, ADJACENCY, GAMMA,
                  track_threshold=CONVERGENCE_THRESHOLD)
    n_tot = res["n_tot"]
    print(f"Pooled samples: {n_tot:,}   ESS = {res['ess']:.0f}  "
          f"({100 * res['ess'] / n_tot:.2f}%)")

    # ---- exceedance curve ----
    ep_rows = []
    for t in EXCEEDANCE_THRESHOLDS:
        P, SE = res["ep"][t]["P"], res["ep"][t]["SE"]
        ep_rows.append({
            "Threshold_People": t,
            "Exceedance_Probability": P,
            "SE": SE,
            "CI_95": 1.96 * SE if P > 0 else np.nan,
        })
    df_ep = pd.DataFrame(ep_rows)

    # ---- per-district blackout probabilities (from the same pooled estimator) ----
    rows = []
    for j, n in enumerate(names):
        p = res["blackout_w"][n] / n_tot
        rows.append({
            "District": n,
            "Side": ISTANBUL_ALL_LAND_NODES[n]["side"],
            "Alpha": round(ISTANBUL_ALL_LAND_NODES[n]["alpha"], 4),
            "Population": int(pop[j]),
            "True_Blackout_Probability": p,
            "Expected_People_Affected": p * pop[j],
        })
    df_dist = pd.DataFrame(rows).sort_values("True_Blackout_Probability",
                                             ascending=False)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_dist.to_csv(os.path.join(OUTPUT_DIR, "is_results.csv"), index=False)
    df_ep.to_csv(os.path.join(OUTPUT_DIR, "is_population_impact.csv"), index=False)
    pd.DataFrame(res["conv"]).to_csv(
        os.path.join(OUTPUT_DIR, "is_convergence.csv"), index=False)

    # ---- report ----
    print("\nPOPULATION EXCEEDANCE CURVE  P(affected >= X)   [MIS]")
    print(f"{'>= people':>12}{'probability':>16}{'± 95% CI':>14}")
    print("-" * 42)
    for _, r in df_ep.iterrows():
        p = r["Exceedance_Probability"]
        shown = f"{p:.3e}" if p > 0 else "not reached"
        ci = f"{r['CI_95']:.2e}" if p > 0 else "--"
        print(f"{int(r['Threshold_People']):>12,}{shown:>16}{ci:>14}")
    print("=" * 80)
    return df_dist, df_ep


if __name__ == "__main__":
    run_importance_sampling()
