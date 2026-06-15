"""Lemonade loop recipe registry — custom Omni model recipes for the improvement loop.

Defines the loop's model catalog per task category and registers each recipe in
Lemonade with safe OOM-bounded settings (ctx_size=16384, save_options=true).
This is the single source of truth for which model runs which task type.

N3 compliance: all heavy models (≥26B) are registered with ctx_size=16384 via
`POST :13305/api/v1/load {save_options:true}`. recipe_options.ctx_size is
authoritative over user_models.json, so this permanently bounds the KV cache.

See harness.md §N3 for the full OOM incident analysis.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass


logger = logging.getLogger(__name__)

# Safe KV-cache ceiling for any heavy model on Strix Halo (128 GiB unified).
# N3: ctx_size=0 → full trained context → unbounded KV → OOM hang.
SAFE_CTX_SIZE = 16384

# Fast-path ctx for small models where the full KV budget is affordable.
SMALL_CTX_SIZE = 32768


@dataclass(frozen=True)
class LoopRecipe:
    """One Lemonade model recipe for the improvement loop.

    Attributes:
        model_name: Lemonade catalog id (must match /v1/models exactly).
        ctx_size: KV-cache ceiling. Always 16384 for heavy (≥26B) models.
        task_categories: Task categories that prefer this model.
        system_role: One-line BMAD-style persona injected as system message
            (improves structured output on smaller models).
        heavy: Whether this is a heavy model requiring the N3 RAM guard.
        llamacpp_backend: Optional backend hint for GGUF models.
    """

    model_name: str
    ctx_size: int
    task_categories: tuple[str, ...]
    system_role: str
    heavy: bool = True
    llamacpp_backend: str = ""


# ── Recipe catalog ─────────────────────────────────────────────────────────
# Each recipe maps to one or more task categories. Categories not explicitly
# listed fall through to OMNI_PLANNER (the quality-default catch-all).
#
# Selection priority (in _select_model):
#   1. Task-specific recipe, if the model is loaded
#   2. OMNI_PLANNER (Qwen3.6-35B-A3B-MTP-GGUF), if loaded
#   3. FAST_FALLBACK (Gemma-4-E4B), always fits in 5 GB — last resort

OMNI_PLANNER = LoopRecipe(
    model_name="Qwen3.6-35B-A3B-MTP-GGUF",
    ctx_size=SAFE_CTX_SIZE,
    task_categories=("type_fix", "refactor", "feature", "analysis"),
    system_role=(
        "You are a senior Python engineer specialising in static analysis, "
        "type systems, and architectural refactoring. You reason step-by-step "
        "before writing code. You are surgical — you change only what the task requires."
    ),
    heavy=True,
    llamacpp_backend="cuda",  # Strix Halo iGPU via ROCm/llamacpp
)

TEST_SPECIALIST = LoopRecipe(
    model_name="Qwen3.6-35B-A3B-MTP-GGUF",
    ctx_size=SAFE_CTX_SIZE,
    task_categories=("test_fix",),
    system_role=(
        "You are a Python test-fix specialist. You diagnose pytest collection "
        "errors, import failures, and fixture issues. You produce minimal, "
        "surgical fixes — never rewrite tests from scratch when a one-line "
        "fix will do."
    ),
    heavy=True,
    llamacpp_backend="cuda",
)

FAST_LINTER = LoopRecipe(
    model_name="Gemma-4-E4B-it-GGUF",
    ctx_size=SMALL_CTX_SIZE,
    task_categories=("lint_fix",),
    system_role=(
        "You are a Python linting specialist. You fix ruff and flake8 violations "
        "with single-line changes. You NEVER restructure or rename — only the "
        "minimum edit to silence the linter."
    ),
    heavy=False,
    llamacpp_backend="",
)

# Ordered: first match wins when a category appears in multiple recipes.
ALL_RECIPES: tuple[LoopRecipe, ...] = (
    FAST_LINTER,  # lint_fix → Gemma-4-E4B (fast, always fits)
    TEST_SPECIALIST,  # test_fix → Qwen3.6-35B-A3B-MTP with test persona
    OMNI_PLANNER,  # type_fix, refactor, feature, analysis → Omni planner
)

# Stable fallback — 5 GB, always fits, never OOMs.
FAST_FALLBACK_MODEL = FAST_LINTER.model_name
# Primary quality model — 35B Omni planner.
OMNI_PLANNER_MODEL = OMNI_PLANNER.model_name


# ── Registry class ─────────────────────────────────────────────────────────


class LemonadeLoopRecipes:
    """Register and query custom loop recipes in Lemonade.

    Calling `register_all()` at executor startup ensures Lemonade knows
    each recipe with OOM-safe settings. Non-blocking — any error is
    logged and skipped so the executor can still run.
    """

    def __init__(self, base_url: str = "http://localhost:13305") -> None:
        self._base_url = base_url.rstrip("/")
        self._registered: set[str] = set()
        self._available: set[str] = set()

    def refresh_available(self) -> None:
        """Query Lemonade /v1/models to discover what's currently loaded."""
        try:
            req = urllib.request.Request(f"{self._base_url}/v1/models", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                self._available = {m.get("id", "") for m in data.get("data", [])}
        except Exception as exc:
            logger.debug("Could not refresh available models: %s", exc)

    def register_all(self) -> int:
        """Register all loop recipes in Lemonade with safe ctx_size.

        Posts to /api/v1/load with save_options=true so recipe_options.ctx_size
        is written to the Lemonade model registry (N3 compliance).

        Returns the number of recipes successfully registered.
        """
        ok = 0
        seen: set[str] = set()
        for recipe in ALL_RECIPES:
            if recipe.model_name in seen:
                continue
            seen.add(recipe.model_name)
            if self._register_one(recipe):
                ok += 1
        logger.info(
            "LemonadeLoopRecipes: registered %d/%d recipes at %s",
            ok,
            len(seen),
            self._base_url,
        )
        return ok

    def _register_one(self, recipe: LoopRecipe) -> bool:
        """Register a single recipe. Returns True on success."""
        payload: dict = {
            "model_name": recipe.model_name,
            "ctx_size": recipe.ctx_size,
            "save_options": True,
        }
        if recipe.llamacpp_backend:
            payload["llamacpp_backend"] = recipe.llamacpp_backend

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self._base_url}/api/v1/load",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read())
                if body.get("status") == "error":
                    logger.warning(
                        "Lemonade rejected recipe for %s: %s",
                        recipe.model_name,
                        body.get("message", "unknown"),
                    )
                    return False
            self._registered.add(recipe.model_name)
            logger.info(
                "Registered loop recipe: %s (ctx_size=%d, save_options=true)",
                recipe.model_name,
                recipe.ctx_size,
            )
            return True
        except urllib.error.HTTPError as exc:
            # 404 = model not in catalog (not downloaded yet) — skip gracefully
            logger.debug(
                "Recipe registration for %s returned HTTP %d — model may not be downloaded",
                recipe.model_name,
                exc.code,
            )
            return False
        except Exception as exc:
            logger.debug("Recipe registration for %s failed: %s", recipe.model_name, exc)
            return False

    def model_for_category(
        self,
        category: str,
        available_models: list[str] | None = None,
    ) -> tuple[str, str]:
        """Return (model_name, system_role) for a task category.

        Walks ALL_RECIPES in priority order (fast models first), returns
        the first recipe whose model is available. Falls back to OMNI_PLANNER
        then FAST_FALLBACK regardless of availability.

        Args:
            category: Task category string ("lint_fix", "test_fix", etc.)
            available_models: Current /v1/models snapshot. If None, uses last
                refresh (or allows any model through).

        Returns:
            (model_name, system_role) — always a non-empty tuple.
        """
        avail = set(available_models) if available_models is not None else None

        for recipe in ALL_RECIPES:
            if category not in recipe.task_categories:
                continue
            if avail is None or recipe.model_name in avail:
                return recipe.model_name, recipe.system_role

        # Category not explicitly mapped — use Omni planner if available
        if avail is None or OMNI_PLANNER_MODEL in avail:
            return OMNI_PLANNER_MODEL, OMNI_PLANNER.system_role

        # Last resort: Gemma-4-E4B always fits
        return FAST_FALLBACK_MODEL, FAST_LINTER.system_role
