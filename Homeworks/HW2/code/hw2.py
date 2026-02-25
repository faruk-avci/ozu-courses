import numpy as np
import matplotlib.pyplot as plt

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
    N = 10000  # Number of samples
    plot_cdf(N)


def run_problem_1():
    print("Problem 1(b): Generating Rayleigh samples")
    problem_1_b()
    print("\nProblem 1(c): Plotting PDF")
    problem_1_c()


run_problem_1()


##############################################################

