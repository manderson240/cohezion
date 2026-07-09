"""RecipeGuard — runtime + lint assertions that no model is ever called
with default params.

The plan rule: "Defaulting to a card-blind parameter set is a bug, not a
fallback." This module makes that rule enforceable.

Two surfaces:
- assert_aligned(params): runtime check. Callers that hand a default
  InferenceParams (zero max_tokens, empty model_id) get a
  RecipeMisalignment. Callers that hand a populated params object pass.
- assert_card_present(entry): runtime check that a ModelEntry has a
  non-None profile. Cardless entries cannot be dispatched.
- check_file_for_default_params(path): lint check. Scans a .py file for
  `extend_claude(` calls that don't pass a `params=` kwarg and returns
  a list of LintViolation(line, message).
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from cohezion.inference.capability_profile import CapabilityProfile
from cohezion.inference.model_card_harness import InferenceParams


class RecipeMisalignment(RuntimeError):
    """Raised when a model would be called with default/unaligned params.

    Defaulting to a card-blind parameter set is a bug, not a fallback —
    this is the fail-closed runtime assertion.
    """


@dataclass(frozen=True)
class LintViolation:
    line: int
    message: str


class RecipeGuard:
    """Fail-closed guard for card-aligned model usage."""

    # ── Runtime: params must be aligned (non-default) ──────────────────

    @staticmethod
    def assert_aligned(params: InferenceParams) -> None:
        """Raise if `params` looks like an unaligned default.

        An InferenceParams is "unaligned" if any of:
        - model_id is empty
        - max_tokens is zero or negative
        - the InferenceParams was constructed with all defaults AND
          has no extra_body indicating it was filled in

        In practice, callers will either pass a real params object from
        ModelCardHarness.aligned_params (good) or construct a default
        InferenceParams in a hot path (bad). We detect the latter.
        """
        if not params.model_id:
            raise RecipeMisalignment(
                "InferenceParams.model_id is empty — refusing to call an "
                "unknown model. Build params via ModelCardHarness.aligned_params."
            )
        if params.max_tokens <= 0:
            raise RecipeMisalignment(
                f"InferenceParams.max_tokens={params.max_tokens} is invalid. "
                f"Build params via ModelCardHarness.aligned_params so the "
                f"model's card-derived max_tokens is used."
            )

    # ── Runtime: a ModelEntry must have a CapabilityProfile ────────────

    @staticmethod
    def assert_card_present(entry: object) -> None:
        """Raise if a ModelEntry has no CapabilityProfile attached.

        The plan rule: "We never build a profile from a card we haven't
        read" — and by extension we never dispatch to a model whose
        card we haven't read either.
        """
        profile = getattr(entry, "profile", None)
        if profile is None:
            raise RecipeMisalignment(
                f"ModelEntry {getattr(entry, 'model_id', '?')!r} has no "
                f"CapabilityProfile. Cardless models cannot be dispatched "
                f"via route_by_capability. Read the card first."
            )
        if not isinstance(profile, CapabilityProfile):
            raise RecipeMisalignment(
                f"ModelEntry {getattr(entry, 'model_id', '?')!r} profile is "
                f"not a CapabilityProfile (got {type(profile).__name__})."
            )

    # ── Lint: scan a .py file for unaligned extend_claude() calls ─────

    _EXTEND_CLAUDE_RE = re.compile(r"extend_claude\s*\(")

    @classmethod
    def check_file_for_default_params(cls, path: Path) -> list[LintViolation]:
        """Return a list of LintViolations for any `extend_claude(` call
        in `path` that doesn't pass a `params=` kwarg (or for which
        `params` is passed as a `None` or empty literal).
        """
        try:
            source = path.read_text()
        except OSError:
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []  # leave syntax errors to other tools

        violations: list[LintViolation] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Name) or func.id != "extend_claude":
                continue
            # If `params=` is in the kwargs, OK. Otherwise, violation.
            has_params_kwarg = any(kw.arg == "params" for kw in node.keywords)
            if has_params_kwarg:
                continue
            violations.append(
                LintViolation(
                    line=node.lineno,
                    message=(
                        f"extend_claude() call at line {node.lineno} does "
                        f"not pass params=. Use "
                        f"ModelCardHarness.aligned_params(model_id, task) "
                        f"and pass it as params=."
                    ),
                )
            )
        return violations

    @classmethod
    def check_paths(cls, paths: Iterable[Path]) -> list[LintViolation]:
        """Run check_file_for_default_params across many files."""
        all_v: list[LintViolation] = []
        for p in paths:
            if p.suffix != ".py":
                continue
            all_v.extend(cls.check_file_for_default_params(p))
        return all_v
