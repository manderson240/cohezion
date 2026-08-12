"""One missing optional sibling must not blackhole the cohezion.agi package.

Before the guard, `agi/__init__` eagerly imported `kaggle_autoharness`, which imports the
absent `cohezion.inference.unified_hybrid_router`. The ImportError propagated out of
`__init__`, so every module in the package -- including `flume_vae`, which loads fine
standalone and never references the router -- was unimportable.

The invariant pinned here is deliberately independent of branch state: `__all__` must
advertise exactly the names that are bound. That stays true whether or not the router is
ever restored, so restoring it will not turn these tests red.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging

import pytest


def test_flume_vae_is_importable_through_the_package() -> None:
    """The regression itself: this raised ModuleNotFoundError before the guard."""
    from cohezion.agi.flume_vae import FLUMEVAE

    assert FLUMEVAE.__name__ == "FLUMEVAE"


def test_sibling_modules_are_importable_through_the_package() -> None:
    """flume_vae is not special -- the whole package was dark."""
    mod = importlib.import_module("cohezion.agi.flume_vae")
    assert hasattr(mod, "FLUMEEncoding")
    assert hasattr(mod, "FLUMEReconstruction")


def test_all_advertises_only_bound_names() -> None:
    """A hardcoded __all__ listing an unbound name makes `import *` raise AttributeError.

    This is the durable invariant: it fails if anyone reverts to a static list, and it
    keeps passing if the missing dependency is later restored.
    """
    agi = importlib.import_module("cohezion.agi")
    missing = [name for name in agi.__all__ if not hasattr(agi, name)]
    assert not missing, f"__all__ advertises unbound names: {missing}"


def test_core_policy_names_survive_a_failing_optional_import() -> None:
    """The guard must not cost the names that DID import."""
    agi = importlib.import_module("cohezion.agi")
    assert hasattr(agi, "AutoHarnessPolicy")
    assert hasattr(agi, "ActionPolicyResult")
    assert "AutoHarnessPolicy" in agi.__all__


def test_star_import_does_not_raise() -> None:
    """Directly exercises what a mismatched __all__ breaks."""
    ns: dict[str, object] = {}
    exec("from cohezion.agi import *", ns)  # noqa: S102 - the behaviour under test
    assert "AutoHarnessPolicy" in ns


@pytest.mark.skipif(
    importlib.util.find_spec("cohezion.inference.unified_hybrid_router") is not None,
    reason="optional dependency present, so there is no failing import to log about",
)
def test_the_guard_is_not_silent(caplog: pytest.LogCaptureFixture) -> None:
    """A silently-swallowed ImportError reads exactly like 'the feature does not exist'.

    That is how a dependency gap becomes a phantom dormancy finding, so the warning is
    part of the contract, not decoration. Fails if the logger call is removed.
    """
    agi = importlib.import_module("cohezion.agi")
    with caplog.at_level(logging.WARNING, logger="cohezion.agi"):
        importlib.reload(agi)
    assert any(
        "kaggle_autoharness" in rec.message for rec in caplog.records
    ), "guard suppressed the ImportError without logging it"
