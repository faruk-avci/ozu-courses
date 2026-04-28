"""

# PHYS 551: Advanced Monte Carlo Methods
# Homework 3 - Source Code
# Student: Omer Faruk Avci
# Instructor: Prof. Dr. Taylan Akdogan

"""
import numpy as np
import matplotlib.pyplot as plt

"""Problem 2: Mixing Time and The Spectral Gap (Computational)"""


# Transition matrix
P = np.array([
    [1/2, 1/2,   0  ],
    [1/5, 1/2, 3/10 ],
    [0,   2/5,  3/5 ]
])

# Initial distribution given in the problem
mu_init = np.array([1.0, 0.0, 0.0])

t_max = 40
mu_values = np.zeros((t_max + 1, 3))
mu_values[0] = mu_init

for t in range(1, t_max + 1):
    mu_values[t] = mu_values[t-1] @ P  # mu^(t) = mu^(0) * P^t

# Part b: Plot
pi = np.array([8/43, 20/43, 15/43])
time = np.arange(t_max + 1)

plt.figure(figsize=(10, 6))
colors = ['red', 'orange', 'blue']
for i, c in enumerate(colors):
    plt.plot(time, mu_values[:, i], f'-o', color=c, label=f'State {i+1}')
    plt.axhline(pi[i], color=c, linestyle='--', alpha=0.6)

plt.xlabel('Time')
plt.ylabel('Probability')
plt.title('Markov Chain Evolution')
plt.legend(); plt.grid(True, alpha=0.6)
plt.tight_layout()
plt.savefig("markov_evolution.png")

# Part c: Eigenvalues
eigenvalues = np.linalg.eigvals(P)
eigenvalues_sorted = sorted(eigenvalues, key=abs, reverse=True)

lambda_1 = eigenvalues_sorted[0]
lambda_2 = eigenvalues_sorted[1]
gamma    = 1 - abs(lambda_2)
tau      = -1 / np.log(abs(lambda_2))

print(f"lambda1 = {lambda_1:.6f}")
print(f"lambda2 = {lambda_2:.6f}")
print(f"Spectral Gap = {gamma:.6f}")
print(f"Relaxation Time = {tau:.6f}")