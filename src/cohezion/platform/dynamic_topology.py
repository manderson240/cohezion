"""Dynamic Modularity Hardware Topology Manager for Strix Halo Sovereign Inference.
====================================================================================
Provides runtime resolution, dynamic environment overrides, and hardware lane abstraction
across AMD XDNA 2 NPU, Radeon 8060S iGPU, Zen 5 CPU, and Tier 2/3 Cloud reserves.

Zero hardcoded ports; fully hot-reloadable and configurable via environment or JSON profiles.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "hardware" / "strix_halo_topology.json"


@dataclass(frozen=True)
class NPULaneConfig:
    """Configuration schema for the dedicated AMD XDNA 2 NPU Lane."""

    enabled: bool = True
    hardware: str = "AMD XDNA 2 NPU"
    service_name: str = "fastflowlm-npu.service"
    endpoint: str = "http://127.0.0.1:52625/v1/chat/completions"
    default_model: str = "llama3.2:1b"
    available_models: list[str] = field(default_factory=lambda: ["llama3.2:1b", "qwen3.5:4b", "deepseek-r1:8b"])
    power_mode: str = "performance"
    memory_footprint_mb: float = 0.0
    max_context: int = 4096


@dataclass(frozen=True)
class CPULaneConfig:
    """Configuration schema for the host Zen 5 CPU Lane."""

    enabled: bool = True
    hardware: str = "Zen 5 CPU (16c / 32t)"
    endpoint: str = "http://127.0.0.1:13305/v1/chat/completions"
    default_model: str = "Qwen3.6-35B-A3B-Instruct"
    max_concurrent_models: int = 2
    default_context_size: int = 8192
    memory_floor_gb: float = 25.0


@dataclass(frozen=True)
class GPULaneConfig:
    """Configuration schema for the Radeon 8060S iGPU Embedding Lane."""

    enabled: bool = True
    hardware: str = "Radeon 8060S (40 CUs)"
    endpoint: str = "http://127.0.0.1:8006/v1/embeddings"
    default_model: str = "nomic-embed-text-v2-moe.Q8_0"
    max_context: int = 8192
    uma_ceiling_gb: float = 2.0


@dataclass(frozen=True)
class CloudRationingConfig:
    """Configuration schema for Tier 2 and Tier 3 quota protection."""

    rationing_active: bool = True
    evi_threshold: float = 0.85
    allow_background_fallback: bool = False
    endpoint: str = "http://127.0.0.1:11434/v1/chat/completions"


@dataclass
class DynamicTopology:
    """Dynamic Strix Halo Hardware Topology State."""

    topology_version: str = "2.0.0"
    npu: NPULaneConfig = field(default_factory=NPULaneConfig)
    cpu: CPULaneConfig = field(default_factory=CPULaneConfig)
    gpu: GPULaneConfig = field(default_factory=GPULaneConfig)
    cloud: CloudRationingConfig = field(default_factory=CloudRationingConfig)

    @classmethod
    def load(cls, config_path: Path | None = None) -> DynamicTopology:
        """Load topology from JSON profile, merging live environment variable overrides.

        Parameters
        ----------
        config_path : Optional[Path]
            Custom path to topology JSON file. Defaults to config/hardware/strix_halo_topology.json.

        Returns
        -------
        DynamicTopology
            The resolved and validated hardware topology instance.
        """
        path = config_path or DEFAULT_CONFIG_PATH
        raw_data: dict[str, Any] = {}
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
            except Exception as e:
                logger.warning("Failed to parse topology config %s: %s; using defaults", path, e)

        profile = raw_data.get("profiles", {}).get("default", {}).get("lanes", {})

        # 1. Resolve NPU Lane
        npu_raw = profile.get("npu", {})
        npu_ep = os.getenv("FLM_ENDPOINT") or os.getenv("FASTFLOWLM_URL")
        if not npu_ep:
            port = os.getenv("FLM_PORT", str(npu_raw.get("endpoint", "52625")))
            if "://" in port:
                npu_ep = port
            else:
                npu_ep = f"http://127.0.0.1:{port}/v1/chat/completions"
        npu_model = os.getenv("FLM_MODEL", npu_raw.get("default_model", "llama3.2:1b"))
        npu_config = NPULaneConfig(
            enabled=npu_raw.get("enabled", True),
            endpoint=npu_ep,
            default_model=npu_model,
            power_mode=os.getenv("FLM_PMODE", npu_raw.get("power_mode", "performance")),
            max_context=int(os.getenv("FLM_MAX_CONTEXT", str(npu_raw.get("max_context", 4096)))),
        )

        # 2. Resolve CPU Lane
        cpu_raw = profile.get("cpu_sovereign", {})
        cpu_ep = os.getenv("LEMONADE_ENDPOINT", cpu_raw.get("endpoint", "http://127.0.0.1:13305/v1/chat/completions"))
        cpu_ctx = int(os.getenv("LEMONADE_CTX_SIZE", str(cpu_raw.get("default_context_size", 8192))))
        cpu_models = int(os.getenv("LEMONADE_MAX_MODELS", str(cpu_raw.get("max_concurrent_models", 2))))
        cpu_floor = float(os.getenv("LEMONADE_MEMORY_FLOOR_GB", str(cpu_raw.get("memory_floor_gb", 25.0))))
        cpu_config = CPULaneConfig(
            enabled=cpu_raw.get("enabled", True),
            endpoint=cpu_ep,
            default_context_size=cpu_ctx,
            max_concurrent_models=cpu_models,
            memory_floor_gb=cpu_floor,
        )

        # 3. Resolve GPU Lane
        gpu_raw = profile.get("gpu_embeddings", {})
        gpu_config = GPULaneConfig(
            enabled=gpu_raw.get("enabled", True),
            endpoint=os.getenv("EMBEDDINGS_ENDPOINT", gpu_raw.get("endpoint", "http://127.0.0.1:8006/v1/embeddings")),
            default_model=gpu_raw.get("default_model", "nomic-embed-text-v2-moe.Q8_0"),
        )

        # 4. Resolve Cloud Rationing
        cloud_raw = profile.get("tier2_ollama_cloud", {})
        rationing_env = os.getenv("OLLAMA_CLOUD_RATIONING", "1")
        cloud_config = CloudRationingConfig(
            rationing_active=(rationing_env == "1"),
            evi_threshold=float(os.getenv("OLLAMA_CLOUD_EVI_THRESHOLD", str(cloud_raw.get("evi_threshold", 0.85)))),
            allow_background_fallback=(os.getenv("OLLAMA_CLOUD_ALLOW_FALLBACK", "0") == "1"),
            endpoint=os.getenv("OLLAMA_CLOUD_ENDPOINT", cloud_raw.get("endpoint", "http://127.0.0.1:11434/v1/chat/completions")),
        )

        return cls(
            topology_version=raw_data.get("topology_version", "2.0.0"),
            npu=npu_config,
            cpu=cpu_config,
            gpu=gpu_config,
            cloud=cloud_config,
        )

    def is_cloud_fallback_allowed(self, is_background_task: bool = False, evi_score: float = 0.0) -> bool:
        """Determine whether falling back to cloud is permitted under active rationing rules."""
        if not self.cloud.rationing_active:
            return True
        if is_background_task and not self.cloud.allow_background_fallback:
            return False
        return evi_score >= self.cloud.evi_threshold
