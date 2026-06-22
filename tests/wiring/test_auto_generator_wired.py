"""Discriminating test for the wiring-sweep edge: environments → auto_generator (2026-06-06).

`auto_generator` was a genuine production orphan in environments/ — its
EnvironmentGenerator / EnvironmentSpec / GeneratedEnvironment / GeneratedCodeValidator
(specification-driven environment synthesis) had ZERO importers anywhere (src, tests,
registry, entry-points). Wired non-destructively via a guarded `cohezion.environments`
__init__ re-export (cycle-safe; the guard also tolerates transformers/torch being absent
since the module imports them at module scope).

Falsifiable: this test fails if the static edge is removed — the names must resolve FROM the
package AND be the source module's own objects (identity), not lookalikes. A wrong impl that
forgot the re-export, or re-exported a different object, fails.
"""

from __future__ import annotations

import pytest


def test_auto_generator_reexported_from_environments() -> None:
    pytest.importorskip(
        "transformers"
    )  # module imports transformers at scope; skip cleanly if absent
    pytest.importorskip("torch")
    import cohezion.environments as environments
    import cohezion.environments.auto_generator as src

    for name in (
        "EnvironmentGenerator",
        "EnvironmentSpec",
        "GeneratedEnvironment",
        "GeneratedCodeValidator",
    ):
        assert hasattr(environments, name), f"environments.{name} unreachable — wiring edge missing"
        assert getattr(environments, name) is getattr(src, name), f"{name} is not the source object"
        assert name in environments.__all__, f"{name} missing from environments.__all__"
