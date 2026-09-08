"""Minimal, torch-free conftest for shootout mutation testing.

mutmut copies this dir into mutants/ and runs pytest against it. We keep a
blank conftest here (no autouse fixtures) so the repo-wide tests/conftest.py
reset_singletons fixture — which pulls the swarm→research→torch import chain
and crashes under mutation — never loads. The shootout tests are
self-contained and mock all external I/O at source.
"""
