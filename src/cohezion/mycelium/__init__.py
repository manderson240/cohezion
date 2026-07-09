"""Mycelium network: execution pattern capture, registry, observer, and scripter."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.mycelium.loop import CoverageLoop as CoverageLoop

with contextlib.suppress(Exception):
    from cohezion.mycelium.observer import ChangeObserver as ChangeObserver

with contextlib.suppress(Exception):
    from cohezion.mycelium.registry import MyceliumCluster as MyceliumCluster
    from cohezion.mycelium.registry import MyceliumRegistry as MyceliumRegistry

with contextlib.suppress(Exception):
    from cohezion.mycelium.scripter import ShadowScripter as ShadowScripter
