"""
BlueQubit Complete SDK Reference Template
All SDK methods documented with working examples
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import bluequbit
import qiskit


class BlueQubitSDKReference:
    """Complete reference for BlueQubit SDK methods."""

    def __init__(self):
        """Initialize with credentials from project root."""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        load_dotenv(project_root / ".env")
        self.bq = bluequbit.init()
        print("✓ BlueQubit client initialized")

    # ============================================================
    # CORE EXECUTION METHODS
    # ============================================================

    def example_run(self):
        """
        METHOD: run(circuit, device, **kwargs)

        Execute a quantum circuit on specified device.

        Parameters:
        - circuit: Qiskit QuantumCircuit
        - device: "mps.cpu", "mps.gpu", "pauli-path", "ibm.heron", "quantinuum.h2"
        - shots: int (required for >17 qubits)
        - asynchronous: bool (default False)
        - options: dict (e.g., {"mps_bond_dimension": 64})

        Returns:
        - JobResult object with get_counts(), get_statevector() methods

        Status: ✓ TESTED AND WORKING
        """
        qc = qiskit.QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure_all()

        # Basic execution
        result = self.bq.run(qc, device="mps.cpu")
        counts = result.get_counts()

        # With options
        result = self.bq.run(qc, device="mps.cpu", options={"mps_bond_dimension": 64})

        # With shots (required for >17 qubits)
        result = self.bq.run(qc, device="mps.cpu", shots=1024)

        return counts

    def example_async_execution(self):
        """
        METHOD: run(circuit, asynchronous=True) + wait(job_id)

        Non-blocking circuit execution.

        Parameters:
        - asynchronous: True for non-blocking

        Returns:
        - Job object with job_id, run_status
        - Use bq.wait(job_id) to get results

        Status: ✓ TESTED AND WORKING
        """
        qc = qiskit.QuantumCircuit(5)
        qc.h(0)
        for i in range(4):
            qc.cx(i, i + 1)
        qc.measure_all()

        # Submit asynchronously
        job = self.bq.run(qc, device="mps.cpu", asynchronous=True)
        print(f"Job ID: {job.job_id}")

        # Do other work...

        # Wait for completion
        result = self.bq.wait(job.job_id)
        counts = result.get_counts()

        return counts

    async def example_run_native_async(self):
        """
        METHOD: run_native_async(circuit, device)

        Native async/await execution (returns coroutine).

        Parameters:
        - Same as run()

        Returns:
        - Coroutine that resolves to JobResult

        Status: ✓ TESTED (returns coroutine, requires await)
        """
        qc = qiskit.QuantumCircuit(3)
        qc.h(0)
        qc.measure_all()

        # Returns coroutine - must be awaited
        coroutine = self.bq.run_native_async(qc, device="mps.cpu")
        result = await coroutine

        return result.get_counts()

    # ============================================================
    # JOB MANAGEMENT METHODS
    # ============================================================

    def example_get(self):
        """
        METHOD: get(job_id)

        Retrieve job results by ID.

        Parameters:
        - job_id: str

        Returns:
        - JobResult object

        Status: ✓ TESTED AND WORKING
        """
        # First submit a job
        qc = qiskit.QuantumCircuit(2)
        qc.h(0)
        qc.measure_all()

        job = self.bq.run(qc, device="mps.cpu", asynchronous=True)

        # Later, retrieve results
        import time

        time.sleep(2)
        result = self.bq.get(job.job_id)

        return result.get_counts()

    def example_cancel(self):
        """
        METHOD: cancel(job_id)

        Cancel a running job.

        Parameters:
        - job_id: str

        Returns:
        - Success/Failure

        Status: ⚠ TESTED (may race with completion)

        Note: Best for long-running jobs. May fail if job completes first.
        """
        qc = qiskit.QuantumCircuit(15)
        qc.h(0)
        for i in range(14):
            qc.cx(i, i + 1)
        qc.measure_all()

        job = self.bq.run(qc, device="mps.cpu", asynchronous=True)

        try:
            self.bq.cancel(job.job_id)
            print("✓ Job cancelled")
        except Exception as e:
            print(f"ℹ Job may have completed: {e}")

    def example_search(self):
        """
        METHOD: search()

        Search recent jobs (no parameters).

        Returns:
        - List of recent jobs

        Status: ✓ TESTED AND WORKING

        Note: Previous attempt with 'limit' parameter failed.
        """
        jobs = self.bq.search()
        print(f"✓ Found {len(jobs)} recent jobs")
        return jobs

    # ============================================================
    # ESTIMATION AND VALIDATION METHODS
    # ============================================================

    def example_estimate(self):
        """
        METHOD: estimate(circuit, device)

        Estimate cost and runtime before execution.

        Parameters:
        - circuit: Qiskit QuantumCircuit
        - device: str

        Returns:
        - Estimate object with runtime and cost

        Status: ✓ TESTED AND WORKING
        """
        qc = qiskit.QuantumCircuit(10)
        qc.h(0)
        for i in range(9):
            qc.cx(i, i + 1)
        qc.measure_all()

        estimate = self.bq.estimate(qc, device="mps.cpu")
        print(f"✓ Estimated: {estimate}")

        return estimate

    def example_validate_device(self):
        """
        METHOD: validate_device(device)

        Validate device name.

        Parameters:
        - device: str

        Returns:
        - Validated device name

        Status: ✓ TESTED AND WORKING
        """
        result = self.bq.validate_device("mps.cpu")
        print(f"✓ Device validated: {result}")
        return result

    def example_validate_circuit_type(self):
        """
        METHOD: validate_circuit_type(circuit, device)

        Validate circuit for device.

        Parameters:
        - circuit: Qiskit QuantumCircuit
        - device: str

        Status: ? NOT FULLY TESTED (requires device parameter)
        """
        qc = qiskit.QuantumCircuit(2)
        qc.h(0)

        try:
            result = self.bq.validate_circuit_type(qc, "mps.cpu")
            print(f"✓ Circuit validated: {result}")
        except Exception as e:
            print(f"ℹ validate_circuit_type: {e}")

    # ============================================================
    # SPECIALIZED METHODS
    # ============================================================

    def example_get_peaked_circuit(self):
        """
        METHOD: get_peaked_circuit(difficulty)

        Get peaked circuit for challenge.

        Parameters:
        - difficulty: int (1-10 or higher)

        Returns:
        - Circuit object

        Status: ⚠ TESTED (403 Forbidden - likely requires active challenge)

        Note: This method may only work during active challenges.
        """
        for difficulty in [1, 5, 10]:
            try:
                circuit = self.bq.get_peaked_circuit(difficulty)
                print(f"✓ Difficulty {difficulty}: {circuit.num_qubits} qubits")
                return circuit
            except Exception as e:
                print(f"ℹ Difficulty {difficulty}: {type(e).__name__}")

        print("⚠ get_peaked_circuit() requires active challenge access")

    # ============================================================
    # UTILITY PROPERTIES
    # ============================================================

    def example_name_property(self):
        """
        PROPERTY: name

        Get client name.

        Status: ✓ TESTED (returns bound method, not string)
        """
        name = self.bq.name
        print(f"✓ Client name: {name}")
        return name

    # ============================================================
    # RESULT METHODS
    # ============================================================

    def example_result_methods(self):
        """
        RESULT METHODS: get_counts(), get_statevector()

        Get results from execution.

        IMPORTANT:
        - get_counts(): Requires shots > 0 or no measurement
        - get_statevector(): Requires shots = 0 (no measurement)

        Status: ✓ TESTED AND WORKING
        """
        # For statevector (no measurement)
        qc_sv = qiskit.QuantumCircuit(2)
        qc_sv.h(0)
        qc_sv.cx(0, 1)

        result = self.bq.run(qc_sv, device="mps.cpu")
        try:
            statevector = result.get_statevector()
            print(f"✓ Statevector shape: {statevector.shape}")
        except Exception as e:
            print(f"ℹ Statevector: {e}")

        # For counts (with measurement)
        qc_counts = qiskit.QuantumCircuit(2)
        qc_counts.h(0)
        qc_counts.cx(0, 1)
        qc_counts.measure_all()

        result = self.bq.run(qc_counts, device="mps.cpu", shots=1024)
        counts = result.get_counts()
        print(f"✓ Counts: {counts}")

        return counts


def run_all_examples():
    """Execute all SDK examples."""
    print("=" * 70)
    print("BlueQubit SDK Complete Reference")
    print("=" * 70)

    ref = BlueQubitSDKReference()

    examples = [
        ("Basic Execution", ref.example_run),
        ("Async Execution", ref.example_async_execution),
        ("Get Results", ref.example_get),
        ("Cancel Job", ref.example_cancel),
        ("Search Jobs", ref.example_search),
        ("Estimate Cost", ref.example_estimate),
        ("Validate Device", ref.example_validate_device),
        ("Result Methods", ref.example_result_methods),
        ("Name Property", ref.example_name_property),
        ("Peaked Circuit", ref.example_get_peaked_circuit),
        ("Validate Circuit", ref.example_validate_circuit_type),
    ]

    for name, example in examples:
        print(f"\n{'=' * 70}")
        print(f"Example: {name}")
        print(f"{'=' * 70}")
        try:
            example()
        except Exception as e:
            print(f"✗ Error: {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    print("SDK Reference Complete")
    print("=" * 70)


if __name__ == "__main__":
    run_all_examples()
