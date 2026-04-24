# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""HookIntegration - Wire Phase 2.1 security hooks into sandbox execution pipeline.

This module provides hook discovery, registration, and execution for sandbox
lifecycle events. Hooks are shell scripts that fire at specific stages
(PRE_EXECUTE, PRE_OPERATION, POST_OPERATION, CLEANUP) and can BLOCK, WARN, or
ALLOW operations based on their exit codes.
"""

import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class HookStage(StrEnum):
    """Lifecycle stages where hooks can execute."""

    PRE_EXECUTE = "pre_execute"
    PRE_OPERATION = "pre_operation"
    POST_OPERATION = "post_operation"
    CLEANUP = "cleanup"


class HookAction(StrEnum):
    """Actions that hooks can request."""

    BLOCK = "block"  # Exit code 1: Block operation
    WARN = "warn"  # Exit code 2: Warn but allow
    ALLOW = "allow"  # Exit code 0: Allow operation


@dataclass
class HookMetadata:
    """Metadata about a hook script."""

    name: str
    stage: HookStage
    action: HookAction
    timeout: int = 10  # Default timeout in seconds
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "stage": self.stage.value,
            "action": self.action.value,
            "timeout": self.timeout,
            "description": self.description,
        }


@dataclass
class Hook:
    """Represents a single hook script."""

    path: Path
    metadata: HookMetadata

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": str(self.path),
            "metadata": self.metadata.to_dict(),
        }


@dataclass
class HookResult:
    """Result of hook execution."""

    hook_name: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    action: HookAction
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hook_name": self.hook_name,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": self.duration,
            "action": self.action.value,
            "timestamp": self.timestamp,
            "error": self.error,
        }


@dataclass
class ExecutionContext:
    """Context passed to hooks during execution."""

    operation: str
    sandbox_id: str
    files_to_modify: list[str] = field(default_factory=list)
    command: str = ""
    edited_file: str = ""
    agent_files: list[str] = field(default_factory=list)
    extra_env: dict[str, str] = field(default_factory=dict)

    def to_env_dict(self) -> dict[str, str]:
        """Convert context to environment variables for hooks."""
        env = {
            "SANDBOX_OPERATION": self.operation,
            "SANDBOX_SANDBOX_ID": self.sandbox_id,
            "SANDBOX_FILES_TO_MODIFY": " ".join(self.files_to_modify),
            "SANDBOX_COMMAND": self.command,
            "SANDBOX_EDITED_FILE": self.edited_file,
            "SANDBOX_AGENT_FILES": ":".join(self.agent_files),
        }
        # Add extra environment variables
        env.update(self.extra_env)
        return env


class HookDiscovery:
    """Discovers and loads hooks from a directory."""

    @staticmethod
    def discover_hooks(hooks_dir: str | Path) -> dict[str, Hook]:
        """Discover all hook scripts in a directory.

        Args:
            hooks_dir: Path to directory containing hook scripts

        Returns:
            Dictionary mapping hook names to Hook objects
        """
        hooks_dir = Path(hooks_dir)
        hooks: dict[str, Hook] = {}

        if not hooks_dir.exists():
            logger.debug(f"Hooks directory does not exist: {hooks_dir}")
            return hooks

        # Find all .sh files in hooks directory
        for hook_file in sorted(hooks_dir.glob("*.sh")):
            try:
                metadata = HookDiscovery._parse_hook_metadata(hook_file)
                if metadata:
                    hook = Hook(path=hook_file, metadata=metadata)
                    hooks[metadata.name] = hook
                    logger.debug(f"Discovered hook: {metadata.name} ({hook_file})")
            except Exception as e:
                logger.warning(f"Failed to parse hook {hook_file}: {e}")

        return hooks

    @staticmethod
    def _parse_hook_metadata(hook_file: Path) -> HookMetadata | None:
        """Parse hook metadata from script comments.

        Expected format:
            # HOOK_NAME: hook-name
            # HOOK_STAGE: PRE_EXECUTE
            # HOOK_ACTION: BLOCK
            # HOOK_TIMEOUT: 10
            # HOOK_DESCRIPTION: Description

        Args:
            hook_file: Path to hook script

        Returns:
            HookMetadata if valid, None otherwise
        """
        try:
            with open(hook_file) as f:
                content = f.read(500)  # Read first 500 bytes for metadata
        except Exception as e:
            logger.error(f"Failed to read hook file {hook_file}: {e}")
            return None

        # Extract metadata from comments
        metadata_dict = {}
        for line in content.split("\n")[:15]:
            match = re.match(r"#\s*HOOK_(\w+):\s*(.+)", line)
            if match:
                key = match.group(1).lower()
                value = match.group(2).strip()
                metadata_dict[key] = value

        # Validate required fields
        if "name" not in metadata_dict or "stage" not in metadata_dict:
            logger.warning(f"Hook {hook_file} missing required metadata")
            return None

        # Parse and validate values
        try:
            name = metadata_dict["name"]
            stage = HookStage(metadata_dict["stage"].lower())
            action = HookAction(metadata_dict.get("action", "allow").lower())
            timeout = int(metadata_dict.get("timeout", "10"))
            description = metadata_dict.get("description", "")

            return HookMetadata(
                name=name,
                stage=stage,
                action=action,
                timeout=timeout,
                description=description,
            )
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid hook metadata in {hook_file}: {e}")
            return None


class HookExecutor:
    """Executes hook scripts with timeout and error handling."""

    @staticmethod
    def execute_hook(
        hook: Hook,
        context: ExecutionContext,
        timeout: int | None = None,
    ) -> HookResult:
        """Execute a hook script.

        Args:
            hook: Hook to execute
            context: Execution context
            timeout: Timeout in seconds (uses hook metadata if not provided)

        Returns:
            HookResult with execution details
        """
        timeout = timeout or hook.metadata.timeout

        # Build environment for hook
        env = context.to_env_dict()

        # Convert hook action based on exit code
        action_map = {
            0: HookAction.ALLOW,
            1: HookAction.BLOCK,
            2: HookAction.WARN,
        }

        start_time = time.time()
        try:
            # Execute hook script
            result = subprocess.run(  # noqa: S603 - hook.path is registered hook script in trusted hook registry
                [str(hook.path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, **env},  # Merge with current environment
                cwd=Path(hook.path).parent,
            )

            duration = time.time() - start_time
            action = action_map.get(result.returncode, HookAction.WARN)

            return HookResult(
                hook_name=hook.metadata.name,
                exit_code=result.returncode,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                duration=duration,
                action=action,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.warning(f"Hook {hook.metadata.name} timed out after {timeout}s")
            return HookResult(
                hook_name=hook.metadata.name,
                exit_code=-1,
                stdout="",
                stderr=f"Hook timed out after {timeout}s",
                duration=duration,
                action=HookAction.WARN,
                error="timeout",
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to execute hook {hook.metadata.name}: {e}")
            return HookResult(
                hook_name=hook.metadata.name,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration=duration,
                action=HookAction.WARN,
                error=str(e),
            )


class HookRegistry:
    """Manages hooks organized by stage."""

    def __init__(self):
        """Initialize hook registry."""
        self.hooks: dict[HookStage, dict[str, Hook]] = {stage: {} for stage in HookStage}

    def register_hook(self, hook: Hook) -> None:
        """Register a hook in the registry.

        Args:
            hook: Hook to register
        """
        self.hooks[hook.metadata.stage][hook.metadata.name] = hook
        logger.debug(f"Registered hook {hook.metadata.name} for stage {hook.metadata.stage.value}")

    def get_hooks_for_stage(self, stage: HookStage) -> list[Hook]:
        """Get all hooks for a specific stage.

        Args:
            stage: Hook stage

        Returns:
            List of hooks for the stage
        """
        return list(self.hooks[stage].values())

    def get_hook(self, stage: HookStage, name: str) -> Hook | None:
        """Get a specific hook.

        Args:
            stage: Hook stage
            name: Hook name

        Returns:
            Hook if found, None otherwise
        """
        return self.hooks[stage].get(name)

    def disable_hook(self, stage: HookStage, name: str) -> bool:
        """Disable a hook by removing it from registry.

        Args:
            stage: Hook stage
            name: Hook name

        Returns:
            True if hook was disabled, False if not found
        """
        if name in self.hooks[stage]:
            del self.hooks[stage][name]
            logger.debug(f"Disabled hook {name} for stage {stage.value}")
            return True
        return False

    def clear_stage(self, stage: HookStage) -> None:
        """Clear all hooks for a stage.

        Args:
            stage: Hook stage
        """
        self.hooks[stage].clear()
        logger.debug(f"Cleared all hooks for stage {stage.value}")

    def to_dict(self) -> dict[str, Any]:
        """Convert registry to dictionary."""
        result = {}
        for stage in HookStage:
            result[stage.value] = {name: hook.to_dict() for name, hook in self.hooks[stage].items()}
        return result


class HookIntegration:
    """Main coordinator for hook discovery, registration, and execution."""

    def __init__(self, hooks_dir: str | Path = ".claude/hooks"):
        """Initialize HookIntegration.

        Args:
            hooks_dir: Path to hooks directory
        """
        self.hooks_dir = Path(hooks_dir)
        self.registry = HookRegistry()
        self.audit_trail: list[HookResult] = []

        # Discover and register hooks
        discovered = HookDiscovery.discover_hooks(self.hooks_dir)
        for hook in discovered.values():
            self.registry.register_hook(hook)

        logger.info(f"HookIntegration initialized with {len(discovered)} hooks")

    def discover_hooks(self, hooks_dir: str | Path) -> dict[str, Hook]:
        """Discover hooks from a directory.

        Args:
            hooks_dir: Path to hooks directory

        Returns:
            Dictionary mapping hook names to Hook objects
        """
        return HookDiscovery.discover_hooks(hooks_dir)

    def register_hook(self, stage: HookStage, hook: Hook) -> None:
        """Register a hook for a specific stage.

        Args:
            stage: Hook stage
            hook: Hook to register
        """
        self.registry.register_hook(hook)

    def execute_hook(
        self,
        hook: Hook,
        context: ExecutionContext,
        timeout: int | None = None,
    ) -> HookResult:
        """Execute a single hook.

        Args:
            hook: Hook to execute
            context: Execution context
            timeout: Timeout in seconds

        Returns:
            HookResult with execution details
        """
        result = HookExecutor.execute_hook(hook, context, timeout)
        self.audit_trail.append(result)

        # Log result
        log_level = logging.WARNING if result.action == HookAction.BLOCK else logging.DEBUG
        logger.log(
            log_level,
            f"Hook {result.hook_name} completed: {result.action.value} (exit_code={result.exit_code})",
        )
        if result.stdout:
            logger.debug(f"Hook stdout: {result.stdout}")
        if result.stderr:
            logger.debug(f"Hook stderr: {result.stderr}")

        return result

    def validate_hooks(
        self,
        stage: HookStage,
        context: ExecutionContext,
    ) -> tuple[bool, list[HookResult]]:
        """Validate all hooks for a stage and return aggregate decision.

        Args:
            stage: Hook stage to validate
            context: Execution context

        Returns:
            Tuple of (allow: bool, results: list[HookResult])
            - allow is False if any hook blocks
            - results is list of all hook execution results
        """
        hooks = self.registry.get_hooks_for_stage(stage)
        results: list[HookResult] = []

        for hook in hooks:
            result = self.execute_hook(hook, context)
            results.append(result)

            # Check for BLOCK action
            if result.action == HookAction.BLOCK:
                logger.warning(f"Hook {hook.metadata.name} blocked operation: {result.stderr}")
                return False, results

        return True, results

    def get_audit_trail(self) -> list[HookResult]:
        """Get the audit trail of all hook executions.

        Returns:
            List of HookResult entries
        """
        return self.audit_trail.copy()

    def clear_audit_trail(self) -> None:
        """Clear the audit trail."""
        self.audit_trail.clear()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "hooks_dir": str(self.hooks_dir),
            "registry": self.registry.to_dict(),
            "audit_trail": [result.to_dict() for result in self.audit_trail],
        }


def get_hook_integration(
    hooks_dir: str | Path = ".claude/hooks",
) -> HookIntegration:
    """Factory function to get or create HookIntegration singleton.

    Args:
        hooks_dir: Path to hooks directory

    Returns:
        HookIntegration instance
    """
    if not hasattr(get_hook_integration, "_instance"):
        get_hook_integration._instance = HookIntegration(hooks_dir)
    return get_hook_integration._instance


__all__ = [
    "ExecutionContext",
    "Hook",
    "HookAction",
    "HookDiscovery",
    "HookExecutor",
    "HookIntegration",
    "HookMetadata",
    "HookRegistry",
    "HookResult",
    "HookStage",
    "get_hook_integration",
]
