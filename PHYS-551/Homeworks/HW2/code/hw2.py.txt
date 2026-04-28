"""

# PHYS 551: Advanced Monte Carlo Methods
# Homework 2 - Source Code
# Student: Omer Faruk Avci
# Instructor: Prof. Dr. Taylan Akdogan

"""

import numpy as np
import matplotlib.pyplot as plt


"""Problem 1: The Custom Generator (Inverse Transform)"""

# Part (b): Function to generate N Rayleigh samples
def generate_rayleigh(N):
    """Generates N random samples from a Rayleigh distribution using Inverse Transform."""
    N_sample = np.random.uniform(0, 1, N)
    return np.sqrt(-2 * np.log(N_sample))

# Part (c): Function to compute the empirical CDF and showing theoretical CDF
def plot_cdf(N):
    
    samples = generate_rayleigh(N) # Generate N Rayleigh samples from the function defined in part (b)
    plt.hist(samples, bins=50, density=True, alpha=0.6, color='b', label='Empirical PDF (Histogram)')

    x_values = np.linspace(0, 6, 500) # Generate x values for plotting the theoretical PDF
    
    # p(x) = x * exp(-x^2 / 2) for x >= 0
    pdf_theoretical = x_values * np.exp(-x_values**2 / 2) 
    
    plt.plot(x_values, pdf_theoretical, lw=2,color='red', label='Theoretical PDF $p(x)$')

    plt.title('Verification of Rayleigh Distribution Generator')
    plt.xlabel('x')
    plt.ylabel('Probability Density')
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    plt.show()

def problem_1_b():
    samples = generate_rayleigh(10000)  # Generate 10,000 samples
    print("First 10 samples from Rayleigh distribution:", samples[:10])

def problem_1_c():
    N = 10000
    plot_cdf(N)


"""Problem 2: Working Smarter (Variance Reduction)"""

# Part (a): Naive Monte Carlo method
def naive_method(N):
    samples = np.random.uniform(0, 1, N) # N samples from uniform distribution in [0, 1]
    result = np.exp(samples**2) # Compute f(x) = exp(x^2) for each sample
    
    integral_estimate = np.mean(result) 
    variance = np.var(result, ddof=1)
    sem = np.sqrt(variance / N)

    return integral_estimate, variance, sem

# Part (b): Antithetic Variates method
def antithetic_method(N):
    sample_1 = np.random.uniform(0, 1, N//2) # N/2 samples from uniform distribution in [0, 1]
    sample_2 = 1 - sample_1 # Antithetic samples
    
    result_1 = np.exp(sample_1**2) # Compute f(x) for the first set of samples
    result_2 = np.exp(sample_2**2) # Compute f(x) for the antithetic samples

    pair_mean = (result_1 + result_2) / 2 # Average the results of the pairs

    intgral_estimate = np.mean(pair_mean)
    variance = np.var(pair_mean, ddof=1) 
    sem = np.sqrt(variance / (N//2)) 

    return intgral_estimate, variance, sem

# Part (c): Control Variates method
def control_variates_method(N):

    samples  = np.random.uniform(0, 1, N)

    X = np.exp(samples ** 2) # f(X) = e^(X^2)
    Y = samples ** 2 + 1 # g(X) = X^2 + 1, J = E[g(X)] = 4/3

    J = 4 / 3

    c_estimated =  np.cov(X, Y)[0, 1] / np.var(Y, ddof=1) # Estimate the optimal control variate coefficient c

    L = X - c_estimated * (Y - J) # Adjusted estimator using control variates

    mean = np.mean(L)
    variance = np.var(L, ddof=1)
    sem = np.sqrt(variance / N)

    return mean, variance, sem




def run_problem_1():
    print("Problem 1(b): Generating Rayleigh samples")
    problem_1_b()
    print("\nProblem 1(c): Plotting PDF")
    problem_1_c()

def run_problem_2():
    N = 10000

    # Run all three methods and collect their estimates, variances, and SEMs
    naive_est, naive_var, naive_sem = naive_method(N)
    anti_est, anti_var, anti_sem = antithetic_method(N)
    control_est, control_var, control_sem = control_variates_method(N)

    # Calculate Variance Reduction Factors (VRF) for both methods compared to the naive method
    vrf_anti = naive_var / anti_var
    vrf_control = naive_var / control_var


    # Print the results in a formatted table
    print("\nProblem 2 Results (N = 10,000)")
    print("-" * 65)
    print(f"{'Method':<22} {'Estimate':<12} {'Variance':<14} {'SEM':<14}")
    print("-" * 65)

    print(f"{'Naive Monte Carlo':<22} {naive_est:<12.6f} {naive_var:<14.6e} {naive_sem:<14.6e} ")
    print(f"{'Antithetic Variates':<22} {anti_est:<12.6f} {anti_var:<14.6e} {anti_sem:<14.6e} ")
    print(f"{'Control Variates':<22} {control_est:<12.6f} {control_var:<14.6e} {control_sem:<14.6e}")

    print("-" * 65)
    print(f"VRF (Antithetic vs Naive): {vrf_anti:.3f}")
    print(f"VRF (Control vs Naive):    {vrf_control:.3f}")
    print("-" * 65)

"""Problem 3: The Curse of Dimensionality"""

def estimate_volume(d, n_samples=1_000_000):
    # Generate N points in d-dimensions within [-1, 1]
    points = np.random.uniform(-1, 1, (n_samples, d))
    
    # Calculate squared Euclidean distance for each point
    distances_squared = np.sum(points**2, axis=1)
    
    # Count points satisfying the hypersphere condition: sum(x_i^2) <= 1
    inside_count = np.sum(distances_squared <= 1)
    
    # Volume of the bounding hypercube is 2^d
    v_cube = 2**d
    
    # Scale the hit-ratio by the total volume of the cube
    estimated_volume = (inside_count / n_samples) * v_cube
    
    return estimated_volume

def run_problem_3():
    dimensions = [2, 5, 10]
    results = {d: estimate_volume(d) for d in dimensions}
    
    print(f"Problem 3 Results (N = 1,000,000 samples):")
    print("-" * 45)
    print(f"{'Dimension (d)':<15} {'Estimated Volume':<20}")
    print("-" * 45)
    for d, vol in results.items():
        print(f"{d:<15} {vol:<20.5f}")

def main():
    run_problem_1()
    run_problem_2()
    run_problem_3()

main()