"""1-Hour Omnibus Test Runner.

Runs Omnibus for 1 hour with real-time monitoring and memory tracking.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Any


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler("data/logs/omnibus_1hour_test.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class OneHourTest:
    """Test runner for 1-hour Omnibus test."""

    def __init__(self):
        """Initialize test."""
        self.start_time = None
        self.end_time = None
        self.cycle_count = 0
        self.memory_samples = []
        self.gateway_events = []
        self.running = False

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Start memory tracing
        tracemalloc.start()

        logger.info("=" * 70)
        logger.info("🌟 OMNIBUS 1-HOUR TEST INITIATED")
        logger.info("=" * 70)
        logger.info("Target: Run for 3600 seconds (1 hour)")
        logger.info("Monitoring: Memory, cycles, gateway health")
        logger.info("=" * 70)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("\n🛑 Shutdown signal received, finishing gracefully...")
        self.running = False

    async def run_test(self) -> dict[str, Any]:
        """Run 1-hour test."""
        self.start_time = time.time()
        self.end_time = self.start_time + 3600  # 1 hour
        self.running = True

        # Import here to minimize startup memory
        from cohezion.gateways.omnibus import Omnibus

        logger.info("🔧 Initializing Omnibus...")
        omnibus = Omnibus()

        logger.info("🚀 Starting 1-hour test cycle...")
        logger.info("(Press Ctrl+C to stop early)\n")

        # Initial status
        self._log_status(omnibus)

        try:
            while self.running and time.time() < self.end_time:
                cycle_start = time.time()

                # Run one cycle
                await omnibus.run_master_cycle()
                self.cycle_count += 1

                # Sample memory every 10 cycles
                if self.cycle_count % 10 == 0:
                    self._sample_memory()

                # Log status every 5 cycles
                if self.cycle_count % 5 == 0:
                    self._log_status(omnibus)

                # Show progress
                elapsed = time.time() - self.start_time
                remaining = 3600 - elapsed
                progress = (elapsed / 3600) * 100

                logger.info(
                    f"⏱️  Progress: {progress:.1f}% | "
                    f"Cycles: {self.cycle_count} | "
                    f"Remaining: {remaining / 60:.1f} min"
                )

                # Wait before next cycle (10 min interval)
                await asyncio.sleep(600)

        except Exception as e:
            logger.error(f"Test error: {e}", exc_info=True)
        finally:
            await self._finish_test(omnibus)

        return self._generate_report(omnibus)

    def _sample_memory(self) -> None:
        """Sample current memory usage."""
        current, peak = tracemalloc.get_traced_memory()
        self.memory_samples.append(
            {
                "timestamp": datetime.now().isoformat(),
                "cycle": self.cycle_count,
                "current_mb": current / 1024 / 1024,
                "peak_mb": peak / 1024 / 1024,
            }
        )

    def _log_status(self, omnibus) -> None:
        """Log current status."""
        status = omnibus.get_master_status()
        logger.info(f"📊 Gateway Health: {status['total_health']:.1%}")
        logger.info(f"   Unlocked: {status['gateways_unlocked']}/9")
        logger.info(f"   Cycles: {status['omnibus_cycles']}")

    async def _finish_test(self, omnibus) -> None:
        """Finish test gracefully."""
        logger.info("\n" + "=" * 70)
        logger.info("🛑 TEST COMPLETING")
        logger.info("=" * 70)

        omnibus.stop()
        tracemalloc.stop()

        self.end_time = time.time()

    def _generate_report(self, omnibus) -> dict[str, Any]:
        """Generate final test report."""
        duration = self.end_time - self.start_time

        # Memory stats
        avg_memory = sum(m["current_mb"] for m in self.memory_samples) / max(
            len(self.memory_samples), 1
        )
        peak_memory = max((m["peak_mb"] for m in self.memory_samples), default=0)

        # Gateway status
        final_status = omnibus.get_master_status()

        report = {
            "test_duration_seconds": duration,
            "test_duration_minutes": duration / 60,
            "cycles_completed": self.cycle_count,
            "memory": {
                "average_mb": round(avg_memory, 2),
                "peak_mb": round(peak_memory, 2),
                "samples": len(self.memory_samples),
            },
            "gateways": {
                "unlocked": final_status["gateways_unlocked"],
                "total_health": round(final_status["total_health"], 3),
                "individual": final_status["gateways"],
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Save report
        report_path = Path("data/reports/omnibus_1hour_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        # Print summary
        logger.info("\n" + "=" * 70)
        logger.info("📊 FINAL REPORT")
        logger.info("=" * 70)
        logger.info(f"Duration: {duration / 60:.1f} minutes")
        logger.info(f"Cycles: {self.cycle_count}")
        logger.info(f"Avg Memory: {avg_memory:.2f} MB")
        logger.info(f"Peak Memory: {peak_memory:.2f} MB")
        logger.info(f"Gateways Unlocked: {final_status['gateways_unlocked']}/9")
        logger.info(f"Health Score: {final_status['total_health']:.1%}")
        logger.info(f"Report saved: {report_path}")
        logger.info("=" * 70)

        return report


async def main():
    """Main entry point."""
    test = OneHourTest()
    report = await test.run_test()

    # Exit with success if we ran for at least 55 minutes
    if report["test_duration_minutes"] >= 55:
        logger.info("✅ TEST PASSED - Ran for full hour")
        return 0
    else:
        logger.warning("⚠️  TEST INCOMPLETE - Stopped early")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
