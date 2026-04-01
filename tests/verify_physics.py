from __future__ import annotations

import numpy as np


def verify_su2_algebra() -> bool:
    """Verify basic SU(2) algebraic properties for integration testing."""
    # Identity
    I = np.eye(2, dtype=complex)
    
    # Pauli matrices
    sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
    sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
    
    # Check [sigma_x, sigma_y] = 2i * sigma_z
    comm = sigma_x @ sigma_y - sigma_y @ sigma_x
    target = 2j * sigma_z
    
    return np.allclose(comm, target)

if __name__ == "__main__":
    if verify_su2_algebra():
        print("SU(2) Algebra Verified")
    else:
        print("SU(2) Algebra Verification FAILED")
        exit(1)
