import numpy as np
import matplotlib.pyplot as plt
N = np.array([10, 100, 1000, 10000, 100000, 1000000, 10000000])
error = np.array([0.355044, 0.115681, 0.0441629, 0.01028, 0.00453012, 0.00138013, 0.000418931])

log_N = np.log10(N)
log_error = np.log10(error)

C = log_error[0] + 0.5 * log_N[0]
theoretical_line = -0.5 * log_N + C

plt.figure(figsize=(8, 6))

plt.plot(log_N, log_error, 'bo-', label='Experimental Data', markersize=6, linewidth=2)

plt.plot(log_N, theoretical_line, 'r--', label='Theoretical Line (Slope = -0.5)', linewidth=2)

plt.xlabel(r'$\log_{10}(N)$', fontsize=14)
plt.ylabel(r'$\log_{10}(Error)$', fontsize=14)
plt.title('Log-Log Plot of Monte Carlo Error vs. Sample Size', fontsize=16)
plt.legend(fontsize=12)
plt.grid(True, which="both", linestyle="--", alpha=0.7)

plt.savefig('error_plot.png', dpi=300, bbox_inches='tight')
plt.show()