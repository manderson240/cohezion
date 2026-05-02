"""
BlueQubit Submission Pipeline
Automated submission, monitoring, and result handling
"""

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import bluequbit
import qiskit
from dotenv import load_dotenv


@dataclass
class SubmissionResult:
    """Structured submission result."""

    job_id: str
    bitstring: str | None
    probability: float | None
    snr: float | None
    timestamp: str
    device: str
    shots: int
    status: str
    metadata: dict


class SubmissionPipeline:
    """
    End-to-end pipeline for hackathon submissions.

    Features:
    - Automated circuit submission
    - Job monitoring and status tracking
    - Result extraction and formatting
    - Submission logging
    - Retry logic for failures
    """

    def __init__(self, log_file: str = "submissions.jsonl"):
        """Initialize pipeline with logging."""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        load_dotenv(project_root / ".env")

        self.bq = bluequbit.init()
        self.log_file = Path(log_file)
        self.submissions: list[dict] = []

        print("✓ SubmissionPipeline initialized")
        print(f"  Log file: {self.log_file}")

    def submit_circuit(
        self,
        circuit: qiskit.QuantumCircuit,
        device: str = "mps.cpu",
        shots: int = 100000,
        async_mode: bool = False,
        metadata: dict | None = None,
    ) -> str:
        """
        Submit a circuit for execution.

        Args:
            circuit: Quantum circuit to execute
            device: Target device
            shots: Number of shots (required for >17 qubits)
            async_mode: Submit asynchronously
            metadata: Additional metadata to store

        Returns:
            job_id: Submission ID
        """
        print(f"\n{'=' * 60}")
        print("Submitting Circuit")
        print(f"{'=' * 60}")
        print(f"Qubits: {circuit.num_qubits}")
        print(f"Device: {device}")
        print(f"Shots: {shots}")
        print(f"Async: {async_mode}")

        # Validate circuit size
        if circuit.num_qubits > 17 and shots == 0:
            print(f"⚠ WARNING: Circuit has {circuit.num_qubits} qubits but shots=0")
            print("  Setting shots=1024 for MPS device compatibility")
            shots = 1024

        # Estimate before submission
        try:
            estimate = self.bq.estimate(circuit, device=device)
            print(f"Estimate: {estimate}")
        except Exception as e:
            print(f"ℹ Could not get estimate: {e}")

        # Submit
        if async_mode:
            job = self.bq.run(circuit, device=device, shots=shots, asynchronous=True)
            job_id = job.job_id
        else:
            result = self.bq.run(circuit, device=device, shots=shots)
            job_id = getattr(result, "job_id", "synchronous")

        # Log submission
        submission = {
            "timestamp": datetime.now().isoformat(),
            "job_id": job_id,
            "n_qubits": circuit.num_qubits,
            "device": device,
            "shots": shots,
            "async": async_mode,
            "metadata": metadata or {},
        }
        self._log_submission(submission)

        print(f"✓ Submitted: Job ID {job_id}")

        return job_id

    def monitor_job(self, job_id: str, poll_interval: int = 5, timeout: int = 600) -> dict:
        """
        Monitor job until completion.

        Args:
            job_id: Job to monitor
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            Job result dictionary
        """
        print(f"\n{'=' * 60}")
        print(f"Monitoring Job: {job_id}")
        print(f"{'=' * 60}")

        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout:
            try:
                # Try to get result (will fail if still running)
                result = self.bq.get(job_id)
                counts = result.get_counts()

                print("✓ Job completed!")
                print(f"  Runtime: {time.time() - start_time:.1f}s")
                print(f"  Distinct states: {len(counts)}")

                return {
                    "job_id": job_id,
                    "status": "completed",
                    "counts": counts,
                    "runtime_seconds": time.time() - start_time,
                }

            except Exception as e:
                # Job still running
                if "not found" in str(e).lower() or "not completed" in str(e).lower():
                    status = "running"
                    if status != last_status:
                        print(f"  Status: {status} ({int(time.time() - start_time)}s)")
                        last_status = status
                    time.sleep(poll_interval)
                else:
                    raise

        raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")

    def extract_heavy_output(
        self, counts: dict, threshold: float = 0.5
    ) -> SubmissionResult | None:
        """
        Extract heavy output from counts.

        Args:
            counts: Measurement counts dictionary
            threshold: Heavy output threshold

        Returns:
            SubmissionResult with heavy output info
        """
        import numpy as np

        n_qubits = len(list(counts.keys())[0])
        total = sum(counts.values())
        uniform_prob = 1.0 / (2**n_qubits)
        threshold_prob = threshold * uniform_prob

        # Find heavy outputs
        heavy_outputs = {}
        for bitstring, count in counts.items():
            prob = count / total if isinstance(count, (int, float)) else count
            if prob > threshold_prob:
                heavy_outputs[bitstring] = prob

        if not heavy_outputs:
            return None

        # Get top output
        top_bitstring = max(heavy_outputs, key=heavy_outputs.get)
        top_prob = heavy_outputs[top_bitstring]

        # Calculate SNR
        noise = np.sqrt(uniform_prob * (1 - uniform_prob))
        signal = top_prob - uniform_prob
        snr = signal / noise if noise > 0 else 0

        return SubmissionResult(
            job_id="extracted",
            bitstring=top_bitstring,
            probability=top_prob,
            snr=snr,
            timestamp=datetime.now().isoformat(),
            device="extracted",
            shots=total,
            status="success",
            metadata={"num_heavy": len(heavy_outputs)},
        )

    def submit_and_extract(
        self,
        circuit: qiskit.QuantumCircuit,
        device: str = "mps.cpu",
        shots: int = 100000,
        threshold: float = 0.5,
    ) -> SubmissionResult:
        """
        Complete pipeline: submit, wait, extract heavy output.

        Args:
            circuit: Circuit to execute
            device: Target device
            shots: Number of shots
            threshold: Heavy output detection threshold

        Returns:
            SubmissionResult with heavy output
        """
        # Submit
        job_id = self.submit_circuit(circuit, device=device, shots=shots)

        # Wait for completion
        result = self.monitor_job(job_id)

        # Extract heavy output
        heavy = self.extract_heavy_output(result["counts"], threshold)

        if heavy:
            heavy.job_id = job_id
            heavy.device = device
            heavy.shots = shots

            print(f"\n{'=' * 60}")
            print("Heavy Output Extracted")
            print(f"{'=' * 60}")
            print(f"Bitstring: {heavy.bitstring}")
            print(f"Probability: {heavy.probability:.6f}")
            print(f"SNR: {heavy.snr:.2f} sigma")
            print(f"{'=' * 60}")

            return heavy
        else:
            print("⚠ No heavy output found")
            return SubmissionResult(
                job_id=job_id,
                bitstring=None,
                probability=None,
                snr=None,
                timestamp=datetime.now().isoformat(),
                device=device,
                shots=shots,
                status="no_heavy_output",
                metadata={},
            )

    def _log_submission(self, submission: dict):
        """Log submission to file."""
        with open(self.log_file, "a") as f:
            f.write(json.dumps(submission) + "\n")

        self.submissions.append(submission)

    def get_submission_history(self) -> list[dict]:
        """Retrieve all submission history."""
        if self.log_file.exists():
            with open(self.log_file) as f:
                return [json.loads(line) for line in f if line.strip()]
        return []

    def export_results(self, filename: str = "hackathon_results.json"):
        """Export all results to JSON file."""
        history = self.get_submission_history()

        with open(filename, "w") as f:
            json.dump(history, f, indent=2)

        print(f"✓ Exported {len(history)} submissions to {filename}")


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("BlueQubit Submission Pipeline Test")
    print("=" * 60)

    # Initialize pipeline
    pipeline = SubmissionPipeline(log_file="test_submissions.jsonl")

    # Create test circuit (GHZ state - should have clear heavy output)
    print("\nCreating test GHZ circuit (10 qubits)...")
    qc = qiskit.QuantumCircuit(10)
    qc.h(0)
    for i in range(9):
        qc.cx(i, i + 1)
    qc.measure_all()

    # Submit and extract
    print("\nSubmitting and extracting heavy output...")
    result = pipeline.submit_and_extract(qc, device="mps.cpu", shots=10000, threshold=0.4)

    # Export results
    pipeline.export_results("test_results.json")

    print("\n✓ Pipeline test complete")
