"""
Performance monitoring system for COHEZION GPU acceleration.

Provides real-time monitoring, analytics, and optimization insights for physics simulations.
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import cupy as cp
import json
from datetime import datetime, timedelta

from .core.cache_manager import CacheManager
from .core.gpu_acceleration import (
    GPUAccelerationManager,
    SimulationMetrics,
    SimulationState,
)
from .agents.base import Agent


class MonitorType(Enum):
    """Types of performance monitors."""

    GPU_UTILIZATION = "gpu_utilization"
    MEMORY_USAGE = "memory_usage"
    SIMULATION_FPS = "simulation_fps"
    LATENCY = "latency"
    TEMPERATURE = "temperature"
    PARTICLE_COUNT = "particle_count"


@dataclass
class MonitorConfig:
    """Configuration for performance monitors."""

    monitor_type: MonitorType
    interval_seconds: float = 1.0
    threshold: Optional[float] = None
    alert_enabled: bool = True
    history_size: int = 1000
    enabled: bool = True


@dataclass
class PerformanceAlert:
    """Performance alert data."""

    timestamp: datetime
    monitor_type: MonitorType
    simulation_name: str
    value: float
    threshold: float
    severity: str
    message: str


@dataclass
class SystemMetrics:
    """System-wide performance metrics."""

    timestamp: datetime
    gpu_utilization: float
    memory_usage_mb: float
    simulation_fps: float
    avg_latency_ms: float
    max_temperature_c: float
    total_particles: int
    active_simulations: int
    alerts_count: int
    anomalies_count: int


class PerformanceMonitor:
    """Monitors and analyzes performance of GPU-accelerated simulations."""

    def __init__(self):
        self.gpu_manager = GPUAccelerationManager()
        self.cache_manager = CacheManager()
        self.monitors: Dict[str, MonitorConfig] = {}
        self.alerts: List[PerformanceAlert] = []
        self.metrics_history: List[SystemMetrics] = []
        self.is_running = False
        self._init_default_monitors()

    def _init_default_monitors(self):
        """Initialize default performance monitors."""
        self.monitors = {
            "gpu_utilization": MonitorConfig(
                monitor_type=MonitorType.GPU_UTILIZATION,
                interval_seconds=2.0,
                threshold=85.0,
                alert_enabled=True,
            ),
            "memory_usage": MonitorConfig(
                monitor_type=MonitorType.MEMORY_USAGE,
                interval_seconds=5.0,
                threshold=7000.0,  # 7GB
                alert_enabled=True,
            ),
            "simulation_fps": MonitorConfig(
                monitor_type=MonitorType.SIMULATION_FPS,
                interval_seconds=1.0,
                threshold=30.0,  # Minimum acceptable FPS
                alert_enabled=True,
            ),
            "latency": MonitorConfig(
                monitor_type=MonitorType.LATENCY,
                interval_seconds=2.0,
                threshold=50.0,  # 50ms max latency
                alert_enabled=True,
            ),
            "temperature": MonitorConfig(
                monitor_type=MonitorType.TEMPERATURE,
                interval_seconds=10.0,
                threshold=85.0,  # Temperature warning threshold
                alert_enabled=True,
            ),
            "particle_count": MonitorConfig(
                monitor_type=MonitorType.PARTICLE_COUNT,
                interval_seconds=10.0,
                threshold=100000,  # Max particle count
                alert_enabled=True,
            ),
        }

    async def start_monitoring(self) -> None:
        """Start the performance monitoring system."""
        if self.is_running:
            return

        self.is_running = True
        print("Starting performance monitoring...")

        # Start all enabled monitors
        for name, config in self.monitors.items():
            if config.enabled:
                asyncio.create_task(self._run_monitor(name, config))

        # Start system metrics collection
        asyncio.create_task(self._collect_system_metrics())

    async def stop_monitoring(self) -> None:
        """Stop the performance monitoring system."""
        self.is_running = False
        print("Stopping performance monitoring...")

    async def _run_monitor(self, name: str, config: MonitorConfig) -> None:
        """Run a specific performance monitor."""
        while self.is_running:
            try:
                # Collect metric
                value = await self._collect_metric(name, config.monitor_type)

                # Check threshold
                if config.threshold is not None and value > config.threshold:
                    if config.alert_enabled:
                        self._trigger_alert(
                            name, config.monitor_type, value, config.threshold
                        )

                # Cache the metric
                self.cache_manager.set(f"monitor_{name}", value, ttl=300)

                # Wait for next interval
                await asyncio.sleep(config.interval_seconds)

            except Exception as e:
                print(f"Error in monitor {name}: {e}")
                await asyncio.sleep(config.interval_seconds)

    async def _collect_metric(self, name: str, monitor_type: MonitorType) -> float:
        """Collect a specific metric value."""
        if monitor_type == MonitorType.GPU_UTILIZATION:
            return await self._collect_gpu_utilization()
        elif monitor_type == MonitorType.MEMORY_USAGE:
            return await self._collect_memory_usage()
        elif monitor_type == MonitorType.SIMULATION_FPS:
            return await self._collect_simulation_fps()
        elif monitor_type == MonitorType.LATENCY:
            return await self._collect_latency()
        elif monitor_type == MonitorType.TEMPERATURE:
            return await self._collect_temperature()
        elif monitor_type == MonitorType.PARTICLE_COUNT:
            return await self._collect_particle_count()
        else:
            raise ValueError(f"Unknown monitor type: {monitor_type}")

    async def _collect_gpu_utilization(self) -> float:
        """Collect GPU utilization percentage."""
        # Get system metrics
        system_metrics = self.gpu_manager.get_system_metrics()

        # Estimate utilization based on memory usage and active simulations
        if system_metrics["gpu_devices"]:
            device = system_metrics["gpu_devices"][0]
            memory_used_mb = system_metrics["total_memory_mb"]

            # Simple utilization estimate: 50% base + 50% from memory usage
            base_utilization = 50.0
            memory_utilization = (memory_used_mb / 8192) * 100  # 8GB GPU

            return min(100.0, base_utilization + memory_utilization)

        return 0.0

    async def _collect_memory_usage(self) -> float:
        """Collect total memory usage in MB."""
        system_metrics = self.gpu_manager.get_system_metrics()
        return system_metrics["total_memory_mb"]

    async def _collect_simulation_fps(self) -> float:
        """Collect average simulation FPS."""
        # Get metrics from all simulations
        fps_values = []
        for name in self.gpu_manager.active_simulations.keys():
            metrics = self.cache_manager.get(f"{name}_metrics")
            if metrics:
                fps_values.append(metrics.get("fps", 0.0))

        return np.mean(fps_values) if fps_values else 0.0

    async def _collect_latency(self) -> float:
        """Collect average simulation latency in ms."""
        latency_values = []
        for name in self.gpu_manager.active_simulations.keys():
            metrics = self.cache_manager.get(f"{name}_metrics")
            if metrics:
                latency_values.append(metrics.get("latency_ms", 0.0))

        return np.mean(latency_values) if latency_values else 0.0

    async def _collect_temperature(self) -> float:
        """Collect maximum GPU temperature in Celsius."""
        system_metrics = self.gpu_manager.get_system_metrics()
        return system_metrics["max_temperature_c"]

    async def _collect_particle_count(self) -> float:
        """Collect total particle count across all simulations."""
        system_metrics = self.gpu_manager.get_system_metrics()
        return system_metrics["total_particles"]

    async def _collect_system_metrics(self) -> None:
        """Collect and store system-wide metrics periodically."""
        while self.is_running:
            try:
                # Get current system metrics
                system_metrics = self.gpu_manager.get_system_metrics()

                # Create SystemMetrics object
                current_metrics = SystemMetrics(
                    timestamp=datetime.now(),
                    gpu_utilization=system_metrics["gpu_utilization"],
                    memory_usage_mb=system_metrics["total_memory_mb"],
                    simulation_fps=system_metrics["simulation_fps"],
                    avg_latency_ms=system_metrics["avg_latency_ms"],
                    max_temperature_c=system_metrics["max_temperature_c"],
                    total_particles=system_metrics["total_particles"],
                    active_simulations=system_metrics["active_simulations"],
                    alerts_count=len(self.alerts),
                    anomalies_count=0,  # To be implemented
                )

                # Store metrics in history
                self.metrics_history.append(current_metrics)

                # Keep only recent history
                max_history = 1000
                if len(self.metrics_history) > max_history:
                    self.metrics_history = self.metrics_history[-max_history:]

                # Cache metrics for quick access
                self.cache_manager.set(
                    "system_metrics", current_metrics.__dict__, ttl=30
                )

                # Wait for next collection
                await asyncio.sleep(5.0)

            except Exception as e:
                print(f"Error collecting system metrics: {e}")
                await asyncio.sleep(5.0)

    def _trigger_alert(
        self, name: str, monitor_type: MonitorType, value: float, threshold: float
    ) -> None:
        """Trigger a performance alert."""
        alert = PerformanceAlert(
            timestamp=datetime.now(),
            monitor_type=monitor_type,
            simulation_name=name,
            value=value,
            threshold=threshold,
            severity="warning" if value < threshold * 1.2 else "critical",
            message=f"{monitor_type.value} exceeded threshold: {value:.2f} > {threshold:.2f}",
        )

        self.alerts.append(alert)

        # Keep only recent alerts
        max_alerts = 100
        if len(self.alerts) > max_alerts:
            self.alerts = self.alerts[-max_alerts:]

        # Log the alert
        print(f"ALERT: {alert.message}")

        # Cache the alert
        self.cache_manager.set(f"alert_{name}", alert.__dict__, ttl=3600)

    def get_metrics_history(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> List[SystemMetrics]:
        """Get metrics history within time range."""
        if start_time is None:
            start_time = datetime.min
        if end_time is None:
            end_time = datetime.max

        return [
            metrics
            for metrics in self.metrics_history
            if start_time <= metrics.timestamp <= end_time
        ]

    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        cached = self.cache_manager.get("system_metrics")
        if cached:
            return SystemMetrics(**cached)

        # Fallback to collecting fresh metrics
        system_metrics = self.gpu_manager.get_system_metrics()
        return SystemMetrics(
            timestamp=datetime.now(),
            gpu_utilization=system_metrics["gpu_utilization"],
            memory_usage_mb=system_metrics["total_memory_mb"],
            simulation_fps=system_metrics["simulation_fps"],
            avg_latency_ms=system_metrics["avg_latency_ms"],
            max_temperature_c=system_metrics["max_temperature_c"],
            total_particles=system_metrics["total_particles"],
            active_simulations=system_metrics["active_simulations"],
            alerts_count=len(self.alerts),
            anomalies_count=0,
        )

    def get_simulation_metrics(self, simulation_name: str) -> Dict[str, Any]:
        """Get detailed metrics for a specific simulation."""
        if simulation_name not in self.gpu_manager.active_simulations:
            return {}

        # Get cached metrics
        metrics = self.cache_manager.get(f"{simulation_name}_metrics")
        if not metrics:
            return {}

        # Get detailed simulation data
        simulation = self.gpu_manager.active_simulations[simulation_name]

        return {
            "name": simulation_name,
            "state": self.gpu_manager.simulation_states.get(
                simulation_name, SimulationState.IDLE
            ).value,
            "fps": metrics.get("fps", 0.0),
            "latency_ms": metrics.get("latency_ms", 0.0),
            "particles": metrics.get("particles", 0),
            "memory_mb": metrics.get("memory_usage_mb", 0.0),
            "gpu_utilization": metrics.get("gpu_utilization", 0.0),
            "temperature_c": metrics.get("temperature_c", 0.0),
            "performance": simulation.get_performance_metrics(),
        }

    def get_alerts(
        self,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[PerformanceAlert]:
        """Get performance alerts."""
        filtered_alerts = self.alerts

        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]

        if start_time:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp >= start_time]

        if end_time:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp <= end_time]

        return filtered_alerts

    def get_monitor_status(self) -> Dict[str, Any]:
        """Get status of all monitors."""
        return {
            name: {
                "type": config.monitor_type.value,
                "interval": config.interval_seconds,
                "threshold": config.threshold,
                "enabled": config.enabled,
                "last_value": self.cache_manager.get(f"monitor_{name}"),
                "alerts_triggered": len(
                    [a for a in self.alerts if a.monitor_type == config.monitor_type]
                ),
            }
            for name, config in self.monitors.items()
        }

    def optimize_simulation(self, simulation_name: str) -> Dict[str, Any]:
        """Optimize a simulation based on performance metrics."""
        if simulation_name not in self.gpu_manager.active_simulations:
            raise ValueError(f"Simulation '{simulation_name}' not found")

        # Get current metrics
        metrics = self.get_simulation_metrics(simulation_name)

        # Analyze performance bottlenecks
        optimizations = {}

        # FPS optimization
        if metrics.get("fps", 0) < 30:
            optimizations["fps"] = self._optimize_fps(simulation_name, metrics)

        # Memory optimization
        if metrics.get("memory_mb", 0) > 6000:  # 6GB
            optimizations["memory"] = self._optimize_memory(simulation_name, metrics)

        # Temperature optimization
        if metrics.get("temperature_c", 0) > 80:
            optimizations["temperature"] = self._optimize_temperature(
                simulation_name, metrics
            )

        return optimizations

    def _optimize_fps(
        self, simulation_name: str, metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize FPS for a simulation."""
        # Reduce particle count if possible
        current_particles = metrics.get("particles", 0)
        if current_particles > 1000:
            return {
                "action": "reduce_particles",
                "from": current_particles,
                "to": max(1000, current_particles // 2),
                "expected_fps_gain": 1.5,
            }

        # Increase timestep if safe
        current_timestep = metrics.get("performance", {}).get("timestep", 0.01)
        return {
            "action": "increase_timestep",
            "from": current_timestep,
            "to": min(0.1, current_timestep * 2),
            "expected_fps_gain": 1.2,
        }

    def _optimize_memory(
        self, simulation_name: str, metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize memory usage for a simulation."""
        # Reduce grid size
        current_grid = self.gpu_manager.active_simulations[
            simulation_name
        ].config.grid_size
        new_grid = tuple(max(32, size // 2) for size in current_grid)

        return {
            "action": "reduce_grid_size",
            "from": current_grid,
            "to": new_grid,
            "expected_memory_saving_mb": 0.5
            * (current_grid[0] * current_grid[1] * current_grid[2]),
        }

    def _optimize_temperature(
        self, simulation_name: str, metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize temperature for a simulation."""
        # Reduce computational intensity
        return {
            "action": "reduce_computation",
            "suggestions": [
                "Reduce particle interactions",
                "Increase timestep",
                "Simplify force calculations",
            ],
        }

    def generate_report(self, period: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Generate performance report for the given period."""
        end_time = datetime.now()
        start_time = end_time - period

        # Get metrics history
        metrics_history = self.get_metrics_history(start_time, end_time)

        # Calculate statistics
        if metrics_history:
            avg_fps = np.mean([m.simulation_fps for m in metrics_history])
            avg_latency = np.mean([m.avg_latency_ms for m in metrics_history])
            max_temp = np.max([m.max_temperature_c for m in metrics_history])
            total_particles = np.sum(
                [m.total_particles for m in metrics_history]
            ) / len(metrics_history)
        else:
            avg_fps = avg_latency = max_temp = total_particles = 0

        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "duration_hours": period.total_seconds() / 3600,
            },
            "summary": {
                "avg_fps": avg_fps,
                "avg_latency_ms": avg_latency,
                "max_temperature_c": max_temp,
                "avg_particles": total_particles,
                "active_simulations": len(metrics_history) if metrics_history else 0,
            },
            "alerts": [
                a.__dict__
                for a in self.get_alerts(start_time=start_time, end_time=end_time)
            ],
            "recommendations": self._generate_recommendations(metrics_history),
        }

    def _generate_recommendations(
        self, metrics_history: List[SystemMetrics]
    ) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []

        if metrics_history:
            # Check for low FPS
            avg_fps = np.mean([m.simulation_fps for m in metrics_history])
            if avg_fps < 30:
                recommendations.append(
                    "Consider reducing particle count or increasing timestep to improve FPS"
                )

            # Check for high memory usage
            max_memory = np.max([m.memory_usage_mb for m in metrics_history])
            if max_memory > 7000:
                recommendations.append(
                    "Consider reducing grid size or particle count to reduce memory usage"
                )

            # Check for high temperature
            max_temp = np.max([m.max_temperature_c for m in metrics_history])
            if max_temp > 80:
                recommendations.append(
                    "Ensure proper cooling and consider reducing computational intensity"
                )

        return recommendations


# Global performance monitor instance
PERFORMANCE_MONITOR = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor."""
    return PERFORMANCE_MONITOR
