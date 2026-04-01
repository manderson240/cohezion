"""
Peaked Circuit Solver - 36-qubit Quantum Advantage Challenge
Engine: Quimb (Tensor Networks) + Cotengra (Contraction Optimization)

Strategy:
Instead of computing the full state vector (which requires ~1TB RAM for 36 qubits),
we use Tensor Networks to represent the state efficiently.
We find the 'peak' (heavy bitstring) by:
1. Representing the circuit as a Tensor Network (Matrix Product State or general TN).
2. Optimizing the contraction path for scalar/marginal queries using Cotengra.
3. performing likelihood-based sampling (since it's a peaked distribution) to find candidates.
"""

import logging
import os
import time

import cotengra as ctg
import numpy as np
import quimb.tensor as qtn


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PeakedSolver")


class PeakedCircuitSolver:
    def __init__(self, qasm_path: str, memory_limit_gb: int = 50):
        self.qasm_path = qasm_path
        self.memory_limit_gb = memory_limit_gb
        self.circ: qtn.Circuit | None = None
        self.tn: qtn.TensorNetwork | None = None
        self.contraction_info = None

        # Verify file exists
        if not os.path.exists(qasm_path):
            raise FileNotFoundError(f"QASM file not found: {qasm_path}")

    def load_circuit(self):
        """Parses the QASM file manually into a Quimb Circuit."""
        logger.info(f"Loading QASM from {self.qasm_path}...")

        try:
            with open(self.qasm_path) as f:
                lines = f.readlines()

            # Simple parser for 'u' and 'cz' gates
            # First find N
            N = 0
            for line in lines:
                if line.startswith("qreg"):
                    # qreg q[36];
                    N = int(line.split("[")[1].split("]")[0])
                    break

            if N == 0:
                raise ValueError("Could not find qreg")

            logger.info(f"Found {N} qubits. Constructing TN...")
            self.circ = qtn.Circuit(N)

            for line in lines:
                line = line.strip().replace(";", "")
                if (
                    not line
                    or line.startswith("OPENQASM")
                    or line.startswith("include")
                    or line.startswith("qreg")
                ):
                    continue

                # Parse CZ
                if line.startswith("cz"):
                    # cz q[1],q[3]
                    parts = line.split()[1].split(",")
                    q1 = int(parts[0].split("[")[1].split("]")[0])
                    q2 = int(parts[1].split("[")[1].split("]")[0])
                    self.circ.apply_gate("CZ", q1, q2)

                # Parse U gate: u(1.2,-1.3,0.9) q[0]
                elif line.startswith("u("):
                    # Extract params
                    params_str = line.split("(")[1].split(")")[0]
                    # Handle pi/2 etc.
                    safe_dict = {"pi": np.pi}
                    params = []
                    for p in params_str.split(","):
                        # Safe eval
                        try:
                            val = float(eval(p, {"__builtins__": None}, safe_dict))
                            params.append(val)
                        except Exception as parse_err:
                            logger.error(f"Failed to parse param {p} in line: {line}")
                            raise parse_err
                    # Extract qubit
                    q_str = line.split(")")[1].strip()
                    q = int(q_str.split("[")[1].split("]")[0])

                    # Quimb U3 uses U3(theta, phi, lam)
                    theta, phi, lam = params
                    self.circ.apply_gate("U3", theta, phi, lam, q)

            logger.info(
                f"Circuit loaded manually. Qubits: {self.circ.N}, Gates: {len(self.circ.gates)}"
            )

        except Exception as e:
            logger.error(f"Failed to load circuit: {e}")
            raise

    def setup_optimizer(self):
        """Configures the Cotengra optimizer for the contraction path."""
        # Now that Kahypar is verified, we use it explicitly.
        # methods=['kahypar'] is the best for complex circuits.
        # We also enable 'slicing' to ensure we stay within memory limits.

        opt = ctg.ReusableHyperOptimizer(
            methods=["kahypar"],
            max_repeats=128,
            progbar=True,
            minimize="flops",
            # Slicing options: target size ~2**28 (256MB) tensors to keep memory low
            # This allows computing very massive contractions by summing over slices
            slicing_opts={"target_size": 2**28},
        )
        return opt

    def simulate_and_sample(self, samples: int = 100000) -> list[tuple[str, float]]:
        """
        Performs Approximate MPS Evolution (Manifold Encoding) to find the peak.
        Strategy: Manual Gate Applications on MPS.
        """
        logger.info("Starting FLUME Manifold Encoding (Manual MPS Evolution)...")
        start_time = time.time()

        try:
            # 1. Parse QASM directly into operations list
            # We assume load_circuit has been called, but we need the raw gates.
            # Let's re-parse or rely on self.circ structure if we trust it.
            # Safest: Re-parse into a clean list of ops.

            with open(self.qasm_path) as f:
                lines = f.readlines()

            N = 36  # Known for this problem
            ops = []

            safe_dict = {"pi": np.pi}

            for line in lines:
                line = line.strip().replace(";", "")
                if not line or line.startswith(("OPENQASM", "include", "qreg", "//")):
                    continue

                if line.startswith("cz"):
                    parts = line.split()[1].split(",")
                    q1 = int(parts[0].split("[")[1].split("]")[0])
                    q2 = int(parts[1].split("[")[1].split("]")[0])
                    ops.append(("CZ", [], (q1, q2)))

                elif line.startswith("u("):
                    params_str = line.split("(")[1].split(")")[0]
                    params = []
                    for p in params_str.split(","):
                        params.append(float(eval(p, {"__builtins__": None}, safe_dict)))

                    q_str = line.split(")")[1].strip()
                    q = int(q_str.split("[")[1].split("]")[0])
                    # Quimb U3 matches QASM U3: U3(theta, phi, lam)
                    ops.append(("U3", params, (q,)))

            logger.info(f"Parsed {len(ops)} operations.")

            # 2. Initialize MPS |00...0>
            # FLUME: This is the 'Vacuum State'
            psi_mps = qtn.MPS_computational_state("0" * N)

            # 3. Evolve (Encode into Manifold)
            # We apply gates one by one, keeping bond dim in check
            max_bond = int(os.environ.get("MAX_BOND", 128))
            cutoff = float(os.environ.get("CUTOFF", 1e-5))

            logger.info(f"Evolving MPS with max_bond={max_bond}, cutoff={cutoff}...")

            # Track which physical qubit is at which MPS site
            # site_to_qubit: site_idx -> physical_qubit_idx
            # qubit_to_site: physical_qubit_idx -> site_idx
            site_to_qubit = list(range(N))
            qubit_to_site = list(range(N))

            # Resource limit to prevent crashes (40GB)
            import resource

            import quimb.gates as qg
            from tqdm import tqdm

            try:
                rsrc = resource.RLIMIT_AS
                soft, hard = resource.getrlimit(rsrc)
                limit_bytes = 40 * 1024**3
                resource.setrlimit(rsrc, (limit_bytes, hard))
                logger.info("Memory Limit set to 40GB")
            except Exception as e:
                logger.warning(f"Could not set memory limit: {e}")

            count_swaps = 0

            for i, (name, params, qubits) in enumerate(tqdm(ops[:100], desc="Manifold Encoding")):
                if name == "CZ":
                    G = qg.CZ
                elif name == "U3":
                    G = qg.U3(*params)
                else:
                    continue

                # Identify target sites for the gate
                target_sites = [qubit_to_site[q] for q in qubits]

                # If 2-qubit gate, route them to be adjacent
                if len(target_sites) == 2:
                    s1, s2 = target_sites

                    # While not adjacent
                    while abs(s1 - s2) > 1:
                        # Move s1 towards s2
                        # Determine direction
                        if s1 < s2:
                            # Swap s1 with s1+1
                            swap_a, swap_b = s1, s1 + 1
                            # Update indices for next iteration
                            s1 += 1
                        else:
                            # Swap s1 with s1-1
                            swap_a, swap_b = s1 - 1, s1
                            s1 -= 1

                        # EXECUTE SWAP on MPS
                        # Intermediate Fidelity: max_bond=128, cutoff=1e-5
                        psi_mps.gate_split(
                            qg.SWAP,
                            (swap_a, swap_b),
                            max_bond=max_bond,
                            cutoff=cutoff,
                            inplace=True,
                        )
                        count_swaps += 1

                        # UPDATE MAPS
                        q_a = site_to_qubit[swap_a]
                        q_b = site_to_qubit[swap_b]

                        site_to_qubit[swap_a], site_to_qubit[swap_b] = q_b, q_a
                        qubit_to_site[q_a] = swap_b
                        qubit_to_site[q_b] = swap_a

                    # UPDATE TARGET SITES after routing
                    target_sites = [qubit_to_site[q] for q in qubits]

                try:
                    # Apply Gate to (potentially new) sites
                    # Single qubit gate? U3
                    if len(target_sites) == 1:
                        psi_mps.gate_(G, tuple(target_sites), contract=True)
                    else:
                        # 2-qubit gate? CZ or Others
                        psi_mps.gate_split(
                            G, tuple(target_sites), max_bond=max_bond, cutoff=cutoff, inplace=True
                        )
                except Exception as e:
                    logger.error(
                        f"Gate application failed at step {i} (Gate {name}). Target sites: {target_sites}"
                    )
                    logger.error(f"Tensor Count: {len(psi_mps.tensors)}")
                    raise e

                # Periodically normalize and check
                if i % 50 == 0:
                    psi_mps.normalize()

                # DEBUG: Check bond dimension
                if i % 100 == 0:
                    logger.info(
                        f"Gate {i}: Max Bond Dim = {psi_mps.max_bond()}. Norm = {psi_mps.norm():.2e}"
                    )

            logger.info(
                f"Manifold Encoding Complete. Final Bond Dim: {psi_mps.max_bond()}. Total Swaps: {count_swaps}. Tensor Count: {len(psi_mps.tensors)}"
            )

            # CHECKPOINT: Save MPS to disk
            try:
                import pickle

                checkpoint_path = "peaked_mps_final.dill"
                with open(checkpoint_path, "wb") as f:
                    pickle.dump(psi_mps, f)
                logger.info(f"Saved checkpoint to {checkpoint_path}")
            except Exception as e:
                logger.warning(f"Failed to save checkpoint: {e}")

            # 4. Sampling
            # CRITICAL: The MPS sites are now scrambled! sites 0..N do NOT correspond to qubits 0..N
            # We need to map the sampled bits back to correct qubits.
            logger.info(f"Sampling {samples} shots (Standard MPS)...")
            raw_samples = psi_mps.sample(samples)

            # Reorder bits
            # raw_samples is iterator of bitstrings e.g. "01001..." corresponding to site 0, site 1...
            # We need to map site i -> qubit site_to_qubit[i]

            candidates = []
            for sample_tuple in raw_samples:  # sample returns (bits, prob) tuple
                bits = sample_tuple[0]

                # Construct valid bitstring
                # bits[j] corresponds to site j. site j holds qubit site_to_qubit[j]

                ordered_bits = [""] * N
                for site_idx, bit in enumerate(bits):
                    q_idx = site_to_qubit[site_idx]
                    try:
                        val = int(bit)
                    except (ValueError, TypeError):
                        val = bit
                    ordered_bits[q_idx] = str(val)

                final_bstr = "".join(ordered_bits)
                candidates.append(final_bstr)

            bitstrings = candidates

        except Exception as e:
            logger.error(f"MPS Evolution failed: {e}")
            raise

        # Force realization
        bitstrings = list(bitstrings)
        elapsed = time.time() - start_time
        logger.info(f"Encoding & Sampling time: {elapsed:.2f}s")

        # Frequency Analysis
        counts = {}
        for b in bitstrings:
            counts[b] = counts.get(b, 0) + 1

        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top_candidates = sorted_counts[:10]

        print(f"FINAL_CANDIDATES: {top_candidates}")
        return top_candidates

    def compute_amplitude(self, bitstring: str) -> complex:
        """
        Computes the exact amplitude <x|psi> for a specific bitstring x.
        This involves contracting the full TN with the bitstring state projected.
        """
        if not self.circ:
            self.load_circuit()

        return self.circ.amplitude(bitstring, optimize="auto-hq")


if __name__ == "__main__":
    # Test run
    path = "P1_little_dimple.qasm"
    if not os.path.exists(path):
        # Fallback to project path
        path = "/home/mike-anderson/dev/cohezion/src/cohezion/physics/quantum/P1_little_dimple.qasm"

    if os.path.exists(path):
        solver = PeakedCircuitSolver(path)
        solver.simulate_and_sample(samples=10)
