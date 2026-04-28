"""

# PHYS 551: Advanced Monte Carlo Methods
# Homework 3 - Source Code
# Student: Omer Faruk Avci
# Instructor: Prof. Dr. Taylan Akdogan

"""
import numpy as np
from scipy import stats
from scipy.stats import skew, kurtosis


"""Problem 1: Offshore Wind & Hurricane Risk"""

N = 100_000
shift = 45 
u_star = 3.1817 # u*: used contraint for Phase 1
theta = 0.799 # Found analitically at the report
k = 4.982 # Found analitically at the report

def simulate_IS(k, theta):
    V = shift + np.random.gamma(k, theta, N)
    p_v = (V / 50) * np.exp(-(V**2) / 100)
    C_v = 10**5 * (V - 45)**3
    q_v = stats.gamma.pdf(V - shift, a=k, scale=theta)
    weighted_evals = C_v * (p_v / q_v)

    eal_est = np.mean(weighted_evals)
    score = np.var(weighted_evals, ddof = 1)

    return eal_est, score

# Stage 1: Geometric Baseline
# ============================================================
# PHASE 1: COARSE GRID SEARCH (mode constraint enforced)
# Search over theta, derive k from (k-1)*theta = u_star
# ============================================================

best_score_p1 = np.inf
best_k_p1     = None
best_theta_p1 = None

for theta_try in np.linspace(0.70, 1.20, 20):
    k_try = (u_star / theta_try) + 1

    scores = []
    for _ in range(3):
        _, score = simulate_IS(k_try, theta_try)
        scores.append(score)

    avg_score = np.mean(scores)
    mode      = (k_try - 1) * theta_try
    marker    = " <- best" if avg_score < best_score_p1 else ""
    print(f"{theta_try:>8.3f} {k_try:>8.4f} {mode:>8.4f} {avg_score:>15.6e}{marker}")

    if avg_score < best_score_p1:
        best_score_p1 = avg_score
        best_k_p1     = k_try
        best_theta_p1 = theta_try



# ============================================================
# PHASE 2: FINE CROSS SEARCH (mode constraint dropped)
# Expand around Phase 1 best with fine step sizes
# k step = 0.005, theta step = 0.005
# Boundaries chosen to include the known optimum region
# ============================================================

best_score_p2 = np.inf
best_k_p2     = None
best_theta_p2 = None

theta_min = round(best_theta_p1 - 0.05, 3)
theta_max = round(best_theta_p1 + 0.05, 3)
k_min     = round(best_k_p1 - 0.15, 3)
k_max     = round(best_k_p1 + 0.15, 3)

theta_range = np.arange(theta_min, theta_max + 0.001, 0.005)
k_range     = np.arange(k_min,     k_max     + 0.001, 0.005)


for theta_try in theta_range:
    for k_try in k_range:
        scores = []
        for _ in range(3):
            _, score = simulate_IS(k_try, theta_try)
            scores.append(score)

        avg_score = np.mean(scores)
        mode      = (k_try - 1) * theta_try
        marker    = " <- best" if avg_score < best_score_p2 else ""

        if marker or avg_score < best_score_p2 * 1.05:  # print only notable rows
            print(f"{theta_try:>8.3f} {k_try:>8.4f} {mode:>8.4f} "
                  f"{avg_score:>15.6e}{marker}")

        if avg_score < best_score_p2:
            best_score_p2 = avg_score
            best_k_p2     = k_try
            best_theta_p2 = theta_try


print("\n" + "="*80)
print(f"{'Optimization Stage':<25} | {'k':<8} | {'theta':<8} | {'Mode':<8} | {'Score':<15}")
print("-" * 80)

_, score = simulate_IS(k, theta)
# Stage 1: Geometric Baseline
print(f"{'Stage 1 (Geometric)':<25} | {k:<8.4f} | {theta:<8.4f} | {(k-1)*theta:<8.4f} | {score:>15.6e}")

# Phase 1: Coarse Grid Results
print(f"{'Phase 1 (Coarse Grid)':<25} | {best_k_p1:<8.4f} | {best_theta_p1:<8.4f} | {(best_k_p1-1)*best_theta_p1:<8.4f} | {best_score_p1:>15.6e}")

# Phase 2: Fine Cross Results (Best)
print(f"{'Phase 2 (Fine Cross)':<25} | {best_k_p2:<8.4f} | {best_theta_p2:<8.4f} | {(best_k_p2-1)*best_theta_p2:<8.4f} | {best_score_p2:>15.6e}")

print("="*80)
print(f"FINAL OPTIMUM: k = {best_k_p2:.4f}, theta = {best_theta_p2:.4f}")
print(f"FINAL ESTIMATED EAL: ${simulate_IS(best_k_p2, best_theta_p2)[0]:.6f}")
print(f"FINAL CONTEST SCORE: {best_score_p2:.6e}")