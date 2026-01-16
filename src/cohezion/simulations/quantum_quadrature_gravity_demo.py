# -------------------------------------------------
# Quantum-Quadrature Gravity demo
# -------------------------------------------------
import matplotlib.pyplot as plt
import numpy as np

# 1. Build a 2-D spin-network lattice (nodes = qubits)
N = 100
phi = np.zeros((N, N))  # phase field (Tempic Field)


# 2. Impose a localized phase bump (simulating intent)
def add_tempic(x0, y0, amp, sigma):
    xs, ys = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    phi[:] += amp * np.exp(-((xs - x0) ** 2 + (ys - y0) ** 2) / (2 * sigma**2))


add_tempic(x0=50, y0=50, amp=1.0, sigma=5.0)  # baseline Tempic Field

# 3. Quadrature coupling (alpha, beta) modifies effective curvature
alpha, beta = 1.0, 1.0  # default (no intent)


def curvature(phi, a, b):
    # simple Laplacian as proxy for Riemann curvature scalar
    lap = np.gradient(np.gradient(phi)[0])[0] + np.gradient(np.gradient(phi)[1])[1]
    return a * lap + b * phi  # mix with phase amplitude (Quadrature)


R = curvature(phi, alpha, beta)

# 4. Compute effective potential (Newtonian-like) from curvature
G_eff = -R / np.max(np.abs(R))  # normalized attractive field

# 5. Visualize
plt.subplot(1, 2, 1)
plt.title("Tempic Field (phase)")
plt.imshow(phi, cmap="viridis")
plt.subplot(1, 2, 2)
plt.title("Effective Gravity (G_eff)")
plt.imshow(G_eff, cmap="inferno")
plt.show()
# -------------------------------------------------
# By varying `alpha` and `beta` you emulate intentional
# Quadrature modulation, which directly reshapes the
# Tempic-Field-derived curvature and thus the gravity map.
# -------------------------------------------------
