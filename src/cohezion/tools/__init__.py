"""Test generation tools for Cohezion."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.tools.test_generator import TestGenerator as TestGenerator
    from cohezion.tools.test_generator import main as main


__all__ = ["TestGenerator", "main"]
