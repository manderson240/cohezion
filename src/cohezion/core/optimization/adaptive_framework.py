#!/usr/bin/env python3
"""
COHEZION Adaptive Framework Optimization Engine
Advanced hardware detection and automatic configuration selection for optimal performance.
"""

import json
import logging
import psutil
import platform
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HardwareProfile:
    """Detected hardware capabilities"""

    total_memory_gb: float
    available_memory_gb: float
    cpu_cores: int
    cpu_type: str
    gpu_count: int
    gpu_memory_total: float
    gpu_type: Optional[str]
    platform: str
    architecture: str
    capabilities: list[str]
    tier: str


class AdaptiveFrameworkOptimizer:
    """Adaptive framework optimization with intelligent hardware detection"""

    def __init__(self, config_dir: str = "/home/mike-anderson/dev/cohezion/config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Hardware profile cache
        self._hardware_cache = None
        self._current_profile = None

        # Available framework configurations
        self.framework_configs = {
            "mobile": self.config_dir / "framework_mobile.json",
            "framework_desktop": self.config_dir / "framework_desktop.json",
            "framework_pro": self.config_dir / "framework_pro.json",
            "adaptive": self.config_dir / "adaptive_optimization.json",
        }

        logger.info("🧠 Adaptive Framework Optimizer initialized")

    def detect_hardware_profile(self) -> HardwareProfile:
        """Comprehensive hardware detection and tier classification"""
        if self._hardware_cache:
            return self._hardware_cache

        logger.info("🔍 Performing hardware detection...")

        # Memory detection
        memory = psutil.virtual_memory()
        total_memory_gb = round(memory.total / (1024**3), 1)
        available_memory_gb = round(memory.available / (1024**3), 1)

        # CPU detection
        cpu_cores = psutil.cpu_count(logical=False)
        cpu_type = platform.processor() or "Unknown CPU"
        cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else 0
        architecture = platform.machine() or "Unknown"

        # GPU detection
        gpu_count = 0
        gpu_memory_total = 0
        gpu_type = None
        gpu_capabilities = []

        try:
            import GPUtil

            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_count = len(gpus)
                gpu_memory_total = (
                    sum(gpu.memoryTotal for gpu in gpus) / 1024
                )  # MB to GB
                gpu_type = gpus[0].name if gpus else "Unknown GPU"
                gpu_capabilities = [f"cuda_{gpu.name}" for gpu in gpus]
        except ImportError:
            logger.warning("⚠️ GPUtil not available - limited GPU detection")

        # Platform detection
        system_platform = platform.system()

        # Determine tier and capabilities
        tier, capabilities = self._classify_hardware_tier(
            total_memory_gb, available_memory_gb, cpu_cores, gpu_count, gpu_memory_total
        )

        self._hardware_cache = HardwareProfile(
            total_memory_gb=total_memory_gb,
            available_memory_gb=available_memory_gb,
            cpu_cores=cpu_cores,
            cpu_type=cpu_type,
            gpu_count=gpu_count,
            gpu_memory_total=gpu_memory_total,
            gpu_type=gpu_type,
            platform=system_platform,
            architecture=architecture,
            capabilities=capabilities,
            tier=tier,
        )

        logger.info(
            f"✅ Hardware Detected: {tier} tier - {total_memory_gb}GB RAM, {cpu_cores} cores, {gpu_count} GPUs"
        )
        return self._hardware_cache

    def _classify_hardware_tier(
        self,
        memory_gb: float,
        available_gb: float,
        cpu_cores: int,
        gpu_count: int,
        gpu_memory_gb: float,
    ) -> Tuple[str, list[str]]:
        """Classify hardware into performance tiers"""

        # Calculate performance score
        memory_score = min(memory_gb / 128.0, 2.0)  # Normalized to 128GB baseline
        cpu_score = min(cpu_cores / 16.0, 2.0)  # Normalized to 16 cores
        gpu_score = min(gpu_count / 2.0, 2.0) if gpu_count > 0 else 0.0
        vram_score = min(gpu_memory_gb / 24.0, 2.0) if gpu_memory_gb > 0 else 0.0

        total_score = (memory_score + cpu_score + gpu_score + vram_score) / 4.0

        if total_score >= 1.5:
            tier = "enterprise"
            capabilities = [
                "massive_universe_simulation",
                "advanced_multimodal_processing",
                "high_performance_optimization",
                "advanced_compound_engineering",
                "multi_gpu_optimization",
                "distributed_inference",
                "enterprise_deployment",
            ]
        elif total_score >= 1.0:
            tier = "professional"
            capabilities = [
                "advanced_universe_simulation",
                "multimodal_processing",
                "high_performance_optimization",
                "advanced_compound_engineering",
                "multi_gpu_optimization",
                "tensor_parallelization",
            ]
        elif total_score >= 0.6:
            tier = "desktop"
            capabilities = [
                "full_universe_simulation",
                "advanced_ai_processing",
                "gpu_acceleration",
                "compound_engineering",
                "development_tools",
            ]
        elif total_score >= 0.3:
            tier = "laptop"
            capabilities = [
                "lightweight_universe_simulation",
                "on_device_ai",
                "gpu_acceleration",
                "basic_multimodal_processing",
            ]
        else:
            tier = "mobile"
            capabilities = [
                "lightweight_universe_simulation",
                "on_device_ai",
                "basic_multimodal_processing",
                "offline_capability",
                "efficient_algorithms",
            ]

        return tier, capabilities

    def select_optimal_framework_config(
        self, hardware_profile: Optional[HardwareProfile] = None
    ) -> Dict[str, Any]:
        """Select optimal framework configuration based on detected hardware"""
        if not hardware_profile:
            hardware_profile = self.detect_hardware_profile()

        self._current_profile = hardware_profile

        # Load base configuration for tier
        if hardware_profile.tier == "enterprise":
            config_file = self.framework_configs.get("framework_pro")
            config_type = "Professional Workstation (128GB)"
        elif hardware_profile.tier == "professional":
            config_file = self.framework_configs.get("framework_pro")
            config_type = "Professional Workstation (128GB)"
        elif hardware_profile.tier == "desktop":
            config_file = self.framework_configs.get("framework_desktop")
            config_type = "High-End Desktop (96GB)"
        elif hardware_profile.tier == "laptop":
            config_file = self.framework_configs.get("framework_desktop")
            config_type = "Laptop (48-64GB)"
        else:
            config_file = self.framework_configs.get("framework_desktop")
            config_type = "Mobile/Low-End (32GB)"

        # Load and adapt configuration
        if config_file and config_file.exists():
            with open(config_file, "r") as f:
                config = json.load(f)

            # Adapt configuration to actual hardware
            adapted_config = self._adapt_config_to_hardware(config, hardware_profile)

            logger.info(f"🎯 Loaded {config_type} configuration")
            return adapted_config
        else:
            logger.error(f"❌ Configuration file not found: {config_file}")
            return self._create_fallback_config(hardware_profile)

    def _adapt_config_to_hardware(
        self, config: Dict[str, Any], hardware: HardwareProfile
    ) -> Dict[str, Any]:
        """Adapt configuration parameters to actual hardware capabilities"""
        adapted = config.copy()

        # Adjust memory targets to actual available
        actual_memory = hardware.available_memory_gb
        adapted["hardware_actual"] = {
            "total_memory_gb": hardware.total_memory_gb,
            "available_memory_gb": hardware.available_memory_gb,
            "cpu_cores": hardware.cpu_cores,
            "gpu_count": hardware.gpu_count,
            "gpu_memory_gb": hardware.gpu_memory_total,
            "detection_timestamp": psutil.boot_time(),
        }

        # Scale optimization targets based on actual resources
        if "optimization_targets" in adapted:
            memory_efficiency = adapted["optimization_targets"]["memory_efficiency"]
            if actual_memory < 64:  # Low memory systems
                memory_efficiency["target"] = "90%"  # Stricter efficiency needed
                memory_efficiency["strategies"].append("aggressive_garbage_collection")
            elif actual_memory > 200:  # High memory systems
                memory_efficiency["target"] = "75%"  # Can afford more overhead
                memory_efficiency["strategies"].append("memory_pool_optimization")

        # Adjust model configurations based on GPU capabilities
        if hardware.gpu_count == 0:
            # CPU-only optimization
            if "model_configurations" in adapted:
                for model_config in adapted["model_configurations"].values():
                    model_config["batch_size"] = 1  # Conservative for CPU
                    model_config["optimization"] = "cpu_optimized"

        return adapted

    def _create_fallback_config(self, hardware: HardwareProfile) -> Dict[str, Any]:
        """Create fallback configuration for unsupported hardware"""
        logger.warning("⚠️ Using fallback configuration")
        return {
            "framework_type": "fallback",
            "hardware_tier": hardware.tier,
            "optimization_mode": "conservative",
            "model_configurations": {
                "default": {
                    "context_window": 32768,
                    "batch_size": 1,
                    "temperature": 0.7,
                    "optimization": "cpu_optimized",
                }
            },
            "runtime_optimization": {
                "auto_scale_context": False,  # Conservative for unknown hardware
                "dynamic_batching": False,
                "memory_pressure_handling": "immediate_fallback",
            },
        }

    def get_current_profile(self) -> Optional[HardwareProfile]:
        """Get currently detected hardware profile"""
        return self._current_profile

    def create_adaptive_config(self) -> Dict[str, Any]:
        """Create adaptive optimization configuration for dynamic switching"""
        return {
            "adaptive_optimization": {
                "enabled": True,
                "detection_interval": 300,  # Check every 5 minutes
                "performance_window": 60,  # 1 hour performance history
                "auto_switch_threshold": 0.8,  # Switch if 80% performance improvement
                "modes": ["conservative", "performance", "efficiency", "multimodal"],
                "transition_grace_period": 120,  # 2 minutes grace period
            },
            "dynamic_scaling": {
                "memory_pressure_scaling": True,
                "cpu_load_scaling": True,
                "gpu_utilization_scaling": True,
                "batch_size_adaptation": True,
                "context_window_adaptation": True,
            },
            "intelligent_routing": {
                "cost_optimization": True,
                "quality_threshold": 0.85,
                "latency_threshold_ms": 2000,
                "hybrid_mode": "auto",
                "local_preference": 0.7,  # 70% preference for local models
            },
            "monitoring": {
                "real_time_metrics": True,
                "performance_history": True,
                "resource_tracking": True,
                "alert_system": True,
                "auto_tuning": True,
            },
        }

    def optimize_runtime_parameters(
        self, config: Dict[str, Any], current_workload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize runtime parameters based on current workload"""
        optimized = config.copy()

        # Analyze current workload
        workload_type = current_workload.get("type", "general")
        complexity = current_workload.get("complexity", "medium")
        latency_requirement = current_workload.get("latency_requirement", "normal")

        # Dynamic parameter optimization
        if "runtime_optimization" in optimized:
            rt_opt = optimized["runtime_optimization"]

            # Adjust based on workload type
            if workload_type == "coding":
                rt_opt["temperature"] = 0.6  # More deterministic for coding
                rt_opt["top_p"] = 0.85
            elif workload_type == "creative":
                rt_opt["temperature"] = 0.9  # More creative
                rt_opt["top_p"] = 0.95
            elif workload_type == "analysis":
                rt_opt["temperature"] = 0.3  # Very deterministic
                rt_opt["top_p"] = 0.8

            # Adjust based on complexity
            if complexity == "simple":
                rt_opt["context_window"] = min(
                    rt_opt.get("context_window", 32768), 8192
                )
            elif complexity == "complex":
                rt_opt["context_window"] = min(
                    rt_opt.get("context_window", 32768), 65536
                )

            # Adjust based on latency
            if latency_requirement == "real_time":
                rt_opt["batch_size"] = 1
                rt_opt["max_tokens"] = min(rt_opt.get("max_tokens", 4096), 1024)

        optimized["workload_adaptation"] = {
            "workload_type": workload_type,
            "complexity": complexity,
            "latency_requirement": latency_requirement,
            "optimization_timestamp": psutil.boot_time(),
        }

        return optimized


# Global optimizer instance
_adaptive_optimizer = None


def get_adaptive_optimizer() -> AdaptiveFrameworkOptimizer:
    """Get or create global adaptive optimizer instance"""
    global _adaptive_optimizer
    if _adaptive_optimizer is None:
        _adaptive_optimizer = AdaptiveFrameworkOptimizer()
    return _adaptive_optimizer


def auto_detect_and_configure() -> Dict[str, Any]:
    """Auto-detect hardware and load optimal configuration"""
    optimizer = get_adaptive_optimizer()
    return optimizer.select_optimal_framework_config()
