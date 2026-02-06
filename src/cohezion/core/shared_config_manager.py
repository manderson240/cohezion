#!/usr/bin/env python3
"""
COHEZION SHARED CONFIGURATION MANAGEMENT SYSTEM v1.1.48

Provides unified configuration management across all IDEs (ZED, Antigravity, OpenCode)
with compound engineering principles and adaptive synchronization.

This system ensures consistency while allowing IDE-specific optimizations.
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ConfigScope(Enum):
    """Configuration scope levels"""

    GLOBAL = "global"  # System-wide defaults
    USER = "user"  # User preferences
    PROJECT = "project"  # Project-specific settings
    IDE = "ide"  # IDE-specific overrides
    RUNTIME = "runtime"  # Dynamic runtime settings


class IDEType(Enum):
    """Supported IDE types"""

    ZED = "zed"
    ANTIGRAVITY = "antigravity"
    OPENCODE = "opencode"
    VSCODE = "vscode"


@dataclass
class ConfigEntry:
    """Configuration entry with metadata"""

    key: str
    value: Any
    scope: ConfigScope
    ide_type: IDEType | None = None
    priority: int = 0
    last_modified: float = 0.0
    description: str = ""
    requires_restart: bool = False


@dataclass
class SyncResult:
    """Result of configuration synchronization"""

    success: bool
    synced_ide: list[IDEType]
    failed_ide: list[IDEType]
    conflicts_resolved: int
    sync_time: float


class SharedConfigManager:
    """Unified configuration management across IDEs"""

    def __init__(self, project_root: str = "/home/mike-anderson/dev/cohezion"):
        self.project_root = Path(project_root)
        self.config_dir = self.project_root / ".ide-config"
        self.config_dir.mkdir(exist_ok=True)

        # Configuration files
        self.global_config_path = self.config_dir / "global.json"
        self.sync_state_path = self.config_dir / "sync_state.json"
        self.performance_metrics_path = self.config_dir / "performance_metrics.json"

        # IDE configuration paths
        self.ide_configs = {
            IDEType.ZED: self.project_root / ".zed",
            IDEType.ANTIGRAVITY: self.project_root / ".antigravity",
            IDEType.OPENCODE: self.project_root / ".opencode",
            IDEType.VSCODE: self.project_root / ".vscode",
        }

        # Configuration storage
        self.config_entries: dict[str, ConfigEntry] = {}
        self.sync_state: dict[str, Any] = {}
        self.performance_metrics: dict[str, Any] = {}

        # Load existing configurations
        self._load_all_configurations()

    def _load_all_configurations(self):
        """Load all configuration files"""
        self._load_global_config()
        self._load_sync_state()
        self._load_performance_metrics()
        self._load_ide_configurations()

    def _load_global_config(self):
        """Load global configuration"""
        if self.global_config_path.exists():
            try:
                with open(self.global_config_path) as f:
                    global_data = json.load(f)
                    for key, entry_data in global_data.items():
                        entry = ConfigEntry(**entry_data)
                        entry.last_modified = entry_data.get(
                            "last_modified", time.time()
                        )
                        self.config_entries[key] = entry
                logger.info(f"Loaded {len(global_data)} global configuration entries")
            except Exception as e:
                logger.error(f"Failed to load global config: {e}")
                self.config_entries = {}

    def _load_sync_state(self):
        """Load synchronization state"""
        if self.sync_state_path.exists():
            try:
                with open(self.sync_state_path) as f:
                    self.sync_state = json.load(f)
                logger.debug("Loaded synchronization state")
            except Exception as e:
                logger.error(f"Failed to load sync state: {e}")
                self.sync_state = {}

    def _load_performance_metrics(self):
        """Load performance metrics"""
        if self.performance_metrics_path.exists():
            try:
                with open(self.performance_metrics_path) as f:
                    self.performance_metrics = json.load(f)
                logger.debug("Loaded performance metrics")
            except Exception as e:
                logger.error(f"Failed to load performance metrics: {e}")
                self.performance_metrics = {}

    def _load_ide_configurations(self):
        """Load IDE-specific configurations"""
        for ide_type, ide_path in self.ide_configs.items():
            if ide_path.exists():
                self._load_ide_config(ide_type, ide_path)

    def _load_ide_config(self, ide_type: IDEType, ide_path: Path):
        """Load specific IDE configuration"""
        config_files = list(ide_path.glob("**/*.json"))

        for config_file in config_files:
            try:
                with open(config_file) as f:
                    ide_data = json.load(f)

                # Extract configuration entries with IDE scope
                for key, value in ide_data.items():
                    if key.startswith("cohezion_"):
                        config_key = (
                            f"{ide_type.value}_{key[10:]}"  # Remove 'cohezion_' prefix
                        )

                        config_entry = ConfigEntry(
                            key=config_key,
                            value=value,
                            scope=ConfigScope.IDE,
                            ide_type=ide_type,
                            priority=1,  # IDE configs have priority over global
                            last_modified=config_file.stat().st_mtime,
                            description=f"IDE-specific config from {config_file.name}",
                        )

                        self.config_entries[config_key] = config_entry

                logger.debug(
                    f"Loaded {len(config_files)} config files for {ide_type.value}"
                )

            except Exception as e:
                logger.error(f"Failed to load IDE config for {ide_type.value}: {e}")

    def set_config(
        self,
        key: str,
        value: Any,
        scope: ConfigScope = ConfigScope.GLOBAL,
        ide_type: IDEType | None = None,
        description: str = "",
        requires_restart: bool = False,
    ):
        """Set a configuration entry"""

        config_entry = ConfigEntry(
            key=key,
            value=value,
            scope=scope,
            ide_type=ide_type,
            priority=self._calculate_priority(scope, ide_type),
            last_modified=time.time(),
            description=description,
            requires_restart=requires_restart,
        )

        self.config_entries[key] = config_entry
        logger.info(
            f"Set config: {key} = {value} (scope: {scope.value}, ide: {ide_type})"
        )

    def get_config(
        self, key: str, ide_type: IDEType | None = None, default: Any = None
    ) -> Any:
        """Get configuration value with IDE-specific resolution"""

        # Find all matching configuration entries
        matching_entries = []

        for entry_key, entry in self.config_entries.items():
            if entry_key == key or entry_key.endswith(f"_{key}"):
                # Check if this entry applies to the requested IDE
                if ide_type is None or entry.ide_type in [None, ide_type]:
                    matching_entries.append(entry)

        # Sort by priority (higher priority wins)
        matching_entries.sort(key=lambda x: x.priority, reverse=True)

        if matching_entries:
            selected_entry = matching_entries[0]
            logger.debug(
                f"Found config {key} = {selected_entry.value} (priority: {selected_entry.priority})"
            )
            return selected_entry.value

        logger.debug(f"Config not found: {key}, returning default: {default}")
        return default

    def _calculate_priority(self, scope: ConfigScope, ide_type: IDEType | None) -> int:
        """Calculate configuration priority"""
        base_priorities = {
            ConfigScope.RUNTIME: 100,
            ConfigScope.IDE: 50,
            ConfigScope.PROJECT: 30,
            ConfigScope.USER: 20,
            ConfigScope.GLOBAL: 10,
        }

        priority = base_priorities.get(scope, 0)

        # Add IDE-specific priority boost
        if ide_type is not None:
            ide_priorities = {
                IDEType.ANTIGRAVITY: 3,  # Highest priority per user preference
                IDEType.ZED: 2,
                IDEType.OPENCODE: 1,
                IDEType.VSCODE: 1,
            }
            priority += ide_priorities.get(ide_type, 0)

        return priority

    async def synchronize_all_ides(self) -> SyncResult:
        """Synchronize configuration across all IDEs"""
        start_time = time.time()

        synced_ide = []
        failed_ide = []
        conflicts_resolved = 0

        logger.info("Starting configuration synchronization across IDEs")

        for ide_type in IDEType:
            try:
                result = await self._synchronize_ide(ide_type)
                if result:
                    synced_ide.append(ide_type)
                    conflicts_resolved += result.get("conflicts_resolved", 0)
                else:
                    failed_ide.append(ide_type)

            except Exception as e:
                logger.error(f"Failed to sync {ide_type.value}: {e}")
                failed_ide.append(ide_type)

        sync_time = time.time() - start_time

        # Update sync state
        self.sync_state["last_sync"] = {
            "timestamp": time.time(),
            "synced_ides": [ide.value for ide in synced_ide],
            "failed_ides": [ide.value for ide in failed_ide],
            "sync_time": sync_time,
            "conflicts_resolved": conflicts_resolved,
        }

        self._save_sync_state()

        sync_result = SyncResult(
            success=len(failed_ide) == 0,
            synced_ide=synced_ide,
            failed_ide=failed_ide,
            conflicts_resolved=conflicts_resolved,
            sync_time=sync_time,
        )

        logger.info(
            f"Sync completed: {len(synced_ide)} IDEs synced, {len(failed_ide)} failed, {conflicts_resolved} conflicts resolved"
        )

        return sync_result

    async def _synchronize_ide(self, ide_type: IDEType) -> dict[str, Any] | None:
        """Synchronize configuration with specific IDE"""
        ide_path = self.ide_configs.get(ide_type)

        if not ide_path or not ide_path.exists():
            logger.debug(f"IDE path does not exist: {ide_path}")
            return None

        try:
            # Get IDE-specific configurations
            ide_configs = self._get_ide_configurations(ide_type)

            # Merge with global configurations
            merged_configs = self._merge_configurations(ide_type, ide_configs)

            # Write to IDE configuration files
            conflicts_resolved = await self._write_ide_config(ide_type, merged_configs)

            return {
                "ide_type": ide_type.value,
                "config_count": len(merged_configs),
                "conflicts_resolved": conflicts_resolved,
            }

        except Exception as e:
            logger.error(f"Error syncing {ide_type.value}: {e}")
            return None

    def _get_ide_configurations(self, ide_type: IDEType) -> dict[str, Any]:
        """Get configurations for specific IDE type"""
        configs = {}

        for key, entry in self.config_entries.items():
            if entry.ide_type in [None, ide_type]:
                # Remove IDE prefix if present
                config_key = key
                if key.startswith(f"{ide_type.value}_"):
                    config_key = key[len(f"{ide_type.value}_") :]

                configs[config_key] = entry.value

        return configs

    def _merge_configurations(
        self, ide_type: IDEType, ide_configs: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge IDE-specific configs with global configs"""

        merged = {}
        conflicts_resolved = 0

        # Add global configurations first
        for key, entry in self.config_entries.items():
            if entry.scope == ConfigScope.GLOBAL:
                merged[key] = entry.value

        # Add/override with IDE-specific configurations
        for key, value in ide_configs.items():
            if key in merged and merged[key] != value:
                logger.info(
                    f"Resolving config conflict for {key}: IDE value {value} overrides global {merged[key]}"
                )
                conflicts_resolved += 1

            merged[key] = value

        # Add compound engineering optimizations
        merged.update(self._get_compound_optimizations(ide_type))

        self.sync_state[f"{ide_type.value}_conflicts_resolved"] = conflicts_resolved

        return merged

    def _get_compound_optimizations(self, ide_type: IDEType) -> dict[str, Any]:
        """Get compound engineering optimizations for IDE"""

        base_optimizations = {
            "cohezion_quantum_routing": True,
            "cohezion_adaptive_templates": True,
            "cohezion_performance_monitoring": True,
            "cohezion_compound_engineering": True,
        }

        # IDE-specific optimizations
        ide_optimizations = {
            IDEType.ZED: {
                "cohezion_thread_allocation": 16,  # 50% of 32 threads
                "cohezion_memory_reserve": 25,  # 25GB for ZED
                "cohezion_preferred_models": [
                    "phi4:latest",
                    "qwen2.5-coder-14b-256k:latest",
                ],
                "cohezion_max_concurrent": 4,
            },
            IDEType.ANTIGRAVITY: {
                "cohezion_thread_allocation": 24,  # 75% of 32 threads (highest priority)
                "cohezion_memory_reserve": 45,  # 45GB for Antigravity
                "cohezion_preferred_models": [
                    "qwen3-coder-next:q8_0",
                    "qwen3-coder-next:latest",
                ],
                "cohezion_max_concurrent": 2,
            },
            IDEType.OPENCODE: {
                "cohezion_thread_allocation": 4,  # 12.5% of 32 threads
                "cohezion_memory_reserve": 15,  # 15GB for OpenCode
                "cohezion_preferred_models": [
                    "qwen2.5-coder-14b-256k:latest",
                    "phi4:latest",
                ],
                "cohezion_max_concurrent": 4,
            },
        }

        optimizations = base_optimizations.copy()
        optimizations.update(ide_optimizations.get(ide_type, {}))

        return optimizations

    async def _write_ide_config(
        self, ide_type: IDEType, configs: dict[str, Any]
    ) -> int:
        """Write configuration to IDE-specific files"""
        conflicts_resolved = 0

        if ide_type == IDEType.ZED:
            conflicts_resolved = await self._write_zed_config(configs)
        elif ide_type == IDEType.ANTIGRAVITY:
            conflicts_resolved = await self._write_antigravity_config(configs)
        elif ide_type == IDEType.OPENCODE:
            conflicts_resolved = await self._write_opencode_config(configs)
        elif ide_type == IDEType.VSCODE:
            conflicts_resolved = await self._write_vscode_config(configs)

        return conflicts_resolved

    async def _write_zed_config(self, configs: dict[str, Any]) -> int:
        """Write ZED configuration"""
        zed_path = self.ide_configs[IDEType.ZED]
        zed_path.mkdir(exist_ok=True)

        settings_file = zed_path / "settings.json"

        # Load existing ZED settings if exists
        existing_settings = {}
        if settings_file.exists():
            with open(settings_file) as f:
                existing_settings = json.load(f)

        # Update with Cohezion configurations
        cohezion_settings = self._extract_cohezion_configs(configs)
        existing_settings.update(cohezion_settings)

        # Write updated settings
        with open(settings_file, "w") as f:
            json.dump(existing_settings, f, indent=2)

        logger.info(
            f"Updated ZED configuration with {len(cohezion_settings)} Cohezion settings"
        )
        return 0  # ZED configs don't typically have conflicts

    async def _write_antigravity_config(self, configs: dict[str, Any]) -> int:
        """Write Antigravity configuration"""
        antigravity_path = self.ide_configs[IDEType.ANTIGRAVITY]
        antigravity_path.mkdir(exist_ok=True)

        config_file = antigravity_path / "config.yml"

        # Convert to YAML format for Antigravity
        yaml_content = self._convert_to_yaml(configs)

        with open(config_file, "w") as f:
            f.write(yaml_content)

        logger.info("Updated Antigravity configuration")
        return 0

    async def _write_opencode_config(self, configs: dict[str, Any]) -> int:
        """Write OpenCode configuration"""
        opencode_path = self.ide_configs[IDEType.OPENCODE]
        opencode_path.mkdir(exist_ok=True)

        config_file = opencode_path / "config.json"

        # Extract Cohezion-specific configurations
        cohezion_configs = self._extract_cohezion_configs(configs)

        # Load existing OpenCode config if exists
        existing_config = {}
        if config_file.exists():
            with open(config_file) as f:
                existing_config = json.load(f)

        # Merge configurations
        existing_config.update(cohezion_configs)

        with open(config_file, "w") as f:
            json.dump(existing_config, f, indent=2)

        logger.info("Updated OpenCode configuration")
        return 0

    async def _write_vscode_config(self, configs: dict[str, Any]) -> int:
        """Write VSCode configuration"""
        vscode_path = self.ide_configs[IDEType.VSCODE]
        vscode_path.mkdir(exist_ok=True)

        settings_file = vscode_path / "settings.json"

        # Load existing VSCode settings
        existing_settings = {}
        if settings_file.exists():
            with open(settings_file) as f:
                existing_settings = json.load(f)

        # Update with Cohezion configurations
        cohezion_settings = self._extract_cohezion_configs(configs)
        existing_settings.update(cohezion_settings)

        with open(settings_file, "w") as f:
            json.dump(existing_settings, f, indent=2)

        logger.info("Updated VSCode configuration")
        return 0

    def _extract_cohezion_configs(self, configs: dict[str, Any]) -> dict[str, Any]:
        """Extract Cohezion-specific configurations"""
        return {k: v for k, v in configs.items() if k.startswith("cohezion_")}

    def _convert_to_yaml(self, configs: dict[str, Any]) -> str:
        """Convert configurations to YAML format"""
        yaml_lines = ["# COHEZION Antigravity Configuration v1.1.48", ""]

        for key, value in configs.items():
            if isinstance(value, bool):
                yaml_lines.append(f"{key}: {'true' if value else 'false'}")
            elif isinstance(value, list):
                yaml_lines.append(f"{key}:")
                for item in value:
                    yaml_lines.append(f"  - {item}")
            elif isinstance(value, dict):
                yaml_lines.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    yaml_lines.append(f"  {sub_key}: {sub_value}")
            else:
                yaml_lines.append(f"{key}: {value}")

        return "\n".join(yaml_lines)

    def _save_global_config(self):
        """Save global configuration"""
        global_data = {}

        for key, entry in self.config_entries.items():
            if entry.scope == ConfigScope.GLOBAL:
                global_data[key] = asdict(entry)

        with open(self.global_config_path, "w") as f:
            json.dump(global_data, f, indent=2)

        logger.info(f"Saved {len(global_data)} global configuration entries")

    def _save_sync_state(self):
        """Save synchronization state"""
        with open(self.sync_state_path, "w") as f:
            json.dump(self.sync_state, f, indent=2)

    def _save_performance_metrics(self):
        """Save performance metrics"""
        with open(self.performance_metrics_path, "w") as f:
            json.dump(self.performance_metrics, f, indent=2)

    def record_performance_metric(
        self, ide_type: IDEType, metric_name: str, value: float
    ):
        """Record performance metric for analysis"""

        if ide_type.value not in self.performance_metrics:
            self.performance_metrics[ide_type.value] = {}

        if metric_name not in self.performance_metrics[ide_type.value]:
            self.performance_metrics[ide_type.value][metric_name] = []

        # Add metric with timestamp
        metric_record = {"value": value, "timestamp": time.time()}

        self.performance_metrics[ide_type.value][metric_name].append(metric_record)

        # Keep only last 1000 records per metric
        if len(self.performance_metrics[ide_type.value][metric_name]) > 1000:
            self.performance_metrics[ide_type.value][metric_name] = (
                self.performance_metrics[ide_type.value][metric_name][-1000:]
            )

        logger.debug(f"Recorded metric {metric_name}={value} for {ide_type.value}")

    def get_performance_summary(
        self, ide_type: IDEType | None = None
    ) -> dict[str, Any]:
        """Get performance summary for IDE(s)"""

        if ide_type:
            return self.performance_metrics.get(ide_type.value, {})

        return self.performance_metrics

    async def continuous_sync_daemon(self, sync_interval: int = 300):  # 5 minutes
        """Run continuous synchronization daemon"""

        logger.info(f"Starting continuous sync daemon (interval: {sync_interval}s)")

        while True:
            try:
                sync_result = await self.synchronize_all_ides()

                if not sync_result.success:
                    logger.warning(f"Sync failed: {sync_result.failed_ide}")

                await asyncio.sleep(sync_interval)

            except Exception as e:
                logger.error(f"Sync daemon error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    def save_all_configurations(self):
        """Save all configurations to disk"""
        self._save_global_config()
        self._save_sync_state()
        self._save_performance_metrics()

        logger.info("All configurations saved")


# Initialize global config manager
config_manager = SharedConfigManager()

if __name__ == "__main__":
    # Test configuration management
    async def test_config_manager():
        # Set some test configurations
        config_manager.set_config(
            "quantum_routing_enabled", True, description="Enable quantum-aware routing"
        )

        config_manager.set_config(
            "preferred_model",
            "qwen2.5-coder-14b-256k:latest",
            ide_type=IDEType.ZED,
            description="Preferred model for ZED",
        )

        config_manager.set_config(
            "memory_budget",
            45,
            ide_type=IDEType.OPENCODE,
            description="Memory budget for OpenCode in GB",
        )

        # Test retrieval
        print(
            "ZED preferred model:",
            config_manager.get_config("preferred_model", IDEType.ZED),
        )
        print(
            "OpenCode memory budget:",
            config_manager.get_config("memory_budget", IDEType.OPENCODE),
        )
        print("Quantum routing:", config_manager.get_config("quantum_routing_enabled"))

        # Test synchronization
        sync_result = await config_manager.synchronize_all_ides()
        print(f"Sync result: {sync_result}")

        # Save configurations
        config_manager.save_all_configurations()

    asyncio.run(test_config_manager())
