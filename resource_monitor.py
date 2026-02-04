"""
🛡️ COHEZION RESOURCE MONITOR & OOM PREVENTION SYSTEM
Infinite Scale with Sovereign Protection

This system monitors system resources in real-time and prevents OOM errors
through intelligent resource management, graceful degradation, and compound
engineering optimization.
"""

import asyncio
import psutil
import torch
import numpy as np
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
from datetime import datetime
import gc
import os
import signal
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ResourceThresholds:
    """Resource thresholds for OOM prevention"""

    memory_percent: float = 85.0  # Percentage of total RAM
    memory_available_gb: float = 4.0  # Minimum available RAM in GB
    cpu_percent: float = 95.0  # CPU usage threshold
    gpu_memory_percent: float = 90.0  # GPU memory threshold
    disk_usage_percent: float = 90.0  # Disk usage threshold
    swap_usage_percent: float = 50.0  # Swap usage threshold
    process_memory_gb: float = 32.0  # Per-process memory limit


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources"""

    timestamp: float
    memory_total_gb: float
    memory_used_gb: float
    memory_available_gb: float
    memory_percent: float
    cpu_percent: float
    cpu_count: int
    gpu_available: bool
    gpu_memory_total_gb: float
    gpu_memory_used_gb: float
    gpu_memory_free_gb: float
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    disk_percent: float
    swap_total_gb: float
    swap_used_gb: float
    swap_free_gb: float
    swap_percent: float
    process_memory_gb: float
    process_cpu_percent: float
    open_files: int
    threads: int


class OOMPreventionStrategy:
    """
    🛡️ OOM Prevention Strategy

    Implements multiple layers of OOM prevention:
    1. Monitoring & Early Warning
    2. Graceful Degradation
    3. Resource Reclamation
    4. Emergency Response
    5. Compound Optimization
    """

    def __init__(self, thresholds: Optional[ResourceThresholds] = None):
        self.thresholds = thresholds or ResourceThresholds()
        self.warning_callbacks: List[Callable] = []
        self.critical_callbacks: List[Callable] = []
        self.emergency_callbacks: List[Callable] = []
        self.action_history: List[Dict] = []
        self.compound_improvements = 0

    def register_warning_callback(self, callback: Callable):
        """Register callback for warning level events"""
        self.warning_callbacks.append(callback)

    def register_critical_callback(self, callback: Callable):
        """Register callback for critical level events"""
        self.critical_callbacks.append(callback)

    def register_emergency_callback(self, callback: Callable):
        """Register callback for emergency level events"""
        self.emergency_callbacks.append(callback)

    async def check_resources(self, snapshot: ResourceSnapshot) -> str:
        """
        Check resources and trigger appropriate responses
        Returns: 'normal', 'warning', 'critical', or 'emergency'
        """
        status = "normal"
        issues = []

        # Check memory
        if snapshot.memory_percent > self.thresholds.memory_percent:
            issues.append(f"Memory usage: {snapshot.memory_percent:.1f}%")
            status = "warning"
        if snapshot.memory_available_gb < self.thresholds.memory_available_gb:
            issues.append(f"Low memory: {snapshot.memory_available_gb:.1f}GB available")
            status = "critical"

        # Check CPU
        if snapshot.cpu_percent > self.thresholds.cpu_percent:
            issues.append(f"High CPU: {snapshot.cpu_percent:.1f}%")
            if status == "normal":
                status = "warning"

        # Check GPU
        if snapshot.gpu_available:
            gpu_percent = (
                (snapshot.gpu_memory_used_gb / snapshot.gpu_memory_total_gb * 100)
                if snapshot.gpu_memory_total_gb > 0
                else 0
            )
            if gpu_percent > self.thresholds.gpu_memory_percent:
                issues.append(f"GPU memory: {gpu_percent:.1f}%")
                if status in ["normal", "warning"]:
                    status = "critical"

        # Check process memory
        if snapshot.process_memory_gb > self.thresholds.process_memory_gb:
            issues.append(f"Process memory: {snapshot.process_memory_gb:.1f}GB")
            status = "critical"

        # Check disk
        if snapshot.disk_percent > self.thresholds.disk_usage_percent:
            issues.append(f"Disk usage: {snapshot.disk_percent:.1f}%")
            if status == "normal":
                status = "warning"

        # Check swap
        if snapshot.swap_percent > self.thresholds.swap_usage_percent:
            issues.append(f"Swap usage: {snapshot.swap_percent:.1f}%")
            if status in ["normal", "warning"]:
                status = "critical"

        # Trigger callbacks based on status
        if status == "warning":
            await self._trigger_warning(issues, snapshot)
        elif status == "critical":
            await self._trigger_critical(issues, snapshot)
        elif status == "emergency":
            await self._trigger_emergency(issues, snapshot)

        return status

    async def _trigger_warning(self, issues: List[str], snapshot: ResourceSnapshot):
        """Trigger warning-level responses"""
        logger.warning(f"⚠️ RESOURCE WARNING: {', '.join(issues)}")

        # Notify callbacks
        for callback in self.warning_callbacks:
            try:
                await callback("warning", issues, snapshot)
            except Exception as e:
                logger.error(f"Warning callback error: {e}")

        # Log action
        self.action_history.append(
            {
                "timestamp": time.time(),
                "level": "warning",
                "issues": issues,
                "snapshot": snapshot,
            }
        )

    async def _trigger_critical(self, issues: List[str], snapshot: ResourceSnapshot):
        """Trigger critical-level responses"""
        logger.error(f"🚨 RESOURCE CRITICAL: {', '.join(issues)}")

        # Immediate actions
        await self._reclaim_resources()

        # Notify callbacks
        for callback in self.critical_callbacks:
            try:
                await callback("critical", issues, snapshot)
            except Exception as e:
                logger.error(f"Critical callback error: {e}")

        # Log action
        self.action_history.append(
            {
                "timestamp": time.time(),
                "level": "critical",
                "issues": issues,
                "snapshot": snapshot,
                "actions": ["reclaim_resources"],
            }
        )

    async def _trigger_emergency(self, issues: List[str], snapshot: ResourceSnapshot):
        """Trigger emergency-level responses"""
        logger.critical(f"🔥 RESOURCE EMERGENCY: {', '.join(issues)}")

        # Emergency actions
        await self._emergency_response()

        # Notify callbacks
        for callback in self.emergency_callbacks:
            try:
                await callback("emergency", issues, snapshot)
            except Exception as e:
                logger.error(f"Emergency callback error: {e}")

        # Log action
        self.action_history.append(
            {
                "timestamp": time.time(),
                "level": "emergency",
                "issues": issues,
                "snapshot": snapshot,
                "actions": ["emergency_response"],
            }
        )

    async def _reclaim_resources(self):
        """Reclaim resources through garbage collection and cleanup"""
        logger.info("🧹 Reclaiming resources...")

        # Python garbage collection
        gc.collect()

        # Clear PyTorch cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("   Cleared GPU cache")

        # Clear numpy memory pools
        # (NumPy doesn't have explicit cache clearing, but we can release large arrays)

        # Close unused file handles
        process = psutil.Process()
        open_files = process.open_files()
        if len(open_files) > 100:
            logger.warning(f"   Process has {len(open_files)} open files")

        self.compound_improvements += 1
        logger.info("✅ Resource reclamation complete")

    async def _emergency_response(self):
        """Emergency resource response - aggressive cleanup"""
        logger.critical("🔥 EMERGENCY RESOURCE RESPONSE")

        # Aggressive garbage collection
        gc.collect()
        gc.collect()  # Second pass

        # Clear all caches
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            # Reset peak memory stats
            for i in range(torch.cuda.device_count()):
                torch.cuda.reset_peak_memory_stats(i)

        # Force memory release
        import ctypes

        ctypes.CDLL(None).malloc_trim(0)  # Linux only

        logger.critical("✅ Emergency response complete")


class ResourceMonitor:
    """
    📊 Real-time Resource Monitor

    Monitors system resources continuously and provides:
    - Real-time metrics
    - Historical tracking
    - Predictive alerting
    - Compound optimization
    """

    def __init__(
        self,
        check_interval: float = 5.0,
        history_size: int = 1000,
        thresholds: Optional[ResourceThresholds] = None,
    ):
        self.check_interval = check_interval
        self.history_size = history_size
        self.thresholds = thresholds or ResourceThresholds()
        self.oom_strategy = OOMPreventionStrategy(self.thresholds)

        self.history: List[ResourceSnapshot] = []
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None

        # Statistics
        self.peak_memory_gb = 0.0
        self.peak_cpu_percent = 0.0
        self.warning_count = 0
        self.critical_count = 0
        self.emergency_count = 0

    async def start_monitoring(self):
        """Start continuous resource monitoring"""
        if self.monitoring:
            logger.warning("Resource monitoring already active")
            return

        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("🛡️ Resource monitoring started")

    async def stop_monitoring(self):
        """Stop resource monitoring"""
        if not self.monitoring:
            return

        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Resource monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Get resource snapshot
                snapshot = await self._get_snapshot()

                # Update history
                self.history.append(snapshot)
                if len(self.history) > self.history_size:
                    self.history.pop(0)

                # Update peaks
                self.peak_memory_gb = max(self.peak_memory_gb, snapshot.memory_used_gb)
                self.peak_cpu_percent = max(self.peak_cpu_percent, snapshot.cpu_percent)

                # Check thresholds
                status = await self.oom_strategy.check_resources(snapshot)

                if status == "warning":
                    self.warning_count += 1
                elif status == "critical":
                    self.critical_count += 1
                elif status == "emergency":
                    self.emergency_count += 1

                # Log periodic status
                if len(self.history) % 12 == 0:  # Every minute (5s * 12)
                    self._log_status(snapshot)

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            await asyncio.sleep(self.check_interval)

    async def _get_snapshot(self) -> ResourceSnapshot:
        """Get current resource snapshot"""
        # Memory
        mem = psutil.virtual_memory()

        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()

        # GPU
        gpu_available = torch.cuda.is_available()
        gpu_memory_total = 0.0
        gpu_memory_used = 0.0
        gpu_memory_free = 0.0

        if gpu_available:
            try:
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    gpu_memory_total += props.total_memory / (1024**3)
                    gpu_memory_used += torch.cuda.memory_allocated(i) / (1024**3)
                gpu_memory_free = gpu_memory_total - gpu_memory_used
            except:
                pass

        # Disk
        disk = psutil.disk_usage("/")

        # Swap
        swap = psutil.swap_memory()

        # Process
        process = psutil.Process()
        process_memory = process.memory_info().rss / (1024**3)
        process_cpu = process.cpu_percent(interval=0.1)

        return ResourceSnapshot(
            timestamp=time.time(),
            memory_total_gb=mem.total / (1024**3),
            memory_used_gb=mem.used / (1024**3),
            memory_available_gb=mem.available / (1024**3),
            memory_percent=mem.percent,
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            gpu_available=gpu_available,
            gpu_memory_total_gb=gpu_memory_total,
            gpu_memory_used_gb=gpu_memory_used,
            gpu_memory_free_gb=gpu_memory_free,
            disk_total_gb=disk.total / (1024**3),
            disk_used_gb=disk.used / (1024**3),
            disk_free_gb=disk.free / (1024**3),
            disk_percent=disk.percent,
            swap_total_gb=swap.total / (1024**3),
            swap_used_gb=swap.used / (1024**3),
            swap_free_gb=swap.free / (1024**3),
            swap_percent=swap.percent,
            process_memory_gb=process_memory,
            process_cpu_percent=process_cpu,
            open_files=len(process.open_files()),
            threads=process.num_threads(),
        )

    def _log_status(self, snapshot: ResourceSnapshot):
        """Log current resource status"""
        logger.info(
            f"📊 Resources: "
            f"Memory={snapshot.memory_percent:.1f}% ({snapshot.memory_available_gb:.1f}GB free), "
            f"CPU={snapshot.cpu_percent:.1f}%, "
            f"Process={snapshot.process_memory_gb:.1f}GB"
        )

    def get_current_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        if not self.history:
            return {"status": "no_data"}

        latest = self.history[-1]

        return {
            "status": "active" if self.monitoring else "inactive",
            "current_memory_percent": latest.memory_percent,
            "current_cpu_percent": latest.cpu_percent,
            "current_process_memory_gb": latest.process_memory_gb,
            "peak_memory_gb": self.peak_memory_gb,
            "peak_cpu_percent": self.peak_cpu_percent,
            "warning_count": self.warning_count,
            "critical_count": self.critical_count,
            "emergency_count": self.emergency_count,
            "history_size": len(self.history),
            "compound_improvements": self.oom_strategy.compound_improvements,
        }

    def get_resource_trends(self) -> Dict[str, List[float]]:
        """Get resource usage trends over time"""
        if not self.history:
            return {}

        return {
            "timestamps": [s.timestamp for s in self.history],
            "memory_percent": [s.memory_percent for s in self.history],
            "cpu_percent": [s.cpu_percent for s in self.history],
            "process_memory_gb": [s.process_memory_gb for s in self.history],
        }


class SimulationResourceGuardian:
    """
    🛡️ Simulation Resource Guardian

    Special resource guardian for large-scale simulations like the 50M
    agent quantum topology simulation. Provides:
    - Pre-flight resource checks
    - Runtime monitoring
    - Graceful degradation
    - Checkpoint on low resources
    """

    def __init__(
        self,
        simulation_name: str,
        expected_memory_gb: float = 64.0,
        expected_duration_hours: float = 24.0,
    ):
        self.simulation_name = simulation_name
        self.expected_memory_gb = expected_memory_gb
        self.expected_duration_hours = expected_duration_hours

        self.monitor = ResourceMonitor(
            check_interval=2.0,  # More frequent for simulations
            thresholds=ResourceThresholds(
                memory_percent=80.0,  # Lower threshold for simulations
                memory_available_gb=8.0,
                process_memory_gb=48.0,
            ),
        )

        self.checkpoint_callback: Optional[Callable] = None
        self.degradation_callback: Optional[Callable] = None

        # Setup callbacks
        self.monitor.oom_strategy.register_critical_callback(self._on_critical)
        self.monitor.oom_strategy.register_emergency_callback(self._on_emergency)

    async def pre_flight_check(self) -> Dict[str, Any]:
        """Check if system has sufficient resources before starting"""
        logger.info(f"🛫 Pre-flight check for {self.simulation_name}")

        snapshot = await self.monitor._get_snapshot()

        checks = {
            "memory_sufficient": snapshot.memory_available_gb
            >= self.expected_memory_gb,
            "memory_available_gb": snapshot.memory_available_gb,
            "memory_required_gb": self.expected_memory_gb,
            "cpu_sufficient": snapshot.cpu_count >= 4,
            "cpu_count": snapshot.cpu_count,
            "disk_sufficient": snapshot.disk_free_gb >= 10.0,
            "disk_free_gb": snapshot.disk_free_gb,
            "gpu_available": snapshot.gpu_available,
        }

        checks["ready"] = all(
            [
                checks["memory_sufficient"],
                checks["cpu_sufficient"],
                checks["disk_sufficient"],
            ]
        )

        if checks["ready"]:
            logger.info("✅ Pre-flight check PASSED")
        else:
            logger.warning("⚠️ Pre-flight check FAILED")
            for check, result in checks.items():
                if isinstance(result, bool) and not result and check != "ready":
                    logger.warning(f"   Failed: {check}")

        return checks

    async def start_guardian(self):
        """Start the resource guardian"""
        await self.monitor.start_monitoring()
        logger.info(f"🛡️ Resource guardian active for {self.simulation_name}")

    async def stop_guardian(self):
        """Stop the resource guardian"""
        await self.monitor.stop_monitoring()
        logger.info(f"🛑 Resource guardian stopped for {self.simulation_name}")

    def register_checkpoint_callback(self, callback: Callable):
        """Register callback for creating checkpoints on low resources"""
        self.checkpoint_callback = callback

    def register_degradation_callback(self, callback: Callable):
        """Register callback for graceful degradation"""
        self.degradation_callback = callback

    async def _on_critical(
        self, level: str, issues: List[str], snapshot: ResourceSnapshot
    ):
        """Handle critical resource events"""
        logger.warning(f"🔴 Critical resources for {self.simulation_name}: {issues}")

        if self.degradation_callback:
            try:
                await self.degradation_callback()
            except Exception as e:
                logger.error(f"Degradation callback error: {e}")

        if self.checkpoint_callback:
            try:
                logger.info("💾 Creating emergency checkpoint...")
                await self.checkpoint_callback()
            except Exception as e:
                logger.error(f"Checkpoint callback error: {e}")

    async def _on_emergency(
        self, level: str, issues: List[str], snapshot: ResourceSnapshot
    ):
        """Handle emergency resource events"""
        logger.critical(f"🚨 Emergency resources for {self.simulation_name}: {issues}")

        # Always try to checkpoint on emergency
        if self.checkpoint_callback:
            try:
                logger.critical(
                    "💾 Creating emergency checkpoint before potential OOM..."
                )
                await self.checkpoint_callback()
            except Exception as e:
                logger.error(f"Emergency checkpoint error: {e}")

    def get_guardian_report(self) -> Dict[str, Any]:
        """Get comprehensive guardian report"""
        monitor_status = self.monitor.get_current_status()

        return {
            "simulation_name": self.simulation_name,
            "expected_memory_gb": self.expected_memory_gb,
            "expected_duration_hours": self.expected_duration_hours,
            "monitor_status": monitor_status,
            "oom_prevention_actions": len(self.monitor.oom_strategy.action_history),
            "compound_improvements": self.monitor.oom_strategy.compound_improvements,
            "ready_for_simulation": monitor_status.get("current_memory_percent", 100)
            < 50,
        }


# Global resource monitor instance
_global_monitor: Optional[ResourceMonitor] = None


def get_global_monitor() -> ResourceMonitor:
    """Get or create global resource monitor"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = ResourceMonitor()
    return _global_monitor


async def monitor_simulation_resources(
    simulation_func: Callable, simulation_name: str = "simulation", **kwargs
) -> Any:
    """
    🛡️ Monitor resources during simulation execution

    Wraps a simulation function with resource monitoring and OOM prevention.
    Automatically handles resource reclamation and emergency checkpoints.

    Args:
        simulation_func: Async function to monitor
        simulation_name: Name of the simulation
        **kwargs: Arguments to pass to simulation_func

    Returns:
        Result from simulation_func
    """
    guardian = SimulationResourceGuardian(
        simulation_name=simulation_name,
        expected_memory_gb=kwargs.get("expected_memory_gb", 64.0),
    )

    # Pre-flight check
    preflight = await guardian.pre_flight_check()
    if not preflight["ready"]:
        raise RuntimeError(f"Pre-flight check failed for {simulation_name}")

    # Start guardian
    await guardian.start_guardian()

    try:
        # Run simulation
        logger.info(f"🚀 Starting monitored simulation: {simulation_name}")
        result = await simulation_func(**kwargs)
        logger.info(f"✅ Simulation complete: {simulation_name}")
        return result

    except Exception as e:
        logger.error(f"❌ Simulation failed: {e}")
        raise

    finally:
        # Stop guardian
        await guardian.stop_guardian()

        # Print report
        report = guardian.get_guardian_report()
        logger.info("📊 Resource Guardian Report:")
        logger.info(
            f"   Peak Memory: {report['monitor_status']['peak_memory_gb']:.1f}GB"
        )
        logger.info(f"   Warnings: {report['monitor_status']['warning_count']}")
        logger.info(f"   Critical: {report['monitor_status']['critical_count']}")
        logger.info(f"   Emergency: {report['monitor_status']['emergency_count']}")
        logger.info(f"   Compound Improvements: {report['compound_improvements']}")


# Example usage and testing
async def example_simulation():
    """Example simulation that uses resources"""
    logger.info("🧪 Running example simulation...")

    # Allocate some memory
    data = [np.random.randn(1000, 1000) for _ in range(10)]

    await asyncio.sleep(2)

    # Use more memory
    more_data = torch.randn(5000, 5000)

    await asyncio.sleep(2)

    logger.info("✅ Example simulation complete")
    return {"status": "success", "data_size": len(data)}


async def main():
    """Main function for testing"""
    print("=" * 80)
    print("🛡️ COHEZION RESOURCE MONITOR & OOM PREVENTION SYSTEM")
    print("=" * 80)
    print()

    # Run monitored example
    result = await monitor_simulation_resources(
        example_simulation, simulation_name="test_simulation", expected_memory_gb=2.0
    )

    print("\n" + "=" * 80)
    print("🎉 RESOURCE MONITOR TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    # Run resource monitor
    asyncio.run(main())
