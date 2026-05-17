"""

# PHYS 551: Advanced Monte Carlo Methods
# Homework 6 - Source Code
# Student: Omer Faruk Avci
# Instructor: Prof. Dr. Taylan Akdogan

"""
import pymc as pm
import numpy as np
import matplotlib.pyplot as plt
import arviz as az

# ============================================================
# DATA
# ============================================================
stress = np.array([400, 380, 350, 320, 290, 260, 230, 200, 180, 160], dtype=float)
cycles = np.array([1.2e4, 2.6e4, 6.2e4, 1.4e5, 4.1e5, 1.1e6, 3.5e6, 1.5e7, 5.2e7, 1.8e8])

# Centering to reduce alpha-beta correlation in sampling
log_S = np.log(stress)
log_S_mean = np.mean(log_S)
log_S_centered = log_S - log_S_mean

# Smooth stress range for plotting
s_plot = np.linspace(150, 450, 200)
log_s_plot_c = np.log(s_plot) - log_S_mean


# ============================================================
# PROBLEM 1: MODEL 1 - BASQUIN'S EQUATION
# N = A * S^(-beta)  =>  ln(N) = alpha - beta*ln(S)
# ============================================================

with pm.Model() as model1:
    # alpha ~ log-life at the mean stress level, roughly 12-15
    alpha = pm.Normal('alpha', mu=13.5, sigma=5)
    # beta must be positive for N drops with S
    beta = pm.Normal('beta', mu=10, sigma=5)
    sigma = pm.HalfNormal('sigma', sigma=1)

    mu_i = alpha - beta * log_S_centered
    N_obs = pm.LogNormal('N_obs', mu=mu_i, sigma=sigma, observed=cycles)

# --- 1a: Prior Predictive Check ---

with model1:
    prior = pm.sample_prior_predictive(draws=500, random_seed=42)

pr_alpha = prior.prior['alpha'].values.flatten()
pr_beta = prior.prior['beta'].values.flatten()

plt.figure(figsize=(10, 6))
for i in range(len(pr_alpha)):
    mu_line = pr_alpha[i] - pr_beta[i] * log_s_plot_c
    plt.plot(s_plot, np.exp(mu_line), color='steelblue', alpha=0.03, lw=0.7)

plt.scatter(stress, cycles, color='red', edgecolor='black', zorder=5, label='Observed Data')
plt.yscale('log'); plt.xscale('log')
plt.xlabel('Stress S (MPa)')
plt.ylabel('Cycles to Failure N')
plt.title('Prior Predictive Check - Model 1 (Basquin)')
plt.legend(); plt.grid(True, which='both', ls='--', alpha=0.4)
plt.tight_layout()
plt.savefig('prior_predictive_m1.png', dpi=150)
plt.close()

n_neg = np.sum(pr_beta < 0)
print(f"Prior draws with beta < 0 (unphysical): {n_neg}/{len(pr_beta)}")

# --- 1b: Inference & Diagnostics ---

with model1:
    trace_m1 = pm.sample(draws=2000, tune=1000, chains=4,
                         target_accept=0.95, random_seed=42)
    pm.compute_log_likelihood(trace_m1)

summary1 = az.summary(trace_m1, var_names=['alpha', 'beta', 'sigma'])
print("\n=== Model 1 Summary ===")
print(summary1)

divs1 = trace_m1.sample_stats['diverging'].values.sum()
print(f"Divergent transitions: {divs1}")

az.plot_trace(trace_m1, var_names=['alpha', 'beta', 'sigma'])
plt.tight_layout()
plt.savefig('trace_m1.png', dpi=150)
plt.close()

# --- 1c: Posterior Predictive Check ---

post_alpha = trace_m1.posterior['alpha'].values.flatten()
post_beta = trace_m1.posterior['beta'].values.flatten()
post_sigma = trace_m1.posterior['sigma'].values.flatten()

rng = np.random.default_rng(42)
mu_pred = post_alpha[:, None] - post_beta[:, None] * log_s_plot_c
log_N_pred = mu_pred + rng.normal(0, post_sigma[:, None], size=mu_pred.shape)
N_pred = np.exp(log_N_pred)

low = np.percentile(N_pred, 2.5, axis=0)
high = np.percentile(N_pred, 97.5, axis=0)
med = np.percentile(N_pred, 50, axis=0)

plt.figure(figsize=(10, 6))
plt.fill_between(s_plot, low, high, color='blue', alpha=0.2, label='95% Credible Interval')
plt.plot(s_plot, med, 'b-', lw=2, label='Median Prediction')
plt.scatter(stress, cycles, color='red', edgecolor='black', zorder=5, label='Observed Data')
plt.yscale('log'); plt.xscale('log')
plt.xlabel('Stress S (MPa)')
plt.ylabel('Cycles to Failure N')
plt.title('Posterior Predictive Check - Model 1 (Basquin)')
plt.legend(); plt.grid(True, which='both', ls='--', alpha=0.4)
plt.tight_layout()
plt.savefig('ppc_m1.png', dpi=150)
plt.close()


# ============================================================
# PROBLEM 2: MODEL 2 - STROMEYER'S EQUATION
# N = A * (S - Se)^(-beta)  =>  mu = alpha - beta*ln(S - Se)
# ============================================================

with pm.Model() as model2:
    # Similar priors, but alpha is larger here because ln(S-Se) < ln(S)
    alpha2 = pm.Normal('alpha', mu=40, sigma=15)
    beta2 = pm.Normal('beta', mu=8, sigma=5)
    sigma2 = pm.HalfNormal('sigma', sigma=1)

    # Fatigue limit: bounded so that S - Se > 0 for all data points
    Se = pm.Uniform('Se', lower=0, upper=155)

    # Stromeyer model (use pm.math.log because Se is a random variable)
    mu_i2 = alpha2 - beta2 * pm.math.log(stress - Se)
    N_obs2 = pm.LogNormal('N_obs', mu=mu_i2, sigma=sigma2, observed=cycles)

    # More tuning steps + higher target_accept to handle the funnel
    trace_m2 = pm.sample(draws=2000, tune=2000, chains=4,
                         target_accept=0.99, random_seed=42)
    pm.compute_log_likelihood(trace_m2)

summary2 = az.summary(trace_m2, var_names=['alpha', 'beta', 'sigma', 'Se'])
print("\n=== Model 2 Summary ===")
print(summary2)

divs2 = trace_m2.sample_stats['diverging'].values.sum()
print(f"Divergent transitions: {divs2}")

# --- 2c: Se results (94% HDI) ---
se_samples = trace_m2.posterior['Se'].values.flatten()
se_hdi = az.hdi(trace_m2, var_names=['Se'], prob=0.94)

print(f"\nFatigue Limit Se:")
print(f"  Mean = {np.mean(se_samples):.1f} MPa")
print(f"  94% HDI = [{se_hdi['Se'].values[0]:.1f}, {se_hdi['Se'].values[1]:.1f}] MPa")

az.plot_trace(trace_m2, var_names=['alpha', 'beta', 'sigma', 'Se'])
plt.tight_layout()
plt.savefig('trace_m2.png', dpi=150)
plt.close()


# ============================================================
# PROBLEM 3: MODEL COMPARISON - PSIS-LOO  (20 pts)
# ============================================================

comparison = az.compare({"Basquin": trace_m1, "Stromeyer": trace_m2})
print("\n=== LOO Model Comparison ===")
print(comparison)

az.plot_compare(comparison)
plt.tight_layout()
plt.savefig('loo_comparison.png', dpi=150)
plt.close()

print("\nAll figures saved. Done.")