"""Test generation tools for Cohezion."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.tools.test_generator import TestGenerator as TestGenerator
    from cohezion.tools.test_generator import main as main


__all__ = ["TestGenerator", "main"]

# reconcile 2026-08-27: branch-only re-exports preserved (worktree-virtual-soaring-shamir)
from typing import TYPE_CHECKING, Any
from cohezion.tools.test_generator import CodeTestGenerator, main
from cohezion.tools.test_generator import CodeTestGenerator
