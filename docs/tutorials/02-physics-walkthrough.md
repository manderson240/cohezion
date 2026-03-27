# Physics Walkthrough: The Mathematics Behind the Genesis Engine

This tutorial walks through the real physics and mathematics that ground the Genesis Engine. Every equation here is implemented in working Python code.

## 1. Brahmagupta's Zero (628 CE) — The Foundation

Before numbers, before dimensions, before symmetry — there is zero. Brahmagupta formalized it:

- **a + 0 = a** — the void changes nothing (`ZeroAlgebra.identity()`)
- **a x 0 = 0** — the void collapses structure (`ZeroAlgebra.annihilate()`)
- **a - a = 0** — opposites cancel to void (`ZeroAlgebra.complement()`)

In Cohezion, HIHO at coherence = 0.5 IS Brahmagupta's zero: delta = coherence - 0.5 = 0. The restoring force F = -k*delta vanishes at the equilibrium.

**Module**: `src/cohezion/physics/cosmogony.py` — `ZeroAlgebra` class

## 2. SU(2) Spinor Algebra — SPIN on the Bloch Sphere

SPIN (Rotation + Precession) maps to the Lie algebra su(2) via Pauli matrices:

- sigma_x = [[0,1],[1,0]] — Rotation generator
- sigma_y = [[0,-i],[i,0]] — Precession generator
- sigma_z = [[1,0],[0,-1]] — Charge generator

A spinor |psi> = alpha|up> + beta|down> lives on the Bloch sphere. The HIHO state is:

|HIHO> = (|up> + |down>) / sqrt(2)

This gives: charge = <sigma_z> = 0, rotation = <sigma_x> = 1, coherence = 1.

**Try it**: `curl localhost:8080/api/genesis/spinor/hiho`

**Module**: `src/cohezion/physics/spinor.py` — 33 tests verify all identities

## 3. Cosmogony — Symmetry Breaking from Nothing

The universe cools through 5 phase transitions following Landau theory:

F(phi, T) = a(T - Tc) * phi^2 + b * phi^4

Below Tc, the order parameter becomes: phi = sqrt(a(Tc - T) / 2b)

The chain: void -> SO(12) -> SO(3)^4 -> U(1)^4 -> Z2^4 -> HIHO

**Try it**: `curl -X POST localhost:8080/api/genesis/cosmogony/set-temperature -d '{"temperature": 5.0}'`

**Module**: `src/cohezion/physics/cosmogony.py` — 34 tests

## 4. Riemannian Geometry — The Shape of the Manifold

The 12D manifold has a Riemannian metric g_ij that defines distances and curvature. The Christoffel symbols:

Gamma^i_jk = (1/2) g^il (partial_j g_lk + partial_k g_jl - partial_l g_jk)

The fabric-block metric encodes gauge coupling constants: g = diag(1.0^3, 0.7^3, 0.5^3, 0.3^3).

**Module**: `src/cohezion/physics/riemannian_metric.py`

## 5. Lagrangian Dynamics — How Agents Move

Agents follow paths minimizing the action S = integral(L dt):

L = T - V = (1/2) g_ij qdot^i qdot^j - V_HIHO(q) - V_gauge(q)

The Euler-Lagrange equations yield: q_ddot^i = -Gamma^i_jk qdot^j qdot^k - g^ij partial_V/partial_q^j

We use a symplectic Stormer-Verlet integrator for bounded energy drift.

**Try it**: `curl -X POST localhost:8080/api/genesis/lagrangian-trajectory -d '{"n_steps":200}'`

**Module**: `src/cohezion/physics/lagrangian.py`

## 6. Fiber Bundles — The Internal Structure

The 12D manifold decomposes as P(B^4, SO(3)^4):

- Base space B^4: (||Space||, ||Field||, ||Control||, ||Precip||) — how much of each fabric
- Fiber F^8: unit directions within each fabric — the internal configuration

**Try it**: `curl -X POST localhost:8080/api/genesis/fiber-bundle`

**Module**: `src/cohezion/physics/fiber_bundle.py`

## 7. Gauge Theory — The Forces

Each fabric carries an SO(3) gauge connection. At HIHO, all curvatures vanish (flat connection = vacuum). The Yang-Mills action: L = -Tr(F ^ *F) / 4g^2.

**Try it**: `curl -X POST localhost:8080/api/genesis/gauge-state`

**Module**: `src/cohezion/physics/gauge_theory.py`

## 8. Fisher Information Metric — The Rosetta Stone

The Fisher metric g_ij = E[(partial log p / partial theta_i)(partial log p / partial theta_j)] simultaneously defines:

1. Natural geometry of the FLUME latent space
2. Riemannian metric for Lagrangian dynamics
3. Thermodynamic metric (entropy, free energy)
4. Optimal 256D -> 12D projection

For diagonal Gaussian: g_ii = 2 / sigma^2.

**Module**: `src/cohezion/physics/information_geometry.py`

## 9. Active Inference = HIHO

Friston's Free Energy Principle says agents minimize F = E - TS. Our HIHO says agents seek coherence = 0.5 (delta = 0). These are the SAME principle — our ThermodynamicMetrics.free_energy IS Friston's variational free energy.

**Module**: `src/cohezion/compound/thermodynamic_metrics.py`

## 10. Topological Persistence — The Shape of Behavior

Persistent homology captures the topology of agent trajectories:
- H0 (components) = behavioral clusters
- H1 (loops) = repetitive cycles

The TopologicalRouter uses this to DRIVE routing decisions, not just visualize.

**Module**: `src/cohezion/compound/topological_persistence.py`, `src/cohezion/swarm/topological_router.py`
