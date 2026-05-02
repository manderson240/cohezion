"""
BlueQubit Async Execution Template
Demonstrates non-blocking job submission
"""

import time

import bluequbit
import qiskit
from dotenv import load_dotenv


def execute_async_circuit(num_qubits: int = 10):
    """
    Execute circuit asynchronously and poll for results.

    Args:
        num_qubits: Number of qubits (default: 10)

    Returns:
        dict: Measurement counts
    """
    # Load credentials from project root
    import pathlib

    project_root = pathlib.Path(__file__).parent.parent.parent.parent.parent
    load_dotenv(project_root / ".env")

    # Initialize client
    bq = bluequbit.init()

    # Build GHZ state circuit
    qc = qiskit.QuantumCircuit(num_qubits)
    qc.h(0)
    for i in range(num_qubits - 1):
        qc.cx(i, i + 1)
    qc.measure_all()

    print(f"Submitting {num_qubits}-qubit circuit asynchronously...")

    # Submit asynchronously (non-blocking)
    job = bq.run(qc, device="mps.cpu", asynchronous=True)
    print(f"Job ID: {job.job_id}")
    print(f"Status: {job.run_status}")

    # Do other work while waiting
    print("Doing other work while circuit executes...")

    # Wait for completion (blocking)
    result = bq.wait(job.job_id)
    print("\nExecution complete!")
    print(f"Results: {result.get_counts()}")

    return result


def cancel_job_example():
    """Demonstrate job cancellation."""
    import pathlib

    project_root = pathlib.Path(__file__).parent.parent.parent.parent.parent
    load_dotenv(project_root / ".env")
    bq = bluequbit.init()

    # Build large circuit
    qc = qiskit.QuantumCircuit(20)
    qc.h(0)
    for i in range(19):
        qc.cx(i, i + 1)
    qc.measure_all()

    # Submit
    job = bq.run(qc, device="mps.cpu", asynchronous=True)
    print(f"Submitted job: {job.job_id}")

    # Cancel after brief delay
    time.sleep(1)
    bq.cancel(job.job_id)
    print(f"Cancelled job: {job.job_id}")


if __name__ == "__main__":
    # Test async execution
    result = execute_async_circuit(num_qubits=10)
    print("\n✓ Async execution complete")
