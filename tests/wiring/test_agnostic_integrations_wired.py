"""Discriminating test for the wiring-sweep edge: platform → agnostic_integrations (2026-06-06).

`agnostic_integrations` was a genuine Class-A orphan in platform/ — zero static importers
anywhere (src, tests, registry, entry-points), cycle-safe (no module-scope swarm/compound
import). Wired non-destructively via a `cohezion.platform` __init__ re-export. This test fails
if the static edge is removed: it asserts the public surface resolves FROM the package AND is
the source module's own objects (a stale/duplicate symbol would fail the identity check).
"""

from __future__ import annotations

import cohezion.platform as platform
import cohezion.platform.agnostic_integrations as src


_PUBLIC = (
    "IDEIntegrationAdapter",
    "AntigravityIDEAdapter",
    "ClaudeCodeAdapter",
    "ZedCodeAdapter",
    "AgnosticExecutionBroker",
)


def test_agnostic_integrations_reexported_from_platform() -> None:
    for name in _PUBLIC:
        assert hasattr(platform, name), f"platform.{name} unreachable — wiring edge missing"
        assert getattr(platform, name) is getattr(src, name), f"{name} is not the source object"


def test_broker_is_constructible_via_package_surface() -> None:
    # The wired symbol must be the real class, not a shadow — instantiating proves it.
    broker = platform.AgnosticExecutionBroker()
    assert broker is not None
