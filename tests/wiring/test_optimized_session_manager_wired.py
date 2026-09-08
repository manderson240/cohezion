"""Discriminating test: `cohezion.compound.CompoundSessionManager` must be the
PRODUCTION session manager from session_manager.py — not a decoy.

History: compound/__init__.py used to re-export optimized_session_manager's
name-colliding CompoundSessionManager while every production consumer
(mcp/compound_server.py, api/streaming.py, agent/unified_harness.py, swarm/*)
imported session_manager's directly — so the package export handed callers a
checkpoint-incompatible class. optimized_session_manager was retired 2026-08-14
(elegant-simplicity audit); this test pins the surviving identity so the decoy
cannot come back.
"""

from __future__ import annotations

import cohezion.compound as compound
import cohezion.compound.session_manager as src


def test_session_manager_reexported_from_compound() -> None:
    assert hasattr(compound, "CompoundSessionManager"), (
        "compound.CompoundSessionManager unreachable — wiring edge missing"
    )
    assert compound.CompoundSessionManager is src.CompoundSessionManager, (
        "package export is not the production session_manager class"
    )


def test_reexport_is_a_class() -> None:
    assert isinstance(compound.CompoundSessionManager, type)
