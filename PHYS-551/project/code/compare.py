"""
PHYS 551 — Monte Carlo Methods Project
Naive vs Importance Sampling — comparison figures and variance-reduction table.

Reads the CSVs written by naive.py and importance_sampling.py and produces, for
the report:
  output/ep_curve.png          exceedance curve P(affected >= X), both methods
  output/convergence.png       running estimate of the rarest bucket vs N
  output/variance_reduction.csv per-threshold SE comparison + variance reduction
Run naive.py and importance_sampling.py first.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from naive import OUTPUT_DIR, CONVERGENCE_THRESHOLD
from importance_sampling import SAMPLES_PER_THETA

NAIVE_N = 100_000   # must match the naive run that produced the CSVs


def _load():
    naive = pd.read_csv(os.path.join(OUTPUT_DIR, "naive_population_impact.csv"))
    is_ep = pd.read_csv(os.path.join(OUTPUT_DIR, "is_population_impact.csv"))
    return naive, is_ep


def ep_curve(naive, is_ep):
    fig, ax = plt.subplots(figsize=(9, 6))

    # IS: full curve with CI band
    m = is_ep["Exceedance_Probability"] > 0
    x = is_ep["Threshold_People"][m] / 1e6
    p = is_ep["Exceedance_Probability"][m]
    se = is_ep["SE"][m]
    ax.plot(x, p, "-o", color="#c0392b", lw=2, ms=6, label="Importance Sampling", zorder=3)
    ax.fill_between(x, np.maximum(p - 1.96 * se, 1e-12), p + 1.96 * se,
                    color="#c0392b", alpha=0.2, zorder=2)

    # Naive: points where it actually observed hits
    seen = naive["Hits"] > 0
    ax.errorbar(naive["Threshold_People"][seen] / 1e6,
                naive["Exceedance_Probability"][seen],
                yerr=1.96 * naive["SE"][seen],
                fmt="s", color="#2c3e50", ms=6, capsize=3,
                label=f"Naive MC (N={NAIVE_N:,})", zorder=4)

    # Naive: 0-hit thresholds -> rule-of-three upper bound, drawn as open arrows
    blind = naive["Hits"] == 0
    for t in naive["Threshold_People"][blind]:
        ub = 3.0 / NAIVE_N
        ax.annotate("", xy=(t / 1e6, ub * 0.25), xytext=(t / 1e6, ub),
                    arrowprops=dict(arrowstyle="->", color="#7f8c8d"))
        ax.scatter([t / 1e6], [ub], marker="v", facecolors="none",
                   edgecolors="#7f8c8d", s=70, zorder=4)
        ax.annotate("naive blind\n(0 hits)", (t / 1e6, ub), color="#7f8c8d",
                    fontsize=9, ha="center", va="bottom", xytext=(0, 8),
                    textcoords="offset points")

    ax.set_yscale("log")
    ax.set_xlabel("People without power  X  (millions)", fontsize=12)
    ax.set_ylabel("Exceedance probability  P(affected ≥ X)  per day", fontsize=12)
    ax.set_title("Istanbul cascading-blackout exceedance curve\n"
                 "Naive Monte Carlo vs Importance Sampling", fontsize=13, fontweight="bold")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(fontsize=11, loc="lower left")
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "ep_curve.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"✓ {os.path.relpath(path)}")


def convergence():
    nv = pd.read_csv(os.path.join(OUTPUT_DIR, "naive_convergence.csv"))
    iss = pd.read_csv(os.path.join(OUTPUT_DIR, "is_convergence.csv"))

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(iss["n"], iss["estimate"], color="#c0392b", lw=2, label="Importance Sampling")
    ax.fill_between(iss["n"], np.maximum(iss["estimate"] - iss["ci95"], 1e-12),
                    iss["estimate"] + iss["ci95"], color="#c0392b", alpha=0.2)
    ax.plot(nv["n"], nv["estimate"], color="#2c3e50", lw=2, label="Naive MC")
    ax.fill_between(nv["n"], np.maximum(nv["estimate"] - nv["ci95"], 1e-12),
                    nv["estimate"] + nv["ci95"], color="#2c3e50", alpha=0.15)

    final_is = iss["estimate"].iloc[-1]
    ax.axhline(final_is, color="#c0392b", ls="--", lw=1, alpha=0.6)
    ax.set_yscale("log")
    ax.set_xlabel("Number of simulated days  N", fontsize=12)
    ax.set_ylabel(f"Estimated P(affected ≥ {CONVERGENCE_THRESHOLD/1e6:.0f}M)", fontsize=12)
    ax.set_title(f"Convergence on the rarest bucket (≥ {CONVERGENCE_THRESHOLD/1e6:.0f}M people)\n"
                 "Naive stays at zero — it never observes the event", fontsize=13, fontweight="bold")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(fontsize=11)
    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "convergence.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"✓ {os.path.relpath(path)}")


def variance_table(naive, is_ep):
    rows = []
    for _, nr in naive.iterrows():
        t = nr["Threshold_People"]
        ir = is_ep[is_ep["Threshold_People"] == t].iloc[0]
        p_naive = nr["Exceedance_Probability"]
        # Per-sample variance of each estimator, evaluated at the best estimate of
        # the TRUE probability (the IS estimate). Using IS_P rather than the noisy
        # naive count is what makes the blind row (0 naive hits) comparable.
        p_true = ir["Exceedance_Probability"]
        var_naive_ps = p_true * (1 - p_true)                 # Bernoulli at true p
        var_is_ps = (ir["SE"] ** 2) * SAMPLES_PER_THETA      # SE^2 * N
        vr = (var_naive_ps / var_is_ps) if var_is_ps > 0 else np.nan
        rows.append({
            "Threshold_People": int(t),
            "Naive_P": p_naive,
            "Naive_hits": int(nr["Hits"]),
            "Naive_SE": nr["SE"],
            "IS_P": ir["Exceedance_Probability"],
            "IS_SE": ir["SE"],
            "IS_theta": ir["Theta_Used"],
            "Variance_Reduction_x": round(vr, 1) if np.isfinite(vr) else np.nan,
            "Naive_samples_per_event": int(round(1.0 / ir["Exceedance_Probability"]))
                if ir["Exceedance_Probability"] > 0 else np.nan,
            "Naive_blind": nr["Hits"] == 0,
        })
    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, "variance_reduction.csv")
    df.to_csv(path, index=False)
    print(f"✓ {os.path.relpath(path)}")

    print("\nVARIANCE REDUCTION (per-sample variance ratio, naive / IS)")
    print(f"{'>= people':>12}{'naive P':>12}{'IS P':>12}{'var.red.':>11}{'1 event /':>13}")
    print("-" * 60)
    for _, r in df.iterrows():
        np_str = f"{r['Naive_P']:.2e}" if r["Naive_hits"] > 0 else "BLIND"
        vr_str = f"{r['Variance_Reduction_x']:.0f}x" if np.isfinite(r["Variance_Reduction_x"]) else "--"
        ev = f"{int(r['Naive_samples_per_event']):,}" if np.isfinite(r["Naive_samples_per_event"]) else "--"
        print(f"{int(r['Threshold_People']):>12,}{np_str:>12}{r['IS_P']:>12.2e}{vr_str:>11}{ev:>13}")


if __name__ == "__main__":
    naive, is_ep = _load()
    ep_curve(naive, is_ep)
    convergence()
    variance_table(naive, is_ep)
    print("\nAll comparison artefacts written to", os.path.relpath(OUTPUT_DIR))
