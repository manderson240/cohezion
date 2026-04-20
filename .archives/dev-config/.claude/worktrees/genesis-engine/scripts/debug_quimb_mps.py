import logging

import quimb.gates as qg
import quimb.tensor as qtn


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MPS_Debug")


def test_mps_entanglement():
    logger.info("Testing MPS Entanglement generation...")

    # 1. Create simple 4-qubit MPS |0000>
    N = 4
    psi = qtn.MPS_computational_state("0" * N)
    logger.info(f"Initial Max Bond Dim: {psi.max_bond()}")

    # 2. Apply Hadamard to q[0] -> |+000> (Product state, BD=1)
    psi.gate_(qg.H, (0,), max_bond=1024)
    logger.info(f"After H(0): Max Bond Dim: {psi.max_bond()}")

    # 3. Apply CNOT(0, 1) -> Bell state |0000> + |1100> (BD=2)
    # Using manual generic gate application
    psi.gate_(qg.CNOT, (0, 1), max_bond=1024)
    logger.info(f"After CNOT(0, 1): Max Bond Dim: {psi.max_bond()}")

    # 4. Apply CNOT(1, 3) -> Non-adjacent entanglement.
    # Should require swaps or SVD splitting.
    # State became roughly (|0000> + |1100>) -> CNOT(1,3) -> |0000> + |1101>
    # Entanglement across cut 1-2 and 2-3 should exist.
    psi.gate_(qg.CNOT, (1, 3), max_bond=1024)
    logger.info(f"After CNOT(1, 3) [Non-Adjacent]: Max Bond Dim: {psi.max_bond()}")

    # 5. Check if it handles 'swap+split' implicitly or fails
    try:
        psi.gate_(qg.CNOT, (0, 3), max_bond=1024)
        logger.info(f"After CNOT(0, 3) [Long Range]: Max Bond Dim: {psi.max_bond()}")
    except Exception as e:
        logger.error(f"Failed to apply long range gate: {e}")


import resource


def set_memory_limit(limit_gb=40):
    rsrc = resource.RLIMIT_AS
    limit_bytes = limit_gb * 1024**3
    resource.setrlimit(rsrc, (limit_bytes, limit_bytes))
    logger.info(f"Memory limit set to {limit_gb} GB")


if __name__ == "__main__":
    set_memory_limit(20)  # 20GB limit for debug

    logger.info("Testing MPS Entanglement generation with contract='swap+split'...")

    # 1. Create simple 4-qubit MPS |0000>
    N = 4
    psi = qtn.MPS_computational_state("0" * N)

    # 2. Apply Hadamard to q[0] -> |+000>
    psi.gate_(qg.H, (0,), max_bond=1024)
    logger.info(f"After H(0): Max Bond Dim: {psi.max_bond()}")

    # 3. Apply Manual SWAP(0, 1) check
    try:
        logger.info("Testing Manual SWAP(1, 2)...")

        SWAP_mat = qg.SWAP

        # Check current tensor count
        # psi is MPS, it behaves like list of tensors? or psi.tensors?
        # MatrixProductState stores tensors in ._tensors or .tensors or behaves as TN.
        logger.info(f"Tensor count before SWAP: {len(psi.tensors)}")

        psi.gate_(SWAP_mat, (1, 2), max_bond=1024, contract=True)  # Force contract
        logger.info(f"After SWAP(1, 2): Max Bond Dim: {psi.max_bond()}. Tensor Count: {len(psi.tensors)}")

        logger.info("Applying CNOT on sites (0, 1)...")
        psi.gate_(qg.CNOT, (0, 1), max_bond=1024, contract=True)  # Force contract
        logger.info(f"After CNOT(sites 0,1): Max Bond Dim: {psi.max_bond()}. Tensor Count: {len(psi.tensors)}")

    except Exception as e:
        logger.error(f"Failed to apply manual SWAP with contract=True: {e}")
        import traceback

        traceback.print_exc()

    test_mps_entanglement()

    # (Leaving original function call but the main block logic is above)
