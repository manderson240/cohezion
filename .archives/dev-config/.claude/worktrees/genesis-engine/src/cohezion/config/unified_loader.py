"""Unified configuration loader for kernel research.

Loads configuration from unified location (src/cohezion/kernels/)
with fallback to worktree research configs if needed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cohezion.config.unified import SystemConfig, get_config as get_system_config


# Unified config paths
UNIFIED_ROOT = Path(__file__).parent.parent
KERNEL_ROOT = UNIFIED_ROOT / "kernels"
KSEARCH_ROOT = UNIFIED_ROOT / "ksearch"

# Worktree fallback paths (for legacy compatibility)
WORKTREE_KERNEL_ROOT = Path("/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/kernels")
WORKTREE_KSEARCH_ROOT = Path("/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/autoresearch")


def get_unified_kernel_path(kernel_type: str, hardware: str = "amd") -> Path:
    """Get the unified path for a kernel type.

    Args:
        kernel_type: Type of kernel (gemm, moe, mla)
        hardware: Hardware platform (amd, nvidia)

    Returns:
        Path to the kernel directory
    """
    return KERNEL_ROOT / hardware / kernel_type


def get_unified_tree_path(kernel_type: str) -> Path:
    """Get the unified path for a kernel tree.

    Args:
        kernel_type: Type of kernel (gemm, moe, mla)

    Returns:
        Path to the tree JSON file
    """
    return KSEARCH_ROOT / "trees" / f"{kernel_type}_tree.json"


def load_kernel_config(kernel_type: str, hardware: str = "amd") -> dict[str, Any] | None:
    """Load kernel configuration from unified location.

    Args:
        kernel_type: Type of kernel (gemm, moe, mla)
        hardware: Hardware platform (amd, nvidia)

    Returns:
        Kernel configuration dict or None if not found
    """
    kernel_path = get_unified_kernel_path(kernel_type, hardware)

    # Try task.yml first (new format), then task.py config
    config_files = ["task.yml", "config.json", "config.yaml"]

    for config_file in config_files:
        config_path = kernel_path / config_file
        if config_path.exists():
            if config_file.endswith(".json"):
                with open(config_path, encoding="utf-8") as f:
                    return json.load(f)
            else:
                # For YAML files, return a simple dict with the path
                return {"config_path": str(config_path), "format": "yaml"}

    return None


def load_tree_config(kernel_type: str) -> dict[str, Any] | None:
    """Load tree configuration from unified location.

    Args:
        kernel_type: Type of kernel (gemm, moe, mla)

    Returns:
        Tree configuration dict or None if not found
    """
    tree_path = get_unified_tree_path(kernel_type)

    if tree_path.exists():
        with open(tree_path, encoding="utf-8") as f:
            return json.load(f)

    # Fallback to worktree
    worktree_path = WORKTREE_KSEARCH_ROOT / "tree" / f"{kernel_type}_tree.json"
    if worktree_path.exists():
        with open(worktree_path, encoding="utf-8") as f:
            return json.load(f)

    return None


def resolve_kernel_path(relative_path: str) -> Path | None:
    """Resolve a kernel path using unified location first, then fallback.

    Args:
        relative_path: Path relative to kernel root

    Returns:
        Resolved Path or None if not found
    """
    # Try unified location first
    unified_path = KERNEL_ROOT / relative_path
    if unified_path.exists():
        return unified_path

    # Fallback to worktree
    worktree_path = WORKTREE_KERNEL_ROOT / relative_path
    if worktree_path.exists():
        return worktree_path

    return None


class UnifiedConfig:
    """Unified configuration manager for kernel research.

    Provides access to both system configuration and kernel-specific
    configurations with automatic fallback handling.
    """

    def __init__(self):
        self._system_config: SystemConfig | None = None
        self._kernel_configs: dict[str, dict[str, Any]] = {}
        self._tree_configs: dict[str, dict[str, Any]] = {}

    @property
    def system(self) -> SystemConfig:
        """Get system configuration."""
        if self._system_config is None:
            self._system_config = get_system_config()
        return self._system_config

    def get_kernel(self, kernel_type: str, hardware: str = "amd") -> dict[str, Any] | None:
        """Get kernel configuration.

        Args:
            kernel_type: Type of kernel (gemm, moe, mla)
            hardware: Hardware platform (amd, nvidia)

        Returns:
            Kernel configuration dict
        """
        cache_key = f"{hardware}/{kernel_type}"
        if cache_key not in self._kernel_configs:
            self._kernel_configs[cache_key] = load_kernel_config(kernel_type, hardware)
        return self._kernel_configs[cache_key]

    def get_tree(self, kernel_type: str) -> dict[str, Any] | None:
        """Get tree configuration.

        Args:
            kernel_type: Type of kernel (gemm, moe, mla)

        Returns:
            Tree configuration dict
        """
        if kernel_type not in self._tree_configs:
            self._tree_configs[kernel_type] = load_tree_config(kernel_type)
        return self._tree_configs[kernel_type]

    def list_available_kernels(self, hardware: str = "amd") -> list[str]:
        """List available kernel types for a hardware platform.

        Args:
            hardware: Hardware platform (amd, nvidia)

        Returns:
            List of available kernel types
        """
        hardware_path = KERNEL_ROOT / hardware
        if not hardware_path.exists():
            return []

        return [
            d.name
            for d in hardware_path.iterdir()
            if d.is_dir() and (d / "task.py").exists()
        ]

    def list_available_trees(self) -> list[str]:
        """List available tree configurations.

        Returns:
            List of available tree types
        """
        trees_path = KSEARCH_ROOT / "trees"
        if not trees_path.exists():
            return []

        return [
            f.stem.replace("_tree", "")
            for f in trees_path.glob("*_tree.json")
        ]

    def clear_cache(self) -> None:
        """Clear all cached configurations."""
        self._system_config = None
        self._kernel_configs.clear()
        self._tree_configs.clear()


# Singleton instance
_unified_config = None


def get_unified_config() -> UnifiedConfig:
    """Get or create the unified configuration singleton."""
    global _unified_config
    if _unified_config is None:
        _unified_config = UnifiedConfig()
    return _unified_config


def reload_unified_config() -> UnifiedConfig:
    """Force reload all configurations."""
    global _unified_config
    _unified_config = UnifiedConfig()
    return _unified_config


# Convenience functions
def get_kernel_config(kernel_type: str, hardware: str = "amd") -> dict[str, Any] | None:
    """Get kernel configuration (convenience function)."""
    return get_unified_config().get_kernel(kernel_type, hardware)


def get_tree_config(kernel_type: str) -> dict[str, Any] | None:
    """Get tree configuration (convenience function)."""
    return get_unified_config().get_tree(kernel_type)


def list_kernels(hardware: str = "amd") -> list[str]:
    """List available kernels (convenience function)."""
    return get_unified_config().list_available_kernels(hardware)


def list_trees() -> list[str]:
    """List available trees (convenience function)."""
    return get_unified_config().list_available_trees()
