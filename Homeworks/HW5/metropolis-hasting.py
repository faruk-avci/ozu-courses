import numpy as np
import matplotlib.pyplot as plt


# ====================================
# Target Distribution - Rosenbrock-style banana (Unnormalized)
# ====================================
def target_f(state):
    x, y = state
    return np.exp(-(x ** 2) / 20.0 - (y - (x ** 2) / 4.0) ** 2 / 2.0)

def log_target_f(state):
    x, y = state
    return -(x ** 2) / 20.0 - (y - (x ** 2) / 4.0) ** 2 / 2.0   

# ====================================
# The Metropolis-Hastings Algorithm
# ====================================
def metropolis_hasting(num_steps, sigma, start_state):
    samples = np.zeros((num_steps, 2))

    accepted_moves = 0

    # INITIALIZE
    samples[0] = start_state
    current_state = start_state
    current_prob = log_target_f(current_state)

    for i in range(1, num_steps):
        # PROPOSE: Symmetric Gaussian Random Walk
        proposal = current_state + np.random.normal(0, sigma, size=2)
        proposal_prob = log_target_f(proposal)

        # EVALUATE: alpha = f(x') / f(x)
        # (Symmetric proposal q cancels out)
        alpha = proposal_prob - current_prob

        # DECIDE: Draw uniform random number
        if np.log(np.random.uniform(0, 1)) < alpha:
            current_state = proposal
            current_prob = proposal_prob
            accepted_moves += 1

        # RECORD: Record the state (it's the new one or the old one repeated)
        samples[i] = current_state

    acceptance_rate = accepted_moves / (num_steps - 1)
    return samples, acceptance_rate



def main():
    num_samples = 10_000
    start_point = np.array([0.0, 0.0])  # Start at the origin

    # We will run the same algorithm with three different step sizes
    sigmas = [0.1, 8.0, 1.5]
    titles = ["Too Small (The Ant)", "Too Large (The Kangaroo)", "Just Right (Sweet Spot)"]

    # Set up the plot layout
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Create background contour map of the true distribution
    x_grid = np.linspace(-8, 8, 100)
    y_grid = np.linspace(-2, 16, 100)
    X, Y = np.meshgrid(x_grid, y_grid)
    Z = np.exp(-(X ** 2) / 20.0 - (Y - (X ** 2) / 4.0) ** 2 / 2.0)

    # Run and plot all three scenarios
    for i in range(3):
        sigma = sigmas[i]
        title = titles[i]

        samples, acc_rate = metropolis_hasting(num_samples, sigma, start_point)

        ax = axes[i]

        # Plot the true distribution contour
        ax.contourf(X, Y, Z, levels=20, cmap='Blues', alpha=0.6)

        # Plot the MCMC random walk path
        ax.plot(samples[:, 0], samples[:, 1], 'k.', alpha=0.08, markersize=4)
        ax.plot(samples[:, 0], samples[:, 1], 'k-', alpha=0.4, linewidth=0.25)
        ax.plot(samples[0, 0], samples[0, 1], 'go', label="Start")  # Green dot for start
        ax.plot(samples[-1, 0], samples[-1, 1], 'ro', label="End")  # Red dot for end

        ax.set_title(f"{title}\n$\sigma={sigma}$ | Acc. Rate: {acc_rate * 100:.1f}%")
        ax.set_xlim(-8, 8)
        ax.set_ylim(-2, 16)
        ax.legend()

        print(f"Running Scenario {i + 1}: sigma = {sigma}    Acc. Ratio = {acc_rate * 100:4.1f}%")

    plt.tight_layout()
    plt.savefig("metropolis-hasting.png")
    plt.show()


if __name__ == "__main__":
    main()