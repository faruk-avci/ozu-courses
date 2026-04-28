"""

# PHYS 551: Advanced Monte Carlo Methods
# Homework 3 - Source Code
# Student: Omer Faruk Avci
# Instructor: Prof. Dr. Taylan Akdogan

"""
import numpy as np
import matplotlib.pyplot as plt

"""Problem 2: Bayesian Parameter Estimation: The Exoplanet Hunt"""

# Telescope observation data (Time, Velocity, and Measurement Noise)
days_t = np.array([1.2, 2.5, 3.1, 4.8, 6.5, 7.2, 8.1, 9.5, 10.3, 11.9])
v_obs = np.array([12.4, -4.5, -13.2, -6.1, 14.8, 11.2, -3.8, -14.9, -9.1, 13.5])
sigma_noise = 2.5

def v_model(t, K, P):
    # Theoretical radial velocity model (sine wave)
    return K * np.sin((2 * np.pi / P) * t)

def log_posterior(state):
    K, P = state

    # Enforce uniform prior constraints: K in [0, 30], P in [2, 12]
    if not (0 <= K <= 30 and 2 <= P <= 12):
        return -np.inf
    
    # Calculate predicted velocities using the current state parameters
    predicted = v_model(days_t, K, P)
    
    # Compute the log-likelihood assuming Gaussian noise
    log_likelihood = -0.5 * np.sum(((v_obs - predicted) / sigma_noise) ** 2)

    # Since the prior is uniform, posterior is proportional to likelihood
    return log_likelihood

def metropolis_hasting_2d(num_steps, sigmas, start_state):
    # Array to store all generated MCMC samples
    samples = np.zeros((num_steps, 2))
    accepted_moves = 0

    # Initialize the Markov chain
    current_state = start_state
    current_log_prob = log_posterior(current_state)
    samples[0] = current_state

    for i in range(1, num_steps):
        # Propose a new state using independent Gaussian jumps for K and P
        proposal = current_state + np.random.normal(0, sigmas)
        proposal_log_prob = log_posterior(proposal)

        # Calculate the acceptance ratio in log-space (subtraction replaces division)
        alpha = proposal_log_prob - current_log_prob

        # Accept or reject the jump based on a log-uniform random draw
        if np.log(np.random.uniform(0, 1)) < alpha:
            current_state = proposal
            current_log_prob = proposal_log_prob
            accepted_moves += 1

        # Record the state (either the newly accepted state or the old repeated state)
        samples[i] = current_state

    acceptance_rate = accepted_moves / (num_steps - 1)
    return samples, acceptance_rate

def main():
    num_steps = 50_000
    burn_in = 10_000
    start_point = np.array([5.0, 5.0])
    
    # TUNING: K gets a 1.5 jump, P gets a tiny 0.05 jump.
    sigmas = np.array([2.5, 0.1]) 

    print("Running MCMC Exoplanet Hunt...")
    samples, acc_rate = metropolis_hasting_2d(num_steps, sigmas, start_point)
    print(f"Acceptance Rate: {acc_rate * 100:.1f}%")

    # --- Analyze Valid Data (Discard Burn-in) ---
    # Slice the array to remove the initial unmixed samples
    valid_samples = samples[burn_in:]
    K_samples = valid_samples[:, 0]
    P_samples = valid_samples[:, 1]

    # Calculate final physical parameters (Mean +/- Std Dev)
    K_mean, K_std = np.mean(K_samples), np.std(K_samples)
    P_mean, P_std = np.mean(P_samples), np.std(P_samples)
    
    print("\nFinal Results:")
    print(f"Amplitude (K) = {K_mean:.2f} ± {K_std:.2f} m/s")
    print(f"Period (P)    = {P_mean:.3f} ± {P_std:.3f} days")

    # --- Plotting (Separate Figures) ---
    
    # Calculate tight Y-axis limits based only on the valid samples (ignoring burn-in)
    k_min, k_max = np.min(K_samples), np.max(K_samples)
    k_pad = (k_max - k_min) * 0.15 
    
    p_min, p_max = np.min(P_samples), np.max(P_samples)
    p_pad = (p_max - p_min) * 0.15

    # 1. Trace Plot for K
    plt.figure(figsize=(8, 4))
    plt.plot(samples[:, 0], color='blue', alpha=0.5, linewidth=0.5)
    plt.axvline(burn_in, color='red', linestyle='--', linewidth=2, label='Burn-in Cutoff')
    plt.ylim(k_min - k_pad, k_max + k_pad) # NARROWED Y-AXIS
    plt.ylabel('Amplitude K (m/s)')
    plt.xlabel('Iteration')
    plt.title('Trace Plot: Velocity Amplitude')
    plt.legend()
    plt.tight_layout()
    plt.savefig('trace_K.png')
    plt.show()

    plt.close() # Closes the figure so it doesn't overlap with the next one

    # 2. Trace Plot for P
    plt.figure(figsize=(8, 4))
    plt.plot(samples[:, 1], color='green', alpha=0.5, linewidth=0.5)
    plt.axvline(burn_in, color='red', linestyle='--', linewidth=2, label='Burn-in Cutoff')
    plt.ylim(p_min - p_pad, p_max + p_pad) # NARROWED Y-AXIS
    plt.ylabel('Period P (days)')
    plt.xlabel('Iteration')
    plt.title('Trace Plot: Orbital Period')
    plt.legend()
    plt.tight_layout()
    plt.savefig('trace_P.png')
    plt.show()

    plt.close()

    # 3. 2D Posterior Scatter / Histogram
    plt.figure(figsize=(8, 6))
    h = plt.hist2d(P_samples, K_samples, bins=60, cmap='inferno')
    plt.colorbar(h[3], label='Sample Density')
    plt.xlabel('Period P (days)')
    plt.ylabel('Amplitude K (m/s)')
    plt.title('2D Marginal Posterior Distribution')
    plt.tight_layout()
    plt.savefig('posterior_2d.png')
    
    plt.show()

if __name__ == "__main__":
    main()