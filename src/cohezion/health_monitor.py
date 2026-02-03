"""
ASCENDED COHEZION - Health Monitor & Self-Healing System
Compound Engineering Layer 2: Health Foundation

Monitors system health and automatically heals issues.
Builds on Layer 1 (Configuration) to enable self-healing decisions.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import psutil

from cohezion.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class HealthMetric:
    """Single health metric snapshot"""

    name: str
    value: float
    unit: str
    timestamp: float
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None

    @property
    def status(self) -> str:
        if (
            self.threshold_critical is not None
            and self.value >= self.threshold_critical
        ):
            return "CRITICAL"
        if self.threshold_warning is not None and self.value >= self.threshold_warning:
            return "WARNING"
        return "OK"


@dataclass
class HealthSnapshot:
    """Complete system health snapshot"""

    timestamp: float
    metrics: Dict[str, HealthMetric]
    overall_status: str = "OK"
    active_missions: int = 0
    mode: str = "unknown"

    def to_dict(self) -> Dict:
        return {
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "overall_status": self.overall_status,
            "active_missions": self.active_missions,
            "mode": self.mode,
            "metrics": {
                name: {"value": m.value, "unit": m.unit, "status": m.status}
                for name, m in self.metrics.items()
            },
        }


class HealthMonitor:
    """
    Monitors system health metrics and triggers healing actions.

    Compound Engineering Benefits:
    - Centralized health monitoring makes diagnosis easier
    - Automatic healing reduces manual intervention
    - Health history enables pattern detection
    - Metrics enable better resource decisions
    """

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.config = get_config()
        self.history: List[HealthSnapshot] = []
        self.max_history = 1000
        self._running = False
        self._task = None

        # Healing callbacks
        self.healing_actions: Dict[str, List[Callable]] = {
            "memory_pressure": [],
            "cpu_overload": [],
            "disk_full": [],
            "gpu_overload": [],
            "mission_stalled": [],
        }

        # Track healing attempts to avoid loops
        self.last_healing: Dict[str, float] = {}
        self.healing_cooldown = 300  # 5 minutes

        logger.info("🏥 HealthMonitor initialized")

    async def start(self):
        """Start health monitoring loop"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("🏥 Health monitoring started")

    async def stop(self):
        """Stop health monitoring"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🏥 Health monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                snapshot = await self._collect_metrics()
                self.history.append(snapshot)

                # Trim history
                if len(self.history) > self.max_history:
                    self.history = self.history[-self.max_history :]

                # Check for issues and heal
                await self._check_and_heal(snapshot)

                # Save to disk periodically
                if len(self.history) % 10 == 0:
                    self._save_history()

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")

            await asyncio.sleep(self.check_interval)

    async def _collect_metrics(self) -> HealthSnapshot:
        """Collect current system metrics"""
        metrics = {}

        # Memory metrics
        mem = psutil.virtual_memory()
        metrics["memory_percent"] = HealthMetric(
            name="memory_percent",
            value=mem.percent,
            unit="%",
            timestamp=time.time(),
            threshold_warning=80,
            threshold_critical=95,
        )

        metrics["memory_available_gb"] = HealthMetric(
            name="memory_available_gb",
            value=mem.available / (1024**3),
            unit="GB",
            timestamp=time.time(),
            threshold_warning=10,
            threshold_critical=5,
        )

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics["cpu_percent"] = HealthMetric(
            name="cpu_percent",
            value=cpu_percent,
            unit="%",
            timestamp=time.time(),
            threshold_warning=85,
            threshold_critical=95,
        )

        # Disk metrics
        disk = psutil.disk_usage("/")
        metrics["disk_percent"] = HealthMetric(
            name="disk_percent",
            value=disk.percent,
            unit="%",
            timestamp=time.time(),
            threshold_warning=85,
            threshold_critical=95,
        )

        # GPU metrics (if available)
        try:
            vram_used = 0
            vram_total = 0
            vram_path = Path("/sys/class/drm/card1/device/mem_info_vram_used")
            if vram_path.exists():
                vram_used = int(vram_path.read_text().strip()) / (1024**3)

            metrics["vram_used_gb"] = HealthMetric(
                name="vram_used_gb",
                value=vram_used,
                unit="GB",
                timestamp=time.time(),
                threshold_warning=80,
                threshold_critical=100,
            )
        except Exception:
            pass

        # Determine overall status
        statuses = [m.status for m in metrics.values()]
        if "CRITICAL" in statuses:
            overall = "CRITICAL"
        elif "WARNING" in statuses:
            overall = "WARNING"
        else:
            overall = "OK"

        return HealthSnapshot(
            timestamp=time.time(), metrics=metrics, overall_status=overall
        )

    async def _check_and_heal(self, snapshot: HealthSnapshot):
        """Check for issues and trigger healing"""
        current_time = time.time()

        # Memory pressure healing
        if snapshot.metrics.get(
            "memory_percent", HealthMetric("", 0, "", 0)
        ).status in ["WARNING", "CRITICAL"]:
            await self._trigger_healing("memory_pressure", snapshot)

        # CPU overload healing
        if snapshot.metrics.get("cpu_percent", HealthMetric("", 0, "", 0)).status in [
            "WARNING",
            "CRITICAL",
        ]:
            await self._trigger_healing("cpu_overload", snapshot)

        # Disk full healing
        if snapshot.metrics.get("disk_percent", HealthMetric("", 0, "", 0)).status in [
            "WARNING",
            "CRITICAL",
        ]:
            await self._trigger_healing("disk_full", snapshot)

    async def _trigger_healing(self, issue: str, snapshot: HealthSnapshot):
        """Trigger healing for an issue"""
        current_time = time.time()

        # Check cooldown
        if issue in self.last_healing:
            if current_time - self.last_healing[issue] < self.healing_cooldown:
                return  # Too soon

        self.last_healing[issue] = current_time

        logger.warning(f"🚑 Triggering healing for: {issue}")

        # Execute healing callbacks
        for callback in self.healing_actions.get(issue, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(snapshot)
                else:
                    callback(snapshot)
            except Exception as e:
                logger.error(f"Healing callback failed: {e}")

    def register_healing_action(self, issue: str, callback: Callable):
        """Register a callback for healing an issue"""
        if issue not in self.healing_actions:
            self.healing_actions[issue] = []
        self.healing_actions[issue].append(callback)
        logger.info(f"🚑 Registered healing action for: {issue}")

    def get_current_health(self) -> HealthSnapshot:
        """Get most recent health snapshot"""
        if self.history:
            return self.history[-1]
        return HealthSnapshot(timestamp=time.time(), metrics={})

    def get_health_trend(self, metric_name: str, hours: int = 1) -> List[HealthMetric]:
        """Get trend for a specific metric over time"""
        cutoff = time.time() - (hours * 3600)
        return [
            snapshot.metrics.get(metric_name)
            for snapshot in self.history
            if snapshot.timestamp > cutoff and metric_name in snapshot.metrics
        ]

    def _save_history(self):
        """Save health history to disk"""
        try:
            history_path = self.config.data_dir / "health_history.json"
            data = [snapshot.to_dict() for snapshot in self.history[-100:]]  # Last 100
            with open(history_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save health history: {e}")


class SelfHealingEngine:
    """
    Automatic healing actions for common issues.

    Builds on HealthMonitor to provide specific healing strategies.
    """

    def __init__(self, health_monitor: HealthMonitor):
        self.health_monitor = health_monitor
        self.healing_log: List[Dict] = []

        # Register healing actions
        self._register_default_healers()

        logger.info("🚑 SelfHealingEngine initialized")

    def _register_default_healers(self):
        """Register default healing actions"""
        # Memory pressure: Evict non-critical models
        self.health_monitor.register_healing_action(
            "memory_pressure", self._heal_memory_pressure
        )

        # CPU overload: Throttle background tasks
        self.health_monitor.register_healing_action(
            "cpu_overload", self._heal_cpu_overload
        )

        # Disk full: Clean up old logs and checkpoints
        self.health_monitor.register_healing_action("disk_full", self._heal_disk_full)

    async def _heal_memory_pressure(self, snapshot: HealthSnapshot):
        """Heal memory pressure by evicting models"""
        logger.warning("🚑 Healing memory pressure: Evicting non-critical models")

        try:
            from cohezion.agents.model_wrangler_agent import ModelWranglerAscended

            wrangler = ModelWranglerAscended()
            await wrangler._proactive_eviction()

            self._log_healing("memory_pressure", "Evicted non-critical models")
        except Exception as e:
            logger.error(f"Memory healing failed: {e}")

    async def _heal_cpu_overload(self, snapshot: HealthSnapshot):
        """Heal CPU overload by switching to conservative mode"""
        logger.warning("🚑 Healing CPU overload: Switching to conservative mode")

        try:
            from cohezion.swarm.mode_controller import get_mode_controller, SystemMode

            controller = get_mode_controller()
            await controller.switch_mode(SystemMode.CONSERVATIVE)

            self._log_healing("cpu_overload", "Switched to conservative mode")
        except Exception as e:
            logger.error(f"CPU healing failed: {e}")

    async def _heal_disk_full(self, snapshot: HealthSnapshot):
        """Heal disk full by cleaning up old files"""
        logger.warning("🚑 Healing disk full: Cleaning up old files")

        try:
            config = get_config()

            # Clean old checkpoints (keep last 20)
            checkpoint_dir = config.data_dir / "checkpoints"
            if checkpoint_dir.exists():
                checkpoints = sorted(checkpoint_dir.glob("*.json"))
                for old_checkpoint in checkpoints[:-20]:
                    old_checkpoint.unlink()
                    logger.info(f"Deleted old checkpoint: {old_checkpoint}")

            # Clean old logs (keep last 7 days)
            logs_dir = config.logs_dir
            if logs_dir.exists():
                cutoff = datetime.now() - timedelta(days=7)
                for log_file in logs_dir.glob("*.log"):
                    if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                        log_file.unlink()
                        logger.info(f"Deleted old log: {log_file}")

            self._log_healing("disk_full", "Cleaned old checkpoints and logs")
        except Exception as e:
            logger.error(f"Disk healing failed: {e}")

    def _log_healing(self, issue: str, action: str):
        """Log a healing action"""
        self.healing_log.append(
            {"timestamp": datetime.now().isoformat(), "issue": issue, "action": action}
        )

        # Keep only last 100 entries
        if len(self.healing_log) > 100:
            self.healing_log = self.healing_log[-100:]

    def get_healing_history(self) -> List[Dict]:
        """Get history of healing actions"""
        return self.healing_log


# Singleton instances
_health_monitor = None
_self_healing = None


async def get_health_monitor() -> HealthMonitor:
    """Get or create the health monitor singleton"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
        await _health_monitor.start()
    return _health_monitor


async def get_self_healing() -> SelfHealingEngine:
    """Get or create the self-healing engine singleton"""
    global _self_healing
    if _self_healing is None:
        monitor = await get_health_monitor()
        _self_healing = SelfHealingEngine(monitor)
    return _self_healing
