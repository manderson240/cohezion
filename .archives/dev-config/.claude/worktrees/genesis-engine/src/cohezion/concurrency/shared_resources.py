"""Thread-safe shared resource management for multi-agent coordination.

Provides locked access to shared configuration files:
- skill_registry.json: Catalog of available skills across agents
- capability_usage.json: Track capability usage and performance metrics

Uses ConfigManager for atomic read-modify-write operations.
"""

import logging
from pathlib import Path

from cohezion.concurrency.file_lock import ConfigManager


logger = logging.getLogger(__name__)

SKILL_REGISTRY_PATH = Path(__file__).parent.parent / "skills" / "skill_registry.json"
CAPABILITY_USAGE_PATH = Path(__file__).parent.parent / "skills" / "capability_usage.json"


class SkillRegistry:
    """Thread-safe skill registry for multi-agent access.

    Manages a catalog of skills available to the system. Multiple agents
    can read/write skills concurrently without data corruption.

    Example:
        ```python
        registry = SkillRegistry()
        # Register a new skill
        registry.register_skill("my_skill", {
            "version": "1.0",
            "description": "Does something",
        })
        # Get all skills
        skills = registry.get_all_skills()
        ```
    """

    def __init__(self, filepath: str | None = None):
        """Initialize skill registry.

        Args:
            filepath: Path to skill registry JSON. Defaults to standard location.
        """
        self.filepath = filepath or str(SKILL_REGISTRY_PATH)
        self.manager = ConfigManager(self.filepath, lock_timeout=10.0)
        logger.debug("Initialized SkillRegistry at %s", self.filepath)

    def register_skill(self, skill_name: str, skill_data: dict) -> dict:
        """Register a skill atomically.

        Args:
            skill_name: Name of the skill
            skill_data: Skill metadata (version, description, etc.)

        Returns:
            Updated registry
        """

        def update_fn(data):
            if "skills" not in data:
                data["skills"] = {}
            data["skills"][skill_name] = skill_data
            logger.info("Registered skill: %s", skill_name)
            return data

        return self.manager.atomic_update(update_fn)

    def get_skill(self, skill_name: str) -> dict | None:
        """Get skill metadata.

        Args:
            skill_name: Name of the skill

        Returns:
            Skill metadata or None if not found
        """
        data = self.manager.read()
        return data.get("skills", {}).get(skill_name)

    def get_all_skills(self) -> dict:
        """Get all registered skills.

        Returns:
            Dictionary of skill_name -> skill_data
        """
        data = self.manager.read()
        return data.get("skills", {})

    def update_skill_version(self, skill_name: str, new_version: str) -> dict:
        """Atomically update skill version.

        Args:
            skill_name: Name of the skill
            new_version: New version string

        Returns:
            Updated registry
        """

        def update_fn(data):
            if "skills" in data and skill_name in data["skills"]:
                data["skills"][skill_name]["version"] = new_version
                logger.info("Updated %s version to %s", skill_name, new_version)
            return data

        return self.manager.atomic_update(update_fn)

    def remove_skill(self, skill_name: str) -> dict:
        """Remove a skill from registry.

        Args:
            skill_name: Name of the skill to remove

        Returns:
            Updated registry
        """

        def update_fn(data):
            if "skills" in data and skill_name in data["skills"]:
                del data["skills"][skill_name]
                logger.info("Removed skill: %s", skill_name)
            return data

        return self.manager.atomic_update(update_fn)

    def increment_skill_usage(self, skill_name: str) -> dict:
        """Atomically increment skill usage counter.

        Args:
            skill_name: Name of the skill

        Returns:
            Updated registry
        """

        def update_fn(data):
            if "skills" not in data:
                data["skills"] = {}
            if skill_name not in data["skills"]:
                data["skills"][skill_name] = {"usage_count": 0}
            if "usage_count" not in data["skills"][skill_name]:
                data["skills"][skill_name]["usage_count"] = 0
            data["skills"][skill_name]["usage_count"] += 1
            return data

        return self.manager.atomic_update(update_fn)


class CapabilityUsageTracker:
    """Thread-safe capability usage tracking.

    Tracks how capabilities are used across agents, enabling performance
    monitoring and optimization.

    Example:
        ```python
        tracker = CapabilityUsageTracker()
        # Track operation execution
        tracker.record_operation("generate", tokens_used=250, success=True)
        # Get stats
        stats = tracker.get_operation_stats("generate")
        ```
    """

    def __init__(self, filepath: str | None = None):
        """Initialize capability usage tracker.

        Args:
            filepath: Path to usage JSON. Defaults to standard location.
        """
        self.filepath = filepath or str(CAPABILITY_USAGE_PATH)
        self.manager = ConfigManager(self.filepath, lock_timeout=10.0)
        logger.debug("Initialized CapabilityUsageTracker at %s", self.filepath)

    def record_operation(
        self,
        operation_type: str,
        tokens_used: int | None = None,
        success: bool = True,
        metadata: dict | None = None,
    ) -> dict:
        """Record an operation execution.

        Args:
            operation_type: Type of operation (generate, analyze, search, etc.)
            tokens_used: Number of tokens consumed
            success: Whether operation succeeded
            metadata: Additional metadata

        Returns:
            Updated usage data
        """

        def update_fn(data):
            if "operations" not in data:
                data["operations"] = {}
            if operation_type not in data["operations"]:
                data["operations"][operation_type] = {
                    "count": 0,
                    "success_count": 0,
                    "total_tokens": 0,
                    "avg_tokens": 0.0,
                }

            op_stats = data["operations"][operation_type]
            op_stats["count"] += 1
            if success:
                op_stats["success_count"] += 1

            if tokens_used is not None:
                op_stats["total_tokens"] += tokens_used
                op_stats["avg_tokens"] = op_stats["total_tokens"] / op_stats["count"]

            logger.debug(
                "Recorded operation: %s (success=%s, tokens=%s)",
                operation_type,
                success,
                tokens_used,
            )
            return data

        return self.manager.atomic_update(update_fn)

    def get_operation_stats(self, operation_type: str) -> dict | None:
        """Get statistics for an operation type.

        Args:
            operation_type: Type of operation

        Returns:
            Statistics or None if not found
        """
        data = self.manager.read()
        return data.get("operations", {}).get(operation_type)

    def get_all_stats(self) -> dict:
        """Get all operation statistics.

        Returns:
            All operation stats
        """
        data = self.manager.read()
        return data.get("operations", {})

    def reset_operation_stats(self, operation_type: str) -> dict:
        """Reset statistics for an operation type.

        Args:
            operation_type: Type of operation to reset

        Returns:
            Updated data
        """

        def update_fn(data):
            if "operations" in data and operation_type in data["operations"]:
                del data["operations"][operation_type]
                logger.info("Reset stats for operation: %s", operation_type)
            return data

        return self.manager.atomic_update(update_fn)

    def get_success_rate(self, operation_type: str) -> float:
        """Get success rate for operation type.

        Args:
            operation_type: Type of operation

        Returns:
            Success rate (0.0-1.0), or 0.0 if not found
        """
        stats = self.get_operation_stats(operation_type)
        if not stats or stats["count"] == 0:
            return 0.0
        return stats["success_count"] / stats["count"]

    def get_average_tokens(self, operation_type: str) -> float:
        """Get average tokens used for operation type.

        Args:
            operation_type: Type of operation

        Returns:
            Average tokens, or 0.0 if not found
        """
        stats = self.get_operation_stats(operation_type)
        if not stats:
            return 0.0
        return stats.get("avg_tokens", 0.0)
