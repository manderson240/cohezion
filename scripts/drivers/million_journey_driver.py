"""25 Million Agent Journey Capture Simulation Driver.

Orchestrates massive-scale (25M) agent journey simulations with streaming
Parquet output and checkpoint/resume capability.

Architecture:
    - Async worker pools for parallel processing
    - Streaming Parquet shards (100K records each)
    - Checkpoint every 100K simulations for fault tolerance
    - Resource-aware throttling
    - Prometheus metrics + email reports

Usage:
    python -m scripts.drivers.million_journey_driver --target 25_000_000
    python -m scripts.drivers.million_journey_driver --resume --checkpoint 1000000

"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import psutil


logger = logging.getLogger(__name__)


@dataclass
class DriverConfig:
    """Configuration for the Million Journey Driver."""

    target_simulations: int = 25_000_000
    batch_size: int = 10_000
    shard_size: int = 100_000
    checkpoint_interval: int = 100_000
    worker_count: int = 8
    output_dir: Path = field(default_factory=lambda: Path("data/journeys"))
    checkpoint_dir: Path = field(default_factory=lambda: Path("data/journeys/checkpoints"))
    enable_metrics: bool = True
    metrics_port: int = 9090
    email_interval_minutes: int = 30
    cpu_threshold: float = 85.0
    ram_threshold: float = 75.0
    compression: str = "zstd"
    resume_from: int | None = None


@dataclass
class SimulationResult:
    """Result of a single simulation."""

    sim_id: str
    timestamp: float
    trajectory_12d: list[float]
    coherence: float
    efficiency: float
    operation_type: str
    phi_score: float
    success: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Checkpoint:
    """Checkpoint state for resume capability."""

    total_completed: int
    timestamp: float
    last_shard_file: str | None
    config: dict[str, Any]


class BatchProcessor:
    """Process simulation batches with worker pools."""

    def __init__(self, config: DriverConfig):
        self.config = config
        self.queue: asyncio.Queue[tuple[int, int]] = asyncio.Queue()
        self.results_queue: asyncio.Queue[list[SimulationResult]] = asyncio.Queue()
        self.completed_count = 0
        self._shutdown = False

    async def generate_batch(
        self,
        batch_id: int,
        start_idx: int,
        count: int,
    ) -> list[SimulationResult]:
        """Generate a batch of trajectory simulations."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker(seed=batch_id)
        results = []

        for i in range(count):
            sim_id = f"{batch_id}_{i}"

            # Generate synthetic execution result metrics
            coherence = 0.5 + 0.4 * np.random.random()
            efficiency = 0.5 + 0.4 * np.random.random()
            phi = coherence * 0.5 + efficiency * 0.3 + 0.2 * np.random.random()

            # Generate 12D trajectory using JourneyTracker
            task_desc = f"synthetic_task_{batch_id}_{i}"
            latent = tracker.text_to_latent(task_desc)
            projection = tracker.holographic_project(latent)

            # Apply operation modulation (random for synthetic data)
            operation = np.random.choice(["generate", "analyze", "search", "transform"])
            modulation = tracker._modulation_profiles.get(
                operation, tracker._modulation_profiles["transform"]
            )
            quality_weight = 0.5 * coherence + 0.5 * efficiency
            trajectory = projection * (1.0 - quality_weight) + modulation * quality_weight
            trajectory = np.clip(trajectory, 0.0, 1.0)

            result = SimulationResult(
                sim_id=sim_id,
                timestamp=time.time(),
                trajectory_12d=trajectory.tolist(),
                coherence=float(coherence),
                efficiency=float(efficiency),
                operation_type=operation,
                phi_score=float(phi),
                success=phi > 0.5,
                metadata={"batch_id": batch_id, "index": start_idx + i},
            )
            results.append(result)

        return results

    async def worker(self, worker_id: int):
        """Worker coroutine that processes batches from the queue."""
        logger.debug(f"Worker {worker_id} started")

        while not self._shutdown:
            try:
                batch_id, batch_start = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except TimeoutError:
                continue

            try:
                # Calculate batch count (handle last partial batch)
                remaining = self.config.target_simulations - batch_start
                count = min(self.config.batch_size, remaining)

                results = await self.generate_batch(batch_id, batch_start, count)
                await self.results_queue.put(results)
                self.completed_count += count

                logger.debug(
                    f"Worker {worker_id} completed batch {batch_id} ({count} sims, total: {self.completed_count})"
                )

            except Exception as e:
                logger.error(f"Worker {worker_id} failed on batch {batch_id}: {e}")

            finally:
                self.queue.task_done()

    async def start_workers(self) -> list[asyncio.Task]:
        """Start all worker tasks."""
        workers = []
        for i in range(self.config.worker_count):
            task = asyncio.create_task(self.worker(i))
            workers.append(task)
        return workers

    def stop(self):
        """Signal workers to shutdown."""
        self._shutdown = True


class ShardPersistence:
    """Manage streaming Parquet shards."""

    def __init__(self, config: DriverConfig):
        self.config = config
        self.current_shard: list[dict] = []
        self.shard_count = 0
        self.total_records = 0
        self.output_dir = config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _to_record(self, result: SimulationResult) -> dict:
        """Convert SimulationResult to Parquet-compatible dict."""
        record = asdict(result)
        # Flatten 12D trajectory into separate columns
        for i, val in enumerate(record.pop("trajectory_12d")):
            record[f"dim_{i}"] = val
        return record

    def add_result(self, result: SimulationResult):
        """Add a result to the current shard."""
        self.current_shard.append(self._to_record(result))
        self.total_records += 1

        if len(self.current_shard) >= self.config.shard_size:
            self._flush_shard()

    def _flush_shard(self):
        """Write current shard to Parquet file."""
        if not self.current_shard:
            return None

        import pyarrow as pa
        import pyarrow.parquet as pq

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"shard_{timestamp}_{self.shard_count:04d}.parquet"

        # Convert to PyArrow table
        table = pa.Table.from_pylist(self.current_shard)

        # Write with compression
        pq.write_table(
            table,
            filename,
            compression=self.config.compression,
            use_dictionary=True,
            write_statistics=True,
        )

        logger.info(
            f"Flushed shard {self.shard_count}: {len(self.current_shard)} records to {filename}"
        )

        self.shard_count += 1
        self.current_shard = []

        return str(filename)

    def close(self) -> str | None:
        """Flush remaining records and return last filename."""
        return self._flush_shard()


class CheckpointManager:
    """Manage checkpoint and resume capability."""

    def __init__(self, config: DriverConfig):
        self.config = config
        self.checkpoint_dir = config.checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        total_completed: int,
        last_shard_file: str | None,
    ) -> Path:
        """Save checkpoint state."""
        # Convert config Path objects to strings for JSON serialization
        config_dict = {}
        for k, v in self.config.__dict__.items():
            if isinstance(v, Path):
                config_dict[k] = str(v)
            else:
                config_dict[k] = v

        checkpoint = Checkpoint(
            total_completed=total_completed,
            timestamp=time.time(),
            last_shard_file=last_shard_file,
            config=config_dict,
        )

        filename = self.checkpoint_dir / f"checkpoint_{total_completed:010d}.jsonl"
        with open(filename, "w") as f:
            json.dump(checkpoint.__dict__, f)

        logger.info(f"Saved checkpoint: {total_completed} simulations")
        return filename

    def load_checkpoint(self, resume_count: int | None = None) -> Checkpoint | None:
        """Load most recent checkpoint or specific count."""
        if resume_count:
            filename = self.checkpoint_dir / f"checkpoint_{resume_count:010d}.jsonl"
            if not filename.exists():
                return None
        else:
            # Find most recent checkpoint
            checkpoints = list(self.checkpoint_dir.glob("checkpoint_*.jsonl"))
            if not checkpoints:
                return None
            filename = max(checkpoints, key=lambda p: p.stat().st_mtime)

        with open(filename) as f:
            data = json.load(f)

        # Convert config dict back to Path objects
        config_data = data.get("config", {})
        if "output_dir" in config_data:
            config_data["output_dir"] = Path(config_data["output_dir"])
        if "checkpoint_dir" in config_data:
            config_data["checkpoint_dir"] = Path(config_data["checkpoint_dir"])

        return Checkpoint(
            total_completed=data["total_completed"],
            timestamp=data["timestamp"],
            last_shard_file=data.get("last_shard_file"),
            config=config_data,
        )

    def list_checkpoints(self) -> list[Path]:
        """List all available checkpoints."""
        return sorted(self.checkpoint_dir.glob("checkpoint_*.jsonl"))


class MetricsCollector:
    """Collect and report metrics."""

    def __init__(self, config: DriverConfig):
        self.config = config
        self.start_time = time.time()
        self.start_count = 0

    def get_stats(self, current_count: int) -> dict[str, Any]:
        """Get current statistics."""
        elapsed = time.time() - self.start_time
        processed = current_count - self.start_count

        sims_per_sec = processed / elapsed if elapsed > 0 else 0
        eta_seconds = (
            (self.config.target_simulations - current_count) / sims_per_sec
            if sims_per_sec > 0
            else 0
        )

        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage(str(self.config.output_dir)).percent

        return {
            "total_completed": current_count,
            "target": self.config.target_simulations,
            "percent_complete": 100 * current_count / self.config.target_simulations,
            "elapsed_seconds": elapsed,
            "sims_per_second": sims_per_sec,
            "sims_per_hour": sims_per_sec * 3600,
            "eta_seconds": eta_seconds,
            "eta_formatted": str(datetime.fromtimestamp(time.time() + eta_seconds)),
            "cpu_percent": cpu,
            "ram_percent": ram,
            "disk_percent": disk,
        }

    def log_progress(self, current_count: int):
        """Log current progress."""
        stats = self.get_stats(current_count)
        logger.info(
            f"Progress: {current_count:,}/{self.config.target_simulations:,} "
            f"({stats['percent_complete']:.1f}%) | "
            f"Rate: {stats['sims_per_second']:.0f} sims/sec | "
            f"ETA: {stats['eta_formatted']} | "
            f"CPU: {stats['cpu_percent']:.0f}% | RAM: {stats['ram_percent']:.0f}%"
        )
        return stats


class MillionJourneyDriver:
    """Main driver for 25M agent journey simulations."""

    def __init__(self, config: DriverConfig | None = None):
        self.config = config or DriverConfig()
        self.batch_processor = BatchProcessor(self.config)
        self.shard_persistence = ShardPersistence(self.config)
        self.checkpoint_manager = CheckpointManager(self.config)
        self.metrics = MetricsCollector(self.config)

        self._shutdown_requested = False
        self._current_count = 0

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.warning(f"Received signal {signum}, initiating graceful shutdown...")
        self._shutdown_requested = True
        self.batch_processor.stop()

    async def run(self):
        """Main execution loop."""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Check for resume
        if self.config.resume_from:
            checkpoint = self.checkpoint_manager.load_checkpoint(self.config.resume_from)
        else:
            checkpoint = self.checkpoint_manager.load_checkpoint()

        if checkpoint:
            logger.info(f"Resuming from checkpoint: {checkpoint.total_completed} simulations")
            self._current_count = checkpoint.total_completed
            self.metrics.start_count = checkpoint.total_completed
        else:
            logger.info(f"Starting fresh: {self.config.target_simulations:,} simulations")

        # Start workers
        worker_tasks = await self.batch_processor.start_workers()

        # Queue batches
        batch_id = 0
        next_checkpoint = self._current_count + self.config.checkpoint_interval
        last_report_time = time.time()

        try:
            while (
                self._current_count < self.config.target_simulations
                and not self._shutdown_requested
            ):
                # Resource throttling
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent

                if cpu > self.config.cpu_threshold or ram > self.config.ram_threshold:
                    logger.warning(f"Throttling: CPU {cpu:.0f}%, RAM {ram:.0f}%")
                    await asyncio.sleep(1)
                    continue

                # Queue more batches if needed
                while (
                    self.batch_processor.queue.qsize() < self.config.worker_count * 2
                    and self._current_count
                    + (self.batch_processor.queue.qsize() * self.config.batch_size)
                    < self.config.target_simulations
                ):
                    await self.batch_processor.queue.put((batch_id, self._current_count))
                    batch_id += 1
                    self._current_count += self.config.batch_size

                # Process results
                try:
                    results = self.batch_processor.results_queue.get_nowait()
                    for result in results:
                        self.shard_persistence.add_result(result)
                except asyncio.QueueEmpty:
                    pass

                # Periodic checkpoint
                actual_completed = self.batch_processor.completed_count
                if actual_completed >= next_checkpoint:
                    last_shard = self.shard_persistence.close()
                    self.checkpoint_manager.save_checkpoint(actual_completed, last_shard)
                    next_checkpoint = actual_completed + self.config.checkpoint_interval

                # Periodic progress report
                if time.time() - last_report_time > 30:
                    self.metrics.log_progress(actual_completed)
                    last_report_time = time.time()

                await asyncio.sleep(0.01)  # Yield control

        except Exception as e:
            logger.error(f"Main loop error: {e}")
            raise

        finally:
            # Wait for workers to finish
            logger.info("Waiting for workers to complete...")
            await self.batch_processor.queue.join()

            # Cancel worker tasks
            for task in worker_tasks:
                task.cancel()

            # Final flush
            last_shard = self.shard_persistence.close()

            # Final checkpoint
            final_count = self.batch_processor.completed_count
            self.checkpoint_manager.save_checkpoint(final_count, last_shard)

            # Final report
            stats = self.metrics.log_progress(final_count)
            logger.info(f"Run complete! Total: {final_count:,} simulations")

            return stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="25M Agent Journey Simulation Driver")
    parser.add_argument("--target", type=int, default=25_000_000, help="Target simulation count")
    parser.add_argument("--batch-size", type=int, default=10_000, help="Batch size")
    parser.add_argument("--workers", type=int, default=8, help="Worker count")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/journeys"), help="Output directory"
    )
    parser.add_argument("--resume", action="store_true", help="Resume from latest checkpoint")
    parser.add_argument("--checkpoint", type=int, help="Resume from specific checkpoint count")
    parser.add_argument("--shard-size", type=int, default=100_000, help="Records per Parquet shard")
    parser.add_argument(
        "--checkpoint-interval", type=int, default=100_000, help="Checkpoint interval"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    config = DriverConfig(
        target_simulations=args.target,
        batch_size=args.batch_size,
        shard_size=args.shard_size,
        checkpoint_interval=args.checkpoint_interval,
        worker_count=args.workers,
        output_dir=args.output_dir,
        resume_from=args.checkpoint if args.checkpoint else (0 if args.resume else None),
    )

    driver = MillionJourneyDriver(config)
    asyncio.run(driver.run())


if __name__ == "__main__":
    main()
