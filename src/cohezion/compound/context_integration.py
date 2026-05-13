"""Context integration module for unified context system.

Provides traceable, token-efficient context loading for compound executor.
Integrates with .context/ hierarchy and manifest.json traceability.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.compound.context_policy import ContextBudget, ContextPolicy


logger = logging.getLogger(__name__)


class ContextLoadError(Exception):
    """Raised when context loading fails."""

    pass


class ContextCoherenceError(Exception):
    """Raised when context coherence check fails (HIHO threshold)."""

    pass


class ContextManager:
    """Manages unified context loading with traceability.

    Loads core context files from .context/core/ and skill overlays
    from .context/skills/ on demand. Tracks token usage and coherence.

    Attributes:
        manifest_path: Path to traceability manifest.json
        loaded_files: List of currently loaded context files
        token_usage: Current token count
        coherence_state: Current coherence score (0.0-1.0)
    """

    # Class-level TTL'd caches. Each entry is ``(monotonic_timestamp, value)``.
    # Keyed on cwd string for ``_root_cache`` and on absolute resolved path
    # for ``_context_cache``. Bounds staleness to ``CACHE_TTL_SECONDS`` so
    # ``cd``-ing into a different worktree mid-session doesn't return a
    # stale project root indefinitely.
    #
    # **Concurrency:** these caches are NOT thread-safe — they assume the
    # GIL provides atomicity for individual dict get/set, which is only
    # true for CPython simple dict operations. Concurrent writers from
    # multiple threads could double-traverse the filesystem (benign — same
    # value would be cached), but no entry could be partially observed.
    # If used from a free-threaded build (PEP 703) or ported to async
    # tasks holding references across awaits, wrap reads/writes in a
    # ``threading.Lock``. For our compound-executor use case (single
    # event loop, sync helper called from coroutines) this is acceptable.
    CACHE_TTL_SECONDS: float = 60.0

    _root_cache: dict[str, tuple[float, Path]] = {}
    _context_cache: dict[str, tuple[float, Any]] = {}

    @classmethod
    def clear_caches(cls) -> None:
        """Clear class-level caches (root + context). Useful for tests."""
        cls._root_cache.clear()
        cls._context_cache.clear()

    @classmethod
    def _cache_get(
        cls, cache: dict[str, tuple[float, Any]], key: str
    ) -> Any | None:
        """Return cached value if present and fresh, else None.

        Expired entries are evicted on read so the cache cannot grow
        unboundedly with stale keys.
        """
        import time

        entry = cache.get(key)
        if entry is None:
            return None
        ts, value = entry
        if (time.monotonic() - ts) > cls.CACHE_TTL_SECONDS:
            # Expired — evict.
            cache.pop(key, None)
            return None
        return value

    @classmethod
    def _cache_put(
        cls, cache: dict[str, tuple[float, Any]], key: str, value: Any
    ) -> None:
        """Store ``(now, value)`` in cache."""
        import time

        cache[key] = (time.monotonic(), value)

    def __init__(self, project_root: Path | None = None):
        """Initialize context manager.

        Args:
            project_root: Project root directory. Auto-detected if None.
        """
        if project_root is None:
            project_root = self._find_project_root()

        self.project_root = project_root
        self.manifest_path = project_root / ".context" / "traceability" / "manifest.json"
        self.context_dir = project_root / ".context"
        self.loaded_files: list[str] = []
        self.token_usage: int = 0
        self.coherence_state: float = 1.0
        self.manifest: dict[str, Any] | None = None
        self._core_loaded: bool = False

    def _find_project_root(self) -> Path:
        """Find project root by looking for .context directory.

        Cached per-cwd at the class level — first call traverses the
        filesystem, subsequent calls from the same cwd return the cached
        :class:`Path` immediately.

        Returns:
            Path to project root

        Raises:
            ContextLoadError: If project root not found
        """
        cwd = Path.cwd()
        cwd_key = str(cwd)
        cls = type(self)
        cached = cls._cache_get(cls._root_cache, cwd_key)
        if cached is not None:
            return cached

        current = cwd
        while current != current.parent:
            if (current / ".context").exists():
                cls._cache_put(cls._root_cache, cwd_key, current)
                return current
            current = current.parent
        raise ContextLoadError("Project root not found (no .context directory)")

    def load_manifest(self) -> dict[str, Any] | None:
        """Load traceability manifest.

        Returns:
            Manifest dictionary

        Raises:
            ContextLoadError: If manifest not found or invalid
        """
        if self.manifest is not None:
            return self.manifest

        if not self.manifest_path.exists():
            raise ContextLoadError(f"Manifest not found: {self.manifest_path}")

        try:
            with open(self.manifest_path, encoding="utf-8") as f:
                self.manifest = json.load(f)
                logger.debug("Loaded context manifest: %s", self.manifest_path)
                return self.manifest
        except json.JSONDecodeError as e:
            raise ContextLoadError(f"Invalid manifest JSON: {e}") from e

    def load_core_context(self) -> list[dict[str, Any]]:
        """Load all core context files.

        Loads files defined in manifest.core_files if coherence
        threshold is met.

        Returns:
            List of loaded file metadata

        Raises:
            ContextCoherenceError: If coherence below threshold
        """
        if self._core_loaded:
            logger.debug("Core context already loaded")
            return []

        manifest = self.load_manifest()
        core_files = manifest.get("core_files", [])
        loaded = []

        for file_config in core_files:
            file_path = self.context_dir / file_config["path"]
            coherence_threshold = file_config.get("coherence_threshold", 0.5)

            if self.coherence_state < coherence_threshold:
                logger.warning(
                    "Skipping %s: coherence %.2f < threshold %.2f",
                    file_path,
                    self.coherence_state,
                    coherence_threshold,
                )
                raise ContextCoherenceError(
                    f"Coherence {self.coherence_state:.2f} below threshold "
                    f"{coherence_threshold} for {file_path}"
                )

            try:
                content = self._load_file(file_path)
            except ContextLoadError as e:
                # Missing context files are non-fatal — match the executor's
                # "non-blocking helper" pattern (degradation, journey, bioelectric
                # all warn-and-continue). Manifest entries can drift from the
                # filesystem; force the user to fix them via warning, not crash.
                logger.warning("Skipping missing context file: %s (%s)", file_path, e)
                continue

            if content:
                token_budget = file_config.get("token_budget", 0)
                self.token_usage += token_budget
                self.loaded_files.append(str(file_path))
                loaded.append(
                    {
                        "path": str(file_path),
                        "tokens": token_budget,
                        "sources": file_config.get("sources", []),
                    }
                )
                logger.debug("Loaded core context: %s", file_path)

        self._core_loaded = True
        logger.info(
            "Core context loaded: %d files, %d tokens",
            len(loaded),
            self.token_usage,
        )
        return loaded

    def load_skill_context(self, skill_name: str) -> dict[str, Any] | None:
        """Load skill-specific context overlay.

        Args:
            skill_name: Name of the skill to load context for

        Returns:
            Skill context configuration or None if not found
        """
        manifest = self.load_manifest()
        skills = manifest.get("skills", {})
        skill_config = skills.get(skill_name)

        if not skill_config:
            logger.debug("No context found for skill: %s", skill_name)
            return None

        context_file = skill_config.get("context_file")
        if not context_file:
            return None

        context_path = self.context_dir / context_file
        if not context_path.exists():
            logger.warning("Skill context file not found: %s", context_path)
            return None

        # Cache key: absolute resolved path of the YAML file
        cache_key = str(context_path.resolve())
        cls = type(self)
        cached = cls._cache_get(cls._context_cache, cache_key)
        if cached is not None:
            logger.debug("Skill context cache hit: %s", skill_name)
            return cached

        # Load YAML config
        try:
            import yaml

            with open(context_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.debug("Loaded skill context: %s", skill_name)
                if config is not None:
                    cls._cache_put(cls._context_cache, cache_key, config)
                return config
        except ImportError:
            logger.error("PyYAML required for skill context loading")
            return None
        except Exception as e:
            logger.warning("Failed to load skill context: %s", e)
            return None

    def _load_file(self, path: Path) -> str:
        """Load file content.

        Args:
            path: File path

        Returns:
            File content

        Raises:
            ContextLoadError: If file not found
        """
        if not path.exists():
            raise ContextLoadError(f"Context file not found: {path}")

        with open(path, encoding="utf-8") as f:
            return f.read()

    def get_context_summary(self) -> dict[str, Any]:
        """Get current context state summary.

        Returns:
            Dictionary with context state
        """
        return {
            "loaded_files": self.loaded_files,
            "token_usage": self.token_usage,
            "token_budget": 1000,
            "coherence_state": self.coherence_state,
            "core_loaded": self._core_loaded,
        }

    def check_coherence(self, threshold: float = 0.5) -> bool:
        """Check if current coherence meets threshold (HIHO).

        Args:
            threshold: Coherence threshold (default: 0.5)

        Returns:
            True if coherence meets threshold
        """
        return self.coherence_state >= threshold


class CompoundContextMixin:
    """Mixin to add context management to CompoundExecutor.

    Integrates unified context system with compound executor pipeline.
    Loads context at initialization and tracks coherence throughout
    execution lifecycle. Supports optional ContextPolicy for adaptive
    breadth/depth control.
    """

    def __init_context__(self, project_root: Path | None = None):
        """Initialize context manager.

        Construction is tolerant of a missing ``.context`` directory: when
        :class:`ContextManager` cannot locate a project root, a manager
        rooted at ``Path.cwd()`` is created instead. Lazy operations like
        :meth:`ContextManager.load_manifest` will still raise
        :class:`ContextLoadError` when actually invoked without a manifest.

        Args:
            project_root: Project root directory
        """
        try:
            self._context_manager = ContextManager(project_root)
        except ContextLoadError:
            self._context_manager = ContextManager(Path.cwd())
        self._context_loaded = False
        self._active_budget: ContextBudget | None = None
        self._context_policy: ContextPolicy | None = None

    def set_context_policy(self, policy: ContextPolicy) -> None:
        """Attach a ContextPolicy for adaptive context control.

        Args:
            policy: ContextPolicy instance
        """
        self._context_policy = policy

    def apply_policy(
        self,
        task_description: str,
        operation_type: str,
        template_similarity: float = 0.0,
        drift_risk: float = 0.0,
    ) -> ContextBudget | None:
        """Classify task and set active context budget.

        Args:
            task_description: What the task does
            operation_type: Operation type
            template_similarity: Template match score (0-1)
            drift_risk: Drift risk score (0-1)

        Returns:
            Active ContextBudget, or None if no policy attached
        """
        if self._context_policy is None:
            return None

        profile = self._context_policy.classify_task(
            task_description, operation_type, template_similarity, drift_risk
        )
        self._active_budget = self._context_policy.get_budget(profile)
        logger.info(
            "Context policy applied: profile=%s, top_k=%d, tokens=%d",
            profile.value,
            self._active_budget.flux_top_k,
            self._active_budget.token_budget,
        )
        return self._active_budget

    def load_execution_context(self) -> None:
        """Load core context before execution.

        Raises:
            ContextCoherenceError: If coherence below threshold
        """
        if self._context_loaded:
            return

        try:
            self._context_manager.load_core_context()
            self._context_loaded = True
            logger.info("Execution context loaded")
        except ContextCoherenceError as e:
            logger.warning("Context coherence check failed: %s", e)
            raise

    def load_skill_overlay(self, skill_name: str) -> dict[str, Any] | None:
        """Load skill-specific context overlay.

        Skipped if active budget has skill_overlay=False.

        Args:
            skill_name: Name of the skill

        Returns:
            Skill context configuration or None
        """
        if self._active_budget is not None and not self._active_budget.skill_overlay:
            logger.debug("Skill overlay skipped by context policy (budget.skill_overlay=False)")
            return None
        return self._context_manager.load_skill_context(skill_name)

    def get_context_state(self) -> dict[str, Any]:
        """Get current context state for metrics/tracking.

        Returns:
            Context state dictionary including active budget if set
        """
        summary = self._context_manager.get_context_summary()
        if self._active_budget is not None:
            summary["active_budget"] = {
                "flux_top_k": self._active_budget.flux_top_k,
                "flux_min_relevance": self._active_budget.flux_min_relevance,
                "token_budget": self._active_budget.token_budget,
                "skill_overlay": self._active_budget.skill_overlay,
            }
        return summary

    def check_context_coherence(self, threshold: float = 0.5) -> bool:
        """Check context coherence (HIHO threshold).

        Args:
            threshold: Coherence threshold

        Returns:
            True if coherence acceptable
        """
        return self._context_manager.check_coherence(threshold)

    def init_autocontext(self) -> Path | None:
        """Initialize autocontext structure if missing.

        Creates ``.context/traceability/manifest.json`` if it doesn't exist,
        along with the required directory hierarchy. Safe to call multiple
        times — idempotent.

        Returns:
            Path to the manifest file, or None on failure
        """
        try:
            ctx_dir = self._context_manager.project_root / ".context"
            trace_dir = ctx_dir / "traceability"
            policy_dir = ctx_dir / "policy"

            ctx_dir.mkdir(parents=True, exist_ok=True)
            trace_dir.mkdir(parents=True, exist_ok=True)
            policy_dir.mkdir(parents=True, exist_ok=True)

            manifest_path = trace_dir / "manifest.json"
            if not manifest_path.exists():
                default_manifest: dict[str, Any] = {
                    "version": "1.0.0",
                    "created_at": datetime.now().isoformat(),
                    "core_files": [],
                    "skills": {},
                }
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(default_manifest, f, indent=2)
                logger.info("Created autocontext manifest: %s", manifest_path)
            else:
                logger.debug("Autocontext manifest already exists: %s", manifest_path)

            return manifest_path
        except Exception as e:
            logger.warning("Autocontext init failed (non-blocking): %s", e)
            return None

    def archive_session(self, outcome: dict[str, Any] | None = None) -> Path | None:
        """Archive session outcome to ``policy/learned-budgets.md``.

        Appends a YAML-frontmatter markdown entry with the session outcome.
        Safe to call multiple times — always appends.

        Args:
            outcome: Optional session outcome dictionary. If None, records
                a minimal entry.

        Returns:
            Path to the written file, or None on failure
        """
        try:
            policy_dir = self._context_manager.project_root / ".context" / "policy"
            policy_dir.mkdir(parents=True, exist_ok=True)

            budget_path = policy_dir / "learned-budgets.md"
            timestamp = datetime.now().isoformat()

            lines: list[str] = [
                "---",
                f"archived_at: {timestamp}",
            ]
            if outcome:
                for key, value in outcome.items():
                    lines.append(f"{key}: {value}")
            else:
                lines.append("outcome: no_data")
            lines.append("---")
            lines.append("")
            lines.append(f"## Session Archive — {timestamp}")
            lines.append("")
            if outcome:
                for key, value in outcome.items():
                    lines.append(f"- **{key}**: {value}")
            else:
                lines.append("- No outcome data recorded.")
            lines.append("")

            with open(budget_path, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            logger.info("Archived session to %s", budget_path)
            return budget_path
        except Exception as e:
            logger.warning("Session archive failed (non-blocking): %s", e)
            return None