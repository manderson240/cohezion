"""
BlueQubit Job Monitor
Real-time monitoring and dashboard for hackathon submissions
"""

import json
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import bluequbit
from dotenv import load_dotenv


@dataclass
class JobMetrics:
    """Metrics for a single job."""

    job_id: str
    submit_time: datetime
    start_time: datetime | None = None
    end_time: datetime | None = None
    device: str = ""
    n_qubits: int = 0
    shots: int = 0
    status: str = "pending"
    runtime_seconds: float | None = None
    cost: float | None = None
    error: str | None = None


class JobMonitor:
    """
    Monitor BlueQubit jobs with real-time updates.

    Features:
    - Track job status in real-time
    - Monitor costs and runtime
    - Alert on failures
    - Export metrics
    """

    def __init__(self, log_file: str = "job_monitor.jsonl"):
        """Initialize job monitor."""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        load_dotenv(project_root / ".env")

        self.bq = bluequbit.init()
        self.log_file = Path(log_file)
        self.jobs: dict[str, JobMetrics] = {}
        self.running = False
        self.monitor_thread: threading.Thread | None = None
        self.callbacks: list[Callable] = []

        print("✓ JobMonitor initialized")

    def add_job(
        self, job_id: str, device: str, n_qubits: int, shots: int, metadata: dict | None = None
    ) -> JobMetrics:
        """Add a job to monitor."""
        metrics = JobMetrics(
            job_id=job_id,
            submit_time=datetime.now(),
            device=device,
            n_qubits=n_qubits,
            shots=shots,
            status="submitted",
        )

        self.jobs[job_id] = metrics
        self._log_event("job_added", asdict(metrics))

        return metrics

    def update_job(
        self,
        job_id: str,
        status: str = None,
        runtime: float = None,
        cost: float = None,
        error: str = None,
    ):
        """Update job metrics."""
        if job_id not in self.jobs:
            return

        job = self.jobs[job_id]

        if status:
            job.status = status
            if status == "running" and not job.start_time:
                job.start_time = datetime.now()
            elif status in ["completed", "failed", "cancelled"]:
                job.end_time = datetime.now()
                if job.start_time:
                    job.runtime_seconds = (job.end_time - job.start_time).total_seconds()

        if runtime:
            job.runtime_seconds = runtime

        if cost:
            job.cost = cost

        if error:
            job.error = error
            job.status = "failed"

        self._log_event("job_updated", asdict(job))

        # Trigger callbacks
        for callback in self.callbacks:
            try:
                callback(job)
            except Exception as e:
                print(f"Callback error: {e}")

    def start_monitoring(self, poll_interval: int = 5):
        """Start background monitoring thread."""
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(poll_interval,), daemon=True
        )
        self.monitor_thread.start()
        print(f"✓ Started monitoring (poll interval: {poll_interval}s)")

    def stop_monitoring(self):
        """Stop background monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        print("✓ Stopped monitoring")

    def _monitor_loop(self, poll_interval: int):
        """Background monitoring loop."""
        while self.running:
            pending_jobs = [
                job_id
                for job_id, job in self.jobs.items()
                if job.status in ["submitted", "running"]
            ]

            for job_id in pending_jobs:
                try:
                    # Check job status via SDK
                    result = self.bq.get(job_id)

                    # If we got here without error, job completed
                    self.update_job(job_id, status="completed")

                except Exception as e:
                    # Job still running or other error
                    if "not completed" in str(e).lower():
                        self.update_job(job_id, status="running")
                    else:
                        self.update_job(job_id, error=str(e))

            time.sleep(poll_interval)

    def get_summary(self) -> dict:
        """Get summary of all jobs."""
        total = len(self.jobs)
        completed = sum(1 for j in self.jobs.values() if j.status == "completed")
        failed = sum(1 for j in self.jobs.values() if j.status == "failed")
        running = sum(1 for j in self.jobs.values() if j.status == "running")
        pending = sum(1 for j in self.jobs.values() if j.status == "submitted")

        total_cost = sum(j.cost or 0 for j in self.jobs.values())
        total_runtime = sum(j.runtime_seconds or 0 for j in self.jobs.values())

        return {
            "total_jobs": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "total_cost": total_cost,
            "total_runtime_seconds": total_runtime,
            "success_rate": completed / total if total > 0 else 0,
        }

    def print_dashboard(self):
        """Print real-time dashboard."""
        summary = self.get_summary()

        print("\n" + "=" * 70)
        print("BlueQubit Job Monitor Dashboard")
        print("=" * 70)
        print(f"Total Jobs: {summary['total_jobs']}")
        print(f"  ✓ Completed: {summary['completed']}")
        print(f"  ✗ Failed: {summary['failed']}")
        print(f"  ⏳ Running: {summary['running']}")
        print(f"  ⏸ Pending: {summary['pending']}")
        print(f"\nSuccess Rate: {summary['success_rate']:.1%}")
        print(f"Total Runtime: {summary['total_runtime_seconds']:.1f}s")
        print(f"Total Cost: ${summary['total_cost']:.2f}")

        if self.jobs:
            print("\nRecent Jobs:")
            for job in list(self.jobs.values())[-5:]:
                runtime_str = f"{job.runtime_seconds:.1f}s" if job.runtime_seconds else "N/A"
                print(f"  {job.job_id[:12]}... [{job.status:12}] {runtime_str:>8} {job.device}")

        print("=" * 70)

    def export_metrics(self, filename: str = "job_metrics.json"):
        """Export all metrics to JSON."""
        data = {
            "export_time": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "jobs": [asdict(job) for job in self.jobs.values()],
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=2, default=str)

        print(f"✓ Exported metrics to {filename}")

    def on_status_change(self, callback: Callable):
        """Register callback for status changes."""
        self.callbacks.append(callback)

    def _log_event(self, event_type: str, data: dict):
        """Log event to file."""
        event = {"timestamp": datetime.now().isoformat(), "event_type": event_type, "data": data}

        with open(self.log_file, "a") as f:
            f.write(json.dumps(event, default=str) + "\n")


class PerformanceProfiler:
    """Profile circuit execution performance."""

    def __init__(self):
        """Initialize profiler."""
        self.measurements: list[dict] = []

    def profile_execution(self, circuit_func, *args, **kwargs) -> dict:
        """Profile a circuit execution."""
        import time

        start = time.time()
        try:
            result = circuit_func(*args, **kwargs)
            end = time.time()

            measurement = {
                "function": circuit_func.__name__,
                "runtime": end - start,
                "success": True,
                "args": str(args),
                "kwargs": str(kwargs),
            }

        except Exception as e:
            end = time.time()
            measurement = {
                "function": circuit_func.__name__,
                "runtime": end - start,
                "success": False,
                "error": str(e),
            }

        self.measurements.append(measurement)
        return measurement

    def get_performance_report(self) -> dict:
        """Generate performance report."""
        if not self.measurements:
            return {}

        successful = [m for m in self.measurements if m["success"]]
        failed = [m for m in self.measurements if not m["success"]]

        if successful:
            runtimes = [m["runtime"] for m in successful]
            avg_runtime = sum(runtimes) / len(runtimes)
            min_runtime = min(runtimes)
            max_runtime = max(runtimes)
        else:
            avg_runtime = min_runtime = max_runtime = 0

        return {
            "total_executions": len(self.measurements),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.measurements),
            "average_runtime": avg_runtime,
            "min_runtime": min_runtime,
            "max_runtime": max_runtime,
        }


# Example usage
def demo_monitor():
    """Demonstrate job monitoring."""
    print("=" * 70)
    print("BlueQubit Job Monitor Demo")
    print("=" * 70)

    monitor = JobMonitor(log_file="demo_monitor.jsonl")

    # Simulate adding jobs
    job_ids = [f"job_{i:03d}" for i in range(5)]
    for i, job_id in enumerate(job_ids):
        monitor.add_job(job_id=job_id, device="mps.cpu", n_qubits=10 + i * 2, shots=10000)

        # Simulate status progression
        time.sleep(0.1)
        monitor.update_job(job_id, status="running", runtime=5.0 + i * 2)
        time.sleep(0.1)
        monitor.update_job(job_id, status="completed", runtime=15.0 + i * 3, cost=0.0)

    # Print dashboard
    monitor.print_dashboard()

    # Export metrics
    monitor.export_metrics("demo_metrics.json")

    print("\n✓ Monitor demo complete")


if __name__ == "__main__":
    demo_monitor()
