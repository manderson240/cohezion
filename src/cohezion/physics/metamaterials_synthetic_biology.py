r"""Metamaterials & Synthetic Biology Bioelectric Tensor Engine.
===============================================================
Applies Differential Geometry (Metric Tensors g_mu_nu, Energy-Momentum T_mu_nu,
and Scalar Invariants) to:

1. Electromagnetic & Acoustic Metamaterial Design:
   - Transformation Optics: Effective constitutive permittivity epsilon^{ij} & permeability mu^{ij}
     derived from metric tensor: epsilon^{ij} = mu^{ij} = sqrt(det(g)) * g^{ij} / g_00
   - Negative Refractive Index (n < 0) & Cloaking Tensor Invariants.
   - 432 Hz Acoustic Phonon Bandgap Crystals.

2. Synthetic Biology & Morphogenetic Bioelectric Fields:
   - Michael Levin Morphogenetic Field Tensor: M^{ij} = kappa_{ij} * grad(V_mem)
   - Cell Membrane Voltage Potential: V_mem in [-70, -10] mV.
   - Gap-Junction Conductance Topology: Kappa_{ij} in [0, 1].
   - Gene Regulatory Network (GRN) Chemical Morphogen Diffusion (Turing Reaction-Diffusion).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


class MetamaterialTensorSolver:
    """Computes Transformation Optics & Acoustic Phononic Metamaterial Invariants."""

    def compute_transformation_optics_tensors(self, g_metric: np.ndarray) -> dict[str, Any]:
        """Derive anisotropic permittivity epsilon and permeability mu from Riemannian metric g."""
        det_g = float(np.linalg.det(g_metric))
        sqrt_det_g = math.sqrt(max(det_g, 1e-12))
        inv_g = np.linalg.inv(g_metric)

        # Transformation optics constitutive tensors (Ward & Pendry 1996)
        epsilon_tensor = sqrt_det_g * inv_g
        mu_tensor = epsilon_tensor.copy()

        # Effective refractive index eigenvalues
        eigenvals = np.linalg.eigvals(epsilon_tensor)
        n_eff = float(np.mean(np.sqrt(np.abs(eigenvals))))

        # Negative index check (Double negative metamaterial)
        is_negative_index = bool(np.all(np.real(eigenvals) < 0.0) or det_g < 0)

        return {
            "determinant_det_g": round(det_g, 4),
            "effective_refractive_index_n": round(n_eff, 4),
            "is_negative_index": is_negative_index,
            "epsilon_tensor_trace": round(float(np.trace(epsilon_tensor)), 4),
            "anisotropy_ratio": round(float(np.max(eigenvals) / max(np.min(eigenvals), 1e-6)), 4),
        }

    def compute_acoustic_phononic_bandgap(self, lattice_constant_m: float = 1e-3, sound_speed_mps: float = 343.0) -> dict[str, Any]:
        """Compute Bragg & Mie acoustic bandgap frequencies for 432 Hz Pythagorean phononic crystals."""
        # Fundamental Bragg resonance: f_bragg = v_sound / (2 * a)
        f_bragg_hz = sound_speed_mps / (2.0 * lattice_constant_m)
        # Bandgap width delta_f
        delta_f_hz = 0.25 * f_bragg_hz

        return {
            "lattice_constant_mm": lattice_constant_m * 1000.0,
            "bragg_resonance_hz": round(f_bragg_hz, 1),
            "bandgap_range_hz": [round(f_bragg_hz - delta_f_hz/2, 1), round(f_bragg_hz + delta_f_hz/2, 1)],
            "couples_432hz_pythagorean": bool(abs(f_bragg_hz - 432.0) < 50.0 or 432.0 % int(f_bragg_hz) == 0),
        }


class SyntheticBiologyBioelectricSolver:
    """Computes Levin Morphogenetic Field Tensors & Turing Gene Regulatory Dynamics."""

    def compute_morphogenetic_field_tensor(
        self,
        v_mem_grid_mv: np.ndarray,
        gap_junction_kappa: np.ndarray,
    ) -> dict[str, Any]:
        """Compute the Morphogenetic Voltage Gradient Tensor M_{ij} = Kappa_{ij} * grad(V_mem)."""
        grad_y, grad_x = np.gradient(v_mem_grid_mv)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)

        # Coupled bioelectric flux
        bioelectric_flux = gap_junction_kappa * grad_mag
        mean_flux = float(np.mean(bioelectric_flux))
        max_voltage_gradient_mv_per_um = float(np.max(grad_mag))

        # HIHO Morphogenetic Stability: Healthy regenerative state occurs when V_mem is polarized (-50 to -30 mV)
        mean_v_mem = float(np.mean(v_mem_grid_mv))
        is_regenerative_competent = bool(-60.0 <= mean_v_mem <= -20.0 and mean_flux > 0.05)

        return {
            "mean_membrane_potential_mv": round(mean_v_mem, 2),
            "max_voltage_gradient_mv_per_um": round(max_voltage_gradient_mv_per_um, 4),
            "mean_bioelectric_flux": round(mean_flux, 4),
            "regenerative_competence": is_regenerative_competent,
            "pattern_stability_index": round(min(1.0, mean_flux * 2.0), 3),
        }

    def simulate_turing_morphogen_diffusion(
        self,
        grid_size: int = 32,
        steps: int = 50,
        da: float = 0.16,
        db: float = 0.08,
        feed: float = 0.035,
        kill: float = 0.065,
    ) -> dict[str, Any]:
        """Simulate Gray-Scott Turing reaction-diffusion morphogen patterning."""
        # A: Activator, B: Inhibitor
        A = np.ones((grid_size, grid_size), dtype=np.float32)
        B = np.zeros((grid_size, grid_size), dtype=np.float32)
        # Seed initial morphogen spot
        r = grid_size // 4
        A[r:-r, r:-r] = 0.50
        B[r:-r, r:-r] = 0.25

        for _ in range(steps):
            # 2D Laplacian using periodic boundaries
            lap_A = (
                np.roll(A, 1, axis=0) + np.roll(A, -1, axis=0) +
                np.roll(A, 1, axis=1) + np.roll(A, -1, axis=1) - 4 * A
            )
            lap_B = (
                np.roll(B, 1, axis=0) + np.roll(B, -1, axis=0) +
                np.roll(B, 1, axis=1) + np.roll(B, -1, axis=1) - 4 * B
            )

            reaction = A * (B**2)
            A += da * lap_A - reaction + feed * (1.0 - A)
            B += db * lap_B + reaction - (kill + feed) * B

        morphogen_entropy = float(-np.sum((B / (np.sum(B) + 1e-12)) * np.log2((B / (np.sum(B) + 1e-12)) + 1e-12)))
        return {
            "grid_size": f"{grid_size}x{grid_size}",
            "mean_inhibitor_b_density": round(float(np.mean(B)), 4),
            "morphogen_shannon_entropy": round(morphogen_entropy, 4),
            "turing_pattern_formed": bool(morphogen_entropy > 5.0),
        }


def run_metamaterials_synbio_experiment() -> dict[str, Any]:
    # 1. Metamaterials Solver
    meta = MetamaterialTensorSolver()
    g_3d = np.diag([2.5, 2.5, 0.4]).astype(np.float64)  # Anisotropic transformation optics metric
    to_res = meta.compute_transformation_optics_tensors(g_3d)
    phononic_res = meta.compute_acoustic_phononic_bandgap(lattice_constant_m=0.397, sound_speed_mps=343.0)  # Tuned for ~432 Hz

    # 2. Synthetic Biology Solver
    synbio = SyntheticBiologyBioelectricSolver()
    # Simulated 32x32 tissue membrane potential grid (mV)
    np.random.seed(42)
    v_grid = np.random.uniform(-55.0, -25.0, (32, 32)).astype(np.float32)
    kappa_grid = np.random.uniform(0.6, 1.0, (32, 32)).astype(np.float32)  # High gap-junction conductance
    bio_res = synbio.compute_morphogenetic_field_tensor(v_grid, kappa_grid)
    turing_res = synbio.simulate_turing_morphogen_diffusion(grid_size=32, steps=50)

    return {
        "transformation_optics": to_res,
        "phononic_metamaterial": phononic_res,
        "bioelectric_morphogenesis": bio_res,
        "turing_reaction_diffusion": turing_res,
    }


if __name__ == "__main__":
    results = run_metamaterials_synbio_experiment()
    print("=" * 90)
    print("    🧬 METAMATERIALS & SYNTHETIC BIOLOGY DIFFERENTIAL TENSOR ENGINE")
    print("=" * 90)
    for domain, metrics in results.items():
        print(f"\n[{domain.upper()}]:")
        for k, v in metrics.items():
            print(f"  • {k:<32}: {v}")
    print("=" * 90)
