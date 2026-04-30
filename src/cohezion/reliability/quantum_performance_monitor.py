#!/usr/bin/env python3
"""
COHEZION QUANTUM PERFORMANCE MONITORING SYSTEM v1.1.48

Real-time system performance monitoring with intelligent auto-swapping capabilities.
Optimized for AMD Ryzen AI MAX+ 395 with DDR5 bandwidth analysis.

This system ensures optimal performance through continuous monitoring and automatic adjustments.
"""

import asyncio
import json
import logging
import os
import shutil
import statistics
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import psutil


logger = logging.getLogger(__name__)

# Module-level set to retain references to background tasks (RUF006).
_BACKGROUND_TASKS: set[asyncio.Task] = set()


# Resolve external executable paths at module load to avoid S607 partial-path warnings.
_OLLAMA = shutil.which("ollama") or "/usr/local/bin/ollama"
_PKILL = shutil.which("pkill") or "/usr/bin/pkill"
_BASH = shutil.which("bash") or "/bin/bash"


class MetricType(Enum):
    """Performance metric types"""

    MEMORY_USAGE = "memory_usage"
    MEMORY_BANDWIDTH = "memory_bandwidth"
    CPU_USAGE = "cpu_usage"
    CACHE_PERFORMANCE = "cache_performance"
    MODEL_LATENCY = "model_latency"
    THROUGHPUT = "throughput"
    QUEUE_DEPTH = "queue_depth"
    RESPONSE_QUALITY = "response_quality"


class AlertLevel(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ActionType(Enum):
    """Automatic action types"""

    MODEL_SWAP = "model_swap"
    THREAD_ADJUSTMENT = "thread_adjustment"
    CONTEXT_REDUCTION = "context_reduction"
    QUANTIZATION_CHANGE = "quantization_change"
    IDE_PRIORITY_ADJUST = "ide_priority_adjust"
    SYSTEM_RESTART = "system_restart"


@dataclass
class PerformanceMetric:
    """Individual performance metric"""

    metric_type: MetricType
    value: float
    unit: str
    timestamp: float
    source: str
    metadata: dict[str, Any]


@dataclass
class AlertCondition:
    """Alert condition configuration"""

    metric_type: MetricType
    threshold: float
    comparison: str  # ">", "<", ">=", "<=", "=="
    alert_level: AlertLevel
    action: ActionType | None = None
    cooldown_seconds: int = 300  # 5 minutes default
    message_template: str = ""


@dataclass
class AutoSwapDecision:
    """Auto-swap decision result"""

    should_swap: bool
    current_model: str
    recommended_model: str
    reason: str
    confidence: float
    action_type: ActionType
    estimated_improvement: float


class QuantumPerformanceMonitor:
    """Advanced performance monitoring with AI-driven optimization"""

    def __init__(self):
        self.monitoring_active = False
        self.metrics_history: list[PerformanceMetric] = []
        self.alert_conditions: list[AlertCondition] = []
        self.auto_swap_enabled = True
        self.model_performance_cache: dict[str, dict[str, float]] = {}

        # System-specific constants for AMD Ryzen AI MAX+ 395
        self.total_memory_gb = psutil.virtual_memory().total / (1024**3)
        self.total_threads = 32
        self.l3_cache_mb = 64
        self.ddr5_bandwidth_gbps = 85  # Estimated

        # Performance baselines
        self.performance_baselines = self._initialize_baselines()

        # Monitoring state
        self.last_swap_time = 0
        self.swap_cooldown_seconds = 600  # 10 minutes

        # File paths
        self.metrics_dir = Path("/home/mike-anderson/dev/cohezion/.ide-config")
        self.metrics_file = self.metrics_dir / "quantum_metrics.json"
        self.alerts_file = self.metrics_dir / "alerts.json"
        self.decisions_file = self.metrics_dir / "auto_swap_decisions.json"

        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        # Initialize alert conditions
        self._setup_alert_conditions()

        # Load historical data
        self._load_historical_data()

    def _initialize_baselines(self) -> dict[str, dict[str, float]]:
        """Initialize performance baselines for different model sizes"""
        return {
            "small_models": {  # 4-8GB models
                "expected_tps": 10.0,
                "memory_usage": 8.0,
                "latency": 0.8,
                "cache_hit_rate": 0.15,
            },
            "medium_models": {  # 8-16GB models
                "expected_tps": 6.0,
                "memory_usage": 12.0,
                "latency": 1.5,
                "cache_hit_rate": 0.08,
            },
            "large_models": {  # 16-32GB models
                "expected_tps": 3.0,
                "memory_usage": 24.0,
                "latency": 3.0,
                "cache_hit_rate": 0.04,
            },
            "ultra_models": {  # 32+GB models
                "expected_tps": 1.0,
                "memory_usage": 48.0,
                "latency": 8.0,
                "cache_hit_rate": 0.02,
            },
        }

    def _setup_alert_conditions(self):
        """Setup intelligent alert conditions"""
        self.alert_conditions = [
            # Memory alerts
            AlertCondition(
                metric_type=MetricType.MEMORY_USAGE,
                threshold=0.85,  # 85% memory usage
                comparison=">",
                alert_level=AlertLevel.WARNING,
                action=ActionType.MODEL_SWAP,
                cooldown_seconds=300,
                message_template="High memory usage: {value:.1f}% - consider swapping to smaller model",
            ),
            AlertCondition(
                metric_type=MetricType.MEMORY_USAGE,
                threshold=0.95,  # 95% memory usage
                comparison=">",
                alert_level=AlertLevel.CRITICAL,
                action=ActionType.CONTEXT_REDUCTION,
                cooldown_seconds=60,
                message_template="Critical memory usage: {value:.1f}% - reducing context windows",
            ),
            # Performance alerts
            AlertCondition(
                metric_type=MetricType.MODEL_LATENCY,
                threshold=10.0,  # 10 seconds
                comparison=">",
                alert_level=AlertLevel.WARNING,
                action=ActionType.MODEL_SWAP,
                cooldown_seconds=600,
                message_template="High model latency: {value:.1f}s - swapping to faster model",
            ),
            AlertCondition(
                metric_type=MetricType.THROUGHPUT,
                threshold=2.0,  # Less than 2 tokens/sec
                comparison="<",
                alert_level=AlertLevel.WARNING,
                action=ActionType.THREAD_ADJUSTMENT,
                cooldown_seconds=300,
                message_template="Low throughput: {value:.1f} t/s - adjusting thread allocation",
            ),
            # Cache performance alerts
            AlertCondition(
                metric_type=MetricType.CACHE_PERFORMANCE,
                threshold=0.05,  # Less than 5% cache hit rate
                comparison="<",
                alert_level=AlertLevel.WARNING,
                action=ActionType.MODEL_SWAP,
                cooldown_seconds=600,
                message_template="Low cache performance: {value:.3f} - consider cache-optimized model",
            ),
            # Queue depth alerts
            AlertCondition(
                metric_type=MetricType.QUEUE_DEPTH,
                threshold=5.0,
                comparison=">",
                alert_level=AlertLevel.WARNING,
                action=ActionType.IDE_PRIORITY_ADJUST,
                cooldown_seconds=180,
                message_template="High queue depth: {value:.1f} - adjusting IDE priorities",
            ),
            # Emergency conditions
            AlertCondition(
                metric_type=MetricType.MEMORY_USAGE,
                threshold=0.98,  # 98% memory usage
                comparison=">",
                alert_level=AlertLevel.EMERGENCY,
                action=ActionType.SYSTEM_RESTART,
                cooldown_seconds=30,
                message_template="Emergency memory usage: {value:.1f}% - initiating system restart",
            ),
        ]

    def _load_historical_data(self):
        """Load historical performance data"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file) as f:
                    data = json.load(f)
                    self.metrics_history = [PerformanceMetric(**m) for m in data.get("metrics", [])]
                logger.info(f"Loaded {len(self.metrics_history)} historical metrics")
            except Exception as e:
                logger.error(f"Failed to load historical data: {e}")

    def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous performance monitoring"""
        self.monitoring_active = True
        logger.info(f"Starting quantum performance monitoring (interval: {interval_seconds}s)")

        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitoring_loop, args=(interval_seconds,), daemon=True
        )
        monitor_thread.start()

        # Start auto-swap monitoring
        task = asyncio.create_task(self._auto_swap_monitor())
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)

    def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                metrics = self._collect_system_metrics()

                # Store metrics
                for metric in metrics:
                    self.metrics_history.append(metric)

                # Check alert conditions
                self._check_alert_conditions(metrics)

                # Cleanup old metrics (keep last 10000)
                if len(self.metrics_history) > 10000:
                    self.metrics_history = self.metrics_history[-10000:]

                # Save metrics periodically
                if len(self.metrics_history) % 100 == 0:
                    self._save_metrics()

                time.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(interval_seconds)

    def _collect_system_metrics(self) -> list[PerformanceMetric]:
        """Collect comprehensive system metrics"""
        metrics = []
        current_time = time.time()

        # Memory metrics
        memory = psutil.virtual_memory()
        memory_usage = memory.percent / 100.0

        metrics.append(
            PerformanceMetric(
                metric_type=MetricType.MEMORY_USAGE,
                value=memory_usage,
                unit="percentage",
                timestamp=current_time,
                source="psutil",
                metadata={
                    "available_gb": memory.available / (1024**3),
                    "used_gb": memory.used / (1024**3),
                },
            )
        )

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)

        metrics.append(
            PerformanceMetric(
                metric_type=MetricType.CPU_USAGE,
                value=cpu_percent,
                unit="percentage",
                timestamp=current_time,
                source="psutil",
                metadata={"thread_count": self.total_threads},
            )
        )

        # Estimate memory bandwidth (simplified)
        bandwidth_estimate = self._estimate_memory_bandwidth()

        metrics.append(
            PerformanceMetric(
                metric_type=MetricType.MEMORY_BANDWIDTH,
                value=bandwidth_estimate,
                unit="gbps",
                timestamp=current_time,
                source="calculated",
                metadata={"theoretical_max": self.ddr5_bandwidth_gbps},
            )
        )

        # Cache performance estimation
        cache_performance = self._estimate_cache_performance()

        metrics.append(
            PerformanceMetric(
                metric_type=MetricType.CACHE_PERFORMANCE,
                value=cache_performance,
                unit="hit_rate",
                timestamp=current_time,
                source="calculated",
                metadata={"l3_cache_mb": self.l3_cache_mb},
            )
        )

        return metrics

    def _estimate_memory_bandwidth(self) -> float:
        """Estimate current memory bandwidth usage"""
        # This is a simplified estimation
        # In production, would use more sophisticated measurement

        recent_memory_metrics = [
            m for m in self.metrics_history[-20:] if m.metric_type == MetricType.MEMORY_USAGE
        ]

        if len(recent_memory_metrics) < 2:
            return 0.0

        # Calculate memory pressure as bandwidth indicator
        current_usage = recent_memory_metrics[-1].value
        avg_usage = statistics.mean([m.value for m in recent_memory_metrics])

        # Higher usage and volatility = more bandwidth pressure
        volatility = abs(current_usage - avg_usage)
        bandwidth_pressure = (current_usage + volatility * 2) * self.ddr5_bandwidth_gbps

        return min(bandwidth_pressure, self.ddr5_bandwidth_gbps)

    def _estimate_cache_performance(self) -> float:
        """Estimate cache performance based on system behavior"""
        recent_cpu_metrics = [
            m for m in self.metrics_history[-50:] if m.metric_type == MetricType.CPU_USAGE
        ]

        if not recent_cpu_metrics:
            return 0.1

        # CPU efficiency can indicate cache performance
        avg_cpu = statistics.mean([m.value for m in recent_cpu_metrics])

        # Higher CPU efficiency = better cache utilization
        cache_efficiency = max(0, 1.0 - (avg_cpu / 100.0))

        return cache_efficiency

    def _check_alert_conditions(self, metrics: list[PerformanceMetric]):
        """Check alert conditions and trigger actions"""
        for condition in self.alert_conditions:
            # Find matching metric
            matching_metric = next(
                (m for m in metrics if m.metric_type == condition.metric_type), None
            )

            if matching_metric is None:
                continue

            # Check if condition is triggered
            if self._evaluate_condition(matching_metric.value, condition):
                # Check cooldown
                if self._is_in_cooldown(condition):
                    continue

                # Trigger alert
                self._trigger_alert(condition, matching_metric)

    def _evaluate_condition(self, value: float, condition: AlertCondition) -> bool:
        """Evaluate alert condition"""
        if condition.comparison == ">":
            return value > condition.threshold
        elif condition.comparison == ">=":
            return value >= condition.threshold
        elif condition.comparison == "<":
            return value < condition.threshold
        elif condition.comparison == "<=":
            return value <= condition.threshold
        elif condition.comparison == "==":
            return abs(value - condition.threshold) < 0.01

        return False

    def _is_in_cooldown(self, condition: AlertCondition) -> bool:
        """Check if alert is in cooldown period"""
        metric_key = f"{condition.metric_type.value}_{condition.alert_level.value}"
        last_alert_time = getattr(self, f"last_alert_{metric_key}", 0)

        return (time.time() - last_alert_time) < condition.cooldown_seconds

    def _trigger_alert(self, condition: AlertCondition, metric: PerformanceMetric):
        """Trigger alert and optionally execute action"""
        # Format message
        message = condition.message_template.format(value=metric.value)

        logger.warning(f"ALERT [{condition.alert_level.value.upper()}]: {message}")

        # Record alert
        alert_record = {
            "timestamp": time.time(),
            "metric_type": condition.metric_type.value,
            "alert_level": condition.alert_level.value,
            "message": message,
            "metric_value": metric.value,
            "condition_threshold": condition.threshold,
        }

        # Save alert
        self._save_alert(alert_record)

        # Update cooldown timestamp
        metric_key = f"{condition.metric_type.value}_{condition.alert_level.value}"
        setattr(self, f"last_alert_{metric_key}", time.time())

        # Execute automatic action if enabled
        if self.auto_swap_enabled and condition:
            action_task = asyncio.create_task(self._execute_automatic_action(condition, metric))
            _BACKGROUND_TASKS.add(action_task)
            action_task.add_done_callback(_BACKGROUND_TASKS.discard)

    async def _execute_automatic_action(
        self, condition: AlertCondition | None, metric: PerformanceMetric
    ):
        """Execute automatic optimization action"""
        if condition:
            logger.info(f"Executing automatic action: {condition.action.value}")

        try:
            if condition and condition.action == ActionType.MODEL_SWAP:
                decision = await self._evaluate_model_swap(metric)
                if decision.should_swap:
                    await self._perform_model_swap(decision)

            elif condition and condition.action == ActionType.CONTEXT_REDUCTION:
                await self._reduce_context_windows()

            elif condition and condition.action == ActionType.THREAD_ADJUSTMENT:
                await self._adjust_thread_allocation(metric)

            elif condition and condition.action == ActionType.IDE_PRIORITY_ADJUST:
                await self._adjust_ide_priorities(metric)

            elif condition and condition.action == ActionType.SYSTEM_RESTART:
                await self._emergency_system_restart()

        except Exception as e:
            action_name = condition.action.value if condition else "unknown"
            logger.error(f"Failed to execute automatic action {action_name}: {e}")

    async def _auto_swap_monitor(self):
        """Monitor for auto-swap opportunities"""
        while self.monitoring_active:
            try:
                # Check every 2 minutes
                await asyncio.sleep(120)

                if not self.auto_swap_enabled:
                    continue

                # Look for optimization opportunities
                optimization = await self._find_optimization_opportunity()

                if optimization:
                    logger.info(f"Found optimization opportunity: {optimization['reason']}")
                    await self._execute_automatic_action(None, optimization["metric"])

            except Exception as e:
                logger.error(f"Auto-swap monitor error: {e}")

    async def _find_optimization_opportunity(self) -> dict[str, Any] | None:
        """Find opportunities for automatic optimization"""
        recent_metrics = self.metrics_history[-100:]  # Last 100 metrics

        # Analyze trends
        memory_trend = self._analyze_trend(
            [m for m in recent_metrics if m.metric_type == MetricType.MEMORY_USAGE]
        )

        latency_trend = self._analyze_trend(
            [m for m in recent_metrics if m.metric_type == MetricType.MODEL_LATENCY]
        )

        # Check for consistent poor performance
        if (memory_trend > 0.7 and latency_trend > 0.5) and (
            time.time() - self.last_swap_time
        ) > self.swap_cooldown_seconds:
            return {
                "metric": PerformanceMetric(
                    metric_type=MetricType.MEMORY_USAGE,
                    value=memory_trend,
                    unit="trend",
                    timestamp=time.time(),
                    source="auto_swap_monitor",
                    metadata={"latency_trend": latency_trend},
                ),
                "reason": f"Consistent high memory ({memory_trend:.2f}) and latency ({latency_trend:.2f}) trends",
            }

        return None

    def _analyze_trend(self, metrics: list[PerformanceMetric]) -> float:
        """Analyze trend in metrics"""
        if len(metrics) < 10:
            return 0.0

        # Simple linear trend analysis
        values = [m.value for m in metrics]
        x = list(range(len(values)))

        # Calculate slope
        n = len(values)
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)

        # Normalize to 0-1 scale
        return min(max(slope * 10, -1), 1)

    async def _evaluate_model_swap(self, metric: PerformanceMetric) -> AutoSwapDecision:
        """Evaluate if model swap is beneficial"""

        # Get currently loaded models (simplified)
        current_models = await self._get_loaded_models()

        if not current_models:
            return AutoSwapDecision(
                should_swap=False,
                current_model="",
                recommended_model="",
                reason="No loaded models detected",
                confidence=0.0,
                action_type=ActionType.MODEL_SWAP,
                estimated_improvement=0.0,
            )

        current_model = current_models[0]  # Assume first is primary

        # Determine swap recommendation based on metric type
        if metric.metric_type == MetricType.MEMORY_USAGE:
            if metric.value > 0.85:  # High memory usage
                recommended_model = self._find_smaller_model(current_model)
                estimated_improvement = 20.0  # 20% improvement
            else:
                return AutoSwapDecision(
                    should_swap=False,
                    current_model=current_model,
                    recommended_model="",
                    reason="Memory usage within acceptable range",
                    confidence=0.9,
                    action_type=ActionType.MODEL_SWAP,
                    estimated_improvement=0.0,
                )

        elif metric.metric_type == MetricType.MODEL_LATENCY:
            if metric.value > 5.0:  # High latency
                recommended_model = self._find_faster_model(current_model)
                estimated_improvement = 30.0
            else:
                return AutoSwapDecision(
                    should_swap=False,
                    current_model=current_model,
                    recommended_model="",
                    reason="Latency within acceptable range",
                    confidence=0.9,
                    action_type=ActionType.MODEL_SWAP,
                    estimated_improvement=0.0,
                )

        else:
            recommended_model = ""
            estimated_improvement = 0.0

        return AutoSwapDecision(
            should_swap=bool(recommended_model),
            current_model=current_model,
            recommended_model=recommended_model,
            reason=f"Optimization based on {metric.metric_type.value}",
            confidence=0.8,
            action_type=ActionType.MODEL_SWAP,
            estimated_improvement=estimated_improvement,
        )

    async def _get_loaded_models(self) -> list[str]:
        """Get list of currently loaded models"""
        try:
            result = subprocess.run(  # noqa: S603 - ollama args static
                [_OLLAMA, "list"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                models = []
                for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                    if line.strip():
                        model_name = line.split()[0]
                        models.append(model_name)
                return models
        except Exception as e:
            logger.error(f"Failed to get loaded models: {e}")

        return []

    def _find_smaller_model(self, current_model: str) -> str:
        """Find a smaller model for swap"""
        # Model size hierarchy (largest to smallest)
        model_hierarchy = [
            "qwen3-coder-next:q8_0",  # 84GB
            "qwen3-coder-next:latest",  # 51GB
            "qwen3-coder-30b",  # 18GB
            "qwen2.5-coder-14b-256k:latest",  # 9GB
            "phi4:latest",  # 9.1GB
            "qwen3:8b",  # 5.2GB
            "phi3:mini",  # 2.2GB
        ]

        try:
            current_index = model_hierarchy.index(current_model)
            # Return next smaller model
            if current_index < len(model_hierarchy) - 1:
                return model_hierarchy[current_index + 1]
        except ValueError:
            pass

        # Fallback to smallest model
        return "phi3:mini"

    def _find_faster_model(self, current_model: str) -> str:
        """Find a faster model for swap"""
        # Speed hierarchy (fastest to slowest)
        speed_hierarchy = [
            "phi3:mini",  # Fastest small model
            "qwen3:8b",  # Fast small model with Q8_0
            "phi4:latest",  # Fast medium model
            "qwen2.5-coder-14b-256k:latest",  # Balanced speed/quality
            "qwen3-coder-30b",  # Slower but capable
            "qwen3-coder-next:latest",  # Slower large model
            "qwen3-coder-next:q8_0",  # Slowest but highest quality
        ]

        try:
            current_index = speed_hierarchy.index(current_model)
            # Return next faster model
            if current_index > 0:
                return speed_hierarchy[current_index - 1]
        except ValueError:
            pass

        # Fallback to fastest model
        return "phi3:mini"

    async def _perform_model_swap(self, decision: AutoSwapDecision):
        """Perform automatic model swap"""
        logger.info(
            f"Performing model swap: {decision.current_model} -> {decision.recommended_model}"
        )
        logger.info(f"Reason: {decision.reason} (confidence: {decision.confidence:.2f})")

        try:
            # Unload current model
            subprocess.run(  # noqa: S603 - decision fields are internal model registry strings
                [_OLLAMA, "stop", decision.current_model],
                capture_output=True,
                timeout=30,
            )

            # Load recommended model
            subprocess.run(  # noqa: S603 - decision fields are internal model registry strings
                [_OLLAMA, "run", decision.recommended_model, "--dummy"],
                capture_output=True,
                timeout=60,
            )

            # Record swap
            swap_record = {
                "timestamp": time.time(),
                "from_model": decision.current_model,
                "to_model": decision.recommended_model,
                "reason": decision.reason,
                "confidence": decision.confidence,
                "estimated_improvement": decision.estimated_improvement,
            }

            self._save_swap_decision(swap_record)
            self.last_swap_time = time.time()

            logger.info("Model swap completed successfully")

        except Exception as e:
            logger.error(f"Model swap failed: {e}")

    async def _reduce_context_windows(self):
        """Reduce context windows for memory pressure"""
        logger.info("Reducing context windows to free memory")

        # This would integrate with the dynamic router
        # For now, just log the action
        pass

    async def _adjust_thread_allocation(self, metric: PerformanceMetric):
        """Adjust thread allocation based on performance"""
        current_usage = metric.value

        if current_usage > 90:  # High CPU usage
            new_threads = max(4, self.total_threads // 4)  # Reduce to 25%
        elif current_usage > 70:  # Medium CPU usage
            new_threads = max(8, self.total_threads // 2)  # Reduce to 50%
        else:
            new_threads = self.total_threads * 3 // 4  # Default to 75%

        logger.info(f"Adjusting thread allocation to {new_threads} threads")

        # Update environment variables
        os.environ["OLLAMA_NUM_THREADS"] = str(new_threads)

    async def _adjust_ide_priorities(self, metric: PerformanceMetric):
        """Adjust IDE priorities based on system load"""
        queue_depth = metric.value

        if queue_depth > 10:  # Very high queue
            logger.info("High queue depth - prioritizing Antigravity IDE")
            # This would integrate with config manager
        elif queue_depth > 5:  # Medium queue
            logger.info("Elevating ZED IDE priority")

    async def _emergency_system_restart(self):
        """Emergency system restart for critical conditions"""
        logger.critical("Emergency system restart initiated")

        # Save all data before restart
        self._save_metrics()

        # Graceful shutdown of Ollama
        try:
            subprocess.run([_PKILL, "-f", "ollama"], timeout=10)  # noqa: S603 - args static
        except Exception as e:
            logger.debug("Ollama shutdown failed during emergency restart: %s", e)

        # Restart Ollama with conservative settings
        subprocess.run(  # noqa: S603 - bash command is a static maintenance script
            [
                _BASH,
                "-c",
                "sleep 5 && OLLAMA_NUM_THREADS=8 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 ollama serve &",
            ]
        )

    def _save_alert(self, alert_record: dict[str, Any]):
        """Save alert record"""
        alerts = []
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file) as f:
                    alerts = json.load(f).get("alerts", [])
            except (json.JSONDecodeError, OSError):
                pass

        alerts.append(alert_record)

        # Keep only last 1000 alerts
        if len(alerts) > 1000:
            alerts = alerts[-1000:]

        with open(self.alerts_file, "w") as f:
            json.dump({"alerts": alerts}, f, indent=2)

    def _save_swap_decision(self, swap_record: dict[str, Any]):
        """Save swap decision record"""
        decisions = []
        if self.decisions_file.exists():
            try:
                with open(self.decisions_file) as f:
                    decisions = json.load(f).get("decisions", [])
            except (json.JSONDecodeError, OSError):
                pass

        decisions.append(swap_record)

        # Keep only last 500 decisions
        if len(decisions) > 500:
            decisions = decisions[-500:]

        with open(self.decisions_file, "w") as f:
            json.dump({"decisions": decisions}, f, indent=2)

    def _save_metrics(self):
        """Save performance metrics"""
        metrics_data = {
            "metrics": [asdict(m) for m in self.metrics_history[-1000:]],  # Last 1000
            "timestamp": time.time(),
            "system_info": {
                "total_memory_gb": self.total_memory_gb,
                "total_threads": self.total_threads,
                "l3_cache_mb": self.l3_cache_mb,
                "ddr5_bandwidth_gbps": self.ddr5_bandwidth_gbps,
            },
        }

        with open(self.metrics_file, "w") as f:
            json.dump(metrics_data, f, indent=2)

    def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary"""
        recent_metrics = self.metrics_history[-100:]  # Last 100 metrics

        summary = {
            "timestamp": time.time(),
            "monitoring_active": self.monitoring_active,
            "auto_swap_enabled": self.auto_swap_enabled,
            "current_metrics": {},
            "trends": {},
            "alerts_count": 0,
            "last_swap_time": self.last_swap_time,
        }

        # Current values for each metric type
        for metric_type in MetricType:
            type_metrics = [m for m in recent_metrics if m.metric_type == metric_type]
            if type_metrics:
                latest = type_metrics[-1]
                summary["current_metrics"][metric_type.value] = {
                    "value": latest.value,
                    "unit": latest.unit,
                    "timestamp": latest.timestamp,
                }

        return summary

    def enable_auto_swap(self, enabled: bool):
        """Enable or disable automatic swapping"""
        self.auto_swap_enabled = enabled
        logger.info(f"Auto-swap {'enabled' if enabled else 'disabled'}")


# Initialize global performance monitor
performance_monitor = QuantumPerformanceMonitor()

if __name__ == "__main__":
    # Test performance monitoring
    def test_monitor():
        print("🚀 Starting Quantum Performance Monitor Test")

        # Start monitoring
        performance_monitor.start_monitoring(interval_seconds=10)

        # Simulate some metrics for testing
        import random

        for _ in range(50):
            metric = PerformanceMetric(
                metric_type=random.choice(list(MetricType)),
                value=random.uniform(0, 100),
                unit="test",
                timestamp=time.time(),
                source="test",
                metadata={},
            )
            performance_monitor.metrics_history.append(metric)

            time.sleep(1)

        # Get summary
        summary = performance_monitor.get_performance_summary()
        print(f"Performance Summary: {json.dumps(summary, indent=2)}")

    test_monitor()
