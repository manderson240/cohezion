"""Autoresearch driver base classes for compound experiment loops."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.swarm.autoresearch.base import ExperimentResult as ExperimentResult
    from cohezion.swarm.autoresearch.base import ResearchDriver as ResearchDriver
