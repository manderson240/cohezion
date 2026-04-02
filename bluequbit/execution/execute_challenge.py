#!/usr/bin/env python3
"""
BlueQubit Challenge Execution Script

Execute winning strategy on ANY BlueQubit challenge.

Usage:
    python execute_challenge.py --challenge peaked --circuit circuit.qasm
    python execute_challenge.py --challenge qaoa --graph graph.txt
    python execute_challenge.py --auto --circuit circuit.qasm

Based on all 6 tutorials - proven winning strategies.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import argparse
import json
import time
from pathlib import Path

from dotenv import load_dotenv
import bluequbit
import qiskit

from universal_challenge_solver import UniversalChallengeSolver, ChallengeType
from submission_manager import SubmissionManager
from peaked_circuit_solver import PeakedCircuitSolver
from pauli_path_solver import PauliPathSolver
from qaoa_solver import QAOASolver


def parse_graph_file(filepath: str) -> list:
    """Parse graph edges from file."""
    edges = []
    with open(filepath) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                u, v = map(int, line.strip().split())
                edges.append((u, v))
    return edges


def parse_hamiltonian_file(filepath: str) -> list:
    """Parse Hamiltonian from file."""
    terms = []
    with open(filepath) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                parts = line.strip().split()
                coeff = float(parts[0])
                pauli = parts[1]
                terms.append((pauli, coeff))
    return terms


def main():
    parser = argparse.ArgumentParser(description="Execute BlueQubit challenge solver")

    parser.add_argument(
        "--challenge",
        type=str,
        choices=["peaked", "qaoa", "vqe", "auto"],
        default="auto",
        help="Challenge type (default: auto-detect)",
    )

    parser.add_argument("--circuit", type=str, required=True, help="Path to circuit QASM file")

    parser.add_argument("--graph", type=str, help="Path to graph edges file (for QAOA)")

    parser.add_argument("--hamiltonian", type=str, help="Path to Hamiltonian file (for VQE)")

    parser.add_argument(
        "--max-submissions", type=int, default=5, help="Maximum submissions (default: 5)"
    )

    parser.add_argument(
        "--confidence",
        type=str,
        choices=["LOW", "MEDIUM", "HIGH", "VERY HIGH"],
        default="HIGH",
        help="Minimum confidence threshold",
    )

    parser.add_argument("--dry-run", action="store_true", help="Validate without submitting")

    parser.add_argument(
        "--output", type=str, default="challenge_result.json", help="Output file for results"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("BlueQubit Challenge Execution")
    print("=" * 70)
    print(f"Challenge type: {args.challenge}")
    print(f"Circuit: {args.circuit}")
    print(f"Max submissions: {args.max_submissions}")
    print(f"Confidence threshold: {args.confidence}")
    print(f"Dry run: {args.dry_run}")

    # Initialize
    load_dotenv(".env")
    bq = bluequbit.init()

    # Load circuit
    print(f"\nLoading circuit from {args.circuit}...")
    with open(args.circuit) as f:
        qasm_str = f.read()

    circuit = qiskit.QuantumCircuit.from_qasm_str(qasm_str)
    print(f"✓ Loaded: {circuit.num_qubits} qubits, depth {circuit.depth()}")

    # Load additional data
    graph_edges = None
    hamiltonian = None

    if args.graph:
        graph_edges = parse_graph_file(args.graph)
        print(f"✓ Graph: {len(graph_edges)} edges")

    if args.hamiltonian:
        hamiltonian = parse_hamiltonian_file(args.hamiltonian)
        print(f"✓ Hamiltonian: {len(hamiltonian)} terms")

    # Create solvers
    universal_solver = UniversalChallengeSolver(bq, max_submissions=args.max_submissions)
    submission_manager = SubmissionManager(max_submissions=args.max_submissions)

    # Determine challenge type
    if args.challenge == "auto":
        challenge_type = universal_solver.detect_challenge_type(circuit, "")
        print(f"\nAuto-detected: {challenge_type.value}")
    else:
        challenge_type_map = {
            "peaked": ChallengeType.PEAKED_CIRCUIT,
            "qaoa": ChallengeType.QAOA_MAXCUT,
            "vqe": ChallengeType.VQE_GROUND_STATE,
        }
        challenge_type = challenge_type_map[args.challenge]
        print(f"\nManual: {challenge_type.value}")

    # Execute
    print(f"\n{'=' * 70}")
    print("Executing Strategy")
    print(f"{'=' * 70}")

    start_time = time.time()

    result = universal_solver.solve(
        circuit, description=challenge_type.value, graph_edges=graph_edges, hamiltonian=hamiltonian
    )

    elapsed = time.time() - start_time

    print(f"\n✓ Execution complete in {elapsed:.2f}s")
    print(f"\nResult:")
    print(json.dumps(result, indent=2))

    # Validate and submit
    if not args.dry_run:
        print(f"\n{'=' * 70}")
        print("Validating and Submitting")
        print(f"{'=' * 70}")

        submission = submission_manager.validate_and_submit(
            result, confidence_threshold=args.confidence
        )

        if submission:
            print(f"\n✅ SUBMISSION SUCCESSFUL")
            print(f"   Submission #{submission['number']}")
        else:
            print(f"\n❌ SUBMISSION BLOCKED")
            print(f"   Review validation warnings and retry")
    else:
        print(f"\n⚠️ DRY RUN - Not submitted")
        validation = submission_manager.pre_validate(result)
        print(f"Would {'SUBMIT' if validation.recommendation == 'SUBMIT' else 'NOT SUBMIT'}")

    # Save results
    output = {
        "challenge_type": challenge_type.value,
        "circuit_file": args.circuit,
        "result": result,
        "runtime": elapsed,
        "timestamp": time.time(),
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Results saved: {args.output}")

    # Summary
    status = submission_manager.get_status()
    print(f"\n{'=' * 70}")
    print("Summary")
    print(f"{'=' * 70}")
    print(f"Submissions used: {status['used']}/{status['max']}")
    print(f"Remaining: {status['remaining']}")

    return result


if __name__ == "__main__":
    main()
